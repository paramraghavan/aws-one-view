This updated script will walk through your `monthly/` directory, find each `mm-yyyy` subfolder, and process the files
inside.

Since you have multiple allocation files (`bronze.csv`, `uat.csv`, `dev.csv`) for a single `service.csv`, the script
first merges the allocation files to get the "total cluster footprint" before applying the FairShare logic.

### Updated Python Script: Multi-Month Chargeback

```python
import pandas as pd
import os
from pathlib import Path


def generate_monthly_chargebacks(base_folder, platform_namespaces):
    all_monthly_results = []

    # 1. Iterate through each month folder (e.g., monthly/05-2026)
    monthly_path = Path(base_folder)

    for month_dir in monthly_path.iterdir():
        if month_dir.is_dir():
            month_name = month_dir.name
            print(f"--- Processing Month: {month_name} ---")

            # Define file paths for this specific month
            service_file = month_dir / 'service.csv'
            allocation_files = ['bronze.csv', 'uat.csv', 'dev.csv']

            # Check if service.csv exists
            if not service_file.exists():
                print(f"Skipping {month_name}: service.csv not found.")
                continue

            # 2. Load the AWS Bill for the month
            bill_df = pd.read_csv(service_file)
            total_aws_cost = bill_df['total_amortized_cost'].sum()

            # 3. Combine all Allocation Files (bronze, uat, dev)
            allocation_dfs = []
            for f in allocation_files:
                f_path = month_dir / f
                if f_path.exists():
                    temp_df = pd.read_csv(f_path)
                    temp_df['source_file'] = f  # Keep track of which cluster it came from
                    allocation_dfs.append(temp_df)

            if not allocation_dfs:
                print(f"Skipping {month_name}: No allocation files found.")
                continue

            # Merge all namespaces into one master list for the month
            combined_usage = pd.concat(allocation_dfs, ignore_index=True)

            # Group by namespace (in case the same namespace exists in multiple files)
            usage_grouped = combined_usage.groupby('namespace')['costs: fairShare'].sum().reset_index()

            # 4. Calculate Initial Allocation
            total_fairshare_metric = usage_grouped['costs: fairShare'].sum()
            usage_grouped['initial_cost'] = (usage_grouped[
                                                 'costs: fairShare'] / total_fairshare_metric) * total_aws_cost

            # 5. Segregate Platform vs User and Redistribute
            is_platform = usage_grouped['namespace'].isin(platform_namespaces)
            platform_cost_pool = usage_grouped[is_platform]['initial_cost'].sum()

            user_df = usage_grouped[~is_platform].copy()
            total_user_fairshare = user_df['costs: fairShare'].sum()

            # Calculate final chargeback: (User Initial Cost) + (Proportional Share of Platform Pool)
            user_df['platform_tax'] = (user_df['costs: fairShare'] / total_user_fairshare) * platform_cost_pool
            user_df['final_chargeback'] = user_df['initial_cost'] + user_df['platform_tax']

            # Add metadata and store results
            user_df['billing_month'] = month_name
            all_monthly_results.append(user_df)

            # Save individual monthly report
            user_df.to_csv(month_dir / f'chargeback_result_{month_name}.csv', index=False)
            print(f"Completed {month_name}. Total recovered: ${user_df['final_chargeback'].sum():.2f}")

    # 6. Create one master file for all months
    if all_monthly_results:
        master_df = pd.concat(all_monthly_results, ignore_index=True)
        master_df.to_csv('master_chargeback_report.csv', index=False)
        print("\n--- Process Complete ---")
        print("Master report saved as: master_chargeback_report.csv")


# --- Configuration ---
# Update this list with your platform-specific namespaces
platform_list = [
    'kube-system',
    'monitoring',
    'logging',
    'cloudability',
    'shared-services',
    'istio-system'
]

# Run the script
generate_monthly_chargebacks(base_folder='monthly', platform_namespaces=platform_list)
```

---

### How this works for your structure:

1. **Multi-File Aggregation**: Since you have `bronze`, `uat`, and `dev` in the same folder, the script treats them as a
   single fleet. It sums the total `fairShare` across all three files to ensure the "Proportional Tax" is calculated
   against the entire monthly footprint.
2. **The Redistribution**: It calculates the "Platform Tax" once per month. If `kube-system` exists in all three files,
   it totals them up and spreads that cost only to the non-platform namespaces.
3. **Grouping**: By using `.groupby('namespace')`, the script handles cases where a namespace (like `logging`) might
   appear in multiple CSVs. It merges them into a single line item before billing.
4. **Outputs**:
    * **Monthly Report**: A CSV inside each `mm-yyyy` folder for localized auditing.
    * **Master Report**: A single CSV in your root folder containing all months, perfect for importing into a BI tool or
      Excel.

### A Note on the "Pizza" logic here:

In this folder structure, the "Pizza" is the **total `service.csv` cost** for that month. The "Slices" are distributed
across the `bronze`, `uat`, and `dev` files. By combining them, we ensure that if someone "ordered" a slice in UAT and
another slice in PROD, they are billed for their total consumption across the whole platform for that month.

