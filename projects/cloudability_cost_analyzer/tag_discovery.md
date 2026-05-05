Since the Cloudability Reporting API is **dimension-based**, it requires you to explicitly ask for specific columns. It
does not have a single "All Tags" dimension that returns every tag for a resource in a single cell.

If you only specify `tag:AI_003`, the API will simply ignore every other tag on that resource. To avoid missing tags,
you should use a **"Discovery" pattern**.

### 1. The "Discovery" Pattern

To see all tags, you first call the **Measures API** to find every tag key currently known to Cloudability. You then
programmatically inject those keys into your Cost Report request.

**Step 1: Get all available Tag Keys**
Use the `/v3/reporting/resourceinventory/measures` endpoint. It returns a JSON list of all tag dimensions your account
is currently tracking.

**Step 2: Build the Report Dimensions**
Take that list, prefix each name with `tag:`, and join them into your `dimensions` string.

---

### 2. Updated Python Script with Tag Discovery

This script automatically "discovers" every tag in your environment so you never miss one.

```python
import requests
import pandas as pd


class CloudabilityAutoDiscover:
    def __init__(self, api_key):
        self.api_key = api_key
        self.auth = (self.api_key, "")

    def get_all_tag_keys(self):
        """Fetches every tag key currently available in Cloudability."""
        url = "https://api.cloudability.com/v3/reporting/resourceinventory/measures"
        response = requests.get(url, auth=self.auth)

        if response.status_code != 200:
            return []

        data = response.json()
        # Extract tag names from the 'tags' section of the measures response
        tags = data.get('tags', [])
        return [t['name'] for t in tags]

    def get_comprehensive_report(self, start_date, end_date):
        # 1. Discover every tag in the system
        all_tags = self.get_all_tag_keys()

        # 2. Build the dimensions string (limit to top tags if list is huge)
        # Cloudability has a dimension limit (usually 50), so we take the first 45 
        # to leave room for service_name and usage_family.
        tag_dimensions = [f"tag:{t}" for t in all_tags[:45]]

        dimensions = ["service_name", "usage_family"] + tag_dimensions
        dim_string = ",".join(dimensions)

        # 3. Run the report
        url = "https://api.cloudability.com/v3/reporting/cost/run"
        params = {
            "start_date": start_date,
            "end_date": end_date,
            "dimensions": dim_string,
            "metrics": "total_amortized_cost"
        }

        print(f"🔍 Discovered {len(all_tags)} tags. Requesting report with {len(dimensions)} dimensions...")
        response = requests.get(url, auth=self.auth, params=params)

        if response.status_code == 200:
            df = pd.DataFrame(response.json().get('results', []))
            # Clean up (not set) labels
            return df.replace('(not set)', 'Untagged')
        return None


# --- Execution ---
discovery = CloudabilityAutoDiscover("YOUR_API_KEY")
full_df = discovery.get_comprehensive_report("2026-01-01", "2026-01-31")
```

---

### 3. Alternative: Using "Tag Explorer" Logic

If you want to see which tags are **most used** without requesting 50 columns, you can use the **Tag Explorer**
philosophy.

In Cloudability, some dimensions are "Synthetic." Check if your organization has set up **Business Mappings**.

* **Business Dimensions:** These are custom "Super Tags" created by your admins. For example, they might map `AI_003`,
  `ProjectID`, and `CostCenter` all into a single Business Dimension called `Project_Owner`.
* **Benefit:** Instead of requesting 20 different vendor tags, you just request
  `dimensions=business_dimension:Project_Owner`. This is the most reliable way to avoid "missing" a tag.

### 4. Summary of what to look for

If you run the discovery script above, your dataframe will have one column for every tag. To find which resources are
missing tags, look for rows where most of the `tag:` columns are labeled **'Untagged'**.

| service_name | tag:AI_003   | tag:Environment | tag:Owner    | Cost |
|:-------------|:-------------|:----------------|:-------------|:-----|
| Amazon EC2   | Project_X    | Prod            | Team_A       | $100 |
| Amazon S3    | **Untagged** | **Untagged**    | **Untagged** | $50  |

**The $50 S3 row represents your "Missing Tag" risk.** By using the discovery script, you ensure that even if you didn't
know the `tag:Owner` key existed, it will still show up in your report.
