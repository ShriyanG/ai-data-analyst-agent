"""Tooling helpers for Pandas, DuckDB, and plotting."""

from __future__ import annotations

from typing import Any

import duckdb
import pandas as pd


def run_duckdb_query(df: pd.DataFrame, sql: str) -> pd.DataFrame:
    """Execute SQL against a dataframe registered as `data` in DuckDB."""
    con = duckdb.connect(database=":memory:")
    try:
        con.register("data", df)
        return con.execute(sql).fetchdf()
    finally:
        con.close()


def summarize_dataframe(df: pd.DataFrame) -> dict[str, Any]:
    """Return lightweight schema and shape metadata."""
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
    }
