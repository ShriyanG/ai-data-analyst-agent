"""Dataset profiling helpers."""

import re

import pandas as pd


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _looks_numeric(series: pd.Series) -> bool:
    """Return True when a column contains values that can be coerced to numeric form."""
    non_null = series.dropna()
    if non_null.empty:
        return False

    try:
        pd.to_numeric(non_null, errors="raise")
    except (TypeError, ValueError):
        return False
    return True


def _is_identifier_like(column: str, series: pd.Series) -> bool:
    """Treat ID/index columns as identifiers, not business metrics."""
    normalized = _normalize_name(column)
    if not normalized:
        return False

    id_tokens = [
        "rowid",
        "orderid",
        "customerid",
        "productid",
        "employeeid",
        "userid",
        "vendorid",
        "index",
        "id",
    ]
    if any(token in normalized for token in id_tokens):
        return True

    name_parts = set(normalized.split())
    if "row" in name_parts and "id" in name_parts:
        return True

    return False


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Return basic profile metadata used by the agent."""
    inferred_numeric = []
    inferred_categorical = []

    for column in df.columns:
        series = df[column]
        if _is_identifier_like(column, series):
            inferred_categorical.append(column)
            continue

        if _looks_numeric(series):
            inferred_numeric.append(column)
        else:
            inferred_categorical.append(column)

    return {
        "shape": df.shape,
        "columns": df.columns.tolist(),
        "numeric_columns": inferred_numeric,
        "categorical_columns": inferred_categorical,
        "missing_values": df.isna().sum().to_dict(),
    }
