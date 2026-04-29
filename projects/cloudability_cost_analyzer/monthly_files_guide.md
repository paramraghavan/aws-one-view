# Monthly Files Guide

Split your combined costs data into separate files for each month (Jan 2025 - Feb 2026).

---

## 🎯 Quick Start

### **Option 1: Full Workflow (Recommended)**

Fetch → Split by Month → Analyze (all in one command):

```bash
export CLOUDABILITY_API_KEY="your-key"
export CLOUDABILITY_CLUSTER_ID="your-id"

bash run_full_workflow.sh real
```

**Creates:**
- `costs_raw.csv` — Combined file (all months)
- `monthly/costs_2025_01.csv` — January 2025
- `monthly/costs_2025_02.csv` — February 2025
- ... (one file per month)
- `monthly/costs_2026_02.csv` — February 2026
- Chargeback analysis results (4 CSV files)

### **Option 2: Split Manually**

If you already have `costs_raw.csv`:

```bash
python3 split_costs_by_month.py
```

This creates monthly files in `./monthly/` directory.

### **Option 3: Test with Sample Data**

```bash
bash run_full_workflow.sh sample
```

Generates sample data, splits by month, and runs analysis.

---

## 📂 Output Structure

After running full workflow:

```
cloudability_cost_analyzer/
├── costs_raw.csv                    ← Combined (all months)
│
├── monthly/                         ← Monthly files
│   ├── costs_2025_01.csv           ← January 2025
│   ├── costs_2025_02.csv           ← February 2025
│   ├── costs_2025_03.csv           ← March 2025
│   ├── ...
│   └── costs_2026_02.csv           ← February 2026
│
├── chargeback_by_user_monthly.csv  ← Analysis: Monthly chargeback
├── summary_by_user.csv             ← Analysis: Totals
├── chargeback_with_mom_changes.csv ← Analysis: Trends
└── validation_monthly_totals.csv   ← Analysis: Validation
```

---

## 💾 Monthly File Format

Each file contains all namespaces for that month:

**`monthly/costs_2025_01.csv`:**
```csv
Month,Namespace,Service,FairshareValue
2025-01,analytics-prod,pod,18750.75
2025-01,data-science-team-1,pod,12500.50
2025-01,ml-engineering,pod,9250.25
2025-01,kube-system,pod,2100.00
2025-01,prometheus,pod,1800.00
2025-01,ingress-nginx,pod,500.00
```

**`monthly/costs_2025_02.csv`:**
```csv
Month,Namespace,Service,FairshareValue
2025-02,analytics-prod,pod,19800.45
2025-02,data-science-team-1,pod,13200.30
...
```

---

## 🛠️ Usage Examples

### **View a Specific Month**

```bash
# View January 2025
cat monthly/costs_2025_01.csv

# View first 10 rows of January
head monthly/costs_2025_01.csv

# Count rows in January
wc -l monthly/costs_2025_01.csv
```

### **Compare Two Months**

```bash
# See how costs changed from January to February
diff monthly/costs_2025_01.csv monthly/costs_2025_02.csv
```

### **Get Monthly Totals**

```bash
# Sum costs for January
awk -F, 'NR>1 {sum+=$NF} END {print "Total:", sum}' monthly/costs_2025_01.csv

# Sum all monthly files
for file in monthly/costs_*.csv; do
  month=$(basename "$file" .csv | sed 's/costs_//')
  total=$(awk -F, 'NR>1 {sum+=$NF} END {printf "%.2f", sum}' "$file")
  echo "$month: \$$total"
done
```

### **Filter a Specific User per Month**

```bash
# Get analytics-prod costs for January 2025
grep "analytics-prod" monthly/costs_2025_01.csv

# Get all analytics-prod costs across all months
for file in monthly/costs_*.csv; do
  grep "analytics-prod" "$file" >> analytics_prod_all_months.csv
done
```

### **Archive Monthly Files**

```bash
# Compress for storage/sharing
tar -czf monthly_costs.tar.gz monthly/

# Extract later
tar -xzf monthly_costs.tar.gz
```

### **Import to Excel**

```bash
# Combine all monthly files into one Excel workbook
python3 << 'EOF'
import pandas as pd
import glob

# Read all monthly files
files = sorted(glob.glob('monthly/costs_*.csv'))
dfs = [pd.read_csv(f) for f in files]

# Write to Excel (one sheet per month)
with pd.ExcelWriter('monthly_costs.xlsx', engine='openpyxl') as writer:
    for i, file in enumerate(files):
        df = dfs[i]
        month = file.split('_')[1] + '_' + file.split('_')[2].split('.')[0]
        df.to_excel(writer, sheet_name=month, index=False)

print("✓ Created monthly_costs.xlsx")
EOF
```

---

## 📊 Example Output

When you run `python3 split_costs_by_month.py`:

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
  ✓ costs_2025_03.csv            6 rows  $   42,200.00
  ✓ costs_2025_04.csv            6 rows  $   44,100.00
  ✓ costs_2025_05.csv            6 rows  $   43,800.00
  ✓ costs_2025_06.csv            6 rows  $   44,500.00
  ✓ costs_2025_07.csv            6 rows  $   42,100.00
  ✓ costs_2025_08.csv            6 rows  $   41,800.00
  ✓ costs_2025_09.csv            6 rows  $   43,200.00
  ✓ costs_2025_10.csv            6 rows  $   44,800.00
  ✓ costs_2025_11.csv            6 rows  $   46,100.00
  ✓ costs_2025_12.csv            6 rows  $   47,300.00
  ✓ costs_2026_01.csv            6 rows  $   48,000.00
  ✓ costs_2026_02.csv            6 rows  $   46,200.00

======================================================================
 SUMMARY
======================================================================

Files created: 14
Total cost (all months): $1,052,400.00

Monthly breakdown:
  2025-01: $   41,000.00
  2025-02: $   41,500.00
  2025-03: $   42,200.00
  ...
  2026-02: $   46,200.00

Files saved to: ./monthly/
```

---

## 🔧 Standalone Usage

### **Split Existing File**

If you have a combined CSV already:

```bash
# Default: uses costs_raw.csv, outputs to ./monthly/
python3 split_costs_by_month.py

# Custom input/output
python3 split_costs_by_month.py \
  --input my_data.csv \
  --output-dir ./my_monthly_files
```

### **Options**

```bash
python3 split_costs_by_month.py --help
```

Output:
```
usage: split_costs_by_month.py [-h] [--input INPUT] [--output-dir OUTPUT_DIR]

Split combined costs CSV into monthly files

optional arguments:
  -h, --help              Show this help message and exit
  --input INPUT           Input CSV file (default: costs_raw.csv)
  --output-dir OUTPUT_DIR Output directory for monthly files (default: .)
```

---

## 📋 Complete Workflows

### **Workflow 1: Full Automation (Recommended)**

```bash
# One command does everything
bash run_full_workflow.sh real
```

**Steps:**
1. Fetch from Cloudability
2. Split into monthly files
3. Run chargeback analysis

**Output:**
- Combined + monthly files
- Chargeback analysis (4 CSV files)

---

### **Workflow 2: Fetch Only, Then Split**

```bash
# Step 1: Fetch
bash run_chargeback.sh real csv

# Step 2: Split (optional)
python3 split_costs_by_month.py

# Step 3: Analyze (optional)
python3 chargeback_analysis.py
```

---

### **Workflow 3: Sample Data Testing**

```bash
# Generate + split + analyze
bash run_full_workflow.sh sample
```

---

## ✅ Why Monthly Files?

| Benefit | Use Case |
|---------|----------|
| **Easy review** | Check a specific month's costs |
| **Archival** | Keep one file per month for records |
| **Sharing** | Send individual months to teams |
| **Comparison** | Diff between two months |
| **Manual checks** | Excel, pivot tables, manual analysis |
| **Smaller files** | ~16 rows per month vs 224 rows total |

---

## 🎯 Common Tasks

### **Find all files for a date range**

```bash
# Files from Q2 2025
ls monthly/costs_2025_{04,05,06}.csv
```

### **Calculate monthly average**

```bash
# Average cost across all months
awk -F, 'NR>1 {sum+=$NF; count++} END {print "Avg:", sum/count}' monthly/costs_*.csv
```

### **Find highest cost month**

```bash
for file in monthly/costs_*.csv; do
  total=$(awk -F, 'NR>1 {sum+=$NF} END {printf "%.2f", sum}' "$file")
  echo "$(basename $file): $total"
done | sort -t: -k2 -rn | head -1
```

### **Export to Google Sheets**

```bash
# Convert to CSV with headers combined
python3 << 'EOF'
import pandas as pd
import glob

files = sorted(glob.glob('monthly/costs_*.csv'))
for file in files:
    print(f"\n=== {file} ===")
    df = pd.read_csv(file)
    print(df.to_csv(index=False))
EOF
```

---

## 📞 Troubleshooting

### "monthly/ directory not created"

```bash
# Create it manually
mkdir -p monthly

# Then split
python3 split_costs_by_month.py
```

### "Only 1 file created instead of 14"

Check that your `costs_raw.csv` has data for all months:

```bash
cut -d, -f1 costs_raw.csv | sort | uniq
# Should show: Month, 2025-01, 2025-02, ..., 2026-02
```

### "Different costs in monthly vs combined"

They should be identical - monthly files are just split versions. If different:

```bash
# Sum all monthly files
awk -F, 'NR>1 {sum+=$NF}' monthly/costs_*.csv END {print sum}

# Compare to combined
awk -F, 'NR>1 {sum+=$NF}' costs_raw.csv END {print sum}
```

Should be the same value.

---

## 📚 Related Documentation

- `CHARGEBACK_QUICKSTART.md` — Getting started
- `CALCULATIONS_EXPLAINED.md` — How calculations work
- `CSV_FORMAT_USAGE.md` — CSV format options
- `README_CHARGEBACK.md` — Overview

---

## 🚀 Recommended Approach

1. **Run full workflow** to get everything at once:
   ```bash
   bash run_full_workflow.sh real
   ```

2. **Use combined file** (`costs_raw.csv`) for analysis

3. **Use monthly files** for:
   - Archival and record-keeping
   - Manual spot-checking
   - Sharing with specific users
   - Monthly reports

This gives you **both**: fast analysis + organized monthly files!

