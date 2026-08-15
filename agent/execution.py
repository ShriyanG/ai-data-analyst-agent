"""Execution helpers for the analytics agent workflow."""

from __future__ import annotations

import re
from typing import Any, Optional

import pandas as pd

from agent.state import AgentState
from agent.tools import run_duckdb_query, summarize_dataframe
from analytics.profiler import profile_dataframe
from visualizations.charts import make_bar_chart, make_line_chart


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _find_column(df: pd.DataFrame, *candidates: str) -> Optional[str]:
    normalized = {_normalize_name(column): column for column in df.columns}
    for candidate in candidates:
        match = normalized.get(_normalize_name(candidate))
        if match is not None:
            return match
    return None


def _quote_identifier(name: str) -> str:
    escaped = name.replace('"', '""')
    return '"' + escaped + '"'


def _build_chart_for_result(result: pd.DataFrame, metric_label: str) -> Optional[Any]:
    """Create a chart for common result shapes used in the demo workflow."""
    if result.empty or len(result.columns) < 2:
        return None

    x_col = result.columns[0]
    y_col = result.columns[1]

    if not pd.api.types.is_numeric_dtype(result[y_col]):
        return None

    chart_df = result.copy()
    if "trend" in metric_label or str(x_col).lower() == "month":
        return make_line_chart(chart_df, x_col, y_col)

    return make_bar_chart(chart_df.head(10), x_col, y_col)


def _build_duckdb_sql(df: pd.DataFrame, question: str) -> tuple[str, str]:
    lower_question = question.lower()
    region_col = _find_column(df, "Region", "region")
    sales_col = _find_column(df, "Sales", "sales")
    profit_col = _find_column(df, "Profit", "profit")
    product_col = _find_column(df, "Product Name", "product_name", "Product", "product")
    segment_col = _find_column(df, "Segment", "segment")
    date_col = _find_column(df, "Order Date", "order_date", "OrderDate", "date")
    discount_col = _find_column(df, "Discount", "discount")

    if region_col and sales_col and "sales by region" in lower_question:
        return (
            (
                f"SELECT {_quote_identifier(region_col)} AS region, "
                f"SUM({_quote_identifier(sales_col)}) AS total_sales "
                f"FROM data GROUP BY 1 ORDER BY 2 DESC"
            ),
            "total sales by region",
        )

    if product_col and profit_col and (
        "highest total profit" in lower_question or "profit" in lower_question and "product" in lower_question
    ):
        return (
            (
                f"SELECT {_quote_identifier(product_col)} AS product, "
                f"SUM({_quote_identifier(profit_col)}) AS total_profit "
                f"FROM data GROUP BY 1 ORDER BY 2 DESC LIMIT 5"
            ),
            "top products by total profit",
        )

    if segment_col and sales_col and (
        "average order value" in lower_question or "average" in lower_question and "segment" in lower_question
    ):
        return (
            (
                f"SELECT {_quote_identifier(segment_col)} AS customer_segment, "
                f"AVG({_quote_identifier(sales_col)}) AS average_order_value "
                f"FROM data GROUP BY 1 ORDER BY 2 DESC"
            ),
            "average order value by customer segment",
        )

    if date_col and sales_col and ("month" in lower_question or "decline" in lower_question or "drop" in lower_question):
        return (
            (
                f"SELECT DATE_TRUNC('month', CAST({_quote_identifier(date_col)} AS DATE)) AS month, "
                f"SUM({_quote_identifier(sales_col)}) AS total_sales "
                f"FROM data GROUP BY 1 ORDER BY 1"
            ),
            "monthly sales trend",
        )

    if discount_col and profit_col and "discount" in lower_question:
        return (
            (
                f"SELECT CASE WHEN {_quote_identifier(discount_col)} > 0.2 THEN 'Above 20%' ELSE '20% or below' END AS discount_group, "
                f"AVG({_quote_identifier(profit_col)}) AS average_profit "
                f"FROM data GROUP BY 1"
            ),
            "average profit by discount group",
        )

    return (
        "SELECT * FROM data LIMIT 5;",
        "a sample of the dataset",
    )


def _run_pandas_analysis(df: pd.DataFrame, question: str) -> tuple[str, Optional[dict[str, Any]]]:
    lower_question = question.lower()
    if "trend" in lower_question or "month" in lower_question or "quarter" in lower_question:
        date_col = _find_column(df, "Order Date", "order_date", "OrderDate", "date")
        sales_col = _find_column(df, "Sales", "sales")
        if date_col and sales_col:
            work_df = df[[date_col, sales_col]].copy()
            if work_df[date_col].dtype.kind in "OUS":
                work_df[date_col] = pd.to_datetime(work_df[date_col], errors="coerce")
            work_df = work_df.dropna(subset=[date_col])
            if not work_df.empty:
                trend_df = work_df.groupby(pd.Grouper(key=date_col, freq="ME")).sum(numeric_only=True)
                trend_df = trend_df.reset_index()
                preview = trend_df.head(5).to_string(index=False)
                return (
                    f"Direct Answer: Trend analysis was computed from monthly aggregates.\n\nEvidence: {preview}\n\nMethod Note: Used pandas to aggregate the data over time.\n\nAssumptions/Interpretation: The trend is based on the latest available monthly totals.",
                    {"kind": "line", "series": sales_col, "table": trend_df},
                )

    if "outlier" in lower_question or "unusual" in lower_question or "anomaly" in lower_question:
        profit_col = _find_column(df, "Profit", "profit")
        if profit_col:
            outlier_df = df[[profit_col]].copy()
            outlier_df = outlier_df.rename(columns={profit_col: "profit"})
            outlier_df = outlier_df.sort_values("profit")
            preview = outlier_df.head(10).to_string(index=False)
            return (
                f"Direct Answer: Outlier candidates were identified from the lowest-profit rows.\n\nEvidence: {preview}\n\nMethod Note: Used pandas to rank the rows by profit magnitude.\n\nAssumptions/Interpretation: These rows are treated as candidate outliers for the current question.",
                {"kind": "table", "table": outlier_df.head(10)},
            )

    return (
        f"Direct Answer: A pandas-based analysis was prepared for '{question}'.\n\nEvidence: Dataset shape is {df.shape[0]} rows and {df.shape[1]} columns.\n\nMethod Note: Used pandas for a non-SQL execution path.\n\nAssumptions/Interpretation: The current scaffold uses pandas for trend and outlier-style questions.",
        None,
    )


def execute_analysis(state: AgentState) -> AgentState:
    """Run deterministic analysis for supported intents."""
    df = state["dataframe"]
    question = state["question"]

    summary = summarize_dataframe(df)
    profile = state.get("dataset_profile", profile_dataframe(df))
    intent = state.get("intent", "descriptive")
    method = state.get("method", "pandas")

    if method == "duckdb":
        sql, metric_label = _build_duckdb_sql(df, question)
        result = run_duckdb_query(df, sql)
        preview = result.head(10).to_string(index=False)
        state["analysis"] = (
            f"Direct Answer: {metric_label.capitalize()} was executed for '{question}'.\n\n"
            f"Evidence: {preview}\n\n"
            f"Method Note: Used DuckDB to run a deterministic SQL query against the dataframe.\n\n"
            f"Assumptions/Interpretation: The analysis is based on the current dataset snapshot with {summary['rows']} rows and {summary['columns']} columns."
        )
        state["sql"] = sql
        state["result_table"] = result.head(10).to_dict(orient="records")
        state["chart"] = _build_chart_for_result(result, metric_label)
    else:
        analysis, chart = _run_pandas_analysis(df, question)
        state["analysis"] = analysis
        state["sql"] = ""
        if isinstance(chart, dict):
            table = chart.get("table")
            state["result_table"] = table.head(10).to_dict(orient="records") if isinstance(table, pd.DataFrame) else []
            if chart.get("kind") == "line" and isinstance(table, pd.DataFrame) and len(table.columns) >= 2:
                state["chart"] = make_line_chart(table, table.columns[0], table.columns[1])
            else:
                state["chart"] = None
        else:
            state["result_table"] = []
            state["chart"] = chart

    numeric_cols = ", ".join(profile.get("numeric_columns", [])) or "None"
    if "Numeric columns detected:" not in state["analysis"]:
        state["analysis"] += f"\n\nNumeric columns detected: {numeric_cols}."
    return state
