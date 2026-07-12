# AI Data Analyst Agent

An agentic AI data analyst that uses local LLMs, LangGraph, Pandas, and DuckDB to analyze datasets, generate insights, and generate visualizations from natural language queries.

## Project Structure

```text
ai-data-analyst-agent/
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
├── app.py
├── agent/
├── data/
├── analytics/
├── visualizations/
├── evaluation/
└── screenshots/
```

## Features

- Natural language data analysis on CSV datasets
- Agentic workflow orchestration with LangGraph
- SQL-style analytics with DuckDB
- Data wrangling with Pandas
- Chart generation for exploratory insights
- Streamlit frontend for interactive use

## Quickstart

1. Create and activate a Python environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the Streamlit app:

   ```bash
   streamlit run app.py
   ```

## Notes

- The current codebase contains starter scaffolding for core modules.
- Replace placeholder logic with your preferred local LLM integration and tool behavior.
