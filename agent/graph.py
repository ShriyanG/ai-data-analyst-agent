"""LangGraph workflow definition for the data analyst agent."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agent.state import AgentState
from agent.tools import summarize_dataframe
from analytics.profiler import profile_dataframe


def _analyze(state: AgentState) -> AgentState:
    """Run lightweight deterministic analysis for scaffolding."""
    df = state["dataframe"]
    question = state["question"]

    profile = profile_dataframe(df)
    summary = summarize_dataframe(df)

    state["analysis"] = (
        f"Question: {question}\n\n"
        f"Rows: {summary['rows']}, Columns: {summary['columns']}\n"
        f"Numeric columns: {', '.join(profile['numeric_columns']) or 'None'}\n"
        "This is scaffold output. Replace with LLM + tool-calling logic."
    )
    state["sql"] = "SELECT * FROM data LIMIT 5;"
    state["chart"] = None
    return state


def build_graph():
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    workflow.add_node("analyze", _analyze)

    workflow.add_edge(START, "analyze")
    workflow.add_edge("analyze", END)

    return workflow.compile()
