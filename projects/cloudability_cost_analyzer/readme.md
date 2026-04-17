# Cloudability Cost Analyzer

Generate cost reports combining Cloudability cluster data with Workday user information.

## Quick Start

### Using Mock Data (Testing)
```bash
python3 generate_reports_functional.py
```

Generates 21 CSV reports:
- 12 weekly reports (one per week)
- 3 monthly reports
- 6 summary reports (by user, funding block, VP)

### Using Real API Data (Production)
```bash
# 1. Export from Cloudability API
curl -X GET "https://api.cloudability.com/v3/cluster-data" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  > mock_data/weekly/cluster/cluster_data_2026_week_01.csv

# 2. Run script (auto-detects API format!)
python3 generate_reports_functional.py
```

## What It Does

1. **Loads data** from 4 sources:
   - Workday users (identity, org structure)
   - Cloudability cluster data (resource usage, costs)
   - Service costs (AWS services)
   - Instance usage (EC2 instances)

2. **Transforms** API responses:
   - Maps complex API column names → simple business names
   - Calculates derived metrics (efficiency, bronze cost, etc.)
   - Handles missing columns gracefully

3. **Joins & Allocates**:
   - LEFT JOIN users with cluster data
   - Calculates user proportion of cluster costs
   - Allocates service and instance costs proportionally
   - Generates 21 reports

## Output Columns

Each report has 20 columns:
```
user_id, full_name, block_funding, vp,
cpu_mean, gpu_mean, memory_mean,
utilized_cost, idle_cost, cost_by_fair_share,
efficient_score, cluster_cost, cpu_fair_share,
artifactory_cost, license_cost, platform_cost,
aws_service_cost, total_cost, is_new_user
```

## Data Flow

```
Real API Response / Mock Data
    ↓
Auto-detect format (real vs mock)
    ↓
Transform API columns to business names
    ↓
Aggregate by user (sum costs, average metrics)
    ↓
JOIN with Workday users (LEFT JOIN)
    ↓
Allocate service/instance costs proportionally
    ↓
Generate 21 CSV reports
```

## API Support

The script automatically detects and handles:

**Real Cloudability API Format:**
- Detects columns like `'costs: allocation'`, `'cpu/reserved: resource: mean'`
- Transforms to business names
- Calculates derived metrics
- Handles column name variations

**Mock Data Format:**
- Works exactly as before
- No changes needed
- Identical output

## Essential API Columns

Extract these 12 columns from Cloudability API:

| Category | Columns |
|----------|---------|
| Identity | type, namespace |
| Metrics | cpu/reserved: resource: mean, memory/reserved_rss: resource: mean, gpu/reserved: resource: mean |
| Costs | costs: allocation, costs: fairShare, costs: unallocated |
| Network | network/tx: allocation, network/rx: allocation |
| Storage | filesystem/usage: allocation, persistent_volume_filesystem/usage: allocation |

## Understanding API Column Names

Cloudability column names follow this pattern:
```
[RESOURCE_TYPE]/[METRIC]: [MEASUREMENT_TYPE]
```

### Resource Types

| Resource | Meaning |
|----------|---------|
| `cpu/reserved` | CPU capacity allocated to container |
| `memory/reserved_rss` | Memory (RSS = actual memory used, not theoretical) |
| `gpu/reserved` | GPU capacity allocated |
| `network/tx` | Network transmit (outgoing traffic) |
| `network/rx` | Network receive (incoming traffic) |
| `filesystem/usage` | Ephemeral storage (temporary, deleted on pod restart) |
| `persistent_volume_filesystem/usage` | Persistent storage (permanent) |
| `costs` | Cost aggregates and totals |

### Cost Allocation Metrics

| Metric | Meaning | Example |
|--------|---------|---------|
| `costs: allocation` | Cost of reserved/allocated resources (what you paid for capacity you reserved) | $5,000 |
| `costs: fairShare` | Proportional share of shared infrastructure costs (orchestration, networking overhead) | $2,500 |
| `costs: unallocated` | Cost of unused capacity (wasted money on resources you reserved but didn't use) | $1,500 |

### Resource Usage Metrics

| Metric | Meaning | Example |
|--------|---------|---------|
| `resource: mean` | Average actual usage | 4.5 vCPU, 32.5 GB |
| `resource: sum` | Total usage (not needed for cost reports) | 40.5 vCPU total |
| `resource: count` | Number of units (operational metric, not cost) | 9 CPU cores |

### Fair Share Allocation

| Metric | Meaning | Example |
|--------|---------|---------|
| `cpu/reserved: fairShare` | CPU's share of fair share costs | $1,250 |
| `memory/reserved_rss: fairShare` | Memory's share of fair share costs | $750 |
| `network/tx: fairShare` | Network transmit's share | $300 |

### Real Example

Here's an actual row from Cloudability API:

```csv
type,namespace,cpu/reserved: resource: mean,memory/reserved_rss: resource: mean,costs: allocation,costs: fairShare,costs: unallocated
container,team-data,4.5,32.5,5000,2500,1500
```

**Breakdown:**

| Column | Value | Meaning |
|--------|-------|---------|
| `type` | container | Container workload |
| `namespace` | team-data | Team/namespace that owns it |
| `cpu/reserved: resource: mean` | 4.5 | Used 4.5 vCPUs on average |
| `memory/reserved_rss: resource: mean` | 32.5 | Used 32.5 GB of memory on average |
| `costs: allocation` | $5,000 | Cost of the allocated/reserved resources |
| `costs: fairShare` | $2,500 | Fair share of shared infrastructure |
| `costs: unallocated` | $1,500 | Cost of unused capacity (waste) |

**Total Cost = $5,000 + $2,500 + $1,500 = $9,000**

### Column Name Translation

How the script transforms API columns to business names:

```python
API Column Name                            → Business Name
─────────────────────────────────────────────────────────────
'cpu/reserved: resource: mean'            → 'cpu_mean'           # 4.5
'memory/reserved_rss: resource: mean'     → 'memory_mean'        # 32.5
'gpu/reserved: resource: mean'            → 'gpu_mean'           # 0 or 2
'costs: allocation'                       → 'utilized_cost'      # $5,000
'costs: fairShare'                        → 'cost_by_fair_share' # $2,500
'costs: unallocated'                      → 'idle_cost'          # $1,500
'network/tx: allocation'                  → 'network_tx_cost'    # $250
'network/rx: allocation'                  → 'network_rx_cost'    # $200
'filesystem/usage: allocation'            → 'storage_ephemeral_cost'  # $100
'persistent_volume_filesystem/usage: allocation' → 'storage_persistent_cost' # $50
```

### Key Insights

- **`reserved`** = capacity you allocated (not necessarily what you used)
- **`allocation`** = cost of that allocated capacity
- **`fairShare`** = your proportional share of shared costs
- **`unallocated`** = cost of unused allocation (waste/inefficiency)
- **`resource: mean`** = average actual usage (what you really consumed)
- **`rss`** = Resident Set Size (actual memory used, not virtual/theoretical)
- **`/tx`** = transmit (outgoing)
- **`/rx`** = receive (incoming)

## Derived Metrics

These metrics are calculated from API columns:

```python
cluster_cost = utilized_cost + cost_by_fair_share + idle_cost
               # Total cost = what you used + shared costs + what you wasted

efficient_score = (utilized_cost / (utilized_cost + idle_cost)) * 100
                  # Resource utilization percentage (0-100%)
                  # 90% = efficient, 50% = half wasted

bronze_cost = network_tx + network_rx + storage_ephemeral + storage_persistent
              # Network + storage costs (often underestimated)

cpu_fair_share = (cpu_reserved_fairshare / cost_by_fair_share) * 100
                 # What % of shared costs come from CPU
```

### Examples

**Scenario:** Team with allocated resources they're not fully using

```
utilized_cost:     $5,000   (what you actually used)
cost_by_fair_share: $2,500  (your share of shared infrastructure)
idle_cost:         $1,500   (waste - you reserved but didn't use)
───────────────────────────
cluster_cost:      $9,000   (total cost)

efficient_score = $5,000 / ($5,000 + $1,500) = 77%
                  (77% utilized, 23% wasted)
```

**Scenario:** Network costs are significant

```
network_tx:              $250
network_rx:              $200
storage_ephemeral:       $100
storage_persistent:      $50
───────────────────────────
bronze_cost:             $600  (network + storage)
```

## Directory Structure

```
cloudability_cost_analyzer/
├── generate_reports_functional.py    (main script)
├── generate_mock_data.py             (test data generator)
├── README.md                         (this file)
├── mock_data/
│   ├── workday_users.csv
│   ├── weekly/
│   │   ├── cluster/cluster_data_*.csv
│   │   ├── service/service_cost_*.csv
│   │   └── instance/instance_usage_*.csv
│   └── monthly/
│       ├── cluster/cluster_data_*.csv
│       ├── service/service_cost_*.csv
│       └── instance/instance_usage_*.csv
└── reports/
    ├── weekly/cost_report_*.csv
    ├── monthly/cost_report_*.csv
    └── summaries/
        ├── user_summary_*.csv
        ├── funding_summary_*.csv
        └── vp_summary_*.csv
```

## Code Structure

### Main Functions

**Data Loading:**
- `load_users()` - Load Workday users
- `load_cluster_data(filepath)` - Load cluster data with auto-detect
- `load_service_data(filepath)` - Load service costs
- `load_instance_data(filepath)` - Load instance usage

**API Transformation:**
- `transform_cloudability_api_response(df)` - Transform API columns
- `is_real_api_format(df)` - Detect API vs mock format

**Aggregation:**
- `aggregate_cluster_by_user(df)` - Group by user
- `aggregate_service_costs(df)` - Sum service costs
- `aggregate_instance_costs(df)` - Sum instance costs

**Joining & Allocation:**
- `join_and_allocate(users, cluster, service, instance)` - Join and allocate costs

**Formatting & Output:**
- `format_report(df)` - Format and clean data
- `save_report(df, filepath)` - Save to CSV

**Report Generation:**
- `generate_weekly_reports(users)` - Generate 12 weekly reports
- `generate_monthly_reports(users)` - Generate 3 monthly reports
- `generate_user_summary()` - Summarize by user
- `generate_funding_summary()` - Summarize by funding block
- `generate_vp_summary()` - Summarize by VP

## Testing

Run with mock data:
```bash
python3 generate_reports_functional.py
```

Expected output:
```
✓ 75 users loaded
✓ 12 weekly reports generated
✓ 3 monthly reports generated
✓ 6 summary reports generated
✓ 21 CSV files created
```

## Production Use

### Step 1: Get API Credentials
```
From Cloudability dashboard:
- API endpoint URL
- Authentication token
- Cluster IDs
```

### Step 2: Export Data
```bash
for week in {1..12}; do
  curl ... > mock_data/weekly/cluster/cluster_data_2026_week_$week.csv
done
```

### Step 3: Run Script
```bash
python3 generate_reports_functional.py
```

### Step 4: Validate
```bash
# Check a report
head -3 reports/weekly/cost_report_2026_week_01.csv

# Verify totals
awk -F',' '{sum+=$18} END {print sum}' reports/weekly/cost_report_2026_week_01.csv

# Compare with Cloudability invoice
```

## Troubleshooting

**Issue: "ModuleNotFoundError: pandas"**
```bash
pip install pandas
```

**Issue: "All zeros in costs"**
- Check: Are API columns numeric or strings?
- Check: Do column names match expected pattern? (must include spaces around colons)
- Check: Try running with mock data first
- Check: See "Understanding API Column Names" section above

**Issue: "No reports generated"**
- Check: Do CSV files exist in mock_data directory?
- Check: File names match pattern (e.g., cluster_data_2026_week_01.csv)?

**Issue: Output doesn't match invoice**
- Check: Did script run to completion?
- Check: Are all 12 weeks/3 months generated?
- Check: Service and instance costs included?

**Issue: "What does `costs: fairShare` mean?"**
- `costs: allocation` = your direct usage costs ($5,000)
- `costs: fairShare` = your share of shared infrastructure like orchestration ($2,500)
- `costs: unallocated` = your waste/unused capacity ($1,500)
- **Total = $5,000 + $2,500 + $1,500 = $9,000**
- See "Understanding API Column Names" section for details

**Issue: "What does `reserved_rss` mean?"**
- `rss` = Resident Set Size = actual memory used (not theoretical)
- `reserved` = capacity you allocated
- Example: You allocated 64GB but only used 32.5GB on average
- See "Resource Types" table for all resource types

## Cost Allocation Explained

The script allocates global costs (service, instance) proportionally:

```python
# 1. Calculate each user's share of cluster costs
user_proportion = user_cluster_cost / total_cluster_cost

# 2. Allocate global costs based on proportion
user_service = user_proportion × total_service_cost
user_instance = user_proportion × total_instance_cost

# 3. Final cost
final_cost = cluster_cost + user_service + user_instance
```

**Example:**
- Total cluster costs: $100,000
- User A's cluster cost: $10,000 (10%)
- Total service costs: $500,000
- User A's service allocation: 10% × $500,000 = $50,000

## Performance

- Processing time: ~5-10 seconds for 12 weeks
- Memory usage: <100 MB
- Format detection: <0.1 seconds
- Transformation: <1 second per file

## Requirements

- Python 3.7+
- pandas

## Files

### Main Script
- `generate_reports_functional.py` - Report generation with API support

### Supporting Script
- `generate_mock_data.py` - Generate 46 test CSV files

### Documentation
- `README.md` - This file (primary docs)

## See Also

- **generate_mock_data.py** - Create test data
- **mock_data/** - Test data files
- **reports/** - Generated reports

## License

Internal use only

