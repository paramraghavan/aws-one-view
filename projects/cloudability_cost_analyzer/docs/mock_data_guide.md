# Mock Data Guide

Complete guide for using the generated mock Cloudability and Workday data in your dashboard.

---

## Overview

The mock data generator creates 46 CSV files with realistic cost, user, and resource data covering:
- **12 weeks** of data (Jan 5 - Mar 29, 2026)
- **3 months** of aggregated data (Jan, Feb, Mar 2026)
- **75 Workday users** across multiple namespaces and funding blocks
- **12 AWS services** with realistic cost distributions
- **14 instance types** with different lease options

All data is reproducible (seeded random for consistency) and designed to work seamlessly with the reporting engine.

---

## File Structure

```
mock_data/
├── workday_users.csv                    (75 users with org hierarchy)
├── weekly/
│   ├── cluster/
│   │   ├── cluster_data_2026_week_01.csv
│   │   ├── cluster_data_2026_week_02.csv
│   │   └── ... (12 total, one per week)
│   ├── service/
│   │   ├── service_cost_2026_week_01.csv
│   │   ├── service_cost_2026_week_02.csv
│   │   └── ... (12 total)
│   └── instance/
│       ├── instance_usage_2026_week_01.csv
│       ├── instance_usage_2026_week_02.csv
│       └── ... (12 total)
└── monthly/
    ├── cluster/
    │   ├── cluster_data_2026_01.csv    (January)
    │   ├── cluster_data_2026_02.csv    (February)
    │   └── cluster_data_2026_03.csv    (March)
    ├── service/
    │   ├── service_cost_2026_01.csv
    │   ├── service_cost_2026_02.csv
    │   └── service_cost_2026_03.csv
    └── instance/
        ├── instance_usage_2026_01.csv
        ├── instance_usage_2026_02.csv
        └── instance_usage_2026_03.csv
```

**Total:** 1 + 36 + 9 = **46 CSV files**

---

## Data Fields

### Workday Users (workday_users.csv)

```csv
user_id,namespace,full_name,reports_to,vp,block_funding,is_new_user
user000,team-infra,Grace Taylor,user100,user102,Platform,False
```

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| **user_id** | String | `user000` | Unique identifier (user###) |
| **namespace** | String | `team-infra` | Team/namespace assignment |
| **full_name** | String | `Grace Taylor` | User's display name |
| **reports_to** | String | `user100` | Manager's user_id |
| **vp** | String | `user102` | VP's user_id (organizational head) |
| **block_funding** | String | `Platform` | Funding block (7 types) |
| **is_new_user** | Boolean | `False` | Whether hired recently (~10% are new) |

---

### Cluster Data (weekly/monthly)

```csv
user_id,namespace,type,cpu_mean,gpu_mean,memory_mean,utilized_cost,...
user000,team-infra,container,5.01,2.0,48.83,1061.22,...
```

| Field | Type | Range | Notes |
|-------|------|-------|-------|
| **user_id** | String | - | Links to Workday user |
| **namespace** | String | - | Team/namespace |
| **type** | String | `container` | Resource type |
| **cpu_mean** | Float | 2-8 | Average CPU cores |
| **gpu_mean** | Float | 0-2 | Average GPU units |
| **memory_mean** | Float | 16-64 | Average RAM in GB |
| **utilized_cost** | Float | $1K-$5K | Cost of used resources |
| **idle_cost** | Float | $100-$2.5K | Cost of idle resources |
| **cost_by_fair_share** | Float | - | Proportional allocation cost |
| **efficient_score** | Float | 60-90% | Utilization percentage |
| **cluster_cost** | Float | - | Total cluster allocation |
| **cpu_fair_share** | Float | 50-70% | CPU allocation % |
| **artifactory_cost** | Float | $100-$500 | Artifact storage costs |
| **license_cost** | Float | $500-$2K | Software license costs |
| **platform_cost** | Float | $300-$1.5K | Platform infrastructure |
| **aws_service_cost** | Float | $500-$3K | AWS service charges |
| **adjusted_amortized_cost** | Float | - | Total cost (sum of above) |

---

### Service Cost Data (weekly/monthly)

```csv
service_name,usage_family,total_amortized_cost
EC2,Compute,87230.32
```

| Field | Type | Examples | Notes |
|-------|------|----------|-------|
| **service_name** | String | EC2, S3, RDS, Lambda, EKS, etc. | AWS service (12 total) |
| **usage_family** | String | Compute, Storage, Database, Networking | Service category |
| **total_amortized_cost** | Float | $50K-$500K | Aggregated cost for period |

**Services Included:**
- EC2, S3, RDS, Lambda, EKS, ELB
- CloudFront, DynamoDB, ElastiCache, SNS, SQS, API Gateway

---

### Instance Usage Data (weekly/monthly)

```csv
instance_type,instance_category,lease_type,total_amortized_cost
t3.large,Storage Optimized,On-Demand,46921.95
```

| Field | Type | Examples | Notes |
|-------|------|----------|-------|
| **instance_type** | String | t3.large, m5.xlarge, p3.2xlarge, etc. | EC2 instance type (14 types) |
| **instance_category** | String | Compute, Memory Optimized, GPU, Storage Optimized | Instance class |
| **lease_type** | String | On-Demand, Reserved, Spot | Purchase type |
| **total_amortized_cost** | Float | $100-$50K | Cost for period |

---

## Data Characteristics

### Users (75 total)
- **Distribution:** Across 6 namespaces (teams)
- **Hierarchy:** 3 VPs → 9 Managers → 63 Individual Contributors
- **Funding Blocks:** 7 types (Engineering, Product, Platform, Finance, Marketing, Operations, Research)
- **New Users:** ~10% (realistic onboarding rate)

### Cluster Data
- **Time Coverage:**
  - Weekly: 12 weeks (Jan 5 - Mar 29, 2026)
  - Monthly: 3 months (Jan, Feb, Mar 2026)
- **Granularity:** Daily records for sample users within each period
- **Cost Realism:**
  - Utilized vs Idle: 65-80% utilization on average
  - Monthly costs: $5K-$50K per user
  - Growth: ~2-3% month-over-month

### Service Costs
- **Services:** 12 AWS services
- **Distribution:**
  - EC2 (Compute): ~35% of costs
  - S3 (Storage): ~20%
  - RDS (Database): ~18%
  - Others: ~27%
- **Range:** $50K-$500K per service per week

### Instance Usage
- **Instance Types:** 14 common AWS instance types
- **Lease Distribution:**
  - On-Demand: ~40%
  - Reserved: ~45%
  - Spot: ~15%
- **Cost Range:** $100-$50K per instance type per week

---

## Using Mock Data in Flask Dashboard

### Option 1: Load During Development

The reporting engine automatically discovers and loads all CSV files from:
```
data/           (Workday users)
reports/        (Cost reports - but mock data uses different structure)
```

### Option 2: Load Mock Data Directly

Copy mock data to expected directories:

```bash
# Copy Workday users
cp mock_data/workday_users.csv data/users.csv

# Copy monthly cluster data (example)
cp mock_data/monthly/cluster/* reports/

# Copy weekly cluster data (example)
cp mock_data/weekly/cluster/* reports/
```

### Option 3: Load in Python Code

```python
import pandas as pd
from pathlib import Path

# Load Workday users
users = pd.read_csv('mock_data/workday_users.csv')
print(f"Loaded {len(users)} users")

# Load weekly cluster data
cluster_week1 = pd.read_csv('mock_data/weekly/cluster/cluster_data_2026_week_01.csv')
print(f"Week 1: {len(cluster_week1)} cluster records")

# Load all monthly service data
import glob
monthly_services = []
for file in glob.glob('mock_data/monthly/service/*.csv'):
    df = pd.read_csv(file)
    monthly_services.append(df)

combined = pd.concat(monthly_services, ignore_index=True)
print(f"All monthly services: {len(combined)} records")
```

---

## Example Queries

### Query 1: Total Cost by Funding Block

Using the mock data with your dashboard:

```yaml
# config/cost_by_funding_mock.yaml
tab_name: "Cost by Funding Block (Mock)"
description: "Shows mock data aggregated by funding block"
table: "cost_report"
x_axis: "block_funding"
y_axis: "total_cost"
chart_type: "bar"
aggregate_function: "SUM"
filters:
  - column: "block_funding"
    options: ["Engineering", "Product", "Platform", "Operations", "Security"]
```

### Query 2: Weekly Trend Analysis

```yaml
# config/weekly_trend_mock.yaml
tab_name: "Weekly Trend (Mock)"
description: "12-week cost trend using mock data"
table: "cost_report"
x_axis: "week"
y_axis: "total_cost"
chart_type: "line"
aggregate_function: "SUM"
```

### Query 3: Top Users by Cost

```yaml
# config/top_users_mock.yaml
tab_name: "Top Users (Mock)"
description: "Top 10 users by total cost"
table: "cost_report"
x_axis: "full_name"
y_axis: "total_cost"
chart_type: "bar"
aggregate_function: "SUM"
limit: 10
order_by: "total_cost DESC"
```

### Query 4: Service Cost Distribution

```yaml
# config/service_distribution_mock.yaml
tab_name: "AWS Services (Mock)"
description: "Cost breakdown by AWS service"
table: "service_costs"
x_axis: "service_name"
y_axis: "total_amortized_cost"
chart_type: "pie"
aggregate_function: "SUM"
```

---

## Testing Workflow

### Step 1: Generate Mock Data
```bash
python3 generate_mock_data.py
# Output: 46 CSV files in mock_data/
```

### Step 2: Start Dashboard
```bash
python3 reporting_engine.py
# Loads CSV files and creates DuckDB database
```

### Step 3: Test with Sample Configs
```bash
# Use any of the example configs:
# - config/cost_by_vp_filtered.yaml
# - config/budget_vs_actual.yaml
# - config/cost_by_location_filtered.yaml
```

### Step 4: Verify Data
```bash
# Open DuckDB Web UI
duckdb mock_data.duckdb -ui

# Or use DuckDB Studio
duckdb-studio mock_data.duckdb
```

---

## Data Regeneration

To generate fresh mock data with different randomization:

```bash
# Edit generate_mock_data.py, line 25:
# np.random.seed(42)  # Change to different number

# Regenerate
python3 generate_mock_data.py

# Re-run dashboard to load new data
python3 reporting_engine.py
```

---

## Common Use Cases

### Use Case 1: Test Filtering by Funding Block
1. Load mock data
2. Create config with `block_funding` filter
3. Select different funding blocks in dashboard
4. Verify chart updates correctly

### Use Case 2: Test Weekly vs Monthly Aggregation
1. Load both weekly and monthly mock data
2. Create separate tabs for weekly and monthly
3. Compare trend lines
4. Verify monthly ≈ sum of 4 weeks

### Use Case 3: Test Multi-Table Joins
1. Load workday_users.csv with user metadata
2. Join with cluster data on user_id
3. Display cost grouped by VP or namespace
4. Verify organizational hierarchy is reflected

### Use Case 4: Test Large Dataset Performance
1. Regenerate mock data with more users (increase NUM_USERS)
2. Monitor dashboard performance
3. Check DuckDB query times
4. Profile D3.js rendering

---

## Troubleshooting

### Issue: "No data loaded"
```bash
# Verify mock data exists
ls -la mock_data/
# Should show 46 files

# Check CSV format
head -1 mock_data/workday_users.csv
# Should show headers
```

### Issue: "Column not found" error
```bash
# Verify column names in config match CSV headers
# Example CSV headers:
head -1 mock_data/weekly/cluster/cluster_data_2026_week_01.csv

# Update config to use exact column names
```

### Issue: "Inconsistent data between weekly and monthly"
```python
# This is expected! Weekly is daily granularity, monthly is aggregated
# Weekly week_01: 7 days × 75 users × 3 clusters = ~1,575 rows
# Monthly Jan: 31 days × 75 users × 3 clusters = ~7,000 rows

# To verify consistency:
weekly = pd.concat([pd.read_csv(f) for f in glob.glob('mock_data/weekly/service/*.csv')])
monthly = pd.concat([pd.read_csv(f) for f in glob.glob('mock_data/monthly/service/*.csv')])
print(f"Weekly total: ${weekly['total_amortized_cost'].sum():,.0f}")
print(f"Monthly total: ${monthly['total_amortized_cost'].sum():,.0f}")
# Should be similar (within 10-20%)
```

---

## Next Steps

1. **Load into Dashboard:** Copy mock data to `data/` and `reports/` directories
2. **Create Configs:** Use example configs as templates for your dashboard tabs
3. **Test Filters:** Verify dynamic filtering works with mock data
4. **Test Visualizations:** Create different chart types (bar, pie, line)
5. **Performance Test:** Load large volumes and monitor dashboard responsiveness
6. **Join Multiple Tables:** Create configs that JOIN users with cost data

---

## Summary

| Aspect | Details |
|--------|---------|
| **Total Files** | 46 CSV files |
| **Users** | 75 with org hierarchy |
| **Time Range** | Jan-Mar 2026 (12 weeks + 3 months) |
| **AWS Services** | 12 services (EC2, S3, RDS, etc.) |
| **Instance Types** | 14 types with 3 lease options each |
| **Cost Range** | $100-$500K per period |
| **Reproducible** | Yes (seeded random) |
| **Production-Ready** | No (mock data only) |

**Generated by:** `python3 generate_mock_data.py`

**Use for:** Development, testing, demos, learning D3.js visualization

---

## Files Reference

- **Generator Script:** `generate_mock_data.py`
- **Generated Data:** `mock_data/` directory
- **Configuration Examples:** `config/` directory
- **Dashboard:** `reporting_engine.py`
- **D3.js Examples:** `examples/` directory

For questions about specific data fields or to regenerate with different parameters, see the generator script configuration at the top of `generate_mock_data.py`.
