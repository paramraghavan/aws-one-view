# CSV Format Support - Quick Reference

Cloudability API now supports direct CSV export via the `Accept: text/csv` header. This eliminates the JSON → CSV conversion step.

---

## ⚡ Quick Start

### **Option 1: Direct CSV (RECOMMENDED - Faster)**

```bash
export CLOUDABILITY_API_KEY="your-api-key"
export CLOUDABILITY_CLUSTER_ID="your-cluster-id"

# Fetch directly as CSV (no conversion needed)
bash run_chargeback.sh real csv

# Or manually:
bash fetch_cloudability_data.sh csv
```

**Advantages:**
- ✅ Faster (skips JSON conversion)
- ✅ Simpler pipeline
- ✅ One less dependency (no jq needed)

---

### **Option 2: JSON then Convert (Legacy)**

```bash
# Fetch as JSON, convert to CSV
bash run_chargeback.sh real json

# Or manually:
bash fetch_cloudability_data.sh json
```

**When to use:**
- Need raw JSON for other purposes
- Want to verify API response structure

---

## 📊 Comparison

| Aspect | CSV Direct | JSON → CSV |
|--------|-----------|-----------|
| **Speed** | ✅ Faster (1 step) | Slower (2 steps) |
| **Dependencies** | Just curl | curl + jq |
| **File size** | Smaller | Larger (JSON) |
| **Output** | CSV ready | CSV ready |
| **API call** | `Accept: text/csv` | `Accept: application/json` |

---

## 🔧 Usage Examples

### **Run with CSV format (default)**
```bash
bash run_chargeback.sh real csv
bash run_chargeback.sh real      # Defaults to csv
```

### **Run with JSON format**
```bash
bash run_chargeback.sh real json
```

### **Fetch only (no analysis)**
```bash
# CSV direct
bash fetch_cloudability_data.sh csv

# JSON then convert
bash fetch_cloudability_data.sh json
```

---

## 📝 What Each Option Produces

### **CSV Direct Output**
```bash
bash fetch_cloudability_data.sh csv
# Output: costs_raw.csv (direct from API)
```

```csv
Month,Namespace,Service,FairshareValue
2025-01,analytics-prod,pod,18750.75
2025-01,data-science-team-1,pod,12500.50
2025-01,kube-system,pod,2100.00
```

### **JSON then Convert**
```bash
bash fetch_cloudability_data.sh json
# Outputs:
#   - raw_data.json (intermediate)
#   - costs_raw.csv (final)
```

Same CSV output, but creates intermediate JSON file.

---

## 🔍 Console Output Comparison

### CSV Format (Direct)
```
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
```

### JSON Format (Convert)
```
[2/3] Fetching data from Cloudability API...
      Endpoint: https://api.cloudability.com/v1/costs
      Accept: application/json
      ✓ JSON data fetched successfully

[3/3] Converting JSON to CSV...
      ✓ CSV created: costs_raw.csv

========================================================================
 SUMMARY
========================================================================
  Data format: json
  Rows: 225 (including header)
  Total Fairshare Cost: $1,052,400.00
```

---

## 🛠️ How It Works

### **CSV Direct (New)**

```
Cloudability API
     ↓
curl with "Accept: text/csv"
     ↓
costs_raw.csv (direct)
     ↓
python3 chargeback_analysis.py
```

### **JSON then Convert (Legacy)**

```
Cloudability API
     ↓
curl with "Accept: application/json"
     ↓
raw_data.json
     ↓
jq extraction
     ↓
costs_raw.csv
     ↓
python3 chargeback_analysis.py
```

---

## ✅ Which Format Should I Use?

**Use CSV Direct (default) unless you have a specific reason not to:**

```bash
# ✓ RECOMMENDED
bash run_chargeback.sh real csv
```

**Use JSON if you need to:**
- Debug API responses
- Keep raw JSON for archival
- Have other processes that use JSON

```bash
# Alternative (less common)
bash run_chargeback.sh real json
```

---

## 🚀 Performance

### CSV Direct
```
API call: ~500ms
CSV fetch: ~500ms
Total: ~1 second
```

### JSON then Convert
```
API call: ~500ms
JSON fetch: ~500ms
jq conversion: ~200ms
Total: ~1.2 seconds
```

**Difference:** ~200ms faster with CSV direct. Small but cleaner.

---

## 📋 Backwards Compatibility

Both options produce identical output:
- Same `costs_raw.csv` file
- Same format and structure
- Same analysis results

You can switch between them anytime without affecting the analysis.

---

## 🐛 Troubleshooting

### "Invalid format 'csv'"
Make sure you pass the format as second argument:
```bash
bash run_chargeback.sh real csv     # ✓ Correct
bash run_chargeback.sh csv real     # ✗ Wrong order
```

### CSV fetch fails but JSON works
Some edge cases might have issues with CSV format. Fall back to JSON:
```bash
bash run_chargeback.sh real json
```

### Need both JSON and CSV?
```bash
# Get both
bash fetch_cloudability_data.sh json   # Creates raw_data.json
# The script also creates costs_raw.csv
```

---

## 📚 Related Files

- `fetch_cloudability_data.sh` — Main fetch script (supports both formats)
- `run_chargeback.sh` — Wrapper script (passes format parameter)
- `chargeback_analysis.py` — Analysis script (no changes needed)
- `CHARGEBACK_QUICKSTART.md` — General getting started guide

---

## Summary

✨ **Use CSV format by default for faster, simpler data fetching:**

```bash
export CLOUDABILITY_API_KEY="your-key"
export CLOUDABILITY_CLUSTER_ID="your-id"
bash run_chargeback.sh real csv
```

Done! No more JSON conversion overhead.
