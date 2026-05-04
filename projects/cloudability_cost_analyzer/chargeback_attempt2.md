# EKS Chargeback & Cost Redistribution Guide

This document provides a comprehensive framework for reconciling AWS Cloudability billing data with Kubernetes namespace
resource consumption. By following these steps, organizations can achieve 100% cost recovery while ensuring platform
overhead is shared fairly across all tenants.

---

## 1. The Core Difference: Who Pays for the "Empty Space"?

Think of a Kubernetes cluster like a **Pizza Party**:

* **Allocation**: You pay only for the exact slices of pizza you ate.
* **FairShare**: You pay for the slices you ate **PLUS** your share of the leftover slices that nobody touched.

### **Costs: Allocation (The "Order")**

This represents the cost of the CPU and Memory that your pods specifically requested.

* **The Problem**: If your cluster is only 60% utilized, and you only charge back based on "Allocation," you will only
  recover 60% of your AWS bill. You’ll be left with a 40% "funding gap" that the platform team has to pay for out of
  pocket.

### **Costs: FairShare (The "Bill")**

Cloudability calculates this by taking your **Allocation** and adding a proportional slice of the **Idle/Unallocated**
capacity.

* **The Benefit**: It ensures **Full Cost Recovery**. The sum of all `fairShare` costs across all namespaces will (
  ideally) equal 100% of the actual cluster cost.

---

## 2. The Foundation: Why We Use "FairShare"

The primary challenge in Kubernetes chargeback is the "Idle Capacity" (Unallocated cost).

| Metric                | What it Measures                                                      | Financial Impact                                                                                              |
|:----------------------|:----------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------|
| **Costs: Allocation** | Cost of CPU/Memory specifically requested or reserved by a pod.       | **Under-billing.** You only pay for what you "ordered," leaving the platform team to pay for the empty space. |
| **Costs: FairShare**  | **Allocation + A proportional slice of the cluster's Idle capacity.** | **Full Recovery.** Ensures every dollar on the AWS bill is assigned to a namespace.                           |
| **Cost: Unallocated** | The dollar value of wasted/idle resources across the entire cluster.  | **Visibility.** Represents potential savings if the cluster were right-sized.                                 |

### Strategic Benefits of FairShare

* **Zero-Net Budgeting:** The sum of all FairShare costs matches the `total_amortized_cost` in your `service.csv`.
* **Waste Accountability:** If a team requests a huge node but uses very little, their FairShare increases,
  incentivizing them to optimize.

---

## 3. Handling Platform Namespaces

Namespaces such as `kube-system`, `istio-system`, and `monitoring` are essential for the cluster but do not belong to a
specific business unit. We handle these using **Redistribution Logic**:

1. **Step 1:** Assign costs to ALL namespaces (including platform ones) using their FairShare weight.
2. **Step 3:** Sum all costs assigned to platform namespaces to create a **"Platform Cost Pool."**
3. **Step 4:** Calculate the relative weight of each **"User Namespace"** (excluding platform ones).
4. **Step 5:** Distribute the Platform Cost Pool back to users based on their weight.

---

## 4. Python Implementation

The following Python logic processes `service.csv` against your cluster files (`bronze.csv`, `uar.csv`, etc.).


```python
import pandas as pd

def process_eks_chargeback(bill_path, k8s_path, platform_namespaces):
    # 1. Load Data
    bill_df = pd.read_csv(bill_path)
    usage_df = pd.read_csv(k8s_path)
    
    # Total Dollars to recover (matches Cloudability exactly)
    total_aws_cost = bill_df['total_amortized_cost'].sum()
    
    # 2. Initial Proportional Allocation
    total_fairshare_metric = usage_df['costs: fairShare'].sum()
    usage_df['initial_dollars'] = (usage_df['costs: fairShare'] / total_fairshare_metric) * total_aws_cost
    
    # 3. Segregate Platform vs User
    is_platform = usage_df['namespace'].isin(platform_namespaces)
    platform_total = usage_df[is_platform]['initial_dollars'].sum()
    user_namespaces = usage_df[~is_platform].copy()
    
    # 4. Redistribute Platform Tax
    # weight = (user_fairshare) / (total_user_fairshare)
    total_user_usage = user_namespaces['costs: fairShare'].sum()
    user_namespaces['platform_tax'] = (user_namespaces['costs: fairShare'] / total_user_usage) * platform_total
    
    # Final Result
    user_namespaces['total_billable_amount'] = user_namespaces['initial_dollars'] + user_namespaces['platform_tax']
    
    return user_namespaces[['namespace', 'initial_dollars', 'platform_tax', 'total_billable_amount']]

# Configuration
platform_list = ['kube-system', 'monitoring', 'logging', 'shared-services']

# Example Run
# bronze_report = process_eks_chargeback('service.csv', 'bronze.csv', platform_list)
```


