import json
import duckdb
from flask import Flask, render_template, request, jsonify
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
import datetime as dt

app = Flask(__name__)

# Initialize DuckDB and load CSV at startup
DB_CONN = duckdb.connect(database=':memory:')
DB_CONN.execute("CREATE TABLE costs AS SELECT * FROM read_csv_auto('monthly_costs.csv')")


def load_config():
    with open('queries.json') as f:
        return json.load(f)


@app.route('/')
def index():
    config = load_config()
    cursor = DB_CONN.cursor()
    # Fetch unique values for both filters
    projects = [r[0] for r in cursor.execute("SELECT DISTINCT project FROM costs ORDER BY 1").fetchall()]
    cost_centers = [r[0] for r in cursor.execute("SELECT DISTINCT cost_center FROM costs ORDER BY 1").fetchall()]
    return render_template('index.html', tabs=config['tabs'], projects=projects, cost_centers=cost_centers)


def get_where_clause(request):
    """Helper to build dynamic SQL based on multi-select filters"""
    start_date = request.args.get('start_date', '1900-01-01')
    end_date = request.args.get('end_date', '2099-12-31')
    selected_projects = request.args.getlist('projects[]')
    selected_ccs = request.args.getlist('cost_centers[]')

    # Base conditions
    conditions = ["start_date >= ?", "end_date <= ?"]
    params = [start_date, end_date]

    # Dynamic Project Filter
    if selected_projects:
        placeholders = ",".join(["?"] * len(selected_projects))
        conditions.append(f"project IN ({placeholders})")
        params.extend(selected_projects)

    # Dynamic Cost Center Filter
    if selected_ccs:
        placeholders = ",".join(["?"] * len(selected_ccs))
        conditions.append(f"cost_center IN ({placeholders})")
        params.extend(selected_ccs)

    return " AND ".join(conditions), params


@app.route('/api/data/<tab_id>')
def get_data(tab_id):
    config = load_config()
    tab = next(t for t in config['tabs'] if t['id'] == tab_id)

    where_clause, params = get_where_clause(request)
    # We strip the hardcoded "project IN ({projects})" from queries.json and replace with our dynamic clause
    query = tab['query'].split("WHERE")[0] + f" WHERE {where_clause} GROUP BY 1"

    results = DB_CONN.cursor().execute(query, params).fetchall()
    return jsonify([{"label": r[0], "value": float(r[1])} for r in results])


@app.route('/api/summary')
def get_summary():
    start_date = request.args.get('start_date', '1900-01-01')
    end_date = request.args.get('end_date', '2099-12-31')
    selected_projects = request.args.getlist('projects[]')
    project_filter = "SELECT project FROM costs" if not selected_projects else ", ".join(
        [f"'{p}'" for p in selected_projects])

    query = f"""
        SELECT SUM(cost), COUNT(DISTINCT project), AVG(cost)
        FROM costs 
        WHERE start_date >= ? AND end_date <= ? AND project IN ({project_filter})
    """
    res = DB_CONN.cursor().execute(query, [start_date, end_date]).fetchone()
    return jsonify({
        "total": f"${res[0]:,.2f}" if res and res[0] else "$0.00",
        "project_count": res[1] if res else 0,
        "avg": f"${res[2]:,.2f}" if res and res[2] else "$0.00"
    })


@app.route('/api/forecast')
def get_forecast():
    # Fix for the strptime error: CAST to TIMESTAMP first
    query = """
        SELECT date_trunc('month', CAST(start_date AS TIMESTAMP)) as month, SUM(cost) as total
        FROM costs GROUP BY 1 ORDER BY 1
    """
    df = DB_CONN.cursor().execute(query).df()

    if df.empty: return jsonify({"history": [], "forecast": []})

    # Prepare data
    df['month'] = pd.to_datetime(df['month'])
    start_date = df['month'].min()
    df['days'] = (df['month'] - start_date).dt.days

    X = df[['days']].values
    y = df['total'].values
    model = LinearRegression().fit(X, y)

    # Forecast next 6 months
    last_day = df['days'].max()
    future_days = np.array([last_day + (i * 30) for i in range(1, 7)]).reshape(-1, 1)
    preds = model.predict(future_days)

    history = [{"date": d.strftime('%Y-%m-%d'), "value": v} for d, v in zip(df['month'], y)]
    forecast = [{"date": (start_date + dt.timedelta(days=int(d[0]))).strftime('%Y-%m-%d'), "value": max(0, p)}
                for d, p in zip(future_days, preds)]

    return jsonify({"history": history, "forecast": forecast})


if __name__ == '__main__':
    app.run(debug=True, port=5110)