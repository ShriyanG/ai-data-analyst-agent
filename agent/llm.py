"""Lightweight Ollama integration with deterministic fallbacks."""

from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Callable, Optional, Tuple

DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:3b")
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "30"))


def _run_ollama_cli(prompt: str, model: str = DEFAULT_MODEL) -> str:
    """Invoke the local Ollama CLI and return the model response."""
    completed = subprocess.run(
        ["ollama", "run", model],
        input=prompt,
        text=True,
        capture_output=True,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        stderr = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(stderr or "ollama command failed")
    return (completed.stdout or "").strip()


def _parse_json_response(response: str) -> dict[str, Any]:
    """Extract a JSON object from a model response."""
    if not response:
        raise ValueError("empty response")

    text = response.strip()
    if text.startswith("```"):
        text = text.strip("`\n")
        if text.startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("response did not contain JSON")

    return json.loads(text[start : end + 1])


def classify_query(
    question: str,
    fallback_intent: str,
    fallback_method: str,
    model: str = DEFAULT_MODEL,
    runner: Optional[Callable[[str, str], str]] = None,
    dataset_columns: Optional[list[str]] = None,
) -> Tuple[str, str]:
    """Use the local model to classify a query when available; otherwise return the fallback."""
    schema_context = ""
    if dataset_columns:
        schema_context = "\nAvailable dataset columns:\n- " + "\n- ".join(dataset_columns) + "\n"

    prompt = f"""You are routing a natural-language analytics request.
Classify it into one of these intents and methods.

Intents: descriptive, trend, outlier, diagnostic, unsupported
Methods: duckdb, pandas, none

Return JSON only in the form {{"intent": "...", "method": "..."}}

Question: {question}{schema_context}
"""

    try:
        executor = runner or _run_ollama_cli
        response = executor(prompt, model)
        payload = _parse_json_response(response)
        intent = str(payload.get("intent", fallback_intent)).strip().lower()
        method = str(payload.get("method", fallback_method)).strip().lower()
        if intent in {"descriptive", "trend", "outlier", "diagnostic", "unsupported"} and method in {"duckdb", "pandas", "none"}:
            return intent, method
    except Exception:
        pass

    return fallback_intent, fallback_method


def summarize_with_llm(
    question: str,
    analysis: str,
    model: str = DEFAULT_MODEL,
    runner: Optional[Callable[[str, str], str]] = None,
) -> Optional[str]:
    """Ask the local model for a concise summary when it is available."""
    if not analysis.strip():
        return None

    prompt = f"""You are helping produce a concise analytics response.
Write a short, plain-English summary in 3 bullet points.
Do not invent facts beyond the provided analysis.

Question: {question}

Analysis:
{analysis}
"""

    try:
        executor = runner or _run_ollama_cli
        response = executor(prompt, model)
        cleaned = response.strip()
        if cleaned:
            return cleaned
    except Exception:
        pass

    return None
