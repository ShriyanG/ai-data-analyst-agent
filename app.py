"""Streamlit frontend for the AI Data Analyst Agent."""

import pandas as pd
import streamlit as st

from agent.graph import build_graph


st.set_page_config(page_title="AI Data Analyst Agent", layout="wide")
st.title("AI Data Analyst Agent")
st.caption("Analyze datasets with natural language using local LLM workflows.")

uploaded_file = st.file_uploader("Upload a CSV dataset", type=["csv"])
query = st.text_area("What would you like to analyze?", height=120)
run = st.button("Run Analysis", type="primary")

if "graph" not in st.session_state:
    st.session_state.graph = build_graph()

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.subheader("Dataset Preview")
    st.dataframe(df.head(20), use_container_width=True)

if run:
    if uploaded_file is None:
        st.warning("Upload a CSV file first.")
    elif not query.strip():
        st.warning("Enter a question to analyze.")
    else:
        df = pd.read_csv(uploaded_file)
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
