"""
report.py
---------
Generates markdown evaluation reports from evaluation results.
"""

from datetime import datetime


def generate_report(results: list[dict], metrics: dict) -> str:
    """
    Generate a full markdown evaluation report.
    
    Returns the report as a markdown string.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"# Text-to-SQL Agent Evaluation Report",
        f"",
        f"**Generated:** {now}  ",
        f"**Model:** Google Gemini (gemini-1.5-flash)  ",
        f"**Database:** ClassicModels (PostgreSQL)  ",
        f"**Framework:** LangChain  ",
        f"",
        f"---",
        f"",
        f"## Aggregate Metrics",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Questions | {metrics['total_questions']} |",
        f"| Execution Accuracy (EX) | {metrics['execution_accuracy']*100:.1f}% |",
        f"| Result Set Accuracy (RSM) | {metrics['result_set_accuracy']*100:.1f}% |",
        f"| Exact Match Accuracy (EM) | {metrics['exact_match_accuracy']*100:.1f}% |",
        f"| First-Attempt Success | {metrics['first_attempt_success']*100:.1f}% |",
        f"| Self-Correction Rate | {metrics['self_correction_rate']*100:.1f}% |",
        f"| Average Attempts per Query | {metrics['average_attempts']:.2f} |",
        f"| Average Latency | {metrics['average_latency_s']:.2f}s |",
        f"",
        f"## Accuracy by Difficulty",
        f"",
        f"| Difficulty | Accuracy |",
        f"|-----------|----------|",
    ]
    
    for diff, acc in sorted(metrics["accuracy_by_difficulty"].items()):
        lines.append(f"| {diff.capitalize()} | {acc*100:.1f}% |")
    
    lines += [
        f"",
        f"---",
        f"",
        f"## Question-by-Question Results",
        f"",
        f"| ID | Question | Difficulty | Success | Attempts | Results Match | Latency |",
        f"|----|----------|-----------|---------|----------|---------------|---------|",
    ]
    
    for r in results:
        success_icon = "✅" if r["success"] else "❌"
        match_icon   = "✅" if r["results_match"] else ("—" if not r["success"] else "❌")
        q_short      = r["question"][:50] + "..." if len(r["question"]) > 50 else r["question"]
        lines.append(
            f"| {r['id']} | {q_short} | {r['difficulty']} | "
            f"{success_icon} | {r['attempts']} | {match_icon} | {r['latency_s']}s |"
        )
    
    lines += [
        f"",
        f"---",
        f"",
        f"## Failed Questions",
        f"",
    ]
    
    failed = [r for r in results if not r["success"]]
    if failed:
        for r in failed:
            lines += [
                f"### Q{r['id']}: {r['question']}",
                f"",
                f"**Generated SQL:**",
                f"```sql",
                f"{r['generated_sql']}",
                f"```",
                f"",
                f"**Error:** `{r.get('agent_error', 'Unknown')}`",
                f"",
                f"**Ground Truth:**",
                f"```sql",
                f"{r['ground_truth_sql']}",
                f"```",
                f"",
            ]
    else:
        lines.append("No failures! 🎉")
    
    return "\n".join(lines)
