"""LangGraph workflow definition for the data analyst agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.execution import execute_analysis
from agent.llm import classify_query, summarize_with_llm
from agent.state import AgentState
from analytics.profiler import profile_dataframe
from analytics.validators import validate_analysis_output


def _profile_data(state: AgentState) -> AgentState:
    """Collect basic dataset metadata for downstream planning."""
    df = state["dataframe"]
    state["dataset_profile"] = profile_dataframe(df)
    return state


def _plan_query(state: AgentState) -> AgentState:
    """Classify query intent using the local LLM when available, then fall back to heuristics."""
    question = state["question"]
    lower_question = question.lower()

    if any(token in lower_question for token in ["forecast", "predict", "causal", "regression", "classify"]):
        fallback_intent, fallback_method = "unsupported", "none"
    elif any(token in lower_question for token in ["plot", "chart", "trend", "graph"]):
        fallback_intent, fallback_method = "trend", "pandas"
    elif any(token in lower_question for token in ["top", "bottom", "highest", "lowest", "total", "average"]):
        fallback_intent, fallback_method = "descriptive", "duckdb"
    elif any(token in lower_question for token in ["outlier", "unusual", "anomaly"]):
        fallback_intent, fallback_method = "outlier", "pandas"
    elif any(token in lower_question for token in ["why", "decline", "drop", "compare", "driver"]):
        fallback_intent, fallback_method = "diagnostic", "duckdb"
    else:
        fallback_intent, fallback_method = "unsupported", "none"

    dataset_columns = state.get("dataset_profile", {}).get("columns") or list(state["dataframe"].columns)
    state["intent"], state["method"] = classify_query(
        question,
        fallback_intent,
        fallback_method,
        dataset_columns=dataset_columns,
    )
    return state


def _route_query(state: AgentState) -> AgentState:
    """Placeholder route node for conditional branching."""
    return state


def _route_label(state: AgentState) -> str:
    """Return the route key for conditional edges."""
    return "execute" if state.get("intent") != "unsupported" else "fallback"


def _execute_analysis(state: AgentState) -> AgentState:
    """Run deterministic analysis for supported intents."""
    return execute_analysis(state)


def _validate_response(state: AgentState) -> AgentState:
    """Enforce minimum quality for analysis output and optionally add an LLM summary."""
    is_valid, reason = validate_analysis_output(state.get("analysis", ""))
    if not is_valid:
        state.setdefault("errors", []).append(reason)

    summary = summarize_with_llm(state.get("question", ""), state.get("analysis", ""))
    if summary:
        state["analysis"] = f"{state.get('analysis', '').strip()}\n\nLLM Summary:\n{summary}"
    return state


def _unsupported_fallback(state: AgentState) -> AgentState:
    """Generate actionable fallback for unsupported requests."""
    reason = "Unsupported request class for v1."
    if state.get("errors"):
        reason = state["errors"][-1]

    state["analysis"] = (
        "This request is out of scope for v1. "
        "Try descriptive, trend, diagnostic, or outlier questions on columns present in the CSV. "
        "Example: 'What is total sales by region?'"
    )
    state["sql"] = ""
    state["chart"] = None
    state.setdefault("errors", []).append(reason)
    return state


def build_graph():
    """Build and compile the Phase 2 LangGraph workflow."""
    workflow = StateGraph(AgentState)

    workflow.add_node("profile", _profile_data)
    workflow.add_node("plan", _plan_query)
    workflow.add_node("route", _route_query)
    workflow.add_node("execute", _execute_analysis)
    workflow.add_node("validate", _validate_response)
    workflow.add_node("fallback", _unsupported_fallback)

    workflow.add_edge(START, "profile")
    workflow.add_edge("profile", "plan")
    workflow.add_edge("plan", "route")
    workflow.add_conditional_edges(
        "route",
        _route_label,
        {
            "execute": "execute",
            "fallback": "fallback",
        },
    )
    workflow.add_edge("execute", "validate")
    workflow.add_edge("validate", END)
    workflow.add_edge("fallback", END)

    return workflow.compile()
