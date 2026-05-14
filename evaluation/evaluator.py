"""
evaluator.py
------------
Runs the full evaluation pipeline on the benchmark dataset.

Usage:
    python evaluation/evaluator.py

This will:
1. Load benchmark questions from benchmark/questions.json
2. Run each question through the Text-to-SQL agent
3. Compare against ground truth (where executable)
4. Print and save a full evaluation report
"""

import json
import time
import os
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.self_correct import run_with_self_correction
from app.database import execute_query
from evaluation.metrics import compute_all_metrics, result_set_match
from evaluation.report import generate_report

console = Console()


# ─────────────────────────────────────────────
# Load benchmark
# ─────────────────────────────────────────────

def load_benchmark(path: str = "benchmark/questions.json") -> list[dict]:
    """Load the benchmark questions JSON file."""
    with open(path, "r") as f:
        return json.load(f)


# ─────────────────────────────────────────────
# Run ground truth query
# ─────────────────────────────────────────────

def run_ground_truth(sql: str) -> tuple[list[dict], str]:
    """
    Execute the ground truth SQL and return (rows, error).
    Returns ([], error_string) if execution fails.
    """
    # Remove trailing semicolons for SQLAlchemy
    sql_clean = sql.strip().rstrip(";")
    try:
        rows = execute_query(sql_clean)
        return rows, ""
    except Exception as e:
        return [], str(e)


# ─────────────────────────────────────────────
# Main evaluation loop
# ─────────────────────────────────────────────

def run_evaluation(
    benchmark_path: str = "benchmark/questions.json",
    max_questions: int = None,
    verbose: bool = False,
) -> list[dict]:
    """
    Run evaluation on all (or max_questions) benchmark questions.
    Returns a list of result dicts for metrics computation.
    """
    questions = load_benchmark(benchmark_path)
    if max_questions:
        questions = questions[:max_questions]
    
    console.print(Panel(
        f"[bold]Running evaluation on {len(questions)} questions[/bold]",
        style="cyan"
    ))
    
    all_results = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        
        task = progress.add_task("Evaluating...", total=len(questions))
        
        for q in questions:
            question_id   = q["id"]
            question_text = q["question"]
            ground_truth  = q["ground_truth_sql"]
            difficulty    = q.get("difficulty", "unknown")
            
            progress.update(
                task,
                description=f"Q{question_id}: {question_text[:50]}..."
            )
            
            start = time.time()
            
            # ── Run agent ──
            agent_result = run_with_self_correction(question_text, verbose=verbose)
            
            # ── Run ground truth ──
            gt_rows, gt_error = run_ground_truth(ground_truth)
            
            # ── Compare results ──
            results_match = False
            if agent_result.success and gt_rows is not None:
                results_match = result_set_match(agent_result.results, gt_rows)
            
            elapsed = time.time() - start
            
            result = {
                "id":                question_id,
                "question":          question_text,
                "difficulty":        difficulty,
                "ground_truth_sql":  ground_truth,
                "generated_sql":     agent_result.final_sql,
                "success":           agent_result.success,
                "attempts":          agent_result.attempts,
                "latency_s":         round(elapsed, 2),
                "generated_rows":    agent_result.results,
                "reference_rows":    gt_rows,
                "results_match":     results_match,
                "gt_error":          gt_error,
                "agent_error":       agent_result.error,
            }
            
            all_results.append(result)
            progress.advance(task)
    
    return all_results


# ─────────────────────────────────────────────
# Display summary table
# ─────────────────────────────────────────────

def display_summary(all_results: list[dict], metrics: dict):
    """Print a formatted summary table of all results."""
    
    # Per-question results table
    table = Table(
        title="Question-by-Question Results",
        show_header=True,
        header_style="bold magenta"
    )
    table.add_column("ID",         style="dim",   width=4)
    table.add_column("Question",   style="white",  width=40)
    table.add_column("Difficulty", style="cyan",   width=8)
    table.add_column("Success",    style="green",  width=8)
    table.add_column("Attempts",   style="yellow", width=8)
    table.add_column("Match",      style="blue",   width=8)
    table.add_column("Time(s)",    style="dim",    width=7)
    
    for r in all_results:
        success_icon = "✅" if r["success"] else "❌"
        match_icon   = "✅" if r["results_match"] else ("—" if not r["success"] else "❌")
        
        table.add_row(
            str(r["id"]),
            r["question"][:38] + ".." if len(r["question"]) > 40 else r["question"],
            r["difficulty"],
            success_icon,
            str(r["attempts"]),
            match_icon,
            str(r["latency_s"]),
        )
    
    console.print(table)
    
    # Metrics summary
    console.print("\n[bold cyan]── Aggregate Metrics ──[/bold cyan]")
    console.print(f"  Execution Accuracy:       {metrics['execution_accuracy']*100:.1f}%")
    console.print(f"  Result Set Accuracy:      {metrics['result_set_accuracy']*100:.1f}%")
    console.print(f"  Exact Match Accuracy:     {metrics['exact_match_accuracy']*100:.1f}%")
    console.print(f"  First-Attempt Success:    {metrics['first_attempt_success']*100:.1f}%")
    console.print(f"  Self-Correction Rate:     {metrics['self_correction_rate']*100:.1f}%")
    console.print(f"  Average Attempts:         {metrics['average_attempts']:.2f}")
    console.print(f"  Average Latency:          {metrics['average_latency_s']:.2f}s")
    
    console.print("\n[bold cyan]── By Difficulty ──[/bold cyan]")
    for diff, acc in metrics["accuracy_by_difficulty"].items():
        console.print(f"  {diff.capitalize():10s}: {acc*100:.1f}%")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    results     = run_evaluation(verbose=False)
    metrics     = compute_all_metrics(results)
    
    display_summary(results, metrics)
    
    # Save results
    output_path = "evaluation/eval_results.json"
    with open(output_path, "w") as f:
        # Make results JSON-serializable
        json_safe = []
        for r in results:
            r_copy = r.copy()
            r_copy["generated_rows"]  = r_copy["generated_rows"][:5]  # Truncate for file
            r_copy["reference_rows"]  = r_copy["reference_rows"][:5]
            json_safe.append(r_copy)
        json.dump({"metrics": metrics, "results": json_safe}, f, indent=2, default=str)
    
    console.print(f"\n[green]Results saved to {output_path}[/green]")
    
    # Generate markdown report
    report_md = generate_report(results, metrics)
    with open("docs/evaluation_report.md", "w") as f:
        f.write(report_md)
    console.print("[green]Evaluation report saved to docs/evaluation_report.md[/green]")
