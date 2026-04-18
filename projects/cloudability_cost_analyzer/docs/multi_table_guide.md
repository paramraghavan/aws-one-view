# Multi-Table Guide - DuckDB with JOINs

Learn how to work with multiple tables and perform JOINs in the Reporting Engine.

---

## Table Structure

The Reporting Engine now supports multiple tables:

### 1. **cost_report** (Default - Main Table)
```
Columns: user_id, full_name, block_funding, vp, cpu_mean, gpu_mean, memory_mean,
         utilized_cost, idle_cost, cost_by_fair_share, efficient_score,
         cluster_cost, cpu_fair_share, artifactory_cost, license_cost,
         platform_cost, aws_service_cost, total_cost, is_new_user
```

### 2. **regions** (Optional - New)
```
Columns: user_id, state, city, region, team_location
```

### 3. **budgets** (Optional - New)
```
Columns: block_funding, budget_allocated, budget_spent, budget_owner, fiscal_year
```

### 4. **users** (Optional - New)
```
Columns: user_id, employee_id, department, manager_id, hire_date, status
```

---

## File Structure

```
cloudability_cost_analyzer/
├── reports/                    # Cost report CSVs (cost_report_*.csv)
├── data/                       # Additional tables (NEW)
│   ├── regions.csv            # User location data
│   ├── budgets.csv            # Budget allocations
│   └── users.csv              # User information
└── config/
    └── *.yaml                 # SQL queries with JOINs
```

---

## Setup: Create Sample Tables

### Create `data/regions.csv`

```csv
user_id,state,city,region,team_location
user001,CA,San Francisco,West,SF HQ
user002,CA,San Francisco,West,SF HQ
user003,NY,New York,East,NYC Office
user004,NY,New York,East,NYC Office
user005,TX,Austin,South,Austin Hub
```

Store at: `/Users/paramraghavan/dev/aws-one-view/projects/cloudability_cost_analyzer/data/regions.csv`

### Create `data/budgets.csv`

```csv
block_funding,budget_allocated,budget_spent,budget_owner,fiscal_year
Engineering,500000,450000,Alice Smith,2026
Product,300000,280000,Bob Jones,2026
Research,200000,180000,Carol White,2026
Operations,150000,140000,David Brown,2026
```

Store at: `/Users/paramraghavan/dev/aws-one-view/projects/cloudability_cost_analyzer/data/budgets.csv`

### Create `data/users.csv`

```csv
user_id,employee_id,department,manager_id,hire_date,status
user001,EMP001,Engineering,mgr001,2020-01-15,active
user002,EMP002,Engineering,mgr001,2021-03-20,active
user003,EMP003,Product,mgr002,2019-06-10,active
user004,EMP004,Product,mgr002,2022-01-05,active
user005,EMP005,Research,mgr003,2021-11-12,active
```

Store at: `/Users/paramraghavan/dev/aws-one-view/projects/cloudability_cost_analyzer/data/users.csv`

---

## How Tables Are Loaded

### In `reporting_engine.py`

```python
class DuckDBEngine:
    def load_all_tables(self):
        """Load all tables"""
        self.load_table('cost_report', 'cost_report_*.csv')  # From reports/
        self.load_table('regions', 'regions.csv')            # From data/
        self.load_table('budgets', 'budgets.csv')            # From data/
        self.load_table('users', 'users.csv')                # From data/
```

---

## Query Examples with JOINs

### Example 1: Cost by State

**Show total cost per state**

```sql
SELECT
    r.state,
    r.region,
    COUNT(DISTINCT c.user_id) as user_count,
    SUM(c.total_cost) as total_cost
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
GROUP BY r.state, r.region
ORDER BY total_cost DESC
```

**In config file:**

```yaml
sql: |
  SELECT
    r.state,
    r.region,
    COUNT(DISTINCT c.user_id) as user_count,
    SUM(c.total_cost) as total_cost
  FROM cost_report c
  JOIN regions r ON c.user_id = r.user_id
  GROUP BY r.state, r.region
  ORDER BY total_cost DESC

chart:
  title: "Cost by State"
  x_axis: "state"
  y_axis: "total_cost"
  show_values: true
```

### Example 2: Budget vs Actual Spend

**Compare budget vs actual spending**

```sql
SELECT
    b.block_funding,
    b.budget_allocated,
    b.budget_spent,
    SUM(c.total_cost) as actual_spend,
    (SUM(c.total_cost) - b.budget_spent) as variance,
    ROUND((SUM(c.total_cost) / b.budget_allocated * 100), 2) as percent_of_budget
FROM cost_report c
JOIN budgets b ON c.block_funding = b.block_funding
WHERE b.fiscal_year = 2026
GROUP BY b.block_funding, b.budget_allocated, b.budget_spent
ORDER BY percent_of_budget DESC
```

### Example 3: Users by Department and Location

**Show users by department and location**

```sql
SELECT
    u.department,
    r.region,
    r.city,
    COUNT(*) as user_count,
    SUM(c.total_cost) as total_cost,
    AVG(c.efficient_score) as avg_efficiency
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
JOIN users u ON c.user_id = u.user_id
GROUP BY u.department, r.region, r.city
ORDER BY total_cost DESC
```

### Example 4: Top Locations by Spend

**Show most expensive office locations**

```sql
SELECT
    r.team_location,
    COUNT(DISTINCT c.user_id) as employee_count,
    SUM(c.total_cost) as total_spend,
    AVG(c.total_cost) as avg_cost_per_employee,
    SUM(c.total_cost) / COUNT(DISTINCT c.user_id) as cost_per_employee
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
GROUP BY r.team_location
ORDER BY total_spend DESC
```

### Example 5: Budget Performance by Region

**Compare budget allocation to actual spend by region**

```sql
SELECT
    r.region,
    b.block_funding,
    b.budget_allocated,
    SUM(c.total_cost) as actual_spend,
    (b.budget_allocated - SUM(c.total_cost)) as remaining_budget,
    ROUND((SUM(c.total_cost) / b.budget_allocated * 100), 1) as percent_spent
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
JOIN budgets b ON c.block_funding = b.block_funding
WHERE b.fiscal_year = 2026
GROUP BY r.region, b.block_funding, b.budget_allocated
ORDER BY percent_spent DESC
```

### Example 6: Employee Tenure vs Cost

**Show cost correlation with hire date**

```sql
SELECT
    EXTRACT(YEAR FROM CAST(u.hire_date AS DATE)) as hire_year,
    COUNT(*) as employee_count,
    AVG(c.total_cost) as avg_cost,
    SUM(c.total_cost) as total_cost,
    AVG(c.efficient_score) as avg_efficiency
FROM cost_report c
JOIN users u ON c.user_id = u.user_id
WHERE u.status = 'active'
GROUP BY hire_year
ORDER BY hire_year DESC
```

---

## JOIN Types Explained

### INNER JOIN (Default)
```sql
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
-- Returns only matching rows
```

### LEFT JOIN
```sql
FROM cost_report c
LEFT JOIN regions r ON c.user_id = r.user_id
-- Returns all cost_report rows, even if no matching region
```

### RIGHT JOIN
```sql
FROM cost_report c
RIGHT JOIN regions r ON c.user_id = r.user_id
-- Returns all regions rows, even if no matching cost_report
```

### FULL OUTER JOIN
```sql
FROM cost_report c
FULL OUTER JOIN regions r ON c.user_id = r.user_id
-- Returns all rows from both tables
```

---

## Multiple JOINs

Join 3+ tables:

```sql
SELECT
    c.user_id,
    c.full_name,
    r.city,
    r.region,
    b.block_funding,
    b.budget_allocated,
    c.total_cost,
    u.department,
    u.hire_date
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
JOIN budgets b ON c.block_funding = b.block_funding
JOIN users u ON c.user_id = u.user_id
WHERE c.total_cost > 10000
ORDER BY c.total_cost DESC
LIMIT 20
```

---

## Advanced Queries

### Subquery Example
```sql
SELECT
    r.region,
    COUNT(*) as user_count,
    SUM(c.total_cost) as total_cost
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
WHERE c.user_id IN (
    SELECT user_id FROM cost_report
    WHERE total_cost > (SELECT AVG(total_cost) FROM cost_report)
)
GROUP BY r.region
ORDER BY total_cost DESC
```

### Window Functions Example
```sql
SELECT
    r.state,
    c.full_name,
    c.total_cost,
    SUM(c.total_cost) OVER (PARTITION BY r.state) as state_total,
    ROW_NUMBER() OVER (PARTITION BY r.state ORDER BY c.total_cost DESC) as rank_in_state
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
WHERE ROW_NUMBER() OVER (PARTITION BY r.state ORDER BY c.total_cost DESC) <= 5
```

### CTE (Common Table Expression) Example
```sql
WITH regional_cost AS (
    SELECT
        r.region,
        SUM(c.total_cost) as total_cost,
        COUNT(*) as user_count
    FROM cost_report c
    JOIN regions r ON c.user_id = r.user_id
    GROUP BY r.region
)
SELECT
    region,
    total_cost,
    user_count,
    total_cost / user_count as avg_cost_per_user,
    (SELECT SUM(total_cost) FROM regional_cost) as grand_total
FROM regional_cost
ORDER BY total_cost DESC
```

---

## How Tables Are Loaded in Code

### Current Code

```python
def load_all_tables(self):
    """Load all tables"""
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

def load_table(self, table_name, csv_pattern):
    """Load a table from CSV files"""
    csv_files = glob.glob(...)  # Find matching CSV files
    dfs = [pd.read_csv(f) for f in csv_files]
    combined = pd.concat(dfs, ignore_index=True)
    self.conn.register(table_name, combined)  # Register in DuckDB
```

---

## Adding More Tables

### To add a new table:

1. **Create CSV file** in `data/` directory
   ```
   data/my_table.csv
   ```

2. **Update `reporting_engine.py`**
   ```python
   def load_all_tables(self):
       # ... existing code ...
       self.load_table('my_table', 'my_table.csv')
   ```

3. **Use in SQL queries**
   ```sql
   SELECT * FROM my_table
   JOIN cost_report c ON my_table.user_id = c.user_id
   ```

---

## Directory Structure After Setup

```
cloudability_cost_analyzer/
├── data/                          # NEW: Additional tables
│   ├── regions.csv               # User locations
│   ├── budgets.csv               # Budget info
│   ├── users.csv                 # User details
│   └── departments.csv           # (Add as needed)
├── reports/                       # Cost reports
│   ├── weekly/
│   │   ├── cost_report_2026_week_01.csv
│   │   └── ...
│   └── monthly/
│       ├── cost_report_2026_01.csv
│       └── ...
├── config/                        # Query configs
│   ├── tabs.yaml
│   ├── cost_by_state.yaml        # Uses JOIN
│   ├── budget_performance.yaml    # Uses JOIN
│   └── ...
├── reporting_engine.py            # Updated to load multiple tables
└── MULTI_TABLE_GUIDE.md          # This file
```

---

## Troubleshooting

### Table Not Found Error
```
ERROR: Table 'regions' not found
```

**Solution:**
- Check that `data/regions.csv` exists
- Verify CSV file has correct columns
- Check column names are lowercase

### Column Not Found Error
```
ERROR: Column 'city' not found
```

**Solution:**
- Check CSV header matches query column names
- Use correct table alias in JOIN: `r.city` not `c.city`

### No Results from JOIN
```sql
-- Problem: May be INNER JOIN excluding non-matching rows
SELECT * FROM cost_report c
JOIN regions r ON c.user_id = r.user_id

-- Solution: Try LEFT JOIN to see unmatched rows
SELECT * FROM cost_report c
LEFT JOIN regions r ON c.user_id = r.user_id
WHERE r.user_id IS NULL  -- Shows unmatched cost_report rows
```

### Performance Issues with Large Tables
```sql
-- Add LIMIT for quick test
SELECT * FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
LIMIT 100

-- Or use aggregate functions
SELECT COUNT(*) as total FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
```

---

## Summary

✅ **Multiple table support** - Load 2+ tables from CSV files
✅ **INNER, LEFT, RIGHT, FULL JOINs** - All standard SQL joins work
✅ **Subqueries & CTEs** - Complex queries supported
✅ **Window functions** - Advanced analytics possible
✅ **No code changes needed** - Just add CSV files and update YAML configs

Just add your CSV files to `data/` and write standard SQL JOINs in your configs!
