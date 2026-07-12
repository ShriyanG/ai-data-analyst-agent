"""Dataset profiling helpers."""

import pandas as pd


def profile_dataframe(df: pd.DataFrame) -> dict:
    """Return basic profile metadata used by the agent."""
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()

    return {
        "shape": df.shape,
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "missing_values": df.isna().sum().to_dict(),
    }
