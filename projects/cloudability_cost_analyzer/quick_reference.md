# Quick Reference - Server vs Local

**TL;DR:** Run fetch on server, everything else on local.

---

## 🖥️ ON SERVER (One-Time Setup)

```bash
# SSH to your server
ssh your-server

# Go to project directory
cd /path/to/cloudability_cost_analyzer

# Set credentials
export CLOUDABILITY_API_KEY="your-api-key"
export CLOUDABILITY_CLUSTER_ID="your-cluster-id"

# ONLY COMMAND YOU NEED TO RUN:
bash fetch_cloudability_data.sh csv

# Verify success
ls -lh costs_raw.csv
head costs_raw.csv
```

**That's it!** The server creates `costs_raw.csv`.

---

## 💻 ON LOCAL MACHINE (Everything Else)

### **Step 1: Get the File from Server**

```bash
# Copy costs_raw.csv from server to local
scp your-user@your-server:/path/to/costs_raw.csv ./

# Verify
ls -lh costs_raw.csv
```

### **Step 2: Install & Setup**

```bash
# One-time: Install Python packages
pip install -r requirements.txt
```

### **Step 3: Run Analysis**

```bash
# Split into monthly files
python3 split_costs_by_month.py

# Run chargeback analysis
python3 chargeback_analysis.py

# Done! Check results
ls -1 *.csv  # Shows all output files
```

---

## 📋 What Each Step Creates

| Location | Command | Creates |
|----------|---------|---------|
| Server | `bash fetch_cloudability_data.sh csv` | `costs_raw.csv` |
| Local | `python3 split_costs_by_month.py` | `monthly/costs_*.csv` (14 files) |
| Local | `python3 chargeback_analysis.py` | 4 analysis CSV files |

---

## 🚀 Fastest Way

### **Server** (copy-paste):
```bash
export CLOUDABILITY_API_KEY="key"
export CLOUDABILITY_CLUSTER_ID="id"
bash fetch_cloudability_data.sh csv
```

### **Local** (copy-paste):
```bash
scp your-user@your-server:costs_raw.csv ./
pip install -r requirements.txt
python3 split_costs_by_month.py
python3 chargeback_analysis.py
```

---

## 📂 Files You'll Have

**After server fetch:**
```
SERVER: costs_raw.csv (224 rows)
```

**After copying to local:**
```
LOCAL: costs_raw.csv (224 rows)
```

**After splitting:**
```
LOCAL: monthly/
  ├── costs_2025_01.csv
  ├── costs_2025_02.csv
  ├── ... 14 files total
  └── costs_2026_02.csv
```

**After analysis:**
```
LOCAL: chargeback_by_user_monthly.csv       (monthly chargeback)
       summary_by_user.csv                  (summary stats)
       chargeback_with_mom_changes.csv      (trends)
       validation_monthly_totals.csv        (QC check)
```

---

## ✅ Verification Commands

### **On Server - Verify Fetch Worked**
```bash
wc -l costs_raw.csv          # Should show ~225 rows
head costs_raw.csv           # Should show data
du -h costs_raw.csv          # Should be ~20-50 KB
```

### **On Local - Verify Split Worked**
```bash
ls monthly/ | wc -l          # Should show 14
du -sh monthly/              # Should be ~20-50 KB
```

### **On Local - Verify Analysis Worked**
```bash
ls chargeback*.csv           # Should show 4 files
wc -l chargeback_by_user_monthly.csv  # Should match number of (users × months)
```

---

## 🔄 Monthly Refresh

When you need to refresh (next month):

### **Server** (get fresh data)
```bash
export CLOUDABILITY_API_KEY="key"
export CLOUDABILITY_CLUSTER_ID="id"
bash fetch_cloudability_data.sh csv
scp costs_raw.csv your-local-user@your-local:/path/
```

### **Local** (reprocess)
```bash
# Old results (optional cleanup)
rm -rf monthly/ chargeback*.csv

# Reprocess with new data
python3 split_costs_by_month.py
python3 chargeback_analysis.py
```

---

## 📞 Common Issues

| Issue | Solution |
|-------|----------|
| "curl: command not found" | Install curl: `apt-get install curl` or `brew install curl` |
| "API Key not set" | `export CLOUDABILITY_API_KEY="actual-key"` |
| "Permission denied (scp)" | `ssh server chmod 644 costs_raw.csv` |
| "pandas not found" | `pip install -r requirements.txt` |
| "No monthly files" | `python3 split_costs_by_month.py --input costs_raw.csv --output-dir monthly` |

---

## 🎯 5-Minute Setup

```bash
# SERVER (2 minutes)
export CLOUDABILITY_API_KEY="your-key"
export CLOUDABILITY_CLUSTER_ID="your-id"
bash fetch_cloudability_data.sh csv

# LOCAL (3 minutes)
scp user@server:costs_raw.csv ./
pip install -r requirements.txt
python3 split_costs_by_month.py
python3 chargeback_analysis.py
```

Done! 🎉

---

## 📚 Full Documentation

- **`SERVER_LOCAL_WORKFLOW.md`** — Complete step-by-step guide
- **`MONTHLY_FILES_GUIDE.md`** — Monthly file examples
- **`CHARGEBACK_QUICKSTART.md`** — All features overview
- **`CALCULATIONS_EXPLAINED.md`** — How it works

---

## 🎓 What the Scripts Do

**Server Script (`fetch_cloudability_data.sh`):**
- Calls Cloudability API
- Requests Jan 2025 - Feb 2026 data
- Fetches as CSV (faster than JSON)
- Saves to `costs_raw.csv`

**Local Scripts:**
- `split_costs_by_month.py` → Splits CSV by month (14 files)
- `chargeback_analysis.py` → Analyzes and generates reports

All outputs are CSV files - easy to view, share, import to Excel.

