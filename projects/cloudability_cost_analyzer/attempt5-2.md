Yes. Since your **service-cost report already includes the Kubernetes cluster/namespace-backed costs**, the goal should
be:

1. Pull **AWS service cost** with enough dimensions to expose cluster/namespace where available.
2. Split rows into:

    * `K8s / Cluster Namespace Cost`
    * `Other AWS Cost`
3. Avoid adding container API cost on top of service cost unless you are using it only for drill-down, because that can
   double-count.

Cloudability v3 cost reports support flexible dimensions/metrics and allow up to **15 dimensions** and **8 metrics** per
API call. The container allocation feature exposes costs by Kubernetes cluster, namespace, services, labels, and related
container views. ([IBM][1])

---

## Corrected service-cost URL

Your current URL has spacing and duplicate-dimension issues. Use this format:

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=service_name,usage_family,container_cluster_name,container_namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

### If `container_namespace` does not work, try this version

Some Cloudability tenants use slightly different container dimension names. Try:

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=service_name,usage_family,container_cluster_name,namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

### Better AWS-service version

I recommend using `enhanced_service_name` instead of only `service_name` because it is usually cleaner for AWS service
grouping:

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=enhanced_service_name,usage_family,container_cluster_name,container_namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

---

## What the response will show

You should now get rows like:

```text
enhanced_service_name | usage_family | container_cluster_name | container_namespace | total_amortized_cost
AWS EC2               | Compute      | prod-eks-cluster       | app-namespace        | 12345.67
AWS EBS               | Storage      | prod-eks-cluster       | app-namespace        | 2345.89
AWS S3                | Storage      |                        |                      | 5678.12
AWS RDS               | Database     |                        |                      | 9999.99
```

Then you classify:

```text
If container_cluster_name or container_namespace is populated:
    Cluster + Namespace Cost

Else:
    Other AWS Cost
```

This way, **EC2/EBS costs that are part of Kubernetes are separated from non-Kubernetes EC2/EBS/S3/RDS/etc.**

---

## Recommended URLs to test

### 1. Cluster + namespace inside service cost

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=enhanced_service_name,usage_family,container_cluster_name,container_namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

### 2. Cluster + namespace + account

Use this if you have multiple AWS accounts.

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=vendor_account_name,enhanced_service_name,usage_family,container_cluster_name,container_namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

### 3. Cluster + namespace + region

Use this if you need regional detail.

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=region,enhanced_service_name,usage_family,container_cluster_name,container_namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

### 4. Cluster + namespace + usage type

Use this for deep investigation.

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=enhanced_service_name,usage_family,usage_type,container_cluster_name,container_namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

---

## Python code to test and classify costs

```python
import os
import requests
import pandas as pd
from datetime import datetime
from calendar import monthrange

CLOUDABILITY_TOKEN = os.getenv("CLOUDABILITY_TOKEN")

COST_RUN_URL = "https://api.cloudability.com/v3/reporting/cost/run"


def normalize_date(date_value: str) -> str:
    """
    Accepts either 20260101 or 2026-01-01.
    Returns 2026-01-01.
    """
    s = str(date_value).strip()

    if "-" in s:
        return s

    return datetime.strptime(s, "%Y%m%d").strftime("%Y-%m-%d")


def run_cloudability_service_cost(
        start_date: str,
        end_date: str,
        dimensions: list[str],
        metrics: list[str] | None = None,
        filters: list[str] | None = None,
        sort: str = "total_amortized_costDESC",
        limit: int = 0,
) -> pd.DataFrame:
    """
    Runs Cloudability v3 reporting cost API.

    Example dimensions:
      [
        "enhanced_service_name",
        "usage_family",
        "container_cluster_name",
        "container_namespace"
      ]

    Example filters:
      ["vendor==Amazon"]
    """

    if not CLOUDABILITY_TOKEN:
        raise ValueError("Set CLOUDABILITY_TOKEN environment variable first.")

    params = [
        ("start_date", normalize_date(start_date)),
        ("end_date", normalize_date(end_date)),
        ("dimensions", ",".join(dimensions)),
        ("metrics", ",".join(metrics or ["total_amortized_cost"])),
        ("sort", sort),
        ("limit", str(limit)),
    ]

    for f in filters or ["vendor==Amazon"]:
        params.append(("filters", f))

    response = requests.get(
        COST_RUN_URL,
        params=params,
        auth=(CLOUDABILITY_TOKEN, ""),
        timeout=120,
    )

    print("Final URL:")
    print(response.url)

    response.raise_for_status()

    data = response.json()
    rows = data.get("results", [])

    df = pd.DataFrame(rows)

    if "total_amortized_cost" in df.columns:
        df["total_amortized_cost"] = pd.to_numeric(
            df["total_amortized_cost"],
            errors="coerce"
        ).fillna(0)

    return df
```

---

## Test Option 1: service + cluster + namespace

```python
dimensions = [
    "enhanced_service_name",
    "usage_family",
    "container_cluster_name",
    "container_namespace",
]

df = run_cloudability_service_cost(
    start_date="20260101",
    end_date="20260131",
    dimensions=dimensions,
)

print(df.head(50))
```

---

## Classify rows into cluster/namespace vs other AWS

```python
def classify_cluster_vs_other(row):
    cluster = str(row.get("container_cluster_name", "")).strip()
    namespace = str(row.get("container_namespace", "")).strip()

    if cluster and cluster.lower() not in {"nan", "none", "null", ""}:
        return "Cluster + Namespace Cost"

    if namespace and namespace.lower() not in {"nan", "none", "null", ""}:
        return "Cluster + Namespace Cost"

    return "Other AWS Cost"


df["cost_category"] = df.apply(classify_cluster_vs_other, axis=1)

summary = (
    df.groupby("cost_category", dropna=False)["total_amortized_cost"]
    .sum()
    .reset_index()
    .sort_values("total_amortized_cost", ascending=False)
)

print(summary)
```

---

## Get detailed cluster + namespace cost

```python
cluster_namespace_detail = (
    df[df["cost_category"] == "Cluster + Namespace Cost"]
    .groupby(
        [
            "container_cluster_name",
            "container_namespace",
            "enhanced_service_name",
            "usage_family",
        ],
        dropna=False,
    )["total_amortized_cost"]
    .sum()
    .reset_index()
    .sort_values("total_amortized_cost", ascending=False)
)

print(cluster_namespace_detail.head(100))
```

---

## Get other AWS cost: S3, EBS, RDS, license, etc.

```python
def classify_other_aws(row):
    service = str(row.get("enhanced_service_name", "")).lower()
    usage_family = str(row.get("usage_family", "")).lower()

    if "s3" in service or "simple storage service" in service:
        return "S3"

    if "ebs" in service or "elastic block store" in service:
        return "EBS"

    if "rds" in service or "relational database" in service:
        return "RDS"

    if "ec2" in service or "elastic compute cloud" in service:
        return "EC2 - Non Cluster"

    if "support" in service or "support" in usage_family:
        return "Support"

    if "marketplace" in service:
        return "License / Marketplace"

    return "Other AWS"


other_aws = df[df["cost_category"] == "Other AWS Cost"].copy()
other_aws["aws_bucket"] = other_aws.apply(classify_other_aws, axis=1)

other_aws_summary = (
    other_aws.groupby("aws_bucket", dropna=False)["total_amortized_cost"]
    .sum()
    .reset_index()
    .sort_values("total_amortized_cost", ascending=False)
)

print(other_aws_summary)
```

---

## Month-by-month pull

```python
def month_ranges(start_yyyymm: str, end_yyyymm: str):
    start = datetime.strptime(start_yyyymm, "%Y%m")
    end = datetime.strptime(end_yyyymm, "%Y%m")

    current = start

    while current <= end:
        last_day = monthrange(current.year, current.month)[1]

        month_start = f"{current.year:04d}-{current.month:02d}-01"
        month_end = f"{current.year:04d}-{current.month:02d}-{last_day:02d}"

        yield month_start, month_end

        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)


def run_monthly_service_cluster_cost(start_yyyymm: str, end_yyyymm: str):
    all_months = []

    dimensions = [
        "enhanced_service_name",
        "usage_family",
        "container_cluster_name",
        "container_namespace",
    ]

    for start_date, end_date in month_ranges(start_yyyymm, end_yyyymm):
        print(f"Running {start_date} to {end_date}")

        df = run_cloudability_service_cost(
            start_date=start_date,
            end_date=end_date,
            dimensions=dimensions,
        )

        df["month"] = start_date[:7]
        df["cost_category"] = df.apply(classify_cluster_vs_other, axis=1)

        all_months.append(df)

    return pd.concat(all_months, ignore_index=True)


monthly_df = run_monthly_service_cluster_cost("202601", "202603")
print(monthly_df.head())
```

---

## Final monthly summary table

```python
monthly_category_summary = (
    monthly_df
    .groupby(["month", "cost_category"], dropna=False)["total_amortized_cost"]
    .sum()
    .reset_index()
    .sort_values(["month", "total_amortized_cost"], ascending=[True, False])
)

print(monthly_category_summary)
```

---

## Cluster + namespace monthly summary

```python
monthly_cluster_namespace = (
    monthly_df[monthly_df["cost_category"] == "Cluster + Namespace Cost"]
    .groupby(
        [
            "month",
            "container_cluster_name",
            "container_namespace",
        ],
        dropna=False,
    )["total_amortized_cost"]
    .sum()
    .reset_index()
    .sort_values(["month", "total_amortized_cost"], ascending=[True, False])
)

print(monthly_cluster_namespace.head(100))
```

---

## Other AWS monthly summary

```python
monthly_other_aws = monthly_df[
    monthly_df["cost_category"] == "Other AWS Cost"
    ].copy()

monthly_other_aws["aws_bucket"] = monthly_other_aws.apply(
    classify_other_aws,
    axis=1,
)

monthly_other_aws_summary = (
    monthly_other_aws
    .groupby(["month", "aws_bucket"], dropna=False)["total_amortized_cost"]
    .sum()
    .reset_index()
    .sort_values(["month", "total_amortized_cost"], ascending=[True, False])
)

print(monthly_other_aws_summary)
```

---

## My recommended final setup

Use this URL as your main service-cost pull:

```text
https://api.cloudability.com/v3/reporting/cost/run?start_date=2026-01-01&end_date=2026-01-31&dimensions=enhanced_service_name,usage_family,container_cluster_name,container_namespace&metrics=total_amortized_cost&filters=vendor%3D%3DAmazon&sort=total_amortized_costDESC&limit=0
```

Then classify:

```text
container_cluster_name populated
OR container_namespace populated
    => Cluster + Namespace Cost

else
    => Other AWS Cost
```

Use the **Container API** only when you need deeper drill-down, such as workload, pod, node group, idle cost, or
allocated cost. Cloudability’s container report endpoint is designed for those container-specific drilldowns by grouping
metrics with dimensions like cluster and namespace. ([IBM][2])

[1]: https://www.ibm.com/docs/en/cloudability-commercial/cloudability-premium/saas?topic=api-cost-reporting-end-point&utm_source=chatgpt.com "Cost Reporting End Point"

[2]: https://www.ibm.com/docs/en/cloudability-commercial/cloudability-enterprise/saas?topic=points-report-api-documentation&utm_source=chatgpt.com "Report API Documentation"
