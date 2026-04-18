# Reporting Engine - Config-Driven Dashboard

A fully configurable reporting engine that slices and dices cost reports using SQL-like statements in YAML config files.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  YAML Config Files (SQL-like queries)               │
│  ├─ funding_block.yaml (group by funding block)    │
│  ├─ cost_by_vp.yaml (group by VP)                  │
│  ├─ top_users.yaml (top 10 users)                  │
│  └─ efficiency.yaml (efficiency scores)             │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  Flask App (reporting_engine.py)                    │
│  ├─ Load YAML configs                              │
│  ├─ Execute SQL-like queries on cost reports       │
│  ├─ Return JSON to frontend                        │
│  └─ Serve HTML dashboard                           │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│  HTML5 + D3.js Frontend (dashboard.html)            │
│  ├─ Tab navigation (one per config)                │
│  ├─ D3.js charting (bar, pie, line)                │
│  ├─ Interactive tables                             │
│  └─ Real-time data loading                         │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
pip install flask pyyaml pandas
```

### 2. Generate Mock Data

```bash
python3 generate_mock_data.py      # Generates test reports
python3 generate_reports_functional.py  # Generates cost reports
```

### 3. Start the Reporting Engine

```bash
python3 reporting_engine.py
```

Output:
```
======================================================================
REPORTING ENGINE - Config-Driven Dashboard
======================================================================

Startup: Loading data...
Loading cost reports...
✓ Loaded 21 reports, 1575 total rows

======================================================================
Starting Flask server...
Open browser: http://localhost:5000
======================================================================
```

### 4. Open Dashboard

Open your browser to: **http://localhost:5000**

## Config Files

### Main Configuration: `config/tabs.yaml`

Defines all tabs and data source:

```yaml
tabs:
  - name: "Cost by Funding Block"
    id: "funding_block_costs"
    description: "Total costs grouped by funding block"
    config_file: "funding_block.yaml"
    chart_type: "bar"
    color_scheme: "blue"
```

### Tab Configuration: `config/funding_block.yaml`

Defines the query and visualization for each tab:

```yaml
query:
  select:
    - "block_funding"
    - "sum(total_cost) as total_cost"
    - "count(user_id) as user_count"

  from: "cost_report"

  group_by: "block_funding"

  order_by: "total_cost DESC"

  filters:
    - column: "total_cost"
      operator: ">"
      value: 0

chart:
  title: "Total Cost by Funding Block"
  x_axis: "block_funding"
  y_axis: "total_cost"
  x_label: "Funding Block"
  y_label: "Total Cost ($)"
  show_values: true
```

## Query Syntax

The config files use SQL-like syntax:

### SELECT

```yaml
select:
  - "block_funding"
  - "sum(total_cost) as total_cost"     # Aggregations
  - "count(distinct user_id) as user_count"
  - "avg(total_cost) as avg_cost"
```

### FROM

```yaml
from: "cost_report"  # DataFrame name (always "cost_report")
```

### GROUP BY

```yaml
group_by: "block_funding"        # Single column
group_by: "block_funding, vp"    # Multiple columns
```

### WHERE (Filters)

```yaml
filters:
  - column: "total_cost"
    operator: ">"
    value: 1000
  - column: "block_funding"
    operator: "=="
    value: "Engineering"
```

**Operators**: `>`, `<`, `>=`, `<=`, `==`, `!=`

### ORDER BY

```yaml
order_by: "total_cost DESC"     # Descending
order_by: "user_count ASC"      # Ascending
```

### LIMIT

```yaml
limit: 10  # Get top 10
```

## Chart Types

### Bar Chart

```yaml
chart:
  title: "Cost by Funding Block"
  type: "bar"
  x_axis: "block_funding"
  y_axis: "total_cost"
  show_values: true
```

### Pie Chart

```yaml
chart:
  title: "Cost Distribution"
  type: "pie"
  x_axis: "block_funding"
  y_axis: "total_cost"
  show_percentage: true
```

### Line Chart

```yaml
chart:
  title: "Cost Trend"
  type: "line"
  x_axis: "week"
  y_axis: "total_cost"
```

## Display Options

### Show Both Chart and Table

```yaml
display:
  type: "both"  # Options: "chart", "table", "both"
  rows_per_page: 10
  sortable: true
  columns:
    - name: "user_id"
      label: "User ID"
      visible: true
    - name: "total_cost"
      label: "Total Cost"
      format: "currency"
```

## Formatting

### Currency Format

```yaml
format:
  currency: true
  decimal_places: 2
```

### Percentage Format

```yaml
format:
  add_percent_sign: true
  decimal_places: 1
```

## Adding a New Tab

### 1. Create Config File

Create `config/my_report.yaml`:

```yaml
query:
  select:
    - "vp"
    - "sum(total_cost) as total_cost"
  from: "cost_report"
  group_by: "vp"
  order_by: "total_cost DESC"

chart:
  title: "Cost by VP"
  x_axis: "vp"
  y_axis: "total_cost"
```

### 2. Add to Main Config

Edit `config/tabs.yaml`:

```yaml
tabs:
  - name: "Cost by VP"
    id: "cost_by_vp"
    description: "Total costs grouped by VP"
    config_file: "my_report.yaml"
    chart_type: "bar"
    color_scheme: "blue"
```

### 3. Restart Server

```bash
python3 reporting_engine.py
```

The new tab appears automatically!

## Real Examples

### Example 1: Cost by Funding Block

```yaml
query:
  select:
    - "block_funding"
    - "sum(total_cost) as total_cost"
    - "count(user_id) as user_count"
  from: "cost_report"
  group_by: "block_funding"
  order_by: "total_cost DESC"
```

**Result**: Bar chart showing total cost per funding block

### Example 2: Top 10 Users by Cost

```yaml
query:
  select:
    - "full_name"
    - "block_funding"
    - "total_cost"
    - "efficient_score"
  from: "cost_report"
  order_by: "total_cost DESC"
  limit: 10
```

**Result**: Table + Bar chart with top 10 users

### Example 3: Average Efficiency by VP

```yaml
query:
  select:
    - "vp"
    - "avg(efficient_score) as avg_efficiency"
    - "count(distinct user_id) as user_count"
  from: "cost_report"
  group_by: "vp"
  order_by: "avg_efficiency DESC"
```

**Result**: Bar chart showing efficiency per VP

### Example 4: Cost Distribution (Pie Chart)

```yaml
query:
  select:
    - "block_funding"
    - "sum(total_cost) as total_cost"
  from: "cost_report"
  group_by: "block_funding"
  order_by: "total_cost DESC"
  limit: 5

chart:
  type: "pie"
  show_percentage: true
```

**Result**: Pie chart showing cost breakdown

## Available Columns

Columns from the cost report you can use in queries:

```
user_id                 - User identifier
full_name              - User's full name
block_funding          - Funding block
vp                     - VP user reports to
cpu_mean               - Average CPU usage (vCPU)
gpu_mean               - Average GPU usage
memory_mean            - Average memory (GB)
utilized_cost          - Cost of used resources
idle_cost              - Cost of unused capacity
cost_by_fair_share     - Shared infrastructure cost
efficient_score        - Utilization percentage (0-100)
cluster_cost           - Total cluster cost
cpu_fair_share         - CPU allocation percentage
artifactory_cost       - Artifact repository cost
license_cost           - Software licensing cost
platform_cost          - Platform/infrastructure cost
aws_service_cost       - AWS service cost
total_cost             - Sum of all costs
is_new_user            - Whether user is new
```

## File Structure

```
cloudability_cost_analyzer/
├── reporting_engine.py          (Flask app)
├── config/
│   ├── tabs.yaml               (Main config - all tabs)
│   ├── funding_block.yaml       (Tab 1)
│   ├── funding_users.yaml       (Tab 2)
│   ├── cost_distribution.yaml   (Tab 3)
│   ├── top_users.yaml           (Tab 4)
│   ├── cost_by_vp.yaml          (Tab 5)
│   └── efficiency.yaml          (Tab 6)
├── templates/
│   └── dashboard.html           (HTML template)
└── static/
    ├── css/style.css           (Styling)
    └── js/dashboard.js         (JavaScript + D3.js)
```

## API Endpoints

### `/` - Dashboard

Returns the HTML dashboard with all tabs.

```
GET http://localhost:5000/
```

### `/api/tabs` - List Tabs

Returns all available tabs.

```
GET http://localhost:5000/api/tabs

Response:
[
  {
    "name": "Cost by Funding Block",
    "id": "funding_block_costs",
    "description": "Total costs grouped by funding block",
    "config_file": "funding_block.yaml",
    "chart_type": "bar",
    "color_scheme": "blue"
  },
  ...
]
```

### `/api/data/<tab_id>` - Get Tab Data

Returns data for a specific tab (executes query and prepares for display).

```
GET http://localhost:5000/api/data/funding_block_costs

Response:
{
  "title": "Cost by Funding Block",
  "description": "Total costs grouped by funding block",
  "chart_type": "bar",
  "data": [
    {"block_funding": "Engineering", "total_cost": 50000, "user_count": 25},
    {"block_funding": "Product", "total_cost": 30000, "user_count": 15},
    ...
  ],
  "columns": ["block_funding", "total_cost", "user_count"],
  "chart_config": {...},
  "display_config": {...},
  "format_config": {...}
}
```

## Troubleshooting

### No reports found

**Problem**: "No data available" error

**Solution**:
```bash
# Generate mock data first
python3 generate_mock_data.py

# Generate cost reports
python3 generate_reports_functional.py

# Then start engine
python3 reporting_engine.py
```

### Column not found

**Problem**: "KeyError: 'column_name'"

**Solution**: Check column name in config matches available columns (see "Available Columns" section)

### Query syntax error

**Problem**: Charts not rendering

**Solution**: Check YAML syntax in config file
- Use proper indentation (2 spaces)
- Quote string values
- Check column names are correct

## Performance

- **Data loading**: ~1-2 seconds (21 reports, 1500 rows)
- **Query execution**: <100ms
- **Rendering**: <500ms
- **Memory usage**: ~50 MB

## Customization

### Change Colors

Edit `static/css/style.css`:

```css
.bar {
    fill: #4CAF50;  /* Change color */
    opacity: 0.8;
}
```

### Change Chart Height

Edit `config/tabs.yaml`:

```yaml
chart_options:
  height: 500  # was 400
  width: 1000  # was 800
```

### Add New Aggregation Function

Edit `reporting_engine.py` QueryEngine class to add support for:
- `min()`, `max()`
- `std()` (standard deviation)
- `var()` (variance)
- Custom functions

## Summary

This reporting engine is fully configurable through YAML files. You can:

✅ Create unlimited tabs
✅ Define custom queries with GROUP BY, WHERE, ORDER BY, LIMIT
✅ Use multiple aggregation functions
✅ Display as bar/pie/line charts or tables
✅ Format numbers as currency or percentages
✅ Show both charts and tables
✅ All without touching Python code!

Simply edit YAML configs and refresh the browser.

