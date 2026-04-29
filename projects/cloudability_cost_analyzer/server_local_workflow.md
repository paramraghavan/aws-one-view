# Server + Local Workflow Guide

Run data fetch on server (where Cloudability credentials are), then run analysis locally.

---

## 📋 Workflow Overview

```
SERVER (where Cloudability API access is)
├── Fetch costs_raw.csv from Cloudability API
└── Copy costs_raw.csv to local machine

LOCAL (your laptop/desktop)
├── Split costs_raw.csv into monthly files
├── Run chargeback analysis
└── Generate reports
```

---

## 🖥️ STEP 1: ON SERVER

### **Prerequisites on Server**
- Bash/shell access
- `curl` command (usually pre-installed)
- Internet access to Cloudability API
- Cloudability API credentials available

### **Commands to Run on Server**

```bash
# SSH to server
ssh your-server

# Navigate to project directory
cd /path/to/cloudability_cost_analyzer

# Set your Cloudability credentials
export CLOUDABILITY_API_KEY="your-api-key-here"
export CLOUDABILITY_CLUSTER_ID="your-cluster-id-here"

# Fetch data from Cloudability (CSV format - fastest)
bash fetch_cloudability_data.sh csv

# Verify file was created
ls -lh costs_raw.csv
head -10 costs_raw.csv

# Get file size and row count
wc -l costs_raw.csv
du -h costs_raw.csv
```

**What this does:**
- Calls Cloudability API (Jan 2025 - Feb 2026)
- Downloads costs data in CSV format
- Saves to `costs_raw.csv`
- Takes ~10-30 seconds

### **Output on Server**

You should see:
```
========================================================================
 CLOUDABILITY DATA FETCHER
========================================================================

[1/3] Configuration
      API Key: your-api...key
      Cluster ID: cluster-123
      Date Range: 2025-01-01 to 2026-02-28
      Format: csv

[2/3] Fetching data from Cloudability API...
      Endpoint: https://api.cloudability.com/v1/costs
      Accept: text/csv
      ✓ CSV data fetched successfully

========================================================================
 SUMMARY
========================================================================
  Data format: csv
  Rows: 225 (including header)
  Total Fairshare Cost: $1,052,400.00

  Sample data (first 10 rows):
  ---
  Month,Namespace,Service,FairshareValue
  2025-01,analytics-prod,pod,18750.75
  2025-01,data-science-team-1,pod,12500.50
  ...
```

### **Copy File to Local Machine**

From **your local terminal** (not on server):

```bash
# Copy from server to local
scp your-user@your-server:/path/to/cloudability_cost_analyzer/costs_raw.csv ./

# Verify it was copied
ls -lh costs_raw.csv
wc -l costs_raw.csv
```

**Or if you prefer, use this on the server:**
```bash
# Display the file content
cat costs_raw.csv
# Copy the output and save locally as costs_raw.csv
```

---

## 💻 STEP 2: ON LOCAL MACHINE

### **Prerequisites on Local**
- Python 3.8+
- pandas library
- The `costs_raw.csv` file from server

### **Setup Local Environment**

```bash
# Navigate to your project directory
cd ~/projects/cloudability_cost_analyzer

# Install dependencies (one time)
pip install -r requirements.txt

# Verify costs_raw.csv is here
ls -lh costs_raw.csv
head costs_raw.csv
```

### **Split into Monthly Files**

```bash
# Create monthly directory
mkdir -p monthly

# Split the CSV by month
python3 split_costs_by_month.py --input costs_raw.csv --output-dir monthly

# Verify files were created
ls -lh monthly/
ls monthly/costs_*.csv | wc -l  # Should show 14 files
```

### **Output**

```
======================================================================
 SPLIT COSTS BY MONTH
======================================================================

Input file: costs_raw.csv
Output directory: ./monthly
Total rows: 224
Date range: 2025-01 to 2026-02

Creating 14 monthly files...

  ✓ costs_2025_01.csv            6 rows  $   41,000.00
  ✓ costs_2025_02.csv            6 rows  $   41,500.00
  ...
  ✓ costs_2026_02.csv            6 rows  $   46,200.00

======================================================================
 SUMMARY
======================================================================

Files created: 14
Total cost (all months): $1,052,400.00

Files saved to: ./monthly/
```

### **Run Chargeback Analysis**

```bash
# Run the full analysis (9 steps)
python3 chargeback_analysis.py

# This generates 4 output files:
#   - chargeback_by_user_monthly.csv
#   - summary_by_user.csv
#   - chargeback_with_mom_changes.csv
#   - validation_monthly_totals.csv
```

### **View Results**

```bash
# Main chargeback report
head -20 chargeback_by_user_monthly.csv
cat chargeback_by_user_monthly.csv

# Summary statistics
cat summary_by_user.csv

# Validation check (should all be ✓)
cat validation_monthly_totals.csv

# Trends (month-over-month changes)
cat chargeback_with_mom_changes.csv | head -20
```

---

## 📂 Final Directory Structure (Local)

After all steps:

```
~/projects/cloudability_cost_analyzer/
├── costs_raw.csv                    ← From server
│
├── monthly/                         ← Split by local script
│   ├── costs_2025_01.csv
│   ├── costs_2025_02.csv
│   ├── ...
│   └── costs_2026_02.csv
│
├── chargeback_by_user_monthly.csv   ← Analysis output
├── summary_by_user.csv              ← Analysis output
├── chargeback_with_mom_changes.csv  ← Analysis output
├── validation_monthly_totals.csv    ← Analysis output
│
├── split_costs_by_month.py          ← Scripts
├── chargeback_analysis.py
├── MONTHLY_FILES_GUIDE.md
├── CALCULATIONS_EXPLAINED.md
└── ... (other guides)
```

---

## 🔄 Complete Step-by-Step

### **On Server (takes ~30 sec)**

```bash
# 1. Navigate to directory
cd /path/to/cloudability_cost_analyzer

# 2. Set credentials
export CLOUDABILITY_API_KEY="your-key"
export CLOUDABILITY_CLUSTER_ID="your-id"

# 3. Fetch data
bash fetch_cloudability_data.sh csv

# 4. Verify
cat costs_raw.csv | head
```

### **On Local (takes ~1-2 min)**

```bash
# 1. Copy file from server
scp your-user@your-server:/path/to/costs_raw.csv ./

# 2. Install dependencies
pip install -r requirements.txt

# 3. Split by month
python3 split_costs_by_month.py

# 4. Run analysis
python3 chargeback_analysis.py

# 5. View results
cat chargeback_by_user_monthly.csv
cat summary_by_user.csv
```

---

## 🎯 Why This Split?

| Step | Where | Why |
|------|-------|-----|
| **Fetch from Cloudability** | Server | Credentials are on server |
| **Split into monthly** | Local | Python work, easier locally |
| **Run analysis** | Local | Python work, easier locally |
| **View/share reports** | Local | You have the results |

---

## ⚡ Quick Reference

### On Server (just one command needed)
```bash
export CLOUDABILITY_API_KEY="key"
export CLOUDABILITY_CLUSTER_ID="id"
bash fetch_cloudability_data.sh csv
# Creates: costs_raw.csv
```

### On Local (three simple commands)
```bash
pip install -r requirements.txt
python3 split_costs_by_month.py
python3 chargeback_analysis.py
# Creates: monthly files + analysis results
```

---

## 🐛 Troubleshooting

### **Server: "curl: command not found"**
```bash
# Install curl
sudo apt-get install curl  # Linux
brew install curl          # macOS
```

### **Server: "API Key not found"**
```bash
# Make sure credentials are set
echo $CLOUDABILITY_API_KEY
echo $CLOUDABILITY_CLUSTER_ID

# If empty, set them
export CLOUDABILITY_API_KEY="your-actual-key"
export CLOUDABILITY_CLUSTER_ID="your-actual-id"
```

### **Local: "pandas not found"**
```bash
pip install -r requirements.txt
# Or
pip install pandas numpy
```

### **File Transfer: "Permission denied"**
```bash
# Make sure file is readable on server
ssh your-server chmod 644 costs_raw.csv

# Then copy
scp your-user@your-server:costs_raw.csv ./
```

### **Validate Data After Transfer**

```bash
# On server (before copying)
wc -l costs_raw.csv
md5sum costs_raw.csv

# On local (after copying)
wc -l costs_raw.csv
md5sum costs_raw.csv
# Should match!
```

---

## 📝 Automation Option

If you run this regularly, you could automate the server part:

### **Server Cron Job** (runs monthly on 1st of month)

```bash
# On server, add to crontab
0 8 1 * * cd /path/to/cloudability_cost_analyzer && \
  export CLOUDABILITY_API_KEY="your-key" && \
  export CLOUDABILITY_CLUSTER_ID="your-id" && \
  bash fetch_cloudability_data.sh csv && \
  echo "Fetch complete"
```

Then you just download `costs_raw.csv` monthly from the server.

---

## ✅ Checklist

### Server Setup
- [ ] SSH access to server
- [ ] Cloudability API key available
- [ ] Cluster ID known
- [ ] curl installed
- [ ] Project directory exists with scripts

### Server Execution
- [ ] Set CLOUDABILITY_API_KEY environment variable
- [ ] Set CLOUDABILITY_CLUSTER_ID environment variable
- [ ] Run `bash fetch_cloudability_data.sh csv`
- [ ] Verify `costs_raw.csv` created
- [ ] Copy to local machine

### Local Setup
- [ ] Python 3.8+ installed
- [ ] pip installed
- [ ] Project directory created
- [ ] `costs_raw.csv` copied from server
- [ ] Dependencies: `pip install -r requirements.txt`

### Local Execution
- [ ] Run `python3 split_costs_by_month.py`
- [ ] Verify `monthly/` directory created with 14 files
- [ ] Run `python3 chargeback_analysis.py`
- [ ] Verify 4 output CSV files created
- [ ] Review results

---

## 📊 Summary

**Server side** (once per month or on-demand):
- Fetch raw data from Cloudability API → `costs_raw.csv`

**Local side** (anytime, can rerun):
- Split data into monthly files → `monthly/costs_*.csv`
- Analyze and generate reports → 4 CSV outputs

This way you get the **best of both worlds**:
- Server handles API authentication
- Local machine handles data processing and analysis

