# Manual Steps to Run Cloudability Cost Analyzer

## Step 1: Set API Credentials

```bash
export CLOUDABILITY_API_KEY='your-api-key'
export CLOUDABILITY_API_PASS='your-api-password'
export CLOUDABILITY_CLUSTER_ID='your-cluster-id'
```

## Step 2: Fetch Data from Cloudability API V3

Run one of these commands:

### Option A: Container Allocations Endpoint (Try this first)
```bash
bash fetch_cloudability_data.sh allocations
```

### Option B: Cost Reporting Endpoint (If option A doesn't work)
```bash
bash fetch_cloudability_data.sh reporting
```

**Expected output:**
- File created: `costs_raw.csv`
- See message: "✓ CSV data fetched successfully"

## Step 3: Run Chargeback Analysis

```bash
python3 chargeback_analysis.py
```

**Expected output files:**
- `chargeback_by_user_monthly.csv` - Monthly costs by user
- `summary_by_user.csv` - Total costs per user
- `chargeback_with_mom_changes.csv` - Month-over-month changes
- `validation_monthly_totals.csv` - Data validation

## Step 4: View Results

```bash
# View chargeback summary
cat summary_by_user.csv

# View monthly breakdown
cat chargeback_by_user_monthly.csv

# View month-over-month changes
cat chargeback_with_mom_changes.csv
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "CLOUDABILITY_API_KEY not set" | Run: `export CLOUDABILITY_API_KEY='your-key'` |
| "CLOUDABILITY_API_PASS not set" | Run: `export CLOUDABILITY_API_PASS='your-password'` |
| "CLOUDABILITY_CLUSTER_ID not set" | Run: `export CLOUDABILITY_CLUSTER_ID='your-id'` |
| "Failed to fetch data - empty response" | Try the other endpoint: `bash fetch_cloudability_data.sh reporting` |
| "API returned an error: unauthorized" | Check your API key and password are correct |

---

## All in One Command

```bash
export CLOUDABILITY_API_KEY='your-key' && \
export CLOUDABILITY_API_PASS='your-password' && \
export CLOUDABILITY_CLUSTER_ID='your-id' && \
bash fetch_cloudability_data.sh allocations && \
python3 chargeback_analysis.py
```
