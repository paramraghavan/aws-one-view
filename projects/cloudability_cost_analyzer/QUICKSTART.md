# Cloudability Cost Analyzer - Quick Start Guide

## Overview
This tool fetches cost data from Cloudability API V3 and analyzes it to produce chargeback reports by user/namespace.

---

## Option 1: Test with Sample Data (No API needed)

```bash
bash run_full_workflow.sh sample
```

This generates fake data and produces all output files so you can see how it works.

---

## Option 2: Use Real Cloudability API V3 Data

### Step 1: Get Your API Credentials

You need three pieces of information from Cloudability:
- **API Key** - Your authentication key
- **API Password** - Your authentication password
- **Cluster ID** - The ID of your Kubernetes cluster

### Step 2: Set Environment Variables

```bash
export CLOUDABILITY_API_KEY='your-actual-api-key'
export CLOUDABILITY_API_PASS='your-actual-password'
export CLOUDABILITY_CLUSTER_ID='your-cluster-id'
```

### Step 3: Choose an Endpoint

#### Option A: Container Allocations (Recommended - Try this first)

```bash
bash run_full_workflow.sh real allocations
```

**Best for**: Container-level cost allocation, detailed breakdown

#### Option B: Cost Reporting (If allocations fails)

```bash
bash run_full_workflow.sh real reporting
```

**Best for**: General cost reporting, aggregated view

### Step 4: Check the Output

The workflow will:
1. Fetch data from Cloudability
2. Split data into monthly files
3. Generate chargeback analysis

**Output files created:**
- `costs_raw.csv` - Combined data from all months
- `chargeback_by_user_monthly.csv` - Chargeback by user per month
- `summary_by_user.csv` - Summary totals per user
- `chargeback_with_mom_changes.csv` - Month-over-month changes
- `validation_monthly_totals.csv` - Validation against Cloudability
- `monthly/` folder - Individual CSV files per month

---

## Complete Example

```bash
# 1. Set credentials
export CLOUDABILITY_API_KEY='abc123xyz789'
export CLOUDABILITY_API_PASS='pass456'
export CLOUDABILITY_CLUSTER_ID='1fe68867-f04b-4791-b7bb-9a5ef584c24b'

# 2. Run the full workflow
bash run_full_workflow.sh real allocations

# 3. View results
cat chargeback_by_user_monthly.csv
cat summary_by_user.csv
```

---

## Troubleshooting

### "Failed to fetch data - empty response"
- **Check API credentials** - Verify CLOUDABILITY_API_KEY and CLOUDABILITY_API_PASS are correct
- **Try the other endpoint** - If using `allocations`, try `reporting`
  ```bash
  bash run_full_workflow.sh real reporting
  ```

### "API returned an error: unauthorized"
- Your API credentials are incorrect
- Check the CLOUDABILITY_API_KEY and CLOUDABILITY_API_PASS values

### "CLOUDABILITY_API_PASS not set"
- Run: `export CLOUDABILITY_API_PASS='your-password'`

### No rows in output
- The date range (2025-01-01 to 2026-03-31) may have no data
- Check if your cluster has cost data in Cloudability for those dates

---

## Manual Steps (Advanced)

If you want to run each step separately:

```bash
# 1. Fetch data
bash fetch_cloudability_data.sh allocations

# 2. Split into monthly files
python3 split_costs_by_month.py --input costs_raw.csv --output-dir ./monthly

# 3. Run analysis
python3 chargeback_analysis.py
```

---

## File Descriptions

| File | Purpose |
|------|---------|
| `fetch_cloudability_data.sh` | Fetches data from Cloudability API V3 |
| `chargeback_analysis.py` | Main analysis script that produces chargeback reports |
| `split_costs_by_month.py` | Splits combined CSV into individual monthly files |
| `generate_sample_cloudability_data.py` | Generates fake sample data for testing |
| `run_full_workflow.sh` | Orchestrates all steps |

---

## Questions?

See the individual script help:
```bash
bash run_full_workflow.sh help
```
