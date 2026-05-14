# Task 2: Evaluation Strategy for Text-to-SQL Agents

---

## Overview

Evaluating a Text-to-SQL system is more complex than evaluating a standard NLP task. A generated SQL query can be:
- **Syntactically different** but **semantically equivalent** (both return the same answer)
- **Syntactically similar** but **logically wrong** (subtle join or filter errors)
- **Completely correct** but **inefficient** (missing indexes, N+1 patterns)

A good evaluation framework must capture all these dimensions.

---

## Evaluation Dimensions

### 1. Execution Accuracy (EX)
> **"Does the generated SQL run without error?"**

The most basic metric. A query that throws a syntax or runtime error has failed completely.

**How to measure:** Execute the generated SQL; record success/failure.  
**Formula:** `EX = (queries that execute without error) / total_queries`  
**Target:** > 90%

---

### 2. Exact Match Accuracy (EM)
> **"Is the generated SQL character-for-character identical to the reference?"**

Strict comparison after normalization (lowercase, remove extra whitespace).

**How to measure:** Normalize both SQLs, compare strings.  
**Formula:** `EM = (exact matches) / total_queries`  
**Limitation:** Very strict. Two semantically equivalent queries with different column order score 0. Use as a lower-bound metric only.  
**Target:** > 30% (lower is expected and acceptable)

---

### 3. Result Set Match (RSM)
> **"Do both queries return the same answer?"**

Execute both the generated SQL and the ground truth SQL, then compare the result sets regardless of order.

**How to measure:** Convert both result sets to sets of tuples; compare.  
**Formula:** `RSM = (matching result sets) / executable_queries`  
**This is the most important accuracy metric.**  
**Target:** > 80%

---

### 4. Partial Credit (Component Scores)
> **"Which parts of the SQL are correct?"**

Break the SQL into components and score each:

| Component | What it tests |
|-----------|---------------|
| **Table Selection** | Does it use the right tables? |
| **Column Selection** | Does it select the right columns? |
| **JOIN Correctness** | Are joins logically correct? |
| **Filter Correctness** | Are WHERE/HAVING conditions right? |
| **Aggregation Correctness** | Is GROUP BY / aggregation correct? |
| **Ordering / Limiting** | Is ORDER BY and LIMIT appropriate? |

**How to measure:** Use an LLM-as-judge (Gemini) to score each component 0/1.  
**Benefit:** Identifies which type of SQL error is most common.

---

### 5. Self-Correction Metrics
> **"Does the retry/correction loop actually help?"**

Track how many questions the agent initially failed on but eventually answered via self-correction.

| Metric | Formula | Target |
|--------|---------|--------|
| First-attempt success rate | (success on attempt 1) / total | > 70% |
| Self-correction recovery rate | (fixed by retry) / total | > 10% |
| Average attempts per query | sum(attempts) / total | < 1.5 |

---

### 6. Latency / Efficiency
> **"Is the system fast enough to be practical?"**

| Metric | Formula | Target |
|--------|---------|--------|
| Average latency | mean(time per query) | < 5s |
| P95 latency | 95th percentile | < 15s |
| Total cost | (API calls × token cost) | track |

---

### 7. Robustness Testing
> **"How does the system handle edge cases?"**

Test with:
- **Ambiguous questions:** "Show me sales" (sales of what? revenue? count?)
- **Typos:** "What ar the top custmers?" 
- **Out-of-scope questions:** "What is the weather today?"
- **Very complex multi-hop questions:** requiring 4+ table joins
- **NULL handling:** "Which orders have no ship date?"

Measure: graceful error rate, incorrect answer rate, refusal rate.

---

## Recommended Evaluation Stack

```
┌─────────────────────────────────────────────┐
│         Evaluation Pipeline                  │
├─────────────────────────────────────────────┤
│  1. Load benchmark questions (JSON)          │
│  2. Run agent → generated SQL                │
│  3. Execute generated SQL (record EX)        │
│  4. Execute ground truth SQL                 │
│  5. Compare result sets (RSM)               │
│  6. Normalize + compare SQL text (EM)        │
│  7. LLM judge component scores              │
│  8. Compute aggregates + per-difficulty      │
│  9. Generate markdown report                │
└─────────────────────────────────────────────┘
```

---

## Benchmark Structure

The benchmark should cover:

| Category | # Questions | Why |
|----------|------------|-----|
| Simple COUNT/SELECT | 4 | Baseline capability |
| Single-table filter | 3 | Basic WHERE |
| Single-table aggregation | 3 | GROUP BY / SUM |
| Two-table JOIN | 4 | Core SQL skill |
| Multi-table JOIN (3+) | 3 | Complex queries |
| Subqueries | 2 | Advanced |
| Date operations | 1 | Temporal reasoning |

**Total:** 20 questions minimum; 50+ for production evaluation.

---

## Baseline vs. Aspirational Targets

| Metric | Poor | Acceptable | Good | Excellent |
|--------|------|-----------|------|-----------|
| Execution Accuracy | < 60% | 60–75% | 75–90% | > 90% |
| Result Set Match | < 40% | 40–60% | 60–80% | > 80% |
| Exact Match | < 15% | 15–30% | 30–45% | > 45% |
| First-Attempt Success | < 50% | 50–65% | 65–80% | > 80% |
| Avg Latency | > 15s | 8–15s | 3–8s | < 3s |

---

## What the Evaluation Reveals

Running the evaluation framework tells you:

1. **Which question types fail most** → focus prompt engineering there
2. **Does self-correction help?** → worth the extra API calls?
3. **Is the schema context sufficient?** → maybe add more examples
4. **Are latencies acceptable?** → switch from gemini-1.5-pro to flash if needed
5. **Which difficulty level is the ceiling?** → guides future improvements

---

## Tools Used in This Implementation

| Tool | Purpose |
|------|---------|
| `evaluation/metrics.py` | All metric computations |
| `evaluation/evaluator.py` | Automated evaluation runner |
| `evaluation/report.py` | Markdown report generation |
| `benchmark/questions.json` | 20-question benchmark dataset |
| Google Gemini (LLM-as-judge) | Component-level scoring |

---

## Citation / Inspiration

This evaluation framework draws on:
- **Spider benchmark** (Yale) — the standard Text-to-SQL evaluation dataset
- **WikiSQL** — simpler single-table benchmark
- **BIRD benchmark** — realistic, messy database evaluation
- **LangChain SQL evaluation docs** — chain-of-thought SQL grading
