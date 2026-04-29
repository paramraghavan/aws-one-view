# Chargeback Calculations Explained

Detailed breakdown of every calculation, decision, and formula used in the analysis.

---

## YOUR QUESTIONS ANSWERED

### Q1: Which Cost Column - Unblended or Fairshare?

**Answer: Use `fairshare` for chargeback.**

#### Why?

| Aspect | Unblended | Fairshare |
|--------|-----------|-----------|
| **Definition** | Raw AWS costs as billed | AWS costs + idle capacity redistributed to users |
| **Cluster scenario** | Cluster cost $10K, only $9K allocated to users → $1K orphaned | Cluster cost $10K → 100% distributed to users |
| **For chargeback** | Leaves unanswered: who pays for idle? | Every dollar is accounted for, proportional to usage |
| **Formula** | Direct usage cost only | Direct usage + (idle × user's proportion) |
| **Monthly total** | May not equal cluster cost | Always equals cluster cost |

#### Real Example

```
Cluster: 100 cores @ $100/hour = $10,000/day

User A requests: 40 cores (40%)
User B requests: 30 cores (30%)
User C requests: 10 cores (10%)
Unallocated: 20 cores (20%)

UNBLENDED COST (raw):
  User A: (40/100) × $10,000 = $4,000
  User B: (30/100) × $10,000 = $3,000
  User C: (10/100) × $10,000 = $1,000
  Unallocated: (20/100) × $10,000 = $2,000  ← Who pays this?
  Total: $10,000

FAIRSHARE COST (redistributed idle):
  Calculate: Who used what proportion of ALLOCATED resources?
    Total allocated = 40 + 30 + 10 = 80 cores
    User A: 40/80 = 50%
    User B: 30/80 = 37.5%
    User C: 10/80 = 12.5%

  Distribute idle proportionally:
    User A: $4,000 + (50% × $2,000) = $4,000 + $1,000 = $5,000
    User B: $3,000 + (37.5% × $2,000) = $3,000 + $750 = $3,750
    User C: $1,000 + (12.5% × $2,000) = $1,000 + $250 = $1,250
    Total: $5,000 + $3,750 + $1,250 = $10,000 ✓
```

**Result**: Every dollar is recovered, proportional to usage. This is fair and transparent.

#### In Your Code

```bash
# fetch_cloudability_data.sh requests:
--data-urlencode "metrics=cost.fairshare"  # NOT cost.unblended
```

```python
# chargeback_analysis.py uses:
df['FairshareValue']  # This is already fairshare from Cloudability
```

---

### Q2: Service Namespaces vs User Namespaces - Which to Charge?

**Answer: Charge service costs proportionally to user costs.**

#### Service Namespaces (Non-billable directly)

These provide **infrastructure** that benefits all users:

```
kube-system           ← Kubernetes control plane
kube-node-lease       ← Node heartbeat
kube-public           ← Kubernetes public data
prometheus            ← Metrics (everyone needs this)
grafana               ← Dashboards (everyone benefits)
loki/logging          ← Log storage (cluster-wide)
ingress-nginx         ← API gateway (all traffic goes through)
cert-manager          ← SSL certs (infrastructure)
vault                 ← Secrets (cluster-level)
external-dns          ← DNS (cluster management)
cluster-autoscaler    ← Auto-scaling logic
kyverno               ← Policy enforcement
```

**These ARE billable**, but distributed proportionally.

**Why proportionally?**
- If User A allocates 50% of cluster, they benefit from infrastructure 50% more
- User A should pay 50% of infrastructure costs
- User B should pay 30%, User C should pay 20%

#### Service Cost Distribution Algorithm

```python
# For each month:

1. Get total service cost
   service_cost_jan = kube-system + prometheus + logging + ... = $5,000

2. Get each user's direct cost
   User A direct cost = $6,000
   User B direct cost = $3,000
   User C direct cost = $1,000
   Total user cost = $10,000

3. Calculate each user's proportion
   User A proportion = $6,000 / $10,000 = 0.60 (60%)
   User B proportion = $3,000 / $10,000 = 0.30 (30%)
   User C proportion = $1,000 / $10,000 = 0.10 (10%)

4. Allocate service cost proportionally
   User A gets: 0.60 × $5,000 = $3,000 service allocation
   User B gets: 0.30 × $5,000 = $1,500 service allocation
   User C gets: 0.10 × $5,000 = $500 service allocation
   Total allocated: $3,000 + $1,500 + $500 = $5,000 ✓

5. Final chargeback (user + service)
   User A: $6,000 + $3,000 = $9,000
   User B: $3,000 + $1,500 = $4,500
   User C: $1,000 + $500 = $1,500
   Total: $9,000 + $4,500 + $1,500 = $15,000 ✓
```

#### In Your Code

```python
# chargeback_analysis.py, STEP 6

# Define service namespaces
SERVICE_NAMESPACES = {
    'kube-system', 'kube-node-lease', 'prometheus',
    'logging', 'ingress-nginx', 'vault',
    ...
}

# Separate data
user_ns = df[~df['Namespace'].isin(SERVICE_NAMESPACES)]
service_ns = df[df['Namespace'].isin(SERVICE_NAMESPACES)]

# Calculate proportions
user_monthly['Proportion'] = user_monthly['DirectCost'] / user_monthly['TotalUserCost']

# Allocate service costs
user_monthly['ServiceAllocation'] = user_monthly['ServiceCost'] * user_monthly['Proportion']

# Final chargeback
chargeback['TotalCost'] = chargeback['DirectCost'] + chargeback['ServiceAllocation']
```

---

### Q3: How to Calculate Month-over-Month Change?

**Answer: Track both dollar change and percent change.**

#### Formula

```
MoM Dollar Change = Current Month Cost - Previous Month Cost

MoM Percent Change = (Current Month Cost - Previous Month Cost) / Previous Month Cost × 100%
```

#### Example

```
User A costs:
  Jan 2025: $10,000
  Feb 2025: $10,500
  Mar 2025: $10,200

MoM Changes:
  Jan: N/A (no previous month)
  Feb: +$500 (+5.0%)
    Dollar: $10,500 - $10,000 = $500
    Percent: ($10,500 - $10,000) / $10,000 × 100 = 5.0%

  Mar: -$300 (-2.9%)
    Dollar: $10,200 - $10,500 = -$300
    Percent: ($10,200 - $10,500) / $10,500 × 100 = -2.86%
```

#### Interpreting Results

| Change | Interpretation | Action |
|--------|---|---|
| +0.5% to +1.5% | Normal variance | Monitor |
| +5.0% to +10% | Moderate growth or increased usage | Review |
| +15% or more | Significant change | Investigate |
| -5% to -10% | Decreased usage | Good for cost |
| -15% or more | Dramatic drop | Check if workload moved |

#### In Your Code

```python
# chargeback_analysis.py, STEP 7

# Sort by user and month (time series)
chargeback_sorted = chargeback.sort_values(['User', 'Month'])

# Calculate MoM dollar change per user
chargeback_sorted['MoMDollarChange'] = chargeback_sorted.groupby('User')['TotalCost'].diff()

# Calculate MoM percent change per user
chargeback_sorted['MoMPercentChange'] = (
    chargeback_sorted.groupby('User')['TotalCost'].pct_change() * 100
).round(2)
```

#### Output Example

```csv
Month,User,TotalCost,MoMDollarChange,MoMPercentChange
2025-01,analytics-prod,22118.95,,
2025-02,analytics-prod,23251.20,1132.25,5.12
2025-03,analytics-prod,23769.55,518.35,2.23
2025-04,analytics-prod,25265.55,1496.00,6.30
2025-05,analytics-prod,24614.30,-651.25,-2.58
```

---

## VALIDATION: Monthly Totals = Cloudability Totals

**Critical Check**: Sum of all your chargeback costs = what Cloudability reports

#### Formula

```
Sum(All Users' Total Cost per Month) = Cloudability's Reported Cluster Cost
```

#### Why This Matters

- If it doesn't match, you're missing namespaces or double-counting
- Ensures 100% cost recovery
- Validates your service distribution logic

#### In Code

```python
# chargeback_analysis.py, STEP 6

# What Cloudability says (sum of ALL namespaces)
cloudability_total = df.groupby('Month')['FairshareValue'].sum()
# Example: 2025-01 = $41,000.00

# What you calculated (sum of all user chargebacks)
our_total = chargeback.groupby('Month')['TotalCost'].sum()
# Example: 2025-01 = $41,000.00

# Difference
difference = cloudability_total - our_total
# Should be < 0.01% (rounding errors only)
```

#### Troubleshooting Mismatches

If `validation_monthly_totals.csv` shows DiffPct > 0.01%:

**Step 1: Check for missing namespaces**
```python
import pandas as pd

df = pd.read_csv('costs_raw.csv')
KNOWN_NAMESPACES = set()

# Add all your user + service namespaces
KNOWN_NAMESPACES.update(['analytics-prod', 'data-science-team-1', ...])
KNOWN_NAMESPACES.update(['kube-system', 'prometheus', ...])

unknown = df[~df['Namespace'].isin(KNOWN_NAMESPACES)]['Namespace'].unique()
if len(unknown) > 0:
    print("Unknown namespaces found:")
    for ns in unknown:
        cost = df[df['Namespace'] == ns]['FairshareValue'].sum()
        print(f"  {ns}: ${cost:,.2f}")
```

**Step 2: Update SERVICE_NAMESPACES**
```python
SERVICE_NAMESPACES.add('any-new-namespace-you-found')
```

**Step 3: Re-run analysis**
```bash
python3 chargeback_analysis.py
```

---

## DETAILED CALCULATION WALKTHROUGH

Complete example with real numbers.

### Input Data

```csv
Month,Namespace,Service,FairshareValue
2025-01,analytics-prod,pod,18750.75
2025-01,data-science-team-1,pod,12500.50
2025-01,ml-engineering,pod,9250.25
2025-01,kube-system,pod,2100.00
2025-01,prometheus,pod,1800.00
2025-01,ingress-nginx,pod,500.00
```

### STEP 1: Classify

```
USER NAMESPACES:
  analytics-prod: $18,750.75
  data-science-team-1: $12,500.50
  ml-engineering: $9,250.25
  Total user: $40,501.50

SERVICE NAMESPACES:
  kube-system: $2,100.00
  prometheus: $1,800.00
  ingress-nginx: $500.00
  Total service: $4,400.00

GRAND TOTAL: $44,901.50 (= Cloudability's reported total for Jan 2025)
```

### STEP 2: Calculate User Proportions

```
Total user cost = $40,501.50

analytics-prod proportion:
  = $18,750.75 / $40,501.50
  = 0.4630 (46.30%)

data-science-team-1 proportion:
  = $12,500.50 / $40,501.50
  = 0.3086 (30.86%)

ml-engineering proportion:
  = $9,250.25 / $40,501.50
  = 0.2283 (22.83%)

Verify: 0.4630 + 0.3086 + 0.2283 = 1.0000 ✓
```

### STEP 3: Allocate Service Costs

```
Service cost = $4,400.00

analytics-prod allocation:
  = 0.4630 × $4,400.00 = $2,037.20

data-science-team-1 allocation:
  = 0.3086 × $4,400.00 = $1,357.84

ml-engineering allocation:
  = 0.2283 × $4,400.00 = $1,004.96

Verify: $2,037.20 + $1,357.84 + $1,004.96 = $4,400.00 ✓
```

### STEP 4: Final Chargeback

```
ANALYTICS-PROD:
  Direct cost: $18,750.75
  Service allocation: $2,037.20
  TOTAL: $20,787.95

DATA-SCIENCE-TEAM-1:
  Direct cost: $12,500.50
  Service allocation: $1,357.84
  TOTAL: $13,858.34

ML-ENGINEERING:
  Direct cost: $9,250.25
  Service allocation: $1,004.96
  TOTAL: $10,255.21

GRAND TOTAL: $20,787.95 + $13,858.34 + $10,255.21 = $44,901.50 ✓
```

**Validation**: $44,901.50 = Cloudability reported $44,901.50 ✓

---

## ROUNDING AND PRECISION

### Why Differences < 0.01% Are OK

```
Example:
  Cloudability total: $44,901.50000
  Your calculated:   $44,901.50004
  Difference:        $0.00004 (0.0000009%)

Cause: Floating-point arithmetic, rounding at each step
```

Python's `pandas` carries 64-bit float precision, which is sufficient for currency.

### Recommended Rounding

```python
# Round to 2 decimal places (cents) at each step
user_monthly['ServiceAllocation'] = (
    user_monthly['ServiceCost'] * user_monthly['Proportion']
).round(2)

chargeback['TotalCost'] = (
    chargeback['DirectCost'] + chargeback['ServiceAllocation']
).round(2)
```

---

## AVERAGE DAILY COST (OPTIONAL)

Some reports want daily costs (useful for dashboards):

```python
# Add to chargeback
import pandas as pd

chargeback['MonthYear'] = pd.to_datetime(chargeback['Month'] + '-01')
chargeback['DaysInMonth'] = chargeback['MonthYear'].dt.daysinmonth
chargeback['DailyCost'] = chargeback['TotalCost'] / chargeback['DaysInMonth']

# Example:
# Jan 2025 (31 days): $22,118.95 / 31 = $713.84/day
# Feb 2025 (28 days): $23,251.20 / 28 = $830.40/day
```

---

## SUMMARY STATISTICS CALCULATIONS

### Total Cost per User (Entire Period)

```
TotalCost = Sum of all months for that user

Example (analytics-prod):
  Jan: $22,118.95
  Feb: $23,251.20
  Mar: $23,850.40
  ... (14 months)
  TOTAL: $297,000.00
```

### Average Monthly Cost

```
AvgMonthly = TotalCost / 14 months

Example:
  $297,000.00 / 14 = $21,214.29/month
```

### Min/Max Month

```
MinMonth = Lowest single month cost
MaxMonth = Highest single month cost

Example:
  MinMonth: $20,787.95 (some low month)
  MaxMonth: $25,600.30 (some high month)
```

### Standard Deviation (Volatility)

```
StdDev = Standard deviation of all 14 monthly values

Interpretation:
  Low StdDev (<$500)   = Stable costs
  High StdDev (>$2000) = Volatile costs, hard to forecast
```

---

## EXPORT OPTIONS

### To Excel with Formulas

```python
import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill

# Read and export
chargeback = pd.read_csv('chargeback_by_user_monthly.csv')

with pd.ExcelWriter('chargeback_report.xlsx', engine='openpyxl') as writer:
    chargeback.to_excel(writer, sheet_name='Monthly', index=False)

# Add formulas (optional)
wb = load_workbook('chargeback_report.xlsx')
ws = wb['Monthly']

# Add subtotals by month
# ... (Excel formula work)

wb.save('chargeback_report.xlsx')
```

### To HTML Report

```python
# Generate HTML dashboard
html = chargeback.to_html(index=False)

with open('chargeback_report.html', 'w') as f:
    f.write(f"""
    <html>
        <head>
            <title>Chargeback Report</title>
            <style>
                table {{ border-collapse: collapse; margin: 20px; }}
                th {{ background-color: #4CAF50; color: white; padding: 10px; }}
                td {{ border: 1px solid #ddd; padding: 8px; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>EMR Chargeback Report (Jan 2025 - Feb 2026)</h1>
            {html}
        </body>
    </html>
    """)

print("✓ HTML report saved: chargeback_report.html")
```

---

## COMMON MISTAKES & HOW TO AVOID

| Mistake | Impact | Fix |
|---------|--------|-----|
| Using `unblended` instead of `fairshare` | Orphaned costs, incomplete recovery | Change to `fairshare` in API call |
| Forgetting service namespaces | Under-charging users for infrastructure | Add all service namespaces to SERVICE_NAMESPACES |
| Not validating totals | Silent data errors | Run validation_monthly_totals.csv check |
| Distributing service costs equally | Unfair charge (big users pay same as small) | Use proportional distribution |
| Rounding too early | Accumulating rounding errors | Round only at final output stage |
| Double-counting namespaces | Over-charging significantly | Ensure each namespace appears only once |

