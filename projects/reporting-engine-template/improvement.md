Integrating AI and advanced analytics into a financial dashboard can move it from a "descriptive" tool (what happened)
to a "prescriptive" tool (what will happen and what to do).

Since you are already using **DuckDB** and **Flask**, you can implement several AI-lite and LLM features without complex
infrastructure.

### 1. Automated "Executive Insights" (LLM Integration)

Instead of making managers look at charts, use an LLM (like GPT-4 or Claude) to generate a 3-bullet summary of the data.

**How to implement:**

1. In your Python backend, fetch the same data as your charts.
2. Send a summarized version (JSON) to an LLM API with a prompt.

```python
# Example logic for a new /api/ai-insights endpoint
import openai


@app.route('/api/ai-insights')
def get_ai_insights():
    # 1. Get the raw data from DuckDB (summarized)
    data = DB_CONN.execute("SELECT cost_center, SUM(cost) FROM costs GROUP BY 1").fetchall()

    # 2. Construct a prompt
    prompt = f"Act as a CFO. Here is this month's spend data: {data}. "
             f"Identify the top 2 trends and 1 area for potential cost-saving."

    # 3. Call LLM (Pseudo-code)
    # response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
    # return jsonify({"insight": response.choices[0].message.content})
    return jsonify({
                       "insight": "• Engineering spend increased by 15% due to PROJ003.\n• Marketing is under-budget.\n• Action: Review 'Compute' usage in PROJ003."})
```

### 2. Statistical Anomaly Detection (AI-lite)

You don't need a heavy neural network to find "weird" spending. You can use the **Z-Score** method directly in your
DuckDB query to find days where spending was significantly higher than the average.

**Add this to your `queries.json`:**

```json
{
  "id": "anomalies",
  "label": "Spending Anomalies",
  "query": "WITH stats AS (SELECT AVG(cost) as mu, STDDEV(cost) as sigma FROM costs) SELECT start_date as label, cost as value FROM costs, stats WHERE ABS(cost - mu) > 2 * sigma"
}
```

*Logic: This flags any entry that is 2 standard deviations away from the mean.*

### 3. Predictive Forecasting

Add a "Forecast" report that predicts next month's spend using **Linear Regression**. Since you have `numpy` and
`scikit-learn` typically available in Python environments, you can train a small model on the fly.

**Python Logic:**

```python
from sklearn.linear_model import LinearRegression
import numpy as np


@app.route('/api/forecast')
def forecast():
    # Fetch historical daily totals
    df = DB_CONN.execute("SELECT start_date, SUM(cost) FROM costs GROUP BY 1 ORDER BY 1").df()

    # Convert dates to ordinal numbers for regression
    df['date_ordinal'] = pd.to_datetime(df['start_date']).map(dt.datetime.toordinal)

    X = df[['date_ordinal']]
    y = df['SUM(cost)']

    model = LinearRegression().fit(X, y)

    # Predict for next 30 days
    future_date = df['date_ordinal'].max() + 30
    prediction = model.predict([[future_date]])[0]

    return jsonify({"predicted_next_month": round(prediction, 2)})
```

### 4. "Talk to your Data" (Text-to-SQL)

This is the "Holy Grail" for management. You provide a text box where they type: *"Which project spent the most on
storage in March?"* and the AI writes the DuckDB SQL for them.

**The Workflow:**

1. **Prompt Engineering**: Send the database schema (table names and columns) to the LLM.
2. **User Question**: Send the user's string.
3. **Output**: Ask the LLM to return *only* valid SQL.
4. **Execution**: Pass that SQL directly into `DB_CONN.execute()`.

### Summary of Suggested UI Additions:

| Feature             | User Value                                                                  | Complexity |
|:--------------------|:----------------------------------------------------------------------------|:-----------|
| **Smart Labels**    | Automatically tag "High Spend" items in your lists using a red badge.       | Low        |
| **Clustering**      | Group similar "users" together to see who has similar spending habits.      | Medium     |
| **Trend Direction** | Add small "Up/Down" arrows next to KPIs comparing this month vs last month. | Low        |
| **Chatbot Sidebar** | A "Help" bot that answers questions about the specific CSV data.            | High       |

**Recommendation:** Start with **Anomaly Detection** (it's just a SQL query) and **AI Insights** (a simple API call), as
these provide the most "wow factor" for management with the least amount of code.