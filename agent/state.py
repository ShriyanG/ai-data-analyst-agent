"""State schema for the data analyst agent."""

from typing import Any, Optional, TypedDict

import pandas as pd


class AgentState(TypedDict):
    question: str
    dataframe: pd.DataFrame
    dataset_profile: dict[str, Any]
    intent: str
    method: str
    analysis: str
    sql: str
    result_table: list[dict[str, Any]]
    chart: Optional[Any]
    errors: list[str]
