"""
metrics.py
----------
Evaluation metrics for the Text-to-SQL agent.

Metrics implemented:
  1. Execution Accuracy (EX)         — Did the query execute without error?
  2. Exact Match Accuracy (EM)        — Does generated SQL == ground truth SQL?
  3. Result Set Match (RSM)           — Do the result sets match?
  4. Execution Match Rate             — What % of questions got a successful answer?
  5. Self-Correction Rate (SCR)       — How often did correction help?
  6. Average Latency                  — Mean seconds per question
  7. Component Scores (table/join/etc) — Fine-grained per-component accuracy
"""

import re
import json
from typing import Optional


# ─────────────────────────────────────────────
# 1. Execution Accuracy (EX)
# ─────────────────────────────────────────────

def execution_accuracy(results: list[dict]) -> float:
    """
    Fraction of questions where the generated SQL executed without error.
    
    Args:
        results: List of evaluation result dicts, each with 'success' bool
    
    Returns:
        Float 0.0–1.0
    """
    if not results:
        return 0.0
    return sum(1 for r in results if r.get("success", False)) / len(results)


# ─────────────────────────────────────────────
# 2. Exact Match (EM)
# ─────────────────────────────────────────────

def normalize_sql(sql: str) -> str:
    """
    Normalize SQL for comparison:
    - Lowercase
    - Collapse whitespace
    - Remove trailing semicolons
    """
    sql = sql.lower().strip()
    sql = re.sub(r"\s+", " ", sql)
    sql = sql.rstrip(";")
    return sql


def exact_match(generated_sql: str, reference_sql: str) -> bool:
    """
    Returns True if normalized generated SQL matches normalized reference SQL.
    Note: EM is very strict and often low for correct but differently-phrased queries.
    """
    return normalize_sql(generated_sql) == normalize_sql(reference_sql)


def exact_match_accuracy(results: list[dict]) -> float:
    """
    Fraction of questions where the generated SQL exactly matches the reference.
    """
    if not results:
        return 0.0
    matches = sum(
        1 for r in results
        if exact_match(r.get("generated_sql", ""), r.get("ground_truth_sql", ""))
    )
    return matches / len(results)


# ─────────────────────────────────────────────
# 3. Result Set Match (RSM)
# ─────────────────────────────────────────────

def normalize_result_set(rows: list[dict]) -> set[tuple]:
    """
    Convert result rows to a frozenset of sorted tuples for comparison.
    Values are converted to strings for type-safe comparison.
    """
    normalized = set()
    for row in rows:
        t = tuple(sorted((k, str(v)) for k, v in row.items()))
        normalized.add(t)
    return normalized


def result_set_match(
    generated_rows: list[dict],
    reference_rows: list[dict]
) -> bool:
    """
    Returns True if both result sets contain the same data
    (order-independent comparison).
    """
    return normalize_result_set(generated_rows) == normalize_result_set(reference_rows)


def result_set_accuracy(results: list[dict]) -> float:
    """
    Fraction of questions where the result sets match exactly.
    Requires both 'generated_rows' and 'reference_rows' in result dicts.
    """
    if not results:
        return 0.0
    
    scoreable = [
        r for r in results
        if "generated_rows" in r and "reference_rows" in r
        and r["generated_rows"] is not None
        and r["reference_rows"] is not None
    ]
    
    if not scoreable:
        return 0.0
    
    matches = sum(
        1 for r in scoreable
        if result_set_match(r["generated_rows"], r["reference_rows"])
    )
    return matches / len(scoreable)


# ─────────────────────────────────────────────
# 4. Self-Correction Metrics
# ─────────────────────────────────────────────

def self_correction_success_rate(results: list[dict]) -> float:
    """
    Of queries that initially failed but eventually succeeded (via retries),
    what fraction were recovered through self-correction?
    
    Returns the fraction of ALL queries that needed and succeeded via correction.
    """
    if not results:
        return 0.0
    
    corrected = sum(
        1 for r in results
        if r.get("success", False) and r.get("attempts", 1) > 1
    )
    return corrected / len(results)


def average_attempts(results: list[dict]) -> float:
    """Average number of LLM calls per question (including corrections)."""
    if not results:
        return 0.0
    return sum(r.get("attempts", 1) for r in results) / len(results)


def first_attempt_success_rate(results: list[dict]) -> float:
    """Fraction of questions answered correctly on the FIRST attempt."""
    if not results:
        return 0.0
    return sum(
        1 for r in results
        if r.get("success", False) and r.get("attempts", 1) == 1
    ) / len(results)


# ─────────────────────────────────────────────
# 5. Latency metrics
# ─────────────────────────────────────────────

def average_latency(results: list[dict]) -> float:
    """Average latency in seconds per question."""
    latencies = [r.get("latency_s", 0) for r in results if "latency_s" in r]
    return sum(latencies) / len(latencies) if latencies else 0.0


# ─────────────────────────────────────────────
# 6. Per-difficulty breakdown
# ─────────────────────────────────────────────

def accuracy_by_difficulty(results: list[dict]) -> dict:
    """
    Break down execution accuracy by question difficulty.
    
    Returns dict like: {'easy': 0.9, 'medium': 0.7, 'hard': 0.5}
    """
    by_difficulty: dict[str, list] = {}
    for r in results:
        diff = r.get("difficulty", "unknown")
        by_difficulty.setdefault(diff, []).append(r.get("success", False))
    
    return {
        diff: sum(successes) / len(successes)
        for diff, successes in by_difficulty.items()
    }


# ─────────────────────────────────────────────
# 7. Full metrics report
# ─────────────────────────────────────────────

def compute_all_metrics(results: list[dict]) -> dict:
    """
    Compute all available metrics and return as a single dict.
    
    Input results should have these keys (where available):
      - success (bool)
      - attempts (int)
      - latency_s (float)
      - generated_sql (str)
      - ground_truth_sql (str)
      - generated_rows (list[dict])
      - reference_rows (list[dict])
      - difficulty (str)
    """
    metrics = {
        "total_questions":          len(results),
        "execution_accuracy":       round(execution_accuracy(results), 4),
        "exact_match_accuracy":     round(exact_match_accuracy(results), 4),
        "result_set_accuracy":      round(result_set_accuracy(results), 4),
        "first_attempt_success":    round(first_attempt_success_rate(results), 4),
        "self_correction_rate":     round(self_correction_success_rate(results), 4),
        "average_attempts":         round(average_attempts(results), 2),
        "average_latency_s":        round(average_latency(results), 2),
        "accuracy_by_difficulty":   accuracy_by_difficulty(results),
        "failed_questions": [
            r.get("question", "") for r in results if not r.get("success", False)
        ],
    }
    return metrics
