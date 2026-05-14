"""
self_correct.py
---------------
Implements the self-correction loop for the Text-to-SQL agent.

Flow:
  1. Generate SQL from question
  2. Execute SQL against database
  3. If execution fails → send error to correction chain → retry (up to MAX_RETRIES)
  4. Return result or raise after max retries
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

from app.chain import get_sql_generation_chain, get_sql_correction_chain
from app.database import execute_query

load_dotenv()

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


# ─────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────

@dataclass
class QueryResult:
    """Holds the full result of a Text-to-SQL execution attempt."""
    question:       str
    final_sql:      str
    results:        list[dict]
    success:        bool
    attempts:       int
    error:          Optional[str] = None
    attempt_history: list[dict] = field(default_factory=list)
    
    @property
    def row_count(self) -> int:
        return len(self.results)
    
    def __repr__(self):
        status = "✅ SUCCESS" if self.success else f"❌ FAILED ({self.error})"
        return (
            f"QueryResult(\n"
            f"  status  = {status}\n"
            f"  attempts = {self.attempts}/{MAX_RETRIES}\n"
            f"  rows     = {self.row_count}\n"
            f"  sql      = {self.final_sql[:80]}...\n"
            f")"
        )


# ─────────────────────────────────────────────
# Core self-correction loop
# ─────────────────────────────────────────────

def run_with_self_correction(question: str, verbose: bool = False) -> QueryResult:
    """
    Main entry point: takes a natural language question and returns a QueryResult.
    
    Implements a retry loop with self-correction:
      - Attempt 1: Generate fresh SQL
      - Attempt 2+: Ask model to fix the previous error
    
    Args:
        question: The natural language question to answer
        verbose:  If True, prints each attempt
    
    Returns:
        QueryResult with success/failure, SQL used, and rows returned
    """
    sql_chain        = get_sql_generation_chain()
    correction_chain = get_sql_correction_chain()
    
    current_sql   = ""
    last_error    = ""
    history       = []
    
    for attempt in range(1, MAX_RETRIES + 1):
        
        # ── Step 1: Generate or correct SQL ──
        if attempt == 1:
            # Fresh generation
            if verbose:
                print(f"\n[Attempt {attempt}] Generating SQL...")
            current_sql = sql_chain.invoke(question)
        else:
            # Self-correction using previous error
            if verbose:
                print(f"\n[Attempt {attempt}] Correcting SQL after error: {last_error}")
            current_sql = correction_chain.invoke({
                "question":      question,
                "faulty_sql":    current_sql,
                "error_message": last_error,
            })
        
        if verbose:
            print(f"   SQL: {current_sql}")
        
        # ── Step 2: Execute SQL ──
        try:
            results = execute_query(current_sql)
            
            # Success!
            history.append({
                "attempt": attempt,
                "sql":     current_sql,
                "success": True,
                "error":   None,
            })
            
            if verbose:
                print(f"   ✅ Success! Returned {len(results)} rows.")
            
            return QueryResult(
                question        = question,
                final_sql       = current_sql,
                results         = results,
                success         = True,
                attempts        = attempt,
                attempt_history = history,
            )
        
        except Exception as e:
            last_error = str(e)
            
            history.append({
                "attempt": attempt,
                "sql":     current_sql,
                "success": False,
                "error":   last_error,
            })
            
            if verbose:
                print(f"   ❌ Error: {last_error}")
    
    # All retries exhausted
    return QueryResult(
        question        = question,
        final_sql       = current_sql,
        results         = [],
        success         = False,
        attempts        = MAX_RETRIES,
        error           = last_error,
        attempt_history = history,
    )


# ─────────────────────────────────────────────
# Batch runner (for evaluation)
# ─────────────────────────────────────────────

def run_batch(questions: list[str], verbose: bool = False) -> list[QueryResult]:
    """
    Run a batch of questions and return all results.
    Useful for evaluation.
    """
    results = []
    for i, q in enumerate(questions, 1):
        if verbose:
            print(f"\n{'='*60}")
            print(f"Question {i}/{len(questions)}: {q}")
        result = run_with_self_correction(q, verbose=verbose)
        results.append(result)
    return results


# ─────────────────────────────────────────────
# Quick test
# ─────────────────────────────────────────────

if __name__ == "__main__":
    test_question = "What are the top 5 products by quantity in stock?"
    
    print(f"Testing self-correction loop with: '{test_question}'")
    result = run_with_self_correction(test_question, verbose=True)
    
    print("\nFinal Result:")
    print(result)
    if result.success and result.results:
        print(f"\nFirst row: {result.results[0]}")
