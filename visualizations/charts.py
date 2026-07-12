"""Chart generation utilities."""

from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd


def make_bar_chart(df: pd.DataFrame, x_col: str, y_col: str):
    """Create a simple bar chart figure."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(df[x_col], df[y_col])
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"{y_col} by {x_col}")
    fig.tight_layout()
    return fig
