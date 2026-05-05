To use a specific AWS tag (like `AI_003`) in Cloudability, you must use the prefix `tag:` followed by the exact key
name. So, your dimension becomes `tag:AI_003`.

Integrating this into the `dimension_map` allows you to see costs broken down by that specific tag across all other
categories.

### 1. Dimension Map Definitions

To choose the right level of detail, it helps to understand how AWS costs are structured in a hierarchy.

* **`service_name`**: The top-level AWS service (e.g., `Amazon Elastic Compute Cloud`, `Amazon Simple Storage Service`).
  Use this to see the "Big Picture" bill.
* **`usage_family`**: The broad category of usage. For EC2, this distinguishes between `Instance Usage` (the compute),
  `Storage` (the disks), and `Data Transfer` (the network).
* **`usage_type`**: The technical API identifier. It often includes the region and the specific resource SKU (e.g.,
  `us-east-1-BoxUsage:t3.medium` or `EBS:VolumeUsage.gp3`).
* **`item_description`**: The long-form text you see on an invoice (e.g., "$0.01 per GB-month of provisioned storage").
  This is the best way to manually verify what a "mystery cost" actually is.
* **`transaction_type`**: Crucial for reconciliation.
    * `Usage`: Standard hourly or quantity-based costs.
    * `Fee`: Upfront payments, Marketplace subscriptions, or Support fees.
    * `Credit`: Discounts or promotional credits.
    * `Refund`: Money returned to the account.
* **`vendor_account_name`**: If you buy software through the AWS Marketplace (e.g., Datadog, Snowflake, or Trend Micro),
  this tells you which company is receiving the money.

---

### 2. Updated Python Script

I have updated the script to include a `custom_tag` parameter. It will now dynamically inject `tag:AI_003` into your
requests.

```python
import requests
import pandas as pd


class CloudabilityExplorer:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.cloudability.com/v3/reporting/cost/run"
        self.auth = (self.api_key, "")

    def get_detailed_costs(self, start_date, end_date, detail_level="standard", tag_key=None):
        """
        tag_key: The exact AWS Tag name (e.g., 'AI_003')
        """

        # 1. Basic Dimension sets
        dimension_map = {
            "standard": "service_name,usage_family",
            "granular": "service_name,usage_family,usage_type,item_description",
            "full_recon": "service_name,usage_family,usage_type,transaction_type,vendor_account_name"
        }

        selected_dimensions = dimension_map.get(detail_level, dimension_map["standard"])

        # 2. Append the Custom Tag if provided
        if tag_key:
            # Cloudability requires the 'tag:' prefix
            selected_dimensions += f",tag:{tag_key}"

        params = {
            "start_date": start_date,
            "end_date": end_date,
            "dimensions": selected_dimensions,
            "metrics": "total_amortized_cost",
            "sort": "total_amortized_cost:desc"
        }

        print(f"🚀 Fetching '{detail_level}' data. Dimensions: {selected_dimensions}")

        response = requests.get(self.base_url, auth=self.auth, params=params)

        if response.status_code != 200:
            print(f"❌ Error {response.status_code}: {response.text}")
            return None

        data = response.json()
        results = data.get('results', [])

        if not results:
            print("⚠️ No data found.")
            return pd.DataFrame()

        df = pd.DataFrame(results)
        df['total_amortized_cost'] = df['total_amortized_cost'].astype(float)

        return df


# --- Execution ---
API_KEY = "YOUR_API_KEY"
explorer = CloudabilityExplorer(API_KEY)

# Tag name from your example
MY_TAG = "AI_003"

# Run a granular report for January 2026 filtered by your Tag
df = explorer.get_detailed_costs(
    start_date="2026-01-01",
    end_date="2026-01-31",
    detail_level="granular",
    tag_key=MY_TAG
)

if df is not None:
    # Print the top rows to see how the tag column appears
    print(df.head(10))

    # Quick check: How much did 'AI_003' spend specifically on EKS?
    eks_only = df[df['service_name'].str.contains('Container Service', na=False)]
    print(f"\n💰 Total EKS Cost for {MY_TAG}: ${eks_only['total_amortized_cost'].sum():.2f}")
```

### Pro-Tips for Tagging:

1. **Case Sensitivity**: Cloudability is strictly case-sensitive. If your tag is `ai_003` in AWS, but you search for
   `AI_003`, it will return zero results.
2. **Untagged Resources**: When you include a tag as a dimension, Cloudability will show `(not set)` for resources that
   are missing that tag. This is a great way to find "leakage" in your chargeback model.
3. **The "Reconciliation" dimension**: If your `service.csv` total is still not matching, run the `full_recon` level.
   Look specifically at `transaction_type`. If you see `Tax` or `Credit` and those rows have `(not set)` for your tag,
   you've found the discrepancy—those are global account costs that aren't tied to your specific AI project.

#  ######################################################################################

# how to pivot this data in Python so you can see a "Tag vs. Service" matrix?

To turn that raw list of data into a clear "Tag vs. Service" matrix, we use the **`pd.pivot_table`** function in Python.

This is incredibly useful because it shows you at a glance:

1. Which services are correctly tagged.
2. Which services are "leaking" money (appearing as `(not set)` or "Untagged").
3. The total "Fully Loaded" cost for your project.

### Python Script: The Tag Matrix Generator

This script builds on the previous one. It fetches the data, cleans up the "(not set)" labels, and generates a pivot
table.

```python
import pandas as pd


def generate_tag_matrix(df, tag_key):
    """
    Transforms raw Cloudability data into a Service vs. Tag matrix.
    """
    # 1. Clean the data
    # Cloudability returns '(not set)' for untagged items. Let's make it 'Untagged'
    tag_col = f"tag:{tag_key}"
    df[tag_col] = df[tag_col].replace('(not set)', 'Untagged')

    # 2. Create the Pivot Table
    # Rows = Service Name
    # Columns = The Values of your Tag (e.g., 'Project_A', 'Project_B', 'Untagged')
    matrix = pd.pivot_table(
        df,
        values='total_amortized_cost',
        index=['service_name'],
        columns=[tag_col],
        aggfunc='sum',
        fill_value=0,  # Replace NaNs with $0
        margins=True,  # Adds a 'Total' row and column
        margins_name='Total Bill'
    )

    # 3. Sort by the highest cost service
    matrix = matrix.sort_values(by='Total Bill', ascending=False)

    return matrix


# --- Execution ---
# Assuming 'df' is the dataframe from explorer.get_detailed_costs()
MY_TAG = "AI_003"

if not df.empty:
    matrix_report = generate_tag_matrix(df, MY_TAG)

    print(f"\n--- Cost Matrix for Tag: {MY_TAG} ---")
    print(matrix_report)

    # Save to CSV for Excel consumption
    matrix_report.to_csv(f"matrix_report_{MY_TAG}.csv")
```

---

### How to read this matrix

When you open the resulting CSV or look at the printout, you will see a structure like this:

| service_name    | AI_003_Project | Untagged | Total Bill |
|:----------------|:---------------|:---------|:-----------|
| **Amazon EC2**  | $5,000         | $200     | $5,200     |
| **Amazon RDS**  | $1,200         | $0       | $1,200     |
| **AWS Support** | $0             | $500     | $500       |
| **Total Bill**  | **$6,200**     | **$700** | **$6,900** |

#### **What this tells you for your Chargeback:**

1. **Direct Charge:** You can bill the "AI_003" project **$6,200** with high confidence because those resources are
   tagged.
2. **Shared Overhead:** The **$700** in "Untagged" costs (like AWS Support fees) usually can't be tagged to a specific
   project.
    * *Action:* You should take this $700 and redistribute it across your projects using the **Platform Tax** logic we
      discussed for your Kubernetes namespaces.
3. **Tagging Compliance:** If you see **$200** in Untagged EC2, someone forgot to tag a node group. You should find
   those instances and fix the tags in AWS to make next month's bill more accurate.


