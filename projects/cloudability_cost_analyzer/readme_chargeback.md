# EMR on Kubernetes Cloudability Chargeback - Complete Solution

This solution provides everything needed to create monthly chargeback reports for your EMR on Kubernetes cluster using Cloudability data.

**Period**: Jan 2025 - Feb 2026
**Granularity**: Monthly by user/namespace
**Cost Metric**: Fairshare (includes idle capacity distribution)

---

## 📋 WHAT YOU GET

### Scripts (All executable)
- **`run_chargeback.sh`** — Main entry point (easiest to use)
- **`fetch_cloudability_data.sh`** — Pulls data from Cloudability API
- **`chargeback_analysis.py`** — Performs all calculations (9 steps)
- **`generate_sample_cloudability_data.py`** — Creates test/sample data

### Documentation
- **`CHARGEBACK_QUICKSTART.md`** — Get started in 5 minutes
- **`CALCULATIONS_EXPLAINED.md`** — Deep dive into every formula
- **`README_CHARGEBACK.md`** — This file

### Output Files (Generated)
- **`chargeback_by_user_monthly.csv`** — Main chargeback table
- **`summary_by_user.csv`** — Totals & statistics by user
- **`chargeback_with_mom_changes.csv`** — Month-over-month trends
- **`validation_monthly_totals.csv`** — Quality checks vs Cloudability

### Configuration
- **`requirements.txt`** — Python dependencies

---

## 🚀 QUICKSTART (2 MINUTES)

### Option A: Test with Sample Data (No API Key Needed)

```bash
# Install dependencies
pip install -r requirements.txt

# Generate sample data and run analysis
bash run_chargeback.sh sample

# View results
head chargeback_by_user_monthly.csv
cat summary_by_user.csv
```

### Option B: Use Real Cloudability Data (Production)

```bash
# Install dependencies
pip install -r requirements.txt

# Set your credentials
export CLOUDABILITY_API_KEY="your-api-key"
export CLOUDABILITY_CLUSTER_ID="your-cluster-id"

# Fetch and analyze
bash run_chargeback.sh real

# View results
head chargeback_by_user_monthly.csv
cat summary_by_user.csv
```

---

## 📖 DOCUMENTATION ROADMAP

### For Quick Understanding (5-10 min)
1. Read this file (README_CHARGEBACK.md)
2. Read CHARGEBACK_QUICKSTART.md
3. Run with sample data to see output

### For Implementation (30-60 min)
1. Get Cloudability API key
2. Identify your cluster ID
3. Run `bash run_chargeback.sh real`
4. Review output files

### For Deep Understanding (60+ min)
1. Read CALCULATIONS_EXPLAINED.md
2. Review the Python code comments
3. Customize SERVICE_NAMESPACES for your environment

---

## 🎯 YOUR QUESTIONS ANSWERED

### Q: Which cost column should I use - unblended or fairshare?

**Answer: Use fairshare.** It redistributes idle cluster capacity proportionally to users, ensuring 100% cost recovery with no orphaned costs.

| Metric | Use When |
|--------|----------|
| `fairshare` | **Chargeback** (ensures every dollar is accounted for) |
| `unblended` | Cost accounting (but leaves some costs unaccounted for) |

See: CALCULATIONS_EXPLAINED.md → "Q1: Which Cost Column"

---

### Q: How do I handle service namespaces like kube-system, prometheus, logging?

**Answer: Distribute their costs proportionally to users based on their direct cost.**

Example:
- Total cluster: $10,000/month
- User A direct: $6,000 (60% of user costs)
- User B direct: $4,000 (40% of user costs)
- Services: $1,000
- → User A pays: $6,000 + (60% × $1,000) = $6,600
- → User B pays: $4,000 + (40% × $1,000) = $4,400

See: CALCULATIONS_EXPLAINED.md → "Q2: Service Namespaces"

---

### Q: What are the common service namespaces?

These are defined in `chargeback_analysis.py`:

**Kubernetes Infrastructure:**
- `kube-system` — API server, controller manager, scheduler
- `kube-node-lease` — Node heartbeat mechanism
- `kube-public` — Kubernetes public data

**Monitoring & Logging:**
- `prometheus` — Metrics collection
- `grafana` — Metrics visualization
- `loki` — Log aggregation
- `logging` — Log storage

**Networking & Security:**
- `ingress-nginx` — API gateway/ingress controller
- `cert-manager` — SSL/TLS certificate management
- `vault` — Secrets management
- `external-dns` — DNS management

**Cluster Management:**
- `cluster-autoscaler` — Auto-scaling agent
- `kyverno` — Policy enforcement

**Edit for your environment:**
```python
# In chargeback_analysis.py, STEP 2
SERVICE_NAMESPACES = {
    'kube-system', 'kube-node-lease', 'kube-public',
    'prometheus', 'grafana', 'loki', 'logging',
    'ingress-nginx', 'cert-manager', 'vault',
    'external-dns', 'cluster-autoscaler', 'kyverno',
    'your-custom-service',  # ← Add yours here
}
```

---

### Q: How are monthly totals validated against Cloudability?

**Answer: Sum of all user chargebacks per month must equal Cloudability's reported cluster cost.**

```
Sum(analytics-prod + data-science-team-1 + ... for Jan 2025)
= Cloudability reported cluster cost for Jan 2025
```

Check: `validation_monthly_totals.csv` (should show DiffPct < 0.01%)

See: CALCULATIONS_EXPLAINED.md → "Validation: Monthly Totals"

---

### Q: How do I calculate month-over-month change per user?

**Answer: Track both dollar change and percent change.**

```
MoM Dollar Change = Current Month - Previous Month
MoM % Change = (Current Month - Previous Month) / Previous Month × 100%

Example:
  Jan: $10,000
  Feb: $10,500
  MoM: +$500 (+5.0%)
```

See: CALCULATIONS_EXPLAINED.md → "Q3: Month-over-Month Change"

Output file: `chargeback_with_mom_changes.csv`

---

## 📊 OUTPUT FILES EXPLAINED

### 1. `chargeback_by_user_monthly.csv` (MAIN)

Monthly chargeback amount per user.

```csv
Month,User,DirectCost,ServiceAllocation,TotalCost
2025-01,analytics-prod,18750.75,3368.20,22118.95
2025-01,data-science-team-1,12500.50,2245.10,14745.60
2025-02,analytics-prod,19800.45,3450.75,23251.20
```

**Use for:**
- Monthly invoicing to teams
- Usage reports
- Showing cost breakdown (direct vs service)

---

### 2. `summary_by_user.csv` (TOTALS)

Aggregate stats by user (entire 14-month period).

```csv
User,DirectCost,ServiceAllocated,TotalCost,AvgMonthly,MinMonth,MaxMonth,StdDev
analytics-prod,252000.00,45000.00,297000.00,24750.00,22118.95,25600.30,1200.50
```

**Use for:**
- Annual cost summaries
- Identifying heavy users
- Budget planning
- Forecasting

---

### 3. `chargeback_with_mom_changes.csv` (TRENDS)

Month-over-month changes per user.

```csv
Month,User,TotalCost,MoMDollarChange,MoMPercentChange
2025-01,analytics-prod,22118.95,,
2025-02,analytics-prod,23251.20,1132.25,5.12
2025-03,analytics-prod,23769.55,518.35,2.23
```

**Use for:**
- Cost trend analysis
- Anomaly detection (alert on large % changes)
- Performance monitoring

---

### 4. `validation_monthly_totals.csv` (QUALITY CHECK)

Validates calculations against Cloudability.

```csv
Month,CloudabilityTotal,OurTotal,Difference,DiffPct
2025-01,41000.00,41000.00,0.00,0.000000
2025-02,41500.00,41500.00,0.00,0.000000
```

**If DiffPct > 0.01%:**
- Check for missing namespaces
- Verify SERVICE_NAMESPACES is complete
- Verify Cloudability API response

---

## 🔧 CUSTOMIZATION

### Add/Remove Service Namespaces

Edit `chargeback_analysis.py`:

```python
SERVICE_NAMESPACES = {
    # ... existing items ...
    'my-monitoring',      # ← Add new ones
    'my-custom-service',
}
```

Re-run:
```bash
python3 chargeback_analysis.py
```

### Change Date Range

Edit `fetch_cloudability_data.sh`:

```bash
START_DATE="2024-06-01"   # ← Change this
END_DATE="2026-12-31"     # ← Change this
```

Re-run:
```bash
bash fetch_cloudability_data.sh
python3 chargeback_analysis.py
```

### Export to Excel

```bash
python3 << 'EOF'
import pandas as pd

chargeback = pd.read_csv('chargeback_by_user_monthly.csv')
summary = pd.read_csv('summary_by_user.csv')

with pd.ExcelWriter('chargeback_report.xlsx', engine='openpyxl') as writer:
    chargeback.to_excel(writer, sheet_name='Monthly', index=False)
    summary.to_excel(writer, sheet_name='Summary', index=False)

print("✓ Created chargeback_report.xlsx")
EOF
```

---

## 🔍 TROUBLESHOOTING

### "File not found: costs_raw.csv"
```bash
# Generate sample data first
python3 generate_sample_cloudability_data.py

# Or fetch from Cloudability
export CLOUDABILITY_API_KEY="your-key"
export CLOUDABILITY_CLUSTER_ID="your-id"
bash fetch_cloudability_data.sh
```

### "ERROR: CLOUDABILITY_API_KEY not set"
```bash
export CLOUDABILITY_API_KEY="your-actual-api-key"
export CLOUDABILITY_CLUSTER_ID="your-actual-cluster-id"
bash run_chargeback.sh real
```

### "✗ Validation FAILED - Monthly totals don't match"

You have unmapped namespaces. Find them:

```bash
python3 << 'EOF'
import pandas as pd

df = pd.read_csv('costs_raw.csv')

MAPPED = {
    # User namespaces
    'analytics-prod', 'data-science-team-1', 'data-science-team-2',
    'ml-engineering', 'quant-research', 'research-lab',
    # Service namespaces
    'kube-system', 'kube-node-lease', 'kube-public',
    'prometheus', 'grafana', 'loki', 'logging',
    'ingress-nginx', 'cert-manager', 'vault',
}

unknown = df[~df['Namespace'].isin(MAPPED)]['Namespace'].unique()
if len(unknown) > 0:
    print("Unmapped namespaces:")
    for ns in unknown:
        cost = df[df['Namespace'] == ns]['FairshareValue'].sum()
        print(f"  {ns}: ${cost:,.2f}")
        print("    → Add to SERVICE_NAMESPACES if it's infrastructure")
EOF
```

Then update `chargeback_analysis.py` and re-run.

---

## 📅 WORKFLOW FOR MONTHLY REPORTS

### Setup (One-time)
1. Get Cloudability API key (Settings → API Keys)
2. Find your cluster ID (Cloudability UI)
3. Edit `SERVICE_NAMESPACES` for your environment
4. Test with sample data: `bash run_chargeback.sh sample`

### Monthly Execution (Recurring)
```bash
# Pull latest data from Cloudability
export CLOUDABILITY_API_KEY="your-key"
export CLOUDABILITY_CLUSTER_ID="your-id"
bash fetch_cloudability_data.sh

# Run analysis
python3 chargeback_analysis.py

# Share results
# - Email chargeback_by_user_monthly.csv to finance
# - Share summary_by_user.csv with leadership
# - Archive validation_monthly_totals.csv
```

### Automation (Optional)
```bash
# Add to crontab for automated monthly runs
# (runs on 1st of each month at 8 AM)

0 8 1 * * cd /path/to/project && \
  export CLOUDABILITY_API_KEY="your-key" && \
  export CLOUDABILITY_CLUSTER_ID="your-id" && \
  bash fetch_cloudability_data.sh && \
  python3 chargeback_analysis.py && \
  mail -s "Chargeback report" finance@company.com < chargeback_by_user_monthly.csv
```

---

## 🎓 KEY CONCEPTS

### Fairshare Cost
- Distributes idle cluster capacity to users proportionally
- Ensures 100% cost recovery (no orphaned costs)
- Fair: Users who allocate more pay proportionally more

### Service Cost Distribution
- Infrastructure costs (kube-system, prometheus, etc.) benefit all users
- Allocate proportionally based on each user's direct cost share
- User A gets 60% of cluster = pays 60% of service costs

### Validation
- Monthly totals from all users must equal Cloudability's reported cluster cost
- If they don't match, you're missing namespaces
- Difference should be < 0.01% (rounding only)

### Month-over-Month Change
- Tracks cost trends per user
- Useful for anomaly detection (alert on >10% jumps)
- Helps with cost forecasting

---

## 📞 SUPPORT

### Common Questions
See: **CHARGEBACK_QUICKSTART.md** → "TROUBLESHOOTING" & "FAQ"

### Detailed Calculations
See: **CALCULATIONS_EXPLAINED.md**

### Code Comments
All Python scripts have detailed comments explaining each step

---

## 🗂️ FILE STRUCTURE

```
cloudability_cost_analyzer/
├── README_CHARGEBACK.md              ← You are here
├── CHARGEBACK_QUICKSTART.md           ← Getting started
├── CALCULATIONS_EXPLAINED.md          ← Deep dive
│
├── run_chargeback.sh                  ← Main entry point
├── fetch_cloudability_data.sh         ← Fetch from API
├── chargeback_analysis.py             ← Main analysis
├── generate_sample_cloudability_data.py ← Test data
│
├── requirements.txt                   ← Python dependencies
│
├── costs_raw.csv                      ← Input (generated)
├── chargeback_by_user_monthly.csv     ← Output
├── summary_by_user.csv                ← Output
├── chargeback_with_mom_changes.csv    ← Output
└── validation_monthly_totals.csv      ← Output
```

---

## ✅ CHECKLIST

- [ ] Python 3.8+ installed
- [ ] Dependencies installed: `pip install -r requirements.txt`
- [ ] Test with sample data: `bash run_chargeback.sh sample`
- [ ] Review output files
- [ ] Get Cloudability API key
- [ ] Identify cluster ID
- [ ] Update SERVICE_NAMESPACES for your environment
- [ ] Run with real data: `bash run_chargeback.sh real`
- [ ] Validate results
- [ ] Share with stakeholders

---

## 🎉 YOU'RE READY!

Start here:
```bash
pip install -r requirements.txt
bash run_chargeback.sh sample
```

Then read **CHARGEBACK_QUICKSTART.md** for detailed explanations.

Questions? See **CALCULATIONS_EXPLAINED.md** for the math behind every step.

