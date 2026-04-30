To modernize your chargeback process, we need to transition from the deprecated `/v1/costs` endpoint to the *
*Cloudability v3 Reporting API**.

### 1. Cost Metric: Unblended vs. Fairshare?

For a shared EMR on Kubernetes cluster, you should use **Fairshare Cost** (or Amortized Cost in v3).

* **Unblended Cost:** Does not account for Reserved Instance (RI) or Savings Plan (SP) discounts at the resource
  level—it often shows the "sticker price" or the price at the moment of billing.
* **Fairshare Cost:** This is Cloudability’s calculated metric that distributes your actual enterprise discounts and
  amortized upfront payments down to the namespace level. **Use Fairshare to ensure your chargeback equals your actual
  bill.**

---

### 2. Service Namespaces (Infrastructure)

Based on standard EMR on K8s deployments, these namespaces are likely "Service" or "Platform" overhead rather than
specific modeller workloads:

* **EMR Specific:** `emr-containers`, `spark-operator`.
* **Core Infrastructure:** `kube-system`, `kube-public`, `kube-node-lease`.
* **Platform Services:** `prometheus`, `grafana`, `logging`, `fluent-bit`, `ingress-nginx`, `cert-manager`,
  `external-dns`, `cluster-autoscaler`.

---

### 3. Step 1: The v3 API Fetcher (`fetch_v3_data.sh`)

This script uses the v3 API which uses `dimensions` and `metrics` arrays.

```bash
#!/bin/bash
# fetch_v3_data.sh

set -e

# Configuration
API_KEY="${CLOUDABILITY_API_KEY}"
CLUSTER_ID="${CLOUDABILITY_CLUSTER_ID}"
OUTPUT_FILE="costs_raw.csv"

echo "Pulling Cloudability v3 Data (Jan 2025 - Feb 2026)..."

curl -s -G "https://api.cloudability.com/v3/reporting/cost/run" \
  -u "$API_KEY:" \
  --data-urlencode "start_date=2025-01-01" \
  --data-urlencode "end_date=2026-02-28" \
  --data-urlencode "dimensions=date,category3,category4" \
  --data-urlencode "metrics=adjusted_amortized_cost" \
  --data-urlencode "filters=category1==$CLUSTER_ID" \
  --data-urlencode "format=csv" \
  > "$OUTPUT_FILE"

echo "✓ Data downloaded to $OUTPUT_FILE"
```

*Note: In v3, `category` fields usually map to your mapped Kubernetes tags. I have used `category3` as a placeholder for
Namespace.*

---

### 4. Step 2: The Analysis Engine (`chargeback_v3.py`)

This script processes the data, performs the **Proportional Distribution** of service costs, and calculates the *
*Month-over-Month (MoM) change**.

```python
import pandas as pd
import numpy as np

# Updated Service Namespace List
SERVICE_NAMESPACES = {
    'kube-system', 'emr-containers', 'spark-operator',
    'prometheus', 'logging', 'ingress-nginx', 'cert-manager'
}


def run_analysis(input_csv):
    print("--- STEP 1: LOADING DATA ---")
    df = pd.read_csv(input_csv)
    # Mapping v3 headers to friendly names
    df.columns = ['Month', 'Namespace', 'Service', 'Cost']
    print(f"Total Rows: {len(df)}")
    print(f"Total Cluster Cost: ${df['Cost'].sum():,.2f}")

    print("\n--- STEP 2: CLASSIFYING WORKLOADS ---")
    df['IsService'] = df['Namespace'].apply(lambda x: x in SERVICE_NAMESPACES)

    user_df = df[~df['IsService']].copy()
    service_df = df[df['IsService']].copy()

    print(f"User Workload Cost: ${user_df['Cost'].sum():,.2f}")
    print(f"Platform Service Cost: ${service_df['Cost'].sum():,.2f}")

    print("\n--- STEP 3: PROPORTIONAL SERVICE DISTRIBUTION ---")
    # 1. Total service cost per month
    monthly_service = service_df.groupby('Month')['Cost'].sum().rename('MonthlyServicePool')

    # 2. Total user cost per month (for weighting)
    monthly_user_total = user_df.groupby('Month')['Cost'].sum().rename('MonthlyUserTotal')

    # 3. Join and calculate weighted share
    chargeback = user_df.groupby(['Month', 'Namespace'])['Cost'].sum().reset_index()
    chargeback = chargeback.merge(monthly_service, on='Month')
    chargeback = chargeback.merge(monthly_user_total, on='Month')

    # Weight = (User's Direct Cost / Total User Cost that month)
    chargeback['ServiceShare'] = (chargeback['Cost'] / chargeback['MonthlyUserTotal']) * chargeback[
        'MonthlyServicePool']
    chargeback['FinalTotal'] = chargeback['Cost'] + chargeback['ServiceShare']

    print("\n--- STEP 4: CALCULATING MoM CHANGE ---")
    chargeback = chargeback.sort_values(['Namespace', 'Month'])
    # Change calculation
    chargeback['PrevMonthCost'] = chargeback.groupby('Namespace')['FinalTotal'].shift(1)
    chargeback['DollarChange'] = chargeback['FinalTotal'] - chargeback['PrevMonthCost']
    chargeback['PercentChange'] = (chargeback['DollarChange'] / chargeback['PrevMonthCost']) * 100

    print("\n--- STEP 5: VALIDATION ---")
    calculated_total = chargeback['FinalTotal'].sum()
    original_total = df['Cost'].sum()
    print(f"Calculated Chargeback: ${calculated_total:,.2f}")
    print(f"Original Cloudability: ${original_total:,.2f}")
    print(f"Difference: ${calculated_total - original_total:,.4f} (Should be ~0)")

    return chargeback


if __name__ == "__main__":
    results = run_analysis('costs_raw.csv')
    results.to_csv('final_chargeback_report.csv', index=False)
    print("\n✓ Report generated: final_chargeback_report.csv")
```

### 5. Logic Explained

1. **Proportional Distribution:** We calculate a "Service Pool" for each month (e.g., in January, `kube-system` cost
   \$1,000). We then look at the Modellers. If "User A" was responsible for 20% of the *modeller* activity in January,
   they are automatically billed for 20% of that \$1,000 Service Pool. This ensures the platform cost is shared based on
   usage intensity.
2. **MoM Calculation:**
   The code uses `.shift(1)` to compare the current row's cost to the previous month's cost for that specific user.
3. **Validation:** The script sums the `FinalTotal` (Direct + Allocated) and compares it to the raw CSV total. If they
   match, your chargeback is audit-ready and mathematically sound.

### 6. How to Run

1. **Set Environment Variables:**
   `export CLOUDABILITY_API_KEY='your_key_here'`
   `export CLOUDABILITY_CLUSTER_ID='your_cluster_id_here'`
2. **Fetch:** `bash fetch_v3_data.sh`
3. **Process:** `python3 chargeback_v3.py`

## Explain --data-urlencode "dimensions=date,category3,category4"

The parameter `--data-urlencode "dimensions=date,category3,category4"` is a key part of the Cloudability v3 Reporting
API request. It defines the **granularity** and **grouping** of your cost data.

In the context of your EMR on Kubernetes chargeback project, here is a breakdown of what each dimension represents:

### 1. `date`

This tells Cloudability to group the costs by time.

* Since your goal is to create a report from **Jan 2025 through Feb 2026**, the API uses this dimension to bucket the
  costs into specific time intervals (usually monthly, based on your `start_date` and `end_date` parameters).
* This is the column you will use in your Python logic to calculate **Month-over-Month (MoM)** changes.

### 2. `category3` (Namespace/User)

In Cloudability, "Categories" are custom dimensions mapped by your organization to organize raw cloud provider tags.

* **The User/Namespace Map:** In your specific setup, `category3` is likely mapped to the **Kubernetes Namespace**.
* Because your namespaces often match your modellers, this dimension becomes your **"User"** column.
* This allows you to separate "Direct Costs" (individual modellers) from "Service Costs" (infrastructure namespaces like
  `kube-system`).

### 3. `category4` (Service/Workload)

This provides a second level of grouping to help you understand *what* was running within those namespaces.

* It typically refers to the specific **Service** or workload type (e.g., Spark, Presto, or core system services).
* In your analysis script, this helps you verify if a cost spike for a user was due to a specific EMR service rather
  than just general compute usage.

---

### Why use `urlencode`?

Using `--data-urlencode` (instead of just `-d`) ensures that special characters—like commas or spaces in your dimension
names—are converted into a format that a web server can safely read. For example, it converts the string into
`dimensions=date%2Ccategory3%2Ccategory4`.

### Impact on your CSV

When you run your `curl` command with these dimensions, your resulting `costs_raw.csv` will have a row for every unique
combination of **Date + Namespace + Service**. Your Python script then aggregates these rows to ensure that all
individual entries add up to the **Cloudability monthly total** for your `cluster_id`.