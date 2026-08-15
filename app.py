"""Streamlit frontend for the AI Data Analyst Agent."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from agent.graph import build_graph
from analytics.profiler import profile_dataframe

UPLOAD_DIR = Path(__file__).resolve().parent / ".uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


def _read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Read the current uploaded CSV from the beginning of the file buffer."""
    uploaded_file.seek(0)
    return pd.read_csv(uploaded_file)


def _save_uploaded_csv(uploaded_file) -> Path:
    """Persist an uploaded file in the local .uploads directory for reuse."""
    uploaded_file.seek(0)
    saved_path = UPLOAD_DIR / uploaded_file.name
    with saved_path.open("wb") as output_file:
        output_file.write(uploaded_file.getvalue())
    return saved_path


def _save_uploaded_csvs(uploaded_files) -> list[Path]:
    """Persist multiple uploaded files and return their saved paths."""
    if not uploaded_files:
        return []
    return [_save_uploaded_csv(uploaded_file) for uploaded_file in uploaded_files]


def _list_saved_datasets() -> list[Path]:
    """Return saved CSV files in the persistent uploads directory."""
    if not UPLOAD_DIR.exists():
        return []
    return sorted(
        [path for path in UPLOAD_DIR.iterdir() if path.is_file() and path.suffix.lower() == ".csv"],
        key=lambda path: path.name.lower(),
    )


def _get_available_dataset_names(uploaded_files=None, saved_datasets=None) -> list[str]:
    """Return the combined list of uploaded and previously saved CSV names."""
    names: list[str] = []
    seen: set[str] = set()

    for uploaded_file in uploaded_files or []:
        if uploaded_file.name not in seen:
            names.append(uploaded_file.name)
            seen.add(uploaded_file.name)

    for saved_path in saved_datasets or []:
        if saved_path.name not in seen:
            names.append(saved_path.name)
            seen.add(saved_path.name)

    return names


def _resolve_dataset_path(selected_dataset_name: str | None, uploaded_files=None) -> Path | None:
    """Resolve whichever CSV file is meant to be the active context."""
    if not selected_dataset_name:
        return None

    if uploaded_files:
        for uploaded_file in uploaded_files:
            if uploaded_file.name == selected_dataset_name:
                return _save_uploaded_csv(uploaded_file)

    candidate = UPLOAD_DIR / selected_dataset_name
    if candidate.exists():
        return candidate

    return None


def _delete_saved_dataset(dataset_name: str) -> bool:
    """Delete a previously saved CSV dataset from the local uploads directory."""
    if not dataset_name:
        return False

    candidate = UPLOAD_DIR / dataset_name
    if candidate.exists() and candidate.is_file():
        candidate.unlink()
        return True
    return False


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
                radial-gradient(circle at top left, rgba(59, 130, 246, 0.18), transparent 28%),
                radial-gradient(circle at top right, rgba(168, 85, 247, 0.14), transparent 24%),
                linear-gradient(180deg, #020817 0%, #0f172a 100%);
            color: #e2e8f0;
        }
        .stMarkdown, .stCaption, label, .stTextArea label, .stFileUploader label {
            color: #e2e8f0;
        }
        h1 {
            color: #f8fafc !important;
            letter-spacing: -0.03em;
            font-weight: 800;
            text-shadow: none;
        }
        [data-testid="stCaptionContainer"] {
            color: #cbd5e1;
        }
        .hero-panel {
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
            color: #e2e8f0;
            border-radius: 24px;
            padding: 1.4rem 1.5rem;
            border: 1px solid rgba(148, 163, 184, 0.18);
            box-shadow: 0 24px 60px rgba(2, 8, 23, 0.6);
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
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            color: #e2e8f0;
            box-shadow: 0 18px 40px rgba(2, 8, 23, 0.5);
            font-size: 1rem;
            line-height: 1.6;
        }
        .capability-card {
            background: rgba(15, 23, 42, 0.74);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 0.9rem 1rem;
            min-height: 132px;
            box-shadow: 0 10px 30px rgba(2, 8, 23, 0.35);
        }
        .capability-card h4 {
            margin: 0 0 0.4rem 0;
            color: #f8fafc;
        }
        .capability-card p {
            margin: 0;
            color: #cbd5e1;
            line-height: 1.5;
        }
        .stButton > button {
            background: linear-gradient(135deg, #1d4ed8, #2563eb);
            color: #f8fafc;
            border: 1px solid rgba(96, 165, 250, 0.5);
            border-radius: 14px;
            font-weight: 700;
            box-shadow: 0 14px 28px rgba(37, 99, 235, 0.3);
        }
        .stButton > button:hover {
            background: linear-gradient(135deg, #1e40af, #2563eb);
            color: #ffffff;
            border-color: rgba(147, 197, 253, 0.75);
        }
        .stTextArea textarea {
            background: rgba(15, 23, 42, 0.9);
            color: #f8fafc;
            border: 1px solid rgba(148, 163, 184, 0.45);
        }
        [data-testid="stFileUploaderDropzone"] {
            background: rgba(15, 23, 42, 0.9);
            border: 1px dashed rgba(96, 165, 250, 0.5);
            color: #e2e8f0;
        }
        [data-testid="stFileUploaderDropzone"] * {
            color: #e2e8f0;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(15, 23, 42, 0.4);
        }
        [data-testid="stDataFrameContainer"] {
            background: rgba(15, 23, 42, 0.75);
        }
        .stDataFrame, .stTable {
            color: #e2e8f0;
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

    st.markdown("### Ask a question")
    st.caption("Best results come from CSVs with fields like sales, profit, region, segment, discount, and order date.")

    uploaded_files = st.file_uploader("Upload one or more CSV datasets", type=["csv"], accept_multiple_files=True)
    saved_datasets = _list_saved_datasets()
    available_dataset_names = _get_available_dataset_names(uploaded_files=uploaded_files, saved_datasets=saved_datasets)
    if available_dataset_names:
        selected_dataset_name = st.selectbox(
            "Choose the dataset to use as analysis context",
            available_dataset_names,
            index=0,
            help="Select which CSV should be used as the active context for the LLM and analytics workflow.",
        )
        saved_dataset_names = {path.name for path in saved_datasets}
        if selected_dataset_name in saved_dataset_names:
            delete_saved = st.button("Delete selected saved dataset", type="secondary", use_container_width=True)
            if delete_saved:
                if _delete_saved_dataset(selected_dataset_name):
                    st.success(f"Deleted {selected_dataset_name} from the saved dataset list.")
                    st.rerun()
                else:
                    st.warning(f"Could not delete {selected_dataset_name}.")
    else:
        selected_dataset_name = None

    query = st.text_area("What would you like to analyze?", height=140, placeholder="Example: What is total sales by region?")
    run = st.button("Run Analysis", type="primary", use_container_width=True)

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

selected_dataset_path = None
if available_dataset_names:
    selected_dataset_path = _resolve_dataset_path(selected_dataset_name, uploaded_files)
    if selected_dataset_path is not None:
        try:
            df = pd.read_csv(selected_dataset_path)
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            st.error(f"Unable to read the selected CSV: {exc}")
            df = None

        if df is not None:
            with right_col:
                st.markdown("### Dataset Snapshot")
                _render_dataset_summary(df)
                st.caption(f"Loaded from: {selected_dataset_path.name}")
                st.dataframe(df.head(20), use_container_width=True, height=320)

if run:
    dataset_path = _resolve_dataset_path(selected_dataset_name, uploaded_files)

    if dataset_path is None:
        st.warning("Upload a CSV file or choose a saved dataset first.")
    elif not query.strip():
        st.warning("Enter a question to analyze.")
    else:
        try:
            df = pd.read_csv(dataset_path)
        except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
            st.error(f"Unable to read the dataset: {exc}")
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
