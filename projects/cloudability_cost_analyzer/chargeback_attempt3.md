The current URL you're using is too broad because it only groups by `service_name`. To see the difference between **EKS
nodes**, **EBS volumes**, **RDS instances**, and **License fees**, you need to add dimensions like `usage_type`,
`item_description`, and potentially `tag` keys.

### 1. The Updated Cloudability API URL

I have cleaned up the syntax and added specific dimensions that will give you the "resource-level" detail you need to
reconcile your bill.

**Recommended Dimensions:**

* `service_name`: General AWS Service (e.g., Amazon EC2).
* `usage_type`: Specific resource type (e.g., `us-east-1-gp3` for EBS).
* `item_description`: The human-readable bill line (e.g., "$0.10 per GB-month of provisioned storage").
* `tag:Name`: Useful for identifying specific RDS instances or EKS node groups.
* `transaction_type`: Essential for catching **License Fees**, **Refunds**, and **Marketplace** charges.

**The URL Structure:**

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=${START_DATE}&end_date=${END_DATE}&dimensions=service_name,usage_family,usage_type,item_description,transaction_type&metrics=total_amortized_cost&sort=total_amortized_cost:desc
```

---

### 2. Python Script for Detailed Breakdown

This script is designed to be a "Discovery Tool." You can pass in your dates and toggle different dimension sets to see
which one provides the clearest mapping to your `service.csv`.

```python
import requests
import json
import pandas as pd
from datetime import datetime


class CloudabilityExplorer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.cloudability.com/v3/reporting/cost/run"
        # Standard auth for Cloudability is Basic Auth (API Key as username, password empty)
        self.auth = (self.api_key, "")

    def get_detailed_costs(self, start_date, end_date, detail_level="standard"):
        """
        detail_level options:
        'standard': Service and usage family
        'granular': Service, usage type, and description (Best for RDS vs EBS vs EKS)
        'license_hunt': Focuses on transaction types and marketplace fees
        """

        # Mapping detail levels to Cloudability dimensions
        dimension_map = {
            "standard": "service_name,usage_family",
            "granular": "service_name,usage_family,usage_type,item_description",
            "license_hunt": "service_name,transaction_type,item_description,vendor_account_name"
        }

        params = {
            "start_date": start_date,  # Expected format: YYYY-MM-DD
            "end_date": end_date,
            "dimensions": dimension_map.get(detail_level, dimension_map["standard"]),
            "metrics": "total_amortized_cost",
            "sort": "total_amortized_cost:desc"
        }

        print(f"🚀 Fetching {detail_level} data from {start_date} to {end_date}...")

        response = requests.get(self.base_url, auth=self.auth, params=params)

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(response.text)
            return None

        data = response.json()

        # Convert API response to a clean DataFrame
        results = data.get('results', [])
        if not results:
            print("⚠️ No data returned for these dates.")
            return pd.DataFrame()

        df = pd.DataFrame(results)

        # Ensure costs are floats for math
        df['total_amortized_cost'] = df['total_amortized_cost'].astype(float)

        return df


# --- Configuration & Execution ---
# Replace with your actual Cloudability API Key
API_KEY = "YOUR_API_KEY_HERE"

explorer = CloudabilityExplorer(API_KEY)

# Pass dates in YYYY-MM-DD (Cloudability standard)
# You can convert your 20260101 input easily if needed
start = "2026-01-01"
end = "2026-01-31"

# Try the 'granular' option to see EKS vs RDS vs S3 detail
df_detailed = explorer.get_detailed_costs(start, end, detail_level="granular")

if df_detailed is not None:
    print("\n--- Cost Breakdown Summary ---")
    print(df_detailed.head(20))

    # Example: How to find License fees specifically
    license_df = explorer.get_detailed_costs(start, end, detail_level="license_hunt")
    print("\n--- Potential License/Marketplace Fees ---")
    print(license_df[license_df['transaction_type'] != 'Usage'].head(10))
```

---

### 3. How to Interpret the Results

When you run this with the **`granular`** detail level, you will be able to distinguish the following in the
`usage_type` or `item_description` columns:

#### **A. The EKS Cluster (The "Nodes")**

* **Look for:** `service_name == "Amazon Elastic Compute Cloud"`
* **Usage Type:** Look for types containing your instance sizes (e.g., `t3.medium`) or `BoxUsage`.
* **Validation:** These are the costs that should be reconciled against your `bronze.csv`.

#### **B. Storage (EBS vs S3)**

* **EBS:** Will appear under `service_name: Amazon Elastic Compute Cloud` but the `usage_family` will be `Storage` or
  `Provisioned IOPS`.
* **S3:** Will appear under `service_name: Amazon Simple Storage Service`.

#### **C. License Fees & Marketplace**

* **Look for:** `transaction_type == "Tax"` or `"Fee"`.
* **Usage Family:** Often listed as `Support` or `Subscription`.
* **Marketplace:** Cloudability has a specific dimension `vendor_account_name` that helps identify if you are paying a
  3rd party (like Datadog or MongoDB) through your AWS bill.

### 4. Why your total might have been "incorrect"

If you were only using `service_name`, Cloudability was likely aggregating **Refunds**, **Credits**, and **Reserved
Instance (RI) Adjustments** into the flat service total. By adding `transaction_type` as a dimension, you can see
these "non-usage" costs separately, which explains why the raw "Usage" math didn't match the final "Bill" math.

**Pro-Tip:** If you want to match your `service.csv` exactly, make sure your API call includes **Amortized** metrics.
Cloudability's "Total Amortized Cost" includes the daily portion of any upfront RI or Savings Plan payments, which is
usually how Finance teams prefer to see the data.