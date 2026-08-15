"""Streamlit frontend for the AI Data Analyst Agent."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from agent.graph import build_graph
from analytics.profiler import profile_dataframe


def _read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Read the current uploaded CSV from the beginning of the file buffer."""
    uploaded_file.seek(0)
    return pd.read_csv(uploaded_file)


def _parse_analysis_sections(analysis: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_heading: str | None = None

    for raw_line in analysis.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if ":" in line:
            heading, content = line.split(":", 1)
            normalized = heading.strip().lower()
            if normalized in {
                "direct answer",
                "evidence",
                "method note",
                "assumptions/interpretation",
                "numeric columns detected",
                "llm summary",
            }:
                current_heading = normalized
                sections[current_heading] = content.strip()
                continue

        if current_heading is not None:
            existing = sections.get(current_heading, "")
            sections[current_heading] = f"{existing}\n{line}".strip()

    return sections


def _render_dataset_summary(df: pd.DataFrame) -> None:
    profile = profile_dataframe(df)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Rows", f"{df.shape[0]:,}")
    metric_cols[1].metric("Columns", f"{df.shape[1]:,}")
    metric_cols[2].metric("Numeric Fields", len(profile.get("numeric_columns", [])))
    metric_cols[3].metric("Categorical Fields", len(profile.get("categorical_columns", [])))

    st.caption(
        "Detected numeric columns: "
        + (", ".join(profile.get("numeric_columns", [])[:8]) or "None")
    )


def _render_analysis(result: dict) -> None:
    analysis = result.get("analysis", "")
    sections = _parse_analysis_sections(analysis)

    answer = sections.get("direct answer", "No analysis generated.")
    evidence = sections.get("evidence", "No evidence captured.")
    method_note = sections.get("method note", "No method note available.")
    assumptions = sections.get("assumptions/interpretation", "No assumptions recorded.")
    numeric_columns = sections.get("numeric columns detected", "")
    llm_summary = sections.get("llm summary", "")

    st.subheader("Answer")
    st.markdown(f"<div class='answer-card'>{answer}</div>", unsafe_allow_html=True)

    result_table = pd.DataFrame(result.get("result_table", []))

    detail_cols = st.columns([1.3, 1])
    with detail_cols[0]:
        if result.get("chart") is not None:
            st.markdown("### Visual")
            st.pyplot(result["chart"], clear_figure=False)
        st.markdown("### Evidence")
        if not result_table.empty:
            st.dataframe(result_table, use_container_width=True, hide_index=True)
        else:
            st.code(evidence, language="text")

    with detail_cols[1]:
        st.markdown("### Execution Notes")
        st.markdown(f"**Method**\n\n{method_note}")
        st.markdown(f"**Assumptions**\n\n{assumptions}")
        if numeric_columns:
            st.markdown(f"**Numeric Columns**\n\n{numeric_columns}")
        if llm_summary:
            st.markdown(f"**LLM Summary**\n\n{llm_summary}")

    if result.get("sql"):
        with st.expander("SQL Used"):
            st.code(result["sql"], language="sql")

    if result.get("errors"):
        with st.expander("Warnings and Errors"):
            for err in result["errors"]:
                st.error(err)


st.markdown(
    """
    <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(224, 242, 254, 0.95), transparent 32%),
                radial-gradient(circle at top right, rgba(254, 240, 138, 0.55), transparent 22%),
                linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
        }
        .stMarkdown, .stCaption, label, .stTextArea label, .stFileUploader label {
            color: #0f172a;
        }
        h1 {
            color: #0b1220 !important;
            letter-spacing: -0.03em;
            font-weight: 800;
            text-shadow: 0 1px 0 rgba(255, 255, 255, 0.65);
        }
        [data-testid="stCaptionContainer"] {
            color: #334155;
        }
        .hero-panel {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
            color: #e2e8f0;
            border-radius: 24px;
            padding: 1.4rem 1.5rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
            margin-bottom: 1rem;
        }
        .hero-panel h3 {
            margin: 0 0 0.4rem 0;
            color: #f8fafc;
        }
        .hero-panel p {
            margin: 0;
            color: #cbd5e1;
            line-height: 1.55;
        }
        .answer-card {
            background: linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(239, 246, 255, 0.92));
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            color: #0f172a;
            box-shadow: 0 18px 40px rgba(148, 163, 184, 0.16);
            font-size: 1rem;
            line-height: 1.6;
        }
        .capability-card {
            background: rgba(255, 255, 255, 0.74);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            min-height: 132px;
            box-shadow: 0 10px 30px rgba(148, 163, 184, 0.12);
        }
        .capability-card h4 {
            margin: 0 0 0.4rem 0;
            color: #0f172a;
        }
        .capability-card p {
            margin: 0;
            color: #334155;
            line-height: 1.5;
        }
        .stButton > button {
            background: linear-gradient(135deg, #0f172a, #1d4ed8);
            color: #f8fafc;
            border: 1px solid rgba(15, 23, 42, 0.2);
            border-radius: 14px;
            font-weight: 700;
            box-shadow: 0 14px 28px rgba(29, 78, 216, 0.22);
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #0b1220, #1e40af);
            color: #ffffff;
            border-color: rgba(30, 64, 175, 0.45);
        }
        .stTextArea textarea {
            background: rgba(255, 255, 255, 0.96);
            color: #0f172a;
            border: 1px solid rgba(148, 163, 184, 0.45);
        }
        [data-testid="stFileUploaderDropzone"] {
            background: rgba(255, 255, 255, 0.96);
            border: 1px dashed rgba(29, 78, 216, 0.45);
            color: #0f172a;
        }
        [data-testid="stFileUploaderDropzone"] * {
            color: #0f172a;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(255, 255, 255, 0.82);
        }
    </style>
    """,
    unsafe_allow_html=True,
)


st.set_page_config(page_title="AI Data Analyst Agent", layout="wide")
st.title("AI Data Analyst Agent")
st.caption("Turn CSV files into grounded answers, charts, and traceable SQL with a local analytics workflow.")

st.markdown(
    """
    <div class='hero-panel'>
        <h3>Built For Fast, Grounded CSV Analysis</h3>
        <p>
            Upload a business dataset, ask a plain-language question, and get back a structured answer with evidence,
            traceable SQL, and optional LLM-assisted summarization. The workflow is strongest on descriptive, trend,
            diagnostic, and outlier questions across fields such as sales, profit, segment, region, discount, and date.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

capability_cols = st.columns(4)
capability_cols[0].markdown(
    """
    <div class='capability-card'>
        <h4>Descriptive</h4>
        <p>Break down totals, averages, and top performers by region, segment, or product.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
capability_cols[1].markdown(
    """
    <div class='capability-card'>
        <h4>Trend</h4>
        <p>Inspect month-over-month movement, drops, and broader sales patterns over time.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
capability_cols[2].markdown(
    """
    <div class='capability-card'>
        <h4>Diagnostic</h4>
        <p>Compare slices of the data to explain directional changes using grounded aggregates.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
capability_cols[3].markdown(
    """
    <div class='capability-card'>
        <h4>Outlier Review</h4>
        <p>Surface unusually low or high values in numeric columns for quick investigation.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

left_col, right_col = st.columns([0.95, 1.35], gap="large")

with left_col:
    st.markdown("### Ask a question")
    st.caption("Best results come from CSVs with fields like sales, profit, region, segment, discount, and order date.")
    uploaded_file = st.file_uploader("Upload a CSV dataset", type=["csv"])
    query = st.text_area("What would you like to analyze?", height=140, placeholder="Example: What is total sales by region?")
    run = st.button("Run Analysis", type="primary", use_container_width=True)

    with st.container(border=True):
        st.markdown("**Try prompts like:**")
        st.markdown(
            """
            - What is total sales by region?
            - Which products have the highest total profit?
            - Show the monthly sales trend.
            - How does average order value vary by customer segment?
            - Are there unusual low-profit rows in this dataset?
            """
        )

    with st.container(border=True):
        st.markdown("**What you should expect**")
        st.markdown(
            """
            - A direct answer in plain English
            - Evidence pulled from the uploaded dataset
            - SQL when the query uses the DuckDB path
            - Execution notes and assumptions for traceability
            """
        )

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

if uploaded_file is not None:
    try:
        df = _read_uploaded_csv(uploaded_file)
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        st.error(f"Unable to read the uploaded CSV: {exc}")
        df = None

    if df is not None:
        with right_col:
            st.markdown("### Dataset Snapshot")
            _render_dataset_summary(df)
            st.dataframe(df.head(20), use_container_width=True, height=320)

if run:
    if uploaded_file is None:
        st.warning("Upload a CSV file first.")
    elif not query.strip():
        st.warning("Enter a question to analyze.")
    else:
        try:
            df = _read_uploaded_csv(uploaded_file)
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            st.error(f"Unable to read the uploaded CSV: {exc}")
            st.stop()

        state = {
            "question": query,
            "dataframe": df,
            "dataset_profile": {},
            "intent": "",
            "method": "",
            "analysis": "",
            "sql": "",
            "chart": None,
            "errors": [],
        }
        result = st.session_state.graph.invoke(state)

        with right_col:
            st.markdown("### Analysis Result")
            _render_analysis(result)
