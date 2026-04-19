import json
import duckdb
from flask import Flask, render_template, request, jsonify

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
    # Get unique projects for the filter dropdown
    projects = [r[0] for r in DB_CONN.execute("SELECT DISTINCT project FROM costs").fetchall()]
    return render_template('index.html', tabs=config['tabs'], projects=projects)


@app.route('/api/data/<tab_id>')
def get_data(tab_id):
    config = load_config()
    tab = next(t for t in config['tabs'] if t['id'] == tab_id)

    # Get filters from request
    start_date = request.args.get('start_date', '1900-01-01')
    end_date = request.args.get('end_date', '2099-12-31')
    selected_projects = request.args.getlist('projects[]')

    # Handle 'All Projects' logic
    if not selected_projects:
        project_placeholder = "SELECT project FROM costs"
    else:
        project_placeholder = ", ".join([f"'{p}'" for p in selected_projects])

    # Format the query with the project list
    final_query = tab['query'].replace("{projects}", project_placeholder)

    # Execute query
    results = DB_CONN.execute(final_query, [start_date, end_date]).fetchall()

    # Convert to JSON-friendly format
    data = [{"label": r[0], "value": float(r[1])} for r in results]
    return jsonify(data)


# Add this route to your existing app.py
@app.route('/api/summary')
def get_summary():
    start_date = request.args.get('start_date', '1900-01-01')
    end_date = request.args.get('end_date', '2099-12-31')
    selected_projects = request.args.getlist('projects[]')

    project_filter = "SELECT project FROM costs" if not selected_projects else ", ".join(
        [f"'{p}'" for p in selected_projects])

    query = f"""
        SELECT 
            SUM(cost) as total_cost, 
            COUNT(DISTINCT project) as project_count,
            AVG(cost) as avg_transaction
        FROM costs 
        WHERE start_date >= ? AND end_date <= ? AND project IN ({project_filter})
    """
    # Create a local cursor for this specific request
    cursor = DB_CONN.cursor()

    try:
        # Use the cursor instead of the global DB_CONN
        res = cursor.execute(query, [start_date, end_date]).fetchone()

        if res is None:
            return jsonify({"total": "$0.00", "project_count": 0, "avg": "$0.00"})

        return jsonify({
            "total": f"${res[0]:,.2f}" if res[0] is not None else "$0.00",
            "project_count": res[1] or 0,
            "avg": f"${res[2]:,.2f}" if res[2] is not None else "$0.00"
        })
    finally:
        cursor.close()


if __name__ == '__main__':
    app.run(debug=True, port=5110)
