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


def test_execute_analysis_handles_monthly_trend_dates_in_mdy_format():
    df = pd.DataFrame(
        {
            "Order Date": ["1/3/2023", "1/10/2023", "2/5/2023", "2/20/2023"],
            "Sales": [100.0, 120.0, 90.0, 160.0],
            "Profit": [10.0, 15.0, 8.0, 20.0],
        }
    )

    state = {
        "question": "Show the monthly sales trend.",
        "dataframe": df,
        "dataset_profile": {"numeric_columns": ["Sales", "Profit"]},
        "intent": "trend",
        "method": "duckdb",
        "analysis": "",
        "sql": "",
        "chart": None,
        "errors": [],
    }

    result = _execute_analysis(state)

    assert result["sql"].strip()
    assert "month_bucket" in result["sql"].lower()
    assert "sales" in result["analysis"].lower()


def test_execute_analysis_handles_missing_groupby_columns_gracefully():
    df = pd.DataFrame(
        [
            {"region": "West", "sales": 100.0, "profit": 20.0},
            {"region": "East", "sales": 80.0, "profit": 10.0},
        ]
    )

    state = {
        "question": "What are the total profits by ship mode?",
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

    assert result["sql"] != "SELECT * FROM data LIMIT 5;"
    assert "ship mode" in result["analysis"].lower()
    assert "not" in result["analysis"].lower() or "not available" in result["analysis"].lower()


def test_profile_dataframe_detects_numeric_like_string_columns():
    df = pd.DataFrame(
        {
            "customer": ["A", "B", "C"],
            "sales_amount": ["100", "200", "300"],
            "profit_amount": ["10", "25", "40"],
            "discount_pct": ["0.1", "0.2", "0.3"],
            "order_id": ["1001", "1002", "1003"],
        }
    )

    profile = __import__("analytics.profiler", fromlist=["profile_dataframe"]).profile_dataframe(df)

    for column in ["sales_amount", "profit_amount", "discount_pct"]:
        assert column in profile["numeric_columns"]
    assert "order_id" not in profile["numeric_columns"]


def test_profile_dataframe_keeps_full_schema_in_context():
    df = pd.DataFrame(
        {
            "region": ["West", "East"],
            "sales": [100.0, 200.0],
            "profit": [10.0, 20.0],
        }
    )

    profile = __import__("analytics.profiler", fromlist=["profile_dataframe"]).profile_dataframe(df)

    assert profile["columns"] == ["region", "sales", "profit"]
