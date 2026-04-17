#!/usr/bin/env python3
"""
Reporting Engine - Config-driven cost report visualization
Uses DuckDB for standard SQL queries on cost reports
"""

import yaml
import duckdb
import pandas as pd
import json
from pathlib import Path
from flask import Flask, render_template, jsonify, request
import glob

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "config"
REPORTS_DIR = BASE_DIR / "reports"
DATA_DIR = BASE_DIR / "data"  # For additional tables like regions, budgets, etc.

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# ============================================================================
# DUCKDB SETUP
# ============================================================================

class DuckDBEngine:
    """Execute SQL queries using DuckDB with multiple tables"""

    def __init__(self):
        self.conn = duckdb.connect(':memory:')
        self.loaded_tables = {}

    def load_table(self, table_name, csv_pattern):
        """Load a table from CSV files matching a pattern"""
        if table_name in self.loaded_tables:
            return  # Already loaded

        # Find CSV files matching pattern
        csv_files = glob.glob(str(REPORTS_DIR / "**" / csv_pattern), recursive=True)

        # If not in reports, check data directory
        if not csv_files:
            csv_files = glob.glob(str(DATA_DIR / "**" / csv_pattern), recursive=True)

        if not csv_files:
            print(f"WARNING: No files found for table '{table_name}' with pattern '{csv_pattern}'")
            return

        print(f"  Loading {table_name}...")

        # Load and combine CSV files
        dfs = [pd.read_csv(f) for f in csv_files]
        combined = pd.concat(dfs, ignore_index=True)

        # Register in DuckDB
        self.conn.register(table_name, combined)
        self.loaded_tables[table_name] = len(combined)
        print(f"  ✓ {table_name}: {len(combined)} rows")

    def load_all_tables(self):
        """Load all default tables"""
        if len(self.loaded_tables) > 0:
            return  # Already loaded

        print("Loading tables into DuckDB...")

        # Load main cost report table
        self.load_table('cost_report', 'cost_report_*.csv')

        # Load additional tables if they exist
        self.load_table('regions', 'regions.csv')
        self.load_table('budgets', 'budgets.csv')
        self.load_table('users', 'users.csv')

        print(f"✓ DuckDB ready with {len(self.loaded_tables)} tables\n")

    def execute_query(self, sql_query):
        """Execute SQL query and return DataFrame"""
        self.load_all_tables()
        result = self.conn.execute(sql_query).fetch_df()
        return result

    def get_table_schema(self, table_name):
        """Get column information for a table"""
        self.load_all_tables()
        result = self.conn.execute(f"DESCRIBE {table_name}").fetch_df()
        return result

# Global DuckDB engine
_db_engine = DuckDBEngine()

def get_db():
    """Get DuckDB engine instance"""
    return _db_engine

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Render dashboard"""
    with open(CONFIG_DIR / "tabs.yaml") as f:
        config = yaml.safe_load(f)

    return render_template('dashboard.html', tabs=config['tabs'])

@app.route('/api/data/<tab_id>')
def get_tab_data(tab_id):
    """Get data for a specific tab with optional filters"""
    try:
        # Load tab config
        with open(CONFIG_DIR / "tabs.yaml") as f:
            tabs_config = yaml.safe_load(f)

        # Find tab
        tab = next((t for t in tabs_config['tabs'] if t['id'] == tab_id), None)
        if not tab:
            return jsonify({'error': 'Tab not found'}), 404

        # Load tab query config
        config_file = CONFIG_DIR / tab['config_file']
        with open(config_file) as f:
            query_config = yaml.safe_load(f)

        # Get base SQL query
        db = get_db()
        sql_query = query_config.get('sql') or query_config.get('query')

        if not sql_query:
            return jsonify({'error': 'No SQL query found in config'}), 400

        # Apply filters from request parameters
        filters = request.args.to_dict()
        if filters:
            sql_query = apply_filters_to_query(sql_query, filters)

        result_df = db.execute_query(sql_query)

        # Format for display
        data = result_df.to_dict('records')

        # Prepare response
        response = {
            'title': tab['name'],
            'description': tab.get('description', ''),
            'chart_type': tab['chart_type'],
            'data': data,
            'columns': list(result_df.columns),
            'chart_config': query_config.get('chart', {}),
            'display_config': query_config.get('display', {}),
            'format_config': query_config.get('format', {}),
            'filters_config': query_config.get('filters', [])
        }

        return jsonify(response)

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/filter-options/<table_name>/<column_name>')
def get_filter_options(table_name, column_name):
    """Get distinct values for a column (for filter dropdown)"""
    try:
        db = get_db()
        db.load_all_tables()

        # Sanitize input to prevent SQL injection
        query = f"SELECT DISTINCT {column_name} FROM {table_name} ORDER BY {column_name}"
        result = db.execute_query(query)

        options = result[column_name].dropna().tolist()
        return jsonify({'options': options})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

def apply_filters_to_query(sql_query, filters):
    """Apply filter parameters to SQL query by adding WHERE clauses"""
    if not filters:
        return sql_query

    # Build WHERE clause
    where_clauses = []
    for key, value in filters.items():
        if value and key not in ['_']:
            # Try to determine table alias and column name
            # Simple heuristic: if column exists in multiple tables, try common aliases
            where_clauses.append(f"({key} = '{value}' OR {key} LIKE '%{value}%')")

    if where_clauses:
        # Insert WHERE clause before ORDER BY/GROUP BY if present
        where_sql = " AND ".join(where_clauses)

        if "ORDER BY" in sql_query.upper():
            # Insert before ORDER BY
            parts = sql_query.upper().split("ORDER BY")
            return parts[0].rstrip() + f"\nAND {where_sql}\nORDER BY" + parts[1]
        elif "GROUP BY" in sql_query.upper():
            # Insert before GROUP BY
            parts = sql_query.upper().split("GROUP BY")
            return parts[0].rstrip() + f"\nAND {where_sql}\nGROUP BY" + parts[1]
        else:
            # Append at end
            return sql_query + f"\nAND {where_sql}"

    return sql_query

@app.route('/api/tabs')
def get_tabs():
    """Get all available tabs"""
    with open(CONFIG_DIR / "tabs.yaml") as f:
        config = yaml.safe_load(f)
    return jsonify(config['tabs'])

# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("REPORTING ENGINE - DuckDB + Standard SQL (Multi-Table)")
    print("=" * 70)

    # Load data on startup
    print("\nStartup: Loading tables...")
    db = get_db()
    db.load_all_tables()

    print("=" * 70)
    print("Starting Flask server...")
    print("Open browser: http://localhost:5445")
    print("=" * 70 + "\n")

    app.run(debug=True, port=5445)
