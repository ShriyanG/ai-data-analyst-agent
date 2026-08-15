"""Streamlit frontend for the AI Data Analyst Agent."""

import pandas as pd
import streamlit as st

from agent.graph import build_graph


def _read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Read the current uploaded CSV from the beginning of the file buffer."""
    uploaded_file.seek(0)
    return pd.read_csv(uploaded_file)


st.set_page_config(page_title="AI Data Analyst Agent", layout="wide")
st.title("AI Data Analyst Agent")
st.caption("Turn CSV files into grounded answers, charts, and traceable SQL with a local analytics workflow.")

st.markdown(
    """
    This app is designed for business and product datasets where you need quick answers without writing SQL or Python.
    It works best for descriptive, trend, diagnostic, and outlier-style questions on CSVs with fields such as sales, profit,
    region, segment, discount, and order date.
    """
)

with st.expander("What this app handles well", expanded=True):
    st.markdown(
        """
        - Descriptive questions: total sales by region, top products, average values by segment
        - Trend questions: monthly sales patterns, declines, and time-based movement
        - Diagnostic questions: comparison-style questions grounded in the uploaded columns
        - Outlier questions: unusually low or high values in numeric fields
        """
    )

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

uploaded_file = st.file_uploader("Upload a CSV dataset", type=["csv"])
query = st.text_area("What would you like to analyze?", height=120)
run = st.button("Run Analysis", type="primary")

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

if uploaded_file is not None:
    try:
        df = _read_uploaded_csv(uploaded_file)
    except (pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        st.error(f"Unable to read the uploaded CSV: {exc}")
        df = None

    if df is not None:
        st.subheader("Dataset Preview")
        st.dataframe(df.head(20), use_container_width=True)

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

        st.subheader("Agent Response")
        st.write(result.get("analysis", "No analysis generated."))

        if result.get("sql"):
            st.code(result["sql"], language="sql")

        if result.get("chart") is not None:
            st.pyplot(result["chart"], clear_figure=False)

        if result.get("errors"):
            with st.expander("Errors"):
                for err in result["errors"]:
                    st.error(err)
