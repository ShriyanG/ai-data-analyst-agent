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


def _normalize_tokens(value: str) -> set[str]:
    tokens = {
        token
        for token in re.findall(r"[a-z0-9]+", value.lower())
        if token not in {"the", "a", "an", "by", "of", "for", "in", "on", "at", "to", "and", "or", "with", "what", "is", "are", "how", "which"}
    }

    expanded = set(tokens)
    for token in list(tokens):
        if token.endswith("ies") and len(token) > 4:
            expanded.add(token[:-3] + "y")
        if token.endswith("s") and len(token) > 3:
            expanded.add(token[:-1])
    return expanded


def _tokenize_question(question: str) -> set[str]:
    return _normalize_tokens(question)


def _choose_aggregation(question: str) -> tuple[str, str]:
    lower = question.lower()
    if any(token in lower for token in ["total", "sum", "overall", "grand total"]):
        return "SUM", "total"
    if any(token in lower for token in ["average", "avg", "mean"]):
        return "AVG", "average"
    if any(token in lower for token in ["count", "how many", "number of"]):
        return "COUNT", "count"
    if any(token in lower for token in ["median"]):
        return "MEDIAN", "median"
    if any(token in lower for token in ["maximum", "max", "highest", "largest", "top", "most"]):
        return "MAX", "maximum"
    if any(token in lower for token in ["minimum", "min", "lowest", "smallest", "bottom", "least"]):
        return "MIN", "minimum"
    return "SUM", "total"


def _extract_requested_dimension(question: str) -> Optional[str]:
    match = re.search(
        r"\bby\s+([a-z0-9_\- ]+?)(?:\s+(?:for|in|on|of|with|and|sorted|highest|lowest|average|total|count|limit|\?|$))",
        question.lower(),
    )
    if match:
        return match.group(1).strip()
    return None


def _find_matching_dimension(df: pd.DataFrame, requested_dimension: Optional[str], question_tokens: set[str]) -> Optional[str]:
    non_numeric_columns = [column for column in df.columns if not pd.api.types.is_numeric_dtype(df[column])]

    if requested_dimension:
        requested_norm = _normalize_name(requested_dimension)
        for column in non_numeric_columns:
            column_norm = _normalize_name(column)
            if requested_norm == column_norm or requested_norm in column_norm or column_norm in requested_norm:
                return column
        return None

    best_column = None
    best_score = 0
    for column in non_numeric_columns:
        column_tokens = _normalize_tokens(column)
        score = sum(1 for token in question_tokens if token in column_tokens)
        if score > best_score:
            best_score = score
            best_column = column
    return best_column if best_score > 0 else None


def _find_matching_metric(df: pd.DataFrame, question_tokens: set[str]) -> Optional[str]:
    numeric_columns = [column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])]
    if not numeric_columns:
        return None

    best_column = None
    best_score = 0
    for column in numeric_columns:
        column_tokens = _normalize_tokens(column)
        score = sum(1 for token in question_tokens if token in column_tokens)
        if score > best_score:
            best_score = score
            best_column = column
    return best_column if best_score > 0 else None


def _build_duckdb_sql(df: pd.DataFrame, question: str) -> tuple[str, str]:
    lower_question = question.lower()
    question_tokens = _tokenize_question(question)

    requested_dimension = _extract_requested_dimension(question)
    dimension_col = _find_matching_dimension(df, requested_dimension, question_tokens)
    if requested_dimension and dimension_col is None:
        return (
            "SELECT 'The requested dimension is not available in this dataset.' AS status, 'No matching column found' AS missing_column;",
            "missing requested dimension",
        )

    metric_col = _find_matching_metric(df, question_tokens)
    if metric_col is None:
        return (
            "SELECT 'No numeric measure was found for this question.' AS status, 'No matching column found' AS missing_column;",
            "missing numeric metric",
        )

    aggregation, label = _choose_aggregation(question)
    if "by" in lower_question and dimension_col is not None:
        aggregate_sql = f"{aggregation}({_quote_identifier(metric_col)}) AS {label}_{_normalize_name(metric_col)}"
        return (
            (
                f"SELECT {_quote_identifier(dimension_col)} AS dimension, "
                f"{aggregate_sql} FROM data GROUP BY 1 ORDER BY 2 DESC"
            ),
            f"{label} of {metric_col} by {dimension_col}",
        )

    if "trend" in lower_question or "month" in lower_question or "quarter" in lower_question or "date" in lower_question:
        date_candidates = [
            column
            for column in df.columns
            if "date" in _normalize_name(column) or "month" in _normalize_name(column) or "year" in _normalize_name(column)
        ]
        if date_candidates:
            date_col = date_candidates[0]
            return (
                (
                    f"SELECT DATE_TRUNC('month', CAST({_quote_identifier(date_col)} AS DATE)) AS month_bucket, "
                    f"{aggregation}({_quote_identifier(metric_col)}) AS {label}_{_normalize_name(metric_col)} "
                    f"FROM data GROUP BY 1 ORDER BY 1"
                ),
                f"{label} trend over time",
            )

    return (
        (
            f"SELECT {aggregation}({_quote_identifier(metric_col)}) AS {label}_{_normalize_name(metric_col)} "
            f"FROM data"
        ),
        f"{label} of {metric_col}",
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
