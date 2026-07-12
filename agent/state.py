"""State schema for the data analyst agent."""

from typing import Any, Optional, TypedDict

import pandas as pd


class AgentState(TypedDict):
    question: str
    dataframe: pd.DataFrame
    analysis: str
    sql: str
    chart: Optional[Any]
    errors: list[str]
