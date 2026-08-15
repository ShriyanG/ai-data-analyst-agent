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
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    return fig


def make_line_chart(df: pd.DataFrame, x_col: str, y_col: str):
    """Create a simple line chart figure."""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df[x_col], df[y_col], marker="o", linewidth=2.2, color="#2563eb")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"{y_col} over {x_col}")
    ax.grid(alpha=0.2)
    ax.tick_params(axis="x", rotation=25)
    fig.tight_layout()
    return fig
