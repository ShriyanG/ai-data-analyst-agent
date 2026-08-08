import pandas as pd

from agent.graph import _execute_analysis


def test_execute_analysis_runs_duckdb_tool_for_region_sales_query():
    df = pd.DataFrame(
        [
            {"region": "West", "sales": 100.0, "profit": 20.0},
            {"region": "East", "sales": 80.0, "profit": 10.0},
            {"region": "West", "sales": 40.0, "profit": 5.0},
        ]
    )

    state = {
        "question": "What is total sales by region, sorted highest to lowest?",
        "dataframe": df,
        "dataset_profile": {"numeric_columns": ["sales", "profit"]},
        "intent": "descriptive",
        "method": "duckdb",
        "analysis": "",
        "sql": "",
        "chart": None,
        "errors": [],
    }

    result = _execute_analysis(state)

    assert result["sql"].strip()
    assert "West" in result["analysis"]
    assert "East" in result["analysis"]
    assert "total sales" in result["analysis"].lower()
