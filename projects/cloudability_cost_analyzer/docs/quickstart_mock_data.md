# Quick Start: Using Mock Data

**Time to get started: ~2 minutes**

Mock data is ready to use! 46 CSV files with realistic Cloudability and Workday data.

---

## 1. Verify Mock Data Exists

```bash
# Check directory
ls -la mock_data/

# Verify all 46 files are generated
find mock_data -name "*.csv" | wc -l
# Output: 46
```

✅ **Expected:** 46 CSV files, 2.1MB total

---

## 2. Load Mock Data into Dashboard

### Option A: Direct Copy (Simplest)

```bash
# Copy Workday users to data directory
mkdir -p data
cp mock_data/workday_users.csv data/users.csv

# Copy weekly cluster data to reports
mkdir -p reports
cp mock_data/weekly/cluster/*.csv reports/

# Optional: Also copy monthly data
cp mock_data/monthly/cluster/*.csv reports/
```

### Option B: Use Mock Data Directly in Python

Edit `reporting_engine.py` to load from mock_data:

```python
# In DuckDBEngine.__init__()
def load_cluster_data(self):
    """Load cluster data from mock_data"""
    cluster_dir = BASE_DIR / "mock_data" / "weekly" / "cluster"
    for csv_file in cluster_dir.glob("*.csv"):
        df = pd.read_csv(csv_file)
        self.conn.register("cluster_data", df)
```

---

## 3. Start Dashboard

```bash
python3 reporting_engine.py
```

Output:
```
✓ DuckDB: In-memory mode
✓ Loaded 75 Workday users
✓ Loaded cluster data from mock_data/
✓ Flask running on http://localhost:5445
```

---

## 4. View Dashboard

Open browser to:
```
http://localhost:5445
```

You should see tabs with chart visualizations of the mock data.

---

## 5. Try Example Configs

Copy example config to see mock data:

```bash
cp config/cost_by_vp_filtered.yaml config/test_mock.yaml
```

Edit to use mock data tables:
```yaml
tab_name: "Cost by Team (Mock)"
table: "cluster_data"  # Uses mock data
x_axis: "namespace"
y_axis: "adjusted_amortized_cost"
chart_type: "bar"
```

Restart dashboard to see new tab.

---

## What You Have

### 46 Mock Data Files

| Type | Count | Contents |
|------|-------|----------|
| Workday Users | 1 | 75 users with org hierarchy |
| Weekly Cluster | 12 | Daily records × 12 weeks |
| Weekly Service | 12 | AWS services × 12 weeks |
| Weekly Instance | 12 | Instance types × 12 weeks |
| Monthly Cluster | 3 | Daily records × 3 months |
| Monthly Service | 3 | AWS services × 3 months |
| Monthly Instance | 3 | Instance types × 3 months |

### Data Coverage

- **Time Range:** Jan 5 - Mar 29, 2026
- **Users:** 75 across 6 teams
- **Services:** EC2, S3, RDS, Lambda, EKS, and 7 more
- **Instances:** 14 types × 3 lease options
- **Total Size:** 2.1 MB

---

## 5 Quick Tests

### Test 1: View Service Costs

```bash
# Create config/test_services.yaml
cat > config/test_services.yaml << 'EOF'
- tab_name: "AWS Services"
  table: "service_costs"
  x_axis: "service_name"
  y_axis: "total_amortized_cost"
  chart_type: "pie"
  aggregate_function: "SUM"
EOF

# Restart Flask
# New tab appears with service cost pie chart
```

### Test 2: Filter by Team

```bash
# Create config/test_team_filter.yaml
cat > config/test_team_filter.yaml << 'EOF'
- tab_name: "Cost by Team"
  table: "cluster_data"
  x_axis: "namespace"
  y_axis: "adjusted_amortized_cost"
  chart_type: "bar"
  aggregate_function: "SUM"
  filters:
    - column: "namespace"
      label: "Select Team"
EOF

# Use dropdown filter to select team
```

### Test 3: Horizontal Bar Chart

```bash
# Create config/test_horizontal.yaml
cat > config/test_horizontal.yaml << 'EOF'
- tab_name: "Top Teams"
  table: "cluster_data"
  x_axis: "adjusted_amortized_cost"
  y_axis: "namespace"
  chart_type: "bar"
  aggregate_function: "SUM"
  limit: 5
EOF

# Chart renders horizontally (cost on x-axis, namespace on y-axis)
```

### Test 4: Instance Types

```bash
# Create config/test_instances.yaml
cat > config/test_instances.yaml << 'EOF'
- tab_name: "Instance Types"
  table: "instance_usage"
  x_axis: "instance_category"
  y_axis: "total_amortized_cost"
  chart_type: "bar"
  aggregate_function: "SUM"
  filters:
    - column: "lease_type"
      label: "Lease Type"
EOF

# Filter by On-Demand, Reserved, or Spot
```

### Test 5: Check Data Volume

```bash
# In Python REPL while dashboard is running
import duckdb

conn = duckdb.connect(':memory:')
result = conn.execute("SELECT COUNT(*) FROM cluster_data").fetch_all()
print(f"Total cluster records: {result[0][0]}")

result = conn.execute("SELECT COUNT(DISTINCT namespace) FROM cluster_data").fetch_all()
print(f"Unique teams: {result[0][0]}")
```

---

## Troubleshooting

### Issue: "No data loaded"

```bash
# Check if mock_data exists
ls -la mock_data/ | head -5
# Should show files

# If missing, regenerate:
python3 generate_mock_data.py
```

### Issue: "Table not found" error

```bash
# Check DuckDB loaded correct table names
# Verify config uses correct table name:
#  - cluster_data
#  - service_costs
#  - instance_usage

# Or load manually in Python:
import pandas as pd
df = pd.read_csv('mock_data/workday_users.csv')
print(df.head())
```

### Issue: Blank charts

```bash
# Check if data files have content:
head -2 mock_data/weekly/cluster/cluster_data_2026_week_01.csv

# Verify table has rows:
SELECT COUNT(*) FROM cluster_data;
```

---

## Next Steps

1. **Explore Data:** Open DuckDB Web UI
   ```bash
   duckdb mock_data.duckdb -ui
   # Opens http://localhost:8080
   ```

2. **Create Custom Configs:** Use examples from `config/` as templates

3. **Test Filtering:** Try dynamic column filters

4. **Test Visualizations:** Create different chart types (bar, pie, line)

5. **Performance Test:** Generate more mock data (edit `generate_mock_data.py`)

---

## Files Created

- ✅ `mock_data/` (46 CSV files, 2.1 MB)
- ✅ `MOCK_DATA_GUIDE.md` (comprehensive reference)
- ✅ `config/mock_data_examples.yaml` (10 example configs)
- ✅ `QUICKSTART_MOCK_DATA.md` (this file)

---

## Summary

| Item | Status |
|------|--------|
| Mock data generated | ✅ 46 files |
| Workday users | ✅ 75 users |
| Time coverage | ✅ 12 weeks + 3 months |
| Ready to use | ✅ Yes |
| Documentation | ✅ Complete |

**You're all set!** Start the dashboard and explore the mock data.

```bash
python3 reporting_engine.py
# Open http://localhost:5445
```

For detailed information, see:
- `MOCK_DATA_GUIDE.md` - Full documentation
- `config/mock_data_examples.yaml` - 10 example configurations
- `generate_mock_data.py` - How data was generated
