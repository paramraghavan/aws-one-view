# EMR on Kubernetes Cloudability Chargeback - Quick Start

Complete workflow to generate monthly chargeback reports by user/namespace from Jan 2025 to Feb 2026.

---

## TL;DR - Run This

### Option A: With Real Cloudability Data
```bash
# 1. Set your Cloudability credentials
export CLOUDABILITY_API_KEY="your-api-key"
export CLOUDABILITY_CLUSTER_ID="your-cluster-id"

# 2. Fetch data and analyze
bash fetch_cloudability_data.sh
python3 chargeback_analysis.py

# 3. View results
cat chargeback_by_user_monthly.csv
cat summary_by_user.csv
```

### Option B: Test with Sample Data
```bash
# 1. Generate realistic test data
python3 generate_sample_cloudability_data.py

# 2. Run analysis
python3 chargeback_analysis.py

# 3. View results
cat chargeback_by_user_monthly.csv
cat summary_by_user.csv
```

---

## STEP-BY-STEP EXPLANATION

### STEP 1: Understand the Data Flow

```
Cloudability API
      ↓
  (curl fetch)
      ↓
  costs_raw.csv (Month, Namespace, Service, FairshareValue)
      ↓
  (Python processing)
      ↓
  chargeback_by_user_monthly.csv ✓
  summary_by_user.csv ✓
  validation_monthly_totals.csv ✓
  chargeback_with_mom_changes.csv ✓
```

### STEP 2: Choose Your Approach

#### **Approach A: Real Cloudability Data** (Production)

**Prerequisites:**
- Cloudability API key (from Settings → API Keys)
- Cluster ID (from your cluster in Cloudability UI or AWS)

**What `fetch_cloudability_data.sh` does:**
1. Calls `https://api.cloudability.com/v1/costs` API
2. Filters by cluster ID, date range (Jan 2025 - Feb 2026)
3. Requests dimensions: `month`, `namespace`, `service`
4. Requests metric: `cost.fairshare` (NOT unblended)
5. Converts JSON to CSV

**Run it:**
```bash
export CLOUDABILITY_API_KEY="your-key"
export CLOUDABILITY_CLUSTER_ID="your-cluster-id"
bash fetch_cloudability_data.sh
```

**Output:** `costs_raw.csv` (Month, Namespace, Service, FairshareValue)

**Example output:**
```csv
Month,Namespace,Service,FairshareValue
2025-01,data-science-team-1,pod,12500.50
2025-01,analytics-prod,pod,18750.75
2025-01,kube-system,pod,2100.00
```

---

#### **Approach B: Sample/Test Data** (Development)

**For testing without real Cloudability:**

**What `generate_sample_cloudability_data.py` does:**
1. Creates realistic mock data
2. Includes 8 user namespaces (analytics-prod, data-science-team-1, etc.)
3. Includes 8 service namespaces (kube-system, prometheus, logging, etc.)
4. Generates 14 months of data (Jan 2025 - Feb 2026)
5. Includes seasonal variance, growth trends, month-to-month noise

**Run it:**
```bash
python3 generate_sample_cloudability_data.py
```

**Output:** `costs_raw.csv` (same format as real data)

**Customize:**
```bash
python3 generate_sample_cloudability_data.py --output my_test_data.csv --seed 123
```

---

### STEP 3: Run the Analysis

**What `chargeback_analysis.py` does:**

The script runs 9 steps with detailed output at each stage:

```
STEP 1: Load Data
       └─ Loads CSV, validates structure, shows date range & total cost

STEP 2: Classify Namespaces
       ├─ Separates USER namespaces (billable) vs SERVICE namespaces (infrastructure)
       ├─ Lists which namespaces are which
       └─ Shows cost split (user vs service)

STEP 3: Monthly Costs by User (Before service distribution)
       ├─ Groups by month and user
       ├─ Shows table: User costs by month (first 3 months)
       └─ Shows totals per user across all 14 months

STEP 4: Distribute Service Costs Proportionally
       ├─ Calculates each user's proportion of total user cost per month
       ├─ Allocates service costs based on proportion
       ├─ Example: If analytics-prod is 30% of user costs, it gets 30% of service costs
       └─ Verifies allocations sum to service total

STEP 5: Final Chargeback (User + Service)
       ├─ Combines direct user cost + service allocation
       ├─ Shows full chargeback table (first 15 rows)
       └─ Displays total rows generated

STEP 6: Validation - Monthly Totals vs Cloudability
       ├─ Sums all user costs per month
       ├─ Compares to Cloudability's reported cluster total
       ├─ Verifies difference < 0.01% (accounting for rounding)
       └─ Result: ✓ PASSED or ✗ FAILED

STEP 7: Month-over-Month Changes
       ├─ Calculates dollar change per user, month to month
       ├─ Calculates percent change per user, month to month
       ├─ Shows example MoM for first user
       └─ Shows latest month changes sorted by percent change

STEP 8: Summary Statistics
       ├─ Totals by user (entire 14-month period)
       ├─ Shows: Total cost, Avg monthly, Min/Max month, Std Dev
       ├─ Sorted by total cost (highest to lowest)
       └─ Grand total verification

STEP 9: Save Output Files
       ├─ chargeback_by_user_monthly.csv
       ├─ summary_by_user.csv
       ├─ chargeback_with_mom_changes.csv
       └─ validation_monthly_totals.csv
```

**Run it:**
```bash
python3 chargeback_analysis.py
```

**Output with sample data:**
```
===========================================================================
 EMR ON KUBERNETES CLOUDABILITY CHARGEBACK ANALYSIS
 Jan 2025 - Feb 2026 | Monthly by User
===========================================================================

===========================================================================
 STEP 1: LOAD DATA
===========================================================================

✓ Loaded 224 rows from costs_raw.csv
  Date range: 2025-01 to 2026-02
  Unique namespaces: 16
  Total fairshare cost: $1,052,400.00

===========================================================================
 STEP 2: CLASSIFY NAMESPACES
===========================================================================

✓ User namespaces: 8
  - analytics-prod                  $    252,000.00
  - data-science-team-1             $    168,000.00
  - data-science-team-2             $    148,800.00
  - ml-engineering                  $    126,000.00
  - quant-research                  $    120,000.00
  - research-lab                    $    115,200.00
  - risk-modeling                   $     85,200.00
  - trading-systems                 $     90,000.00

✓ Service namespaces: 8
  - cert-manager                    $     12,000.00
  - grafana                          $     28,000.00
  - ingress-nginx                   $     35,000.00
  - kube-node-lease                 $      7,000.00
  - kube-system                     $    110,000.00
  - logging                          $     84,000.00
  - prometheus                       $     60,000.00
  - vault                            $     30,000.00

Cost breakdown:
  User namespaces:    $  1,005,200.00
  Service namespaces: $     47,200.00
  TOTAL:              $  1,052,400.00

...

===========================================================================
 STEP 6: VALIDATION - Monthly Totals vs Cloudability
===========================================================================

Validation results (all months):
     Month  CloudabilityTotal   OurTotal  Difference  DiffPct
   2025-01        41000.00     41000.00         0.00    0.000000  ✓
   2025-02        41500.00     41500.00         0.00    0.000000  ✓
   2025-03        42200.00     42200.00         0.00    0.000000  ✓
   ...

✓ Validation PASSED

...

===========================================================================
 ANALYSIS COMPLETE
===========================================================================

✓ All output files saved to: ./

  Main files:
    • chargeback_by_user_monthly.csv    (chargeback table)
    • summary_by_user.csv               (totals & statistics)
    • chargeback_with_mom_changes.csv   (month-over-month changes)
    • validation_monthly_totals.csv     (validation vs Cloudability)
```

---

### STEP 4: Understand the Output Files

#### **1. `chargeback_by_user_monthly.csv` (Main)**

Monthly chargeback amount for each user.

```csv
Month,User,DirectCost,ServiceAllocation,TotalCost
2025-01,analytics-prod,18750.75,3368.20,22118.95
2025-01,data-science-team-1,12500.50,2245.10,14745.60
2025-01,ml-engineering,9250.25,1659.90,10910.15
2025-02,analytics-prod,19800.45,3450.75,23251.20
...
```

**Columns:**
- `Month`: YYYY-MM format
- `User`: Namespace name (billable user/team)
- `DirectCost`: Cost directly attributed to this user
- `ServiceAllocation`: Share of service costs (kube-system, prometheus, logging, etc.)
- `TotalCost`: DirectCost + ServiceAllocation (what you charge this user)

**Use for:**
- Monthly invoicing
- Usage reports
- Cost allocation to teams

---

#### **2. `summary_by_user.csv` (Totals)**

Aggregate statistics by user over entire 14-month period.

```csv
User,DirectCost,ServiceAllocated,TotalCost,AvgMonthly,MinMonth,MaxMonth,StdDev
analytics-prod,252000.00,45000.00,297000.00,24750.00,22118.95,25600.30,1200.50
data-science-team-1,168000.00,30000.00,198000.00,16500.00,14745.60,16850.45,750.25
ml-engineering,126000.00,22500.00,148500.00,12375.00,10910.15,12450.80,550.15
...
```

**Columns:**
- `DirectCost`: Total direct costs (14 months)
- `ServiceAllocated`: Total service allocation (14 months)
- `TotalCost`: Total billable cost (14 months)
- `AvgMonthly`: Average monthly cost
- `MinMonth`: Lowest single month
- `MaxMonth`: Highest single month
- `StdDev`: Standard deviation (volatility)

**Use for:**
- Budget planning
- Identifying heavy users
- Trend analysis
- Cost forecasting

---

#### **3. `chargeback_with_mom_changes.csv` (Trends)**

Month-over-month changes for cost tracking and alerts.

```csv
Month,User,DirectCost,ServiceAllocation,TotalCost,MoMDollarChange,MoMPercentChange
2025-01,analytics-prod,18750.75,3368.20,22118.95,,
2025-02,analytics-prod,19800.45,3450.75,23251.20,1132.25,5.12
2025-03,analytics-prod,20250.60,3518.95,23769.55,518.35,2.23
2025-04,analytics-prod,21500.70,3764.85,25265.55,1496.00,6.30
...
```

**Columns:**
- `MoMDollarChange`: Cost change in dollars (current month - previous month)
- `MoMPercentChange`: Cost change in percent (same month last year / this month)

**Use for:**
- Anomaly detection (alert if cost jumps > 10%)
- Trend reports ("costs grew 2.5% month-over-month")
- Performance monitoring

---

#### **4. `validation_monthly_totals.csv` (Quality Check)**

Validates your calculations against Cloudability's reported totals.

```csv
Month,CloudabilityTotal,OurTotal,Difference,DiffPct
2025-01,41000.00,41000.00,0.00,0.000000
2025-02,41500.00,41500.00,0.00,0.000000
2025-03,42200.00,42200.00,0.00,0.000000
...
```

**What it checks:**
- Sum of all user costs per month = Cloudability's cluster cost
- Difference should be < 0.01% (rounding errors only)

**If DiffPct > 0.01%:**
- Check for missing namespaces (new services added?)
- Verify SERVICE_NAMESPACES list is complete
- Check Cloudability API response format changed

---

## CUSTOMIZATION

### Add/Remove Service Namespaces

Edit `chargeback_analysis.py`:

```python
SERVICE_NAMESPACES = {
    'kube-system', 'kube-node-lease', 'kube-public',           # Kubernetes core
    'prometheus', 'grafana', 'loki', 'logging',                 # Monitoring/logging
    'ingress-nginx', 'cert-manager', 'vault',                   # Networking/security
    'external-dns', 'cluster-autoscaler', 'kyverno',           # Cluster management
    'my-custom-service',  # ← Add your service here
}
```

Then re-run:
```bash
python3 chargeback_analysis.py
```

### Change Date Range

Edit `fetch_cloudability_data.sh`:

```bash
START_DATE="2024-01-01"   # ← Change this
END_DATE="2026-12-31"     # ← And this
```

Then:
```bash
bash fetch_cloudability_data.sh
python3 chargeback_analysis.py
```

### Export to Excel

```bash
pip install openpyxl

python3 << 'EOF'
import pandas as pd

# Read CSV files
chargeback = pd.read_csv('chargeback_by_user_monthly.csv')
summary = pd.read_csv('summary_by_user.csv')
validation = pd.read_csv('validation_monthly_totals.csv')

# Write to Excel with multiple sheets
with pd.ExcelWriter('chargeback_report.xlsx') as writer:
    chargeback.to_excel(writer, sheet_name='Monthly', index=False)
    summary.to_excel(writer, sheet_name='Summary', index=False)
    validation.to_excel(writer, sheet_name='Validation', index=False)

print("✓ Created chargeback_report.xlsx")
EOF
```

---

## TROUBLESHOOTING

### "File not found: costs_raw.csv"
```bash
# Did you run the fetch script?
bash fetch_cloudability_data.sh

# Or generate sample data?
python3 generate_sample_cloudability_data.py
```

### "ERROR: CLOUDABILITY_API_KEY not set"
```bash
export CLOUDABILITY_API_KEY="your-actual-api-key"
export CLOUDABILITY_CLUSTER_ID="your-actual-cluster-id"
bash fetch_cloudability_data.sh
```

### "✗ Validation FAILED"

Check if you have new namespaces not in SERVICE_NAMESPACES list:

```bash
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('costs_raw.csv')

KNOWN_SERVICES = {
    'kube-system', 'kube-node-lease', 'kube-public',
    'prometheus', 'grafana', 'loki', 'logging',
    'ingress-nginx', 'cert-manager', 'vault',
    'external-dns', 'cluster-autoscaler', 'kyverno',
}

KNOWN_USERS = {
    'analytics-prod', 'data-science-team-1', 'data-science-team-2',
    'ml-engineering', 'quant-research', 'research-lab',
    'trading-systems', 'risk-modeling',
}

unknown = df[
    (~df['Namespace'].isin(KNOWN_SERVICES)) &
    (~df['Namespace'].isin(KNOWN_USERS))
]['Namespace'].unique()

if len(unknown) > 0:
    print("Unknown namespaces found:")
    for ns in unknown:
        cost = df[df['Namespace'] == ns]['FairshareValue'].sum()
        print(f"  - {ns}: ${cost:,.2f}")
        print("    Add to SERVICE_NAMESPACES? (if infrastructure)")
else:
    print("All namespaces are known")
EOF
```

---

## KEY CONCEPTS RECAP

### Why `fairshare` Cost?

| Column | What it means | When to use |
|--------|---|---|
| **unblended** | Raw AWS cost (on-demand, reserved, spot) | Cost accounting |
| **fairshare** | Cost with idle capacity distributed to users | **Chargeback** ✓ |

Fairshare ensures: `User A cost + User B cost + User C cost = Total cluster cost`

→ No cost is orphaned, 100% of cluster cost is recovered.

### Why Service Namespaces?

Services like `kube-system`, `prometheus`, `logging` benefit **all** users.

**Solution**: Distribute their cost proportionally.

Example:
- Total cluster cost: $10,000
- User A directly uses: $6,000 (60%)
- User B directly uses: $4,000 (40%)
- Service costs: $1,000
- → User A pays: $6,000 + (60% × $1,000) = $6,600
- → User B pays: $4,000 + (40% × $1,000) = $4,400

### Why Month-over-Month?

Tracks usage trends:
- **+5% MoM** → Usage growing, may need cost controls
- **-3% MoM** → Usage shrinking, good for budgeting
- **+25% MoM** → Anomaly! Investigate.

---

## NEXT STEPS

1. **Get API credentials**: Login to Cloudability → Settings → API Keys
2. **Identify your cluster**: Find cluster ID in Cloudability UI
3. **Run the fetch**: `bash fetch_cloudability_data.sh`
4. **Run the analysis**: `python3 chargeback_analysis.py`
5. **Review outputs**: Check CSV files in your directory
6. **Schedule monthly**: Add to cron for automated monthly reports

---

## QUESTIONS?

**Q: Can I go back and charge previous months?**
A: Yes. Just change START_DATE and END_DATE in fetch_cloudability_data.sh. Cloudability retains 13+ months of history.

**Q: What if a user had zero usage one month?**
A: They still get a row with 0 or near-0 cost, but still absorb their proportional share of service costs (minimal).

**Q: How do I handle new namespaces?**
A: Add to USERS list if it's a user, or to SERVICE_NAMESPACES if it's infrastructure. Re-run analysis.

**Q: Can I charge by other dimensions (pod, deployment, etc.)?**
A: Yes. Modify the curl command to request different dimensions (change `dimensions=month,namespace,service` to whatever you need).

**Q: What about reserved instances vs on-demand?**
A: Cloudability handles this automatically in `cost.fairshare`. Your chargeback already accounts for RI utilization.

