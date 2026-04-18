# Dynamic Column Filters Guide

Add interactive filters to your dashboards to let users drill down by state, VP, funding block, or any column!

---

## Overview

Dynamic filters let you:
- ✅ Filter by any column from any table
- ✅ Multiple filters per tab
- ✅ Filters show dropdown with distinct values
- ✅ Chart updates instantly when filter changes
- ✅ All configured in YAML (no code changes!)

---

## How It Works

```
User selects filter value
       ↓
Filter dropdowns populated from table
       ↓
User changes filter
       ↓
JavaScript adds filter to API call
       ↓
Backend modifies SQL WHERE clause
       ↓
New data returned
       ↓
Chart updates automatically
```

---

## Setup: Add Filters to Config

### Example 1: Single Filter (State)

**File:** `config/cost_by_state_filtered.yaml`

```yaml
# SQL Query
sql: |
  SELECT
    r.state,
    SUM(c.total_cost) as total_cost,
    COUNT(DISTINCT c.user_id) as user_count
  FROM cost_report c
  JOIN regions r ON c.user_id = r.user_id
  GROUP BY r.state
  ORDER BY total_cost DESC

# Add filters section
filters:
  - column: "state"           # Column name to filter
    table: "regions"          # Which table it's from
    label: "State"            # Display label in UI
    type: "dropdown"          # Filter type

chart:
  title: "Cost by State"
  x_axis: "state"
  y_axis: "total_cost"

format:
  currency: true
```

**Result:**
```
┌─ Cost by State ─────────────────┐
│ State: [All States ▼]           │
│                                 │
│  ┌─────────────────────────────┐
│  │ CA: $45,000                 │
│  │ NY: $30,000                 │
│  │ TX: $25,000                 │
│  └─────────────────────────────┘
└─────────────────────────────────┘
```

### Example 2: Multiple Filters

**File:** `config/cost_by_vp_filtered.yaml`

```yaml
sql: |
  SELECT
    vp,
    SUM(total_cost) as total_cost,
    COUNT(DISTINCT user_id) as user_count
  FROM cost_report
  GROUP BY vp
  ORDER BY total_cost DESC

# Multiple filters
filters:
  - column: "vp"
    table: "cost_report"
    label: "VP"
    type: "dropdown"

  - column: "state"
    table: "regions"
    label: "State"
    type: "dropdown"

  - column: "block_funding"
    table: "cost_report"
    label: "Funding Block"
    type: "dropdown"

chart:
  title: "Cost by VP (Filtered)"
  x_axis: "vp"
  y_axis: "total_cost"
```

**Result:**
```
┌─ Cost by VP (Filtered) ──────────────────────────────┐
│ VP: [All VPs ▼]                                      │
│ State: [All States ▼]                                │
│ Funding Block: [All Blocks ▼]  [Reset Filters]      │
│                                                      │
│  ┌──────────────────────────────────────────────────┐
│  │ VP1: $50,000                                     │
│  │ VP2: $30,000                                     │
│  │ VP3: $20,000                                     │
│  └──────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────┘
```

---

## Filter Configuration Options

### Basic Structure

```yaml
filters:
  - column: "column_name"        # Required: Column to filter
    table: "table_name"          # Required: Table containing column
    label: "Display Label"       # Optional: Label shown to user
    type: "dropdown"             # Type (currently only 'dropdown')
```

### Properties

| Property | Required | Example | Description |
|----------|----------|---------|-------------|
| `column` | ✅ Yes | `"state"` | Column name in table |
| `table` | ✅ Yes | `"regions"` | Table name (`cost_report`, `regions`, `budgets`, `users`) |
| `label` | ❌ No | `"State"` | Display label in UI (defaults to column name) |
| `type` | ✅ Yes | `"dropdown"` | Filter type (currently only `"dropdown"`) |

---

## Real Examples

### Example 1: Cost by Funding Block, Filter by State

**Config:** `config/funding_block_by_state.yaml`

```yaml
sql: |
  SELECT
    c.block_funding,
    SUM(c.total_cost) as total_cost,
    COUNT(DISTINCT c.user_id) as user_count
  FROM cost_report c
  GROUP BY c.block_funding
  ORDER BY total_cost DESC

filters:
  - column: "state"
    table: "regions"
    label: "Filter by State"
    type: "dropdown"
  - column: "region"
    table: "regions"
    label: "Filter by Region"
    type: "dropdown"

chart:
  title: "Cost by Funding Block"
  x_axis: "block_funding"
  y_axis: "total_cost"
  show_values: true

display:
  type: "both"

format:
  currency: true
```

**Behavior:**
- User opens dashboard
- Sees "Filter by State" and "Filter by Region" dropdowns
- Selects "CA" for state
- SQL becomes: `... WHERE state = 'CA'`
- Chart updates to show only CA costs

### Example 2: Budget vs Actual with Department Filter

**Config:** `config/budget_by_department.yaml`

```yaml
sql: |
  SELECT
    b.block_funding,
    b.budget_allocated,
    SUM(c.total_cost) as actual_spend
  FROM cost_report c
  JOIN budgets b ON c.block_funding = b.block_funding
  WHERE b.fiscal_year = 2026
  GROUP BY b.block_funding, b.budget_allocated
  ORDER BY actual_spend DESC

filters:
  - column: "department"
    table: "users"
    label: "Department"
    type: "dropdown"
  - column: "block_funding"
    table: "cost_report"
    label: "Funding Block"
    type: "dropdown"

chart:
  title: "Budget vs Actual by Department"
  x_axis: "block_funding"
  y_axis: "actual_spend"
  show_values: true

format:
  currency: true
```

### Example 3: Regional Performance with Multi-Select

**Config:** `config/regional_analysis.yaml`

```yaml
sql: |
  SELECT
    r.region,
    r.team_location,
    COUNT(DISTINCT c.user_id) as employee_count,
    SUM(c.total_cost) as total_cost,
    AVG(c.efficient_score) as avg_efficiency
  FROM cost_report c
  JOIN regions r ON c.user_id = r.user_id
  GROUP BY r.region, r.team_location
  ORDER BY total_cost DESC

filters:
  - column: "region"
    table: "regions"
    label: "Region"
  - column: "team_location"
    table: "regions"
    label: "Office Location"
  - column: "block_funding"
    table: "cost_report"
    label: "Funding Block"

chart:
  title: "Regional Performance Analysis"
  x_axis: "region"
  y_axis: "total_cost"

display:
  type: "both"

format:
  currency: true
```

---

## How Filters Work Behind the Scenes

### Step 1: Filter Options Loaded
```javascript
// JavaScript calls this API
fetch('/api/filter-options/regions/state')

// Backend returns:
{
  "options": ["CA", "NY", "TX", "WA", "IL", "GA"]
}

// UI renders dropdown:
<select>
  <option value="">All States</option>
  <option value="CA">CA</option>
  <option value="NY">NY</option>
  ...
</select>
```

### Step 2: User Selects Filter Value
```javascript
// User selects "CA"
// JavaScript detects change and calls:
fetch('/api/data/cost_by_state?state=CA')
```

### Step 3: Backend Modifies SQL
```python
# Original SQL:
SELECT r.state, SUM(c.total_cost) as total_cost
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
GROUP BY r.state

# After filter applied:
SELECT r.state, SUM(c.total_cost) as total_cost
FROM cost_report c
JOIN regions r ON c.user_id = r.user_id
GROUP BY r.state
AND state = 'CA'  # <- Filter added!
```

### Step 4: Chart Updates
```javascript
// New data returned:
[{ state: "CA", total_cost: 45000 }]

// Chart re-renders with only CA data
```

---

## Filter Behavior

### Empty Selection (Default)
```yaml
filters:
  - column: "state"
    table: "regions"
    label: "State"
```

**Dropdown shows:**
```
[All States ▼]  <- Default, no filter applied
[CA]
[NY]
[TX]
...
```

When "All States" selected → No filter applied → Show all data

### When Filter Applied
When user selects "CA":
1. Dropdown shows "CA" selected
2. Filter parameter added to API call: `?state=CA`
3. SQL WHERE clause modified
4. New data returned and chart updates

### Reset Button
```
[State: CA ▼] [Reset Filters]
```

Clicking "Reset Filters" clears all filters and reloads data.

---

## Available Tables for Filtering

### cost_report columns:
```
user_id, full_name, block_funding, vp, cpu_mean, gpu_mean, memory_mean,
utilized_cost, idle_cost, cost_by_fair_share, efficient_score,
cluster_cost, cpu_fair_share, artifactory_cost, license_cost,
platform_cost, aws_service_cost, total_cost, is_new_user
```

### regions columns (if data/regions.csv exists):
```
user_id, state, city, region, team_location
```

### budgets columns (if data/budgets.csv exists):
```
block_funding, budget_allocated, budget_spent, budget_owner, fiscal_year
```

### users columns (if data/users.csv exists):
```
user_id, employee_id, department, manager_id, hire_date, status
```

---

## Common Filter Scenarios

### Scenario 1: Filter by Geography
```yaml
filters:
  - column: "state"
    table: "regions"
    label: "State"
  - column: "region"
    table: "regions"
    label: "Region"
  - column: "team_location"
    table: "regions"
    label: "Office Location"
```

### Scenario 2: Filter by Organization
```yaml
filters:
  - column: "block_funding"
    table: "cost_report"
    label: "Funding Block"
  - column: "vp"
    table: "cost_report"
    label: "Vice President"
  - column: "department"
    table: "users"
    label: "Department"
```

### Scenario 3: Filter by Time/Status
```yaml
filters:
  - column: "fiscal_year"
    table: "budgets"
    label: "Fiscal Year"
  - column: "status"
    table: "users"
    label: "Employee Status"
  - column: "is_new_user"
    table: "cost_report"
    label: "New User"
```

### Scenario 4: Combined
```yaml
filters:
  - column: "region"
    table: "regions"
    label: "Region"
  - column: "block_funding"
    table: "cost_report"
    label: "Funding Block"
  - column: "department"
    table: "users"
    label: "Department"
  - column: "fiscal_year"
    table: "budgets"
    label: "Fiscal Year"
```

---

## Troubleshooting

### Filter Dropdown Shows "No Options"
```
State: [All States ▼]  <- No options appear
```

**Causes:**
- Table doesn't exist (check data files)
- Column name is wrong
- Data hasn't loaded yet

**Solution:**
1. Check CSV file exists: `data/regions.csv`
2. Verify column name matches header: `state`
3. Wait for initial load (watch browser console)

### Filter Applied But Chart Doesn't Change
**Cause:** SQL query not using the filtered column

**Solution:**
Make sure filtered column is in WHERE clause:
```yaml
sql: |
  SELECT state, cost FROM data
  WHERE state = ?  # Must be queryable
```

### "Column Not Found" Error
```
Error: column_name not found
```

**Solution:**
- Check column exists in table
- Use correct table name in filters config
- Verify CSV header matches column name

---

## Best Practices

✅ **DO:**
- Use meaningful labels: `"State"` instead of `"state"`
- Order filters from broad to narrow: Region → State → City
- Test filters with different values
- Document in comments which table each filter comes from

❌ **DON'T:**
- Use spaces in column names (use `block_funding` not `Block Funding`)
- Filter on columns not in the data
- Create filters for read-only columns
- Forget to include filtered columns in your SQL

---

## Summary

| Feature | Status |
|---------|--------|
| Single filters | ✅ Supported |
| Multiple filters | ✅ Supported |
| Filter by any column | ✅ Supported |
| Dynamic dropdowns | ✅ Supported |
| Reset filters | ✅ Supported |
| Multi-select | ⏳ Planned |
| Date range filters | ⏳ Planned |
| Search filters | ⏳ Planned |

Just add a `filters:` section to your YAML config and watch the magic happen! 🎉

For examples, see:
- `config/cost_by_vp_filtered.yaml`
- `config/cost_by_location_filtered.yaml`
