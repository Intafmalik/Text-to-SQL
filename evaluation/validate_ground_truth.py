"""
Validate benchmark ground-truth SQL queries against PostgreSQL.

This script intentionally uses the local `psql` command instead of project
Python dependencies, so it can run even before the app environment is installed.
It writes a compact JSON result file with execution status, row counts, and
sample rows for Task 1 verification.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "benchmark" / "questions.json"
OUTPUT_PATH = ROOT / "evaluation" / "ground_truth_validation.json"


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.split("#", 1)[0].strip().strip("'\"")
        os.environ.setdefault(key, value)


def psql_base_command() -> list[str]:
    load_dotenv(ROOT / ".env")

    env = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": os.getenv("DB_PORT", "5432"),
        "dbname": os.getenv("DB_NAME", "classicmodels"),
        "user": os.getenv("DB_USER", "classicuser"),
    }

    return [
        "psql",
        "-X",
        "-q",
        "-v",
        "ON_ERROR_STOP=1",
        "-h",
        env["host"],
        "-p",
        env["port"],
        "-U",
        env["user"],
        "-d",
        env["dbname"],
    ]


def run_psql(sql: str, *, csv_output: bool = False) -> subprocess.CompletedProcess[str]:
    command = psql_base_command()
    if csv_output:
        command.append("--csv")

    command.extend(["-c", sql])

    env = os.environ.copy()
    env["PGPASSWORD"] = os.getenv("DB_PASSWORD", "classicpass")

    return subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def clean_sql(sql: str) -> str:
    return sql.strip().rstrip(";")


def count_rows(sql: str) -> int:
    wrapped = f"SELECT COUNT(*) AS row_count FROM ({clean_sql(sql)}) AS benchmark_query;"
    result = run_psql(wrapped)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    for line in lines:
        if line.isdigit():
            return int(line)

    raise RuntimeError(f"Could not parse row count output: {result.stdout!r}")


def sample_rows(sql: str, limit: int = 5) -> list[dict[str, str]]:
    wrapped = f"SELECT * FROM ({clean_sql(sql)}) AS benchmark_query LIMIT {limit};"
    result = run_psql(wrapped, csv_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())

    reader = csv.DictReader(io.StringIO(result.stdout))
    return [dict(row) for row in reader]


def main() -> int:
    questions = json.loads(BENCHMARK_PATH.read_text())
    results = []

    for item in questions:
        try:
            rows = count_rows(item["ground_truth_sql"])
            sample = sample_rows(item["ground_truth_sql"])
            results.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "status": "passed",
                    "row_count": rows,
                    "sample_rows": sample,
                    "error": "",
                }
            )
            print(f"PASS Q{item['id']:02d}: {item['question']} ({rows} rows)")
        except Exception as exc:
            results.append(
                {
                    "id": item["id"],
                    "question": item["question"],
                    "status": "failed",
                    "row_count": None,
                    "sample_rows": [],
                    "error": str(exc),
                }
            )
            print(f"FAIL Q{item['id']:02d}: {item['question']} - {exc}")

    summary = {
        "total_questions": len(results),
        "passed": sum(1 for result in results if result["status"] == "passed"),
        "failed": sum(1 for result in results if result["status"] == "failed"),
    }

    OUTPUT_PATH.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(f"\nSaved validation output to {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Passed: {summary['passed']}/{summary['total_questions']}")

    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
