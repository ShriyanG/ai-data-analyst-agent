# Evaluation Guide

This folder contains the evaluation harness and benchmark question set.

## Files

- `evaluate.py`: Runs benchmark cases, scores outputs, and writes a report.
- `test_questions.json`: Benchmark cases and expected behavior metadata.
- `results.json`: Generated output report (created when evaluation runs).

## Benchmark Schema

Each benchmark item supports lightweight expectations:

```json
{
  "id": "q1",
  "question": "What is total sales by region?",
  "expected": {
    "intent": "descriptive",
    "method": "duckdb",
    "must_include": ["rows", "columns"],
    "must_not_include": ["out of scope"]
  }
}
```

Notes:
- `intent` and `method` validate routing behavior.
- `must_include` checks for key analysis phrases.
- `must_not_include` catches obvious failures.
- Extend this schema later with numeric checks and ranking checks.

## Current Scoring (Placeholder)

Per-case score uses:
- Correctness: intent/method/phrase checks from benchmark metadata.
- Contract: non-empty analysis.
- Guardrails: unsupported requests should include an error.
- Reliability: analysis must be present.

Final weighted score:
- 50% correctness
- 20% contract
- 20% guardrails
- 10% reliability

Pass threshold:
- final_score >= 0.80

## Run

From repo root:

```bash
python evaluation/evaluate.py
```

Output:
- Console summary
- `evaluation/results.json`

## Next Extensions

- Add exact/approx numeric expectation checks.
- Add SQL execution validation for query-producing cases.
- Add response contract section checks (direct answer, evidence, assumptions).
- Add per-intent scoring customizations.
