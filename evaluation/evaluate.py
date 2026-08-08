"""Evaluation harness scaffold for benchmark questions.

This file intentionally contains placeholder scoring logic so you can refine
the rubric over time without changing the overall evaluation flow.
"""

from __future__ import annotations

import json
import statistics
import time
from pathlib import Path
from typing import Any

import pandas as pd

from agent.graph import build_graph


DEFAULT_QUESTIONS_PATH = Path("evaluation/test_questions.json")
DEFAULT_DATASET_PATH = Path("data/sample_superstore.csv")
DEFAULT_RESULTS_PATH = Path("evaluation/results.json")


def load_questions(path: Path = DEFAULT_QUESTIONS_PATH) -> list[dict[str, Any]]:
    """Load benchmark questions from JSON file."""
    with path.open("r", encoding="utf-8") as f:
        questions = json.load(f)
    validate_question_schema(questions)
    return questions


def validate_question_schema(questions: list[dict[str, Any]]) -> None:
    """Validate minimum benchmark schema requirements.

    Expected shape per item:
    {
      "id": str,
      "question": str,
      "expected": {
        "intent": str (optional),
        "method": str (optional),
        "must_include": [str, ...] (optional),
        "must_not_include": [str, ...] (optional)
      }
    }
    """
    for idx, item in enumerate(questions):
        if "id" not in item or "question" not in item:
            raise ValueError(f"Invalid question schema at index {idx}: missing id/question")
        if "expected" in item and not isinstance(item["expected"], dict):
            raise ValueError(f"Invalid question schema at index {idx}: expected must be an object")


def load_dataset(path: Path = DEFAULT_DATASET_PATH) -> pd.DataFrame:
    """Load the evaluation dataset used for benchmark runs."""
    return pd.read_csv(path)


def build_initial_state(question: str, df: pd.DataFrame) -> dict[str, Any]:
    """Create a graph input state for a single question."""
    return {
        "question": question,
        "dataframe": df,
        "dataset_profile": {},
        "intent": "",
        "method": "",
        "analysis": "",
        "sql": "",
        "chart": None,
        "errors": [],
    }


def run_single_case(graph: Any, df: pd.DataFrame, case: dict[str, Any]) -> dict[str, Any]:
    """Execute one benchmark case and capture runtime metadata."""
    state = build_initial_state(case["question"], df)
    start = time.perf_counter()
    result = graph.invoke(state)
    latency_ms = (time.perf_counter() - start) * 1000.0

    return {
        "id": case.get("id", "unknown"),
        "question": case["question"],
        "result": result,
        "expected": case.get("expected", {}),
        "latency_ms": latency_ms,
    }


def _sanitize_result_for_report(result: dict[str, Any]) -> dict[str, Any]:
    """Keep report payload JSON-serializable and compact."""
    clean = dict(result)

    # Dataframe is large and not JSON serializable; keep its shape only.
    dataframe = clean.get("dataframe")
    if isinstance(dataframe, pd.DataFrame):
        clean["dataframe"] = {
            "rows": int(dataframe.shape[0]),
            "columns": int(dataframe.shape[1]),
        }

    # Matplotlib figures and other objects are not serializable.
    chart = clean.get("chart")
    if chart is not None and not isinstance(chart, (str, int, float, bool, list, dict)):
        clean["chart"] = "<non-serializable-chart-object>"

    return clean


def score_correctness(case_result: dict[str, Any]) -> float:
    """Score factual correctness.

    Placeholder strategy:
    - Return 0.0/1.0 style baseline using optional expected intent.
    - Expand later with numeric tolerance, ranking checks, and SQL validation.
    """
    expected = case_result.get("expected", {})
    expected_intent = expected.get("intent")
    expected_method = expected.get("method")
    must_include = expected.get("must_include", [])
    must_not_include = expected.get("must_not_include", [])

    result = case_result["result"]
    predicted_intent = result.get("intent")
    predicted_method = result.get("method")
    analysis = str(result.get("analysis", "")).lower()

    checks: list[float] = []

    if expected_intent is not None:
        checks.append(1.0 if expected_intent == predicted_intent else 0.0)
    if expected_method is not None:
        checks.append(1.0 if expected_method == predicted_method else 0.0)

    for phrase in must_include:
        checks.append(1.0 if str(phrase).lower() in analysis else 0.0)
    for phrase in must_not_include:
        checks.append(1.0 if str(phrase).lower() not in analysis else 0.0)

    if not checks:
        return 0.5
    return sum(checks) / len(checks)


def score_contract_compliance(case_result: dict[str, Any]) -> float:
    """Score whether response format matches required output contract.

    Current strategy:
    - Check required response contract sections in analysis text.
    """
    analysis = str(case_result["result"].get("analysis", ""))
    required = [
        "direct answer:",
        "evidence:",
        "method note:",
        "assumptions/interpretation:",
    ]
    if not analysis.strip():
        return 0.0

    present = sum(1 for marker in required if marker in analysis.lower())
    return present / len(required)


def score_guardrails(case_result: dict[str, Any], df: pd.DataFrame) -> float:
    """Score safety and grounding behavior.

    Placeholder strategy:
    - If unsupported intent then require at least one error message.
    - Expand later with fabricated-column detection and SQL schema checks.
    """
    result = case_result["result"]
    intent = result.get("intent")
    errors = result.get("errors", [])
    if intent == "unsupported":
        return 1.0 if errors else 0.0
    return 1.0


def score_reliability(case_result: dict[str, Any]) -> float:
    """Score runtime reliability for a single case."""
    result = case_result["result"]
    has_analysis = bool(str(result.get("analysis", "")).strip())
    has_runtime_error = False
    for err in result.get("errors", []):
        text = str(err).lower()
        if "traceback" in text or "exception" in text:
            has_runtime_error = True
            break

    return 1.0 if has_analysis and not has_runtime_error else 0.0


def weighted_case_score(case_result: dict[str, Any], df: pd.DataFrame) -> dict[str, Any]:
    """Combine component scores into one case-level score."""
    correctness = score_correctness(case_result)
    contract = score_contract_compliance(case_result)
    guardrails = score_guardrails(case_result, df)
    reliability = score_reliability(case_result)

    final_score = (
        0.50 * correctness
        + 0.20 * contract
        + 0.20 * guardrails
        + 0.10 * reliability
    )

    return {
        "id": case_result["id"],
        "question": case_result["question"],
        "correctness": correctness,
        "contract": contract,
        "guardrails": guardrails,
        "reliability": reliability,
        "latency_ms": case_result.get("latency_ms"),
        "final_score": final_score,
        "passed": final_score >= 0.80,
        "result": _sanitize_result_for_report(case_result["result"]),
    }


def summarize_scores(case_scores: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate benchmark metrics."""
    final_scores = [c["final_score"] for c in case_scores]
    pass_count = sum(1 for c in case_scores if c["passed"])
    latencies = [c["latency_ms"] for c in case_scores if c.get("latency_ms") is not None]

    p50 = statistics.median(latencies) if latencies else 0.0
    p95 = 0.0
    if latencies:
        sorted_latencies = sorted(latencies)
        idx = max(0, min(len(sorted_latencies) - 1, int(0.95 * len(sorted_latencies)) - 1))
        p95 = sorted_latencies[idx]

    return {
        "total_cases": len(case_scores),
        "pass_count": pass_count,
        "pass_rate": pass_count / len(case_scores) if case_scores else 0.0,
        "avg_score": statistics.mean(final_scores) if final_scores else 0.0,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
    }


def write_results(payload: dict[str, Any], path: Path = DEFAULT_RESULTS_PATH) -> None:
    """Write evaluation report to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def run_evaluation() -> dict[str, Any]:
    """Run all benchmark cases and return full report payload."""
    questions = load_questions()
    df = load_dataset()
    graph = build_graph()

    raw_results = [run_single_case(graph, df, case) for case in questions]
    case_scores = [weighted_case_score(item, df) for item in raw_results]
    summary = summarize_scores(case_scores)

    return {
        "summary": summary,
        "cases": case_scores,
    }


def main() -> None:
    report = run_evaluation()
    write_results(report)

    summary = report["summary"]
    print(f"Evaluated {summary['total_cases']} cases")
    print(f"Pass rate: {summary['pass_rate']:.2%}")
    print(f"Average score: {summary['avg_score']:.3f}")
    print(f"Latency p50: {summary['latency_p50_ms']:.1f} ms")
    print(f"Latency p95: {summary['latency_p95_ms']:.1f} ms")
    print(f"Detailed report written to: {DEFAULT_RESULTS_PATH}")


if __name__ == "__main__":
    main()
