# DuckDB External UI Guide

Connect to DuckDB databases using web UIs, CLI, and other tools for data exploration and analysis.

---

## Option 1: DuckDB Web UI (Built-in)

### Fastest Way - No Installation

If you switch to disk persistence:

```python
# reporting_engine.py
self.conn = duckdb.connect('duckdb/data.duckdb')
```

### Then use DuckDB CLI with Web UI:

```bash
# Install DuckDB (if not installed)
# macOS
brew install duckdb

# Linux
apt-get install duckdb

# Windows / or use pip
pip install duckdb
```

### Launch the Web UI:

```bash
# Navigate to your project directory
cd /Users/paramraghavan/dev/aws-one-view/projects/cloudability_cost_analyzer

# Open DuckDB with web UI
duckdb duckdb/data.duckdb -ui

# Output:
# ┌──────────────────────────────────────┐
# │ Open browser: http://localhost:8080  │
# └──────────────────────────────────────┘
```

### Web UI Features:
```
URL: http://localhost:8080
├── SQL Query Editor
├── Browse Tables
├── View Schema
├── Execute Queries
├── Download Results
└── View Query History
```

---

## Option 2: DuckDB Studio (Recommended)

Official web UI from DuckDB with better features.

### Install:
```bash
# Using npm/node
npm install -g duckdb-studio

# Or download from:
# https://github.com/duckdb-space/studio
```

### Launch with Database:
```bash
duckdb-studio duckdb/data.duckdb

# Opens at http://localhost:3000
```

### Features:
- ✅ SQL query editor
- ✅ Data visualization
- ✅ Schema browser
- ✅ Query history
- ✅ Export results
- ✅ Dark mode

---

## Option 3: Current In-Memory Setup (No Disk)

If you're using current in-memory setup:
```python
self.conn = duckdb.connect(':memory:')
```

You need to export data first:

### Step 1: Export to Disk
```python
# In a Python script or Flask route
import duckdb

# Create temporary database
conn = duckdb.connect('temp_data.duckdb')

# Load your CSVs
df = pd.read_csv('reports/cost_report.csv')
conn.register('cost_report', df)

# Now use web UI
# duckdb temp_data.duckdb -ui
```

---

## Option 4: DBeaver (Professional Tool)

### Install DBeaver:
```bash
# macOS
brew install dbeaver-community

# Linux
# Download from https://dbeaver.io/download/

# Windows
# Download from https://dbeaver.io/download/
```

### Connect to DuckDB:

1. Open DBeaver
2. Click "Database" → "New Database Connection"
3. Select "DuckDB"
4. Set path: `/path/to/duckdb/data.duckdb`
5. Click "Test Connection"
6. Click "Finish"

### Features:
```
├── SQL Editor
├── Visual Query Builder
├── Schema Browser
├── Data Export (CSV, JSON, SQL)
├── ERD Diagram
└── Performance Analysis
```

---

## Option 5: Python REPL (Interactive)

### Quick exploration in Python:

```python
import duckdb

# Connect to database
conn = duckdb.connect('duckdb/data.duckdb')

# List tables
print(conn.execute("SELECT * FROM information_schema.tables").fetch_all())

# Query data
result = conn.execute("""
    SELECT
        block_funding,
        SUM(total_cost) as total
    FROM cost_report
    GROUP BY block_funding
""").fetch_all()

print(result)

# Get as DataFrame
df = conn.execute("SELECT * FROM cost_report LIMIT 10").fetch_df()
print(df)
```

---

## Option 6: Jupyter Notebook

### Install:
```bash
pip install jupyter duckdb
```

### Create notebook:
```python
# In Jupyter cell
import duckdb
import pandas as pd

# Connect
conn = duckdb.connect('duckdb/data.duckdb')

# Query
result = conn.execute("""
    SELECT * FROM cost_report LIMIT 5
""").fetch_df()

# Display
result
```

---

## Option 7: Metabase (Full BI Tool)

### Install Docker image:
```bash
docker run -p 3000:3000 metabase/metabase
```

### Connect:
1. Open http://localhost:3000
2. Create account
3. Admin → Databases → Add Database
4. Select DuckDB
5. Set database path
6. Create dashboards

### Features:
```
├── Visual Query Builder
├── Dashboards
├── Alerts
├── Sharing
└── Team Collaboration
```

---

## Quick Comparison

| Tool | Setup | Web UI | SQL Editor | Easy |
|------|-------|--------|-----------|------|
| DuckDB CLI | 1 min | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| DuckDB Studio | 2 min | ✅ | ✅ | ⭐⭐⭐⭐ |
| DBeaver | 5 min | ❌ | ✅ | ⭐⭐⭐ |
| Python REPL | 1 min | ❌ | ❌ | ⭐⭐⭐⭐ |
| Jupyter | 3 min | ✅ | ✅ | ⭐⭐⭐⭐ |
| Metabase | 10 min | ✅ | ✅ | ⭐⭐⭐ |

---

## Step-by-Step: Enable DuckDB Web UI

### For Your Current Project:

#### Step 1: Switch to Disk Persistence (Optional but Recommended)

Edit `reporting_engine.py`:
```python
# Change line 35 from:
self.conn = duckdb.connect(':memory:')

# To:
from pathlib import Path
db_dir = Path('duckdb')
db_dir.mkdir(exist_ok=True)
self.conn = duckdb.connect(str(db_dir / 'data.duckdb'))
```

#### Step 2: Start Your Flask App

```bash
python3 reporting_engine.py

# This will:
# - Load CSVs
# - Create duckdb/data.duckdb file
# - Start Flask server on port 5445
```

#### Step 3: Open Web UI in Separate Terminal

```bash
# In new terminal
cd /Users/paramraghavan/dev/aws-one-view/projects/cloudability_cost_analyzer

# Option A: DuckDB CLI
duckdb duckdb/data.duckdb -ui

# Option B: DuckDB Studio (if installed)
duckdb-studio duckdb/data.duckdb
```

#### Step 4: Browse Your Data

Open http://localhost:8080 (or 3000 for Studio)

```
Dashboard:
├── Tables
│   ├── cost_report (1500+ rows)
│   ├── regions (10 rows)
│   ├── budgets (4 rows)
│   └── users (10 rows)
├── SQL Editor
├── Run Query
└── View Results
```

---

## Example Queries to Try

### In Web UI:

```sql
-- See all tables
SELECT * FROM information_schema.tables;

-- Count rows in each table
SELECT table_name, count(*) as row_count
FROM information_schema.columns
GROUP BY table_name;

-- Top users by cost
SELECT full_name, total_cost
FROM cost_report
ORDER BY total_cost DESC
LIMIT 10;

-- Cost by state
SELECT r.state, SUM(c.total_cost) as total
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
GROUP BY r.state
ORDER BY total DESC;

-- Budget performance
SELECT
    b.block_funding,
    b.budget_allocated,
    SUM(c.total_cost) as actual,
    (b.budget_allocated - SUM(c.total_cost)) as remaining
FROM cost_report c
JOIN budgets b ON c.block_funding = b.block_funding
GROUP BY b.block_funding, b.budget_allocated
ORDER BY actual DESC;
```

---

## Troubleshooting

### Error: "duckdb command not found"

**Solution:**
```bash
# Install DuckDB
pip install duckdb

# Or with brew (macOS)
brew install duckdb
```

### Error: "Database file not found"

**Solution:**
Make sure database file exists:
```bash
# Check if file exists
ls -la /path/to/duckdb/data.duckdb

# If not, start Flask app first
python3 reporting_engine.py

# This will create the database
```

### Can't access http://localhost:8080

**Solution:**
```bash
# Check if port is in use
lsof -i :8080

# Use different port
duckdb duckdb/data.duckdb -ui -p 8081

# Open http://localhost:8081
```

### In-Memory Database Shows No Data

**Solution:**
Switch to disk persistence:
```python
# reporting_engine.py line 35
self.conn = duckdb.connect('duckdb/data.duckdb')
```

---

## Recommended Setup

### For Development:
```bash
# Terminal 1: Start Flask app
python3 reporting_engine.py

# Terminal 2: Open DuckDB Web UI
duckdb duckdb/data.duckdb -ui
```

### Access:
- Flask Dashboard: http://localhost:5445
- DuckDB Web UI: http://localhost:8080
- Both running simultaneously!

---

## Data Exploration Workflow

```
1. Flask app loads CSVs and creates database
   ↓
2. Open DuckDB Web UI
   ↓
3. Browse tables and schema
   ↓
4. Write SQL queries
   ↓
5. Explore results
   ↓
6. Use insights for dashboard configs
   ↓
7. Create new tabs in Flask app
```

---

## Compare Approaches

### Flask Dashboard Only
```
Flask: http://localhost:5445
├── Pre-configured tabs
├── D3.js visualizations
└── Limited SQL (no direct access)
```

### DuckDB Web UI + Flask
```
Flask: http://localhost:5445          DuckDB: http://localhost:8080
├── Visualizations                    ├── Raw data exploration
├── Filtered views                    ├── Direct SQL queries
└── Business logic                    └── Schema inspection
```

---

## Quick Start Commands

### Fastest Setup (DuckDB CLI):
```bash
# Install
pip install duckdb

# Switch to disk persistence in reporting_engine.py (optional)

# Start Flask
python3 reporting_engine.py &

# Open Web UI
duckdb duckdb/data.duckdb -ui

# Open browser to http://localhost:8080
```

### Best UI Experience (DuckDB Studio):
```bash
# Install
npm install -g duckdb-studio

# Start Flask
python3 reporting_engine.py &

# Open Studio
duckdb-studio duckdb/data.duckdb

# Open browser to http://localhost:3000
```

---

## Summary

| Use Case | Tool |
|----------|------|
| Quick exploration | DuckDB CLI (`duckdb ... -ui`) |
| Better UI | DuckDB Studio |
| Professional analysis | DBeaver |
| Interactive analysis | Jupyter |
| Full BI suite | Metabase |
| Coding | Python REPL |

**Recommended:** DuckDB CLI (simplest) or DuckDB Studio (best UI)

All tools let you write SQL queries and explore your data directly without going through Flask!
