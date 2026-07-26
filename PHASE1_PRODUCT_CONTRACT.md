# Phase 1 Product Contract: AI Data Analyst Agent (v1)

## 1) One-Page Scope Definition (v1)

### Product Goal
Enable a non-technical user to upload a single CSV, ask a natural-language analytics question, and receive a useful, trustworthy answer with optional SQL and optional chart output.

### Target User
Business, product, and operations users who need fast exploratory insights without writing Python or SQL.

### In-Scope Workflow (End-to-End)
1. User uploads one CSV in the Streamlit app.
2. User asks one natural-language question.
3. Agent profiles data and selects deterministic analysis path (Pandas and/or DuckDB).
4. Agent returns:
   - Insight narrative (required)
   - SQL used (optional)
   - Chart (optional)
   - Clear fallback error when request cannot be completed

### v1 Technical Boundaries
- UI: Streamlit
- Orchestration: LangGraph
- Reasoning/tool routing: LangChain + Ollama
- Data operations: Pandas + DuckDB
- Visualization: Plotly and/or Matplotlib

### v1 Non-Goals
- Multi-file joins
- Persistent semantic model
- Automated dashboard generation
- Scheduled jobs, alerts, or background pipelines
- Enterprise RBAC or audit logging

---

## 2) Supported vs Out-of-Scope Question Types

### Supported (v1)
- Descriptive: totals, averages, counts, top/bottom N, breakdown by dimension
- Diagnostic (lightweight): contribution analysis ("which categories drove the change")
- Trend: daily/weekly/monthly time trends, growth/decline rate
- Outlier: highest/lowest entities, unusually high/low values via simple statistical thresholds
- Filtering and slicing: region, segment, category, date range, product

### Out-of-Scope (v1)
- Predictive forecasting and causal inference
- Advanced statistics (hypothesis testing, regression interpretation guarantees)
- "Why" questions requiring external context not in CSV
- Cross-dataset joins across multiple uploaded files
- Real-time streaming analytics
- Image/PDF/unstructured data analysis
- Guarantees for ambiguous metric definitions not present in column names or metadata

---

## 3) Response Contract (Required Output Shape)

Every successful answer must include:
1. **Direct Answer**: 1-3 sentence summary that directly addresses the question.
2. **Evidence**: Key numbers used in the conclusion (for example totals, percentages, deltas).
3. **Method Note**: Brief statement of how result was computed (Pandas or DuckDB aggregation/filter).
4. **Assumptions/Interpretation**: Any disambiguation performed (for example how "revenue" was mapped).

Optional fields:
1. **SQL** (when SQL path used): query text shown to user.
2. **Chart** (when visual materially helps): rendered figure with labeled axes/title.

If partially successful:
1. Return best-effort answer with explicit "confidence/limitation" note.
2. Provide concrete next-step prompt (for example ask user to clarify metric or date column).

---

## 4) Guardrails and Failure Handling Rules

### Guardrails
- Never fabricate columns, values, or time ranges.
- Only reference fields present in uploaded CSV.
- Prefer deterministic computation over free-form LLM claims.
- If metric mapping is ambiguous, ask for clarification or state assumption explicitly.
- For charts, ensure x/y columns exist and are type-compatible.

### Failure Handling
- Empty upload or parse failure:
  - Error: "CSV could not be read. Please upload a valid CSV file."
- Missing required columns for question intent:
  - Error: "I could not find required columns: <list>."
- Invalid analysis path or SQL execution error:
  - Error: "I could not complete this analysis due to a query/computation error," plus safe detail.
- No rows after filter:
  - Error: "No data matched the requested filters."
- Unsupported request class:
  - Error: "This request is out of scope for v1," and suggest nearest supported question.

### Error Quality Bar
Each error must be:
1. Human-readable
2. Specific about the failure reason
3. Actionable with one suggested next step

---

## 5) Measurable Success Criteria (Phase 1)

### Accuracy
- Benchmark exactness: >= 80% of benchmark questions judged correct by numeric/result match.
- No-fabrication rate: 100% on test set (no nonexistent columns/values referenced).

### Reliability
- End-to-end success rate: >= 95% of valid in-scope questions return a non-empty response object.
- Structured contract compliance: >= 98% responses include required fields (Direct Answer, Evidence, Method Note, Assumptions/Interpretation).
- Graceful failure compliance: 100% of failed runs return actionable error text (not raw stack traces).

### Latency
- p50 response time: <= 4 seconds on sample-size CSV (up to ~50k rows, moderate width).
- p95 response time: <= 8 seconds on same benchmark environment.

### Monitoring for Phase 1
Track per request:
- question type
- success/failure
- latency
- SQL executed (if any)
- error class (if failed)

---

## 6) Top 10 Benchmark Questions (v1)

### Descriptive
1. What is total sales by region, sorted highest to lowest?
2. Which 5 products generated the highest total profit?
3. What is the average order value by customer segment?

### Diagnostic
4. Month over month, which category contributed most to the overall sales decline in the worst month?
5. Which sub-categories have high sales but below-average profit margin?
6. For orders with discounts above 20%, how does average profit compare with orders at 20% or below?

### Trend
7. Plot monthly sales trend and identify the month with the highest growth rate.
8. How has profit margin changed quarter over quarter?

### Outlier
9. Which 10 orders are outliers for loss (most negative profit), and what common attributes do they share?
10. Are there any states with unusually high shipping cost relative to sales?

---

## Sign-Off Definition for Phase 1 Exit

Phase 1 is complete when:
- All benchmark questions run end-to-end,
- Success criteria thresholds are met,
- Failure responses are actionable,
- Contract format is consistently enforced in app outputs.
