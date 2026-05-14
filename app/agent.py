"""
agent.py
--------
Main Text-to-SQL agent CLI.
Run this file to start an interactive session:

    python app/agent.py

Or import run_question() for programmatic use.
"""

import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt

from app.self_correct import run_with_self_correction
from app.chain import get_nl_answer_chain
from app.database import test_connection

console = Console()


# ─────────────────────────────────────────────
# Pretty-print results
# ─────────────────────────────────────────────

def display_results(result, nl_answer: str = ""):
    """Display query results in a nicely formatted Rich table."""
    
    # Status panel
    status_color = "green" if result.success else "red"
    status_text  = f"{'✅ SUCCESS' if result.success else '❌ FAILED'} | Attempts: {result.attempts}"
    console.print(Panel(status_text, style=status_color, expand=False))
    
    # SQL used
    console.print(f"\n[bold cyan]Generated SQL:[/bold cyan]")
    console.print(f"  [dim]{result.final_sql}[/dim]\n")
    
    # Natural language answer
    if nl_answer:
        console.print(Panel(nl_answer, title="[bold]Answer[/bold]", border_style="blue"))
    
    # Results table (if any)
    if result.results:
        table = Table(
            title=f"Query Results ({result.row_count} rows)",
            show_header=True,
            header_style="bold magenta"
        )
        
        # Add columns
        columns = list(result.results[0].keys())
        for col in columns:
            table.add_column(str(col), style="white")
        
        # Add rows (show max 20)
        display_rows = result.results[:20]
        for row in display_rows:
            table.add_row(*[str(v) if v is not None else "NULL" for v in row.values()])
        
        if result.row_count > 20:
            table.caption = f"Showing 20 of {result.row_count} rows"
        
        console.print(table)
    
    elif result.success:
        console.print("[yellow]Query returned 0 rows.[/yellow]")
    
    # Show correction history if there were retries
    if result.attempts > 1:
        console.print(f"\n[dim]Correction history ({result.attempts} attempts):[/dim]")
        for h in result.attempt_history:
            icon = "✅" if h["success"] else "❌"
            console.print(f"  [dim]{icon} Attempt {h['attempt']}: {h.get('error', 'OK')}[/dim]")


# ─────────────────────────────────────────────
# Single question runner
# ─────────────────────────────────────────────

def run_question(question: str, verbose: bool = False) -> dict:
    """
    Answer a single NL question end-to-end.
    Returns a dict with sql, results, answer, success.
    """
    start = time.time()
    
    # Generate + execute SQL with self-correction
    result = run_with_self_correction(question, verbose=verbose)
    
    # Generate NL answer
    nl_answer = ""
    if result.success:
        try:
            nl_chain = get_nl_answer_chain()
            results_str = str(result.results[:10])  # Limit for context
            nl_answer = nl_chain.invoke({
                "question": question,
                "results":  results_str,
            })
        except Exception as e:
            nl_answer = f"(Could not generate NL answer: {e})"
    
    elapsed = time.time() - start
    
    return {
        "question":  question,
        "sql":       result.final_sql,
        "results":   result.results,
        "nl_answer": nl_answer,
        "success":   result.success,
        "attempts":  result.attempts,
        "error":     result.error,
        "latency_s": round(elapsed, 2),
    }


# ─────────────────────────────────────────────
# Interactive CLI
# ─────────────────────────────────────────────

def interactive_session():
    """Start an interactive Text-to-SQL chat session."""
    
    console.print(Panel.fit(
        "[bold blue]Text-to-SQL Agent[/bold blue]\n"
        "[dim]Powered by LangChain + Google Gemini[/dim]\n"
        "[dim]Database: ClassicModels (PostgreSQL)[/dim]",
        border_style="blue"
    ))
    
    # Test DB connection
    console.print("\nChecking database connection...", end="")
    if not test_connection():
        console.print(" [red]FAILED[/red]")
        console.print("[red]Could not connect to PostgreSQL. Check your .env settings.[/red]")
        sys.exit(1)
    console.print(" [green]OK[/green]\n")
    
    console.print("[dim]Type your question in plain English. Type 'exit' to quit.[/dim]\n")
    
    # Sample questions to guide users
    console.print("[bold]Example questions:[/bold]")
    examples = [
        "How many customers do we have in each country?",
        "What are the top 5 best-selling products by revenue?",
        "Which employees report to the VP of Sales?",
        "What is the total payment amount received from each customer in 2004?",
        "List all orders that are currently on hold.",
    ]
    for ex in examples:
        console.print(f"  • [dim]{ex}[/dim]")
    console.print()
    
    # Main loop
    while True:
        try:
            question = Prompt.ask("[bold cyan]Your question[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Goodbye![/dim]")
            break
        
        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            console.print("[dim]Goodbye![/dim]")
            break
        
        console.print()
        with console.status("[bold green]Thinking...[/bold green]", spinner="dots"):
            output = run_question(question, verbose=False)
        
        display_results(
            type("R", (), {
                "success":        output["success"],
                "attempts":       output["attempts"],
                "final_sql":      output["sql"],
                "results":        output["results"],
                "row_count":      len(output["results"]),
                "error":          output["error"],
                "attempt_history": [],
            })(),
            nl_answer=output["nl_answer"]
        )
        
        console.print(f"\n[dim]⏱ Latency: {output['latency_s']}s[/dim]\n")


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Non-interactive: pass question as CLI arg
        question = " ".join(sys.argv[1:])
        output = run_question(question, verbose=True)
        print(f"\nSQL: {output['sql']}")
        print(f"Answer: {output['nl_answer']}")
    else:
        interactive_session()
