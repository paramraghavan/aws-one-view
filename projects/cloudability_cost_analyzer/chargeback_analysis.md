## Updated Scripts — Based on Your Exact API Calls

Two key corrections from your working calls:

- Auth is `API_KEY:API_PASS` (not `API_KEY:` blank)
- Date params are `start=` / `end=` on containers endpoint (not `start_date=`)
- Filter syntax is `cluster==<id>` (not `cluster_id==<id>`)
- Cost metric is `adjusted_amortized_cost` / `total_amortized_cost`

---

### Script 1 — Pull User/Namespace Cost by Month (`containers/allocations`)

```bash
#!/bin/bash
# ============================================================
# pull_namespace_cost.sh
# Pulls K8s namespace (user) cost from containers/allocations
# One CSV per month, Jan 2025 → Feb 2026
# ============================================================
set -euo pipefail

API_KEY="your_api_key"
API_PASS="your_api_pass"
CLUSTER_ID="1fe68867-f04b-4791-b7bb-9a5ef584c24b"
BASE_URL="https://api.cloudability.com/v3/containers/allocations"
OUTPUT_DIR="./chargeback/namespace"
mkdir -p "${OUTPUT_DIR}"

# Month array: "LABEL  START       END"
declare -a MONTHS=(
  "2025-01  2025-01-01  2025-01-31"
  "2025-02  2025-02-01  2025-02-28"
  "2025-03  2025-03-01  2025-03-31"
  "2025-04  2025-04-01  2025-04-30"
  "2025-05  2025-05-01  2025-05-31"
  "2025-06  2025-06-01  2025-06-30"
  "2025-07  2025-07-01  2025-07-31"
  "2025-08  2025-08-01  2025-08-31"
  "2025-09  2025-09-01  2025-09-30"
  "2025-10  2025-10-01  2025-10-31"
  "2025-11  2025-11-01  2025-11-30"
  "2025-12  2025-12-01  2025-12-31"
  "2026-01  2026-01-01  2026-01-31"
  "2026-02  2026-02-01  2026-02-28"
)

echo "================================================"
echo " Cloudability Namespace Chargeback Pull"
echo " Cluster: ${CLUSTER_ID}"
echo "================================================"

for ENTRY in "${MONTHS[@]}"; do
  read -r MONTH START END <<< "${ENTRY}"
  OUT="${OUTPUT_DIR}/namespace_cost_${MONTH}.csv"
  echo -n "  [${MONTH}] ${START} → ${END} ... "

  HTTP_CODE=$(curl -k -s \
    -u "${API_KEY}:${API_PASS}" \
    -X GET \
    --header "Accept: text/csv" \
    -o "${OUT}" \
    -w "%{http_code}" \
    "https://api.cloudability.com/v3/containers/allocations?\
pretty=false\
&start=${START}\
&end=${END}\
&filters=cluster==${CLUSTER_ID}\
&costType=adjusted_amortized_cost")

  if [ "${HTTP_CODE}" -eq 200 ]; then
    ROWS=$(( $(wc -l < "${OUT}") - 1 ))   # subtract header row
    echo "✓ HTTP 200 — ${ROWS} namespace rows → ${OUT}"
  else
    echo "✗ FAILED — HTTP ${HTTP_CODE}"
    echo "  Response: $(cat "${OUT}")"
  fi

  sleep 1   # rate limit courtesy
done

echo ""
echo "Done. Files → ${OUTPUT_DIR}"
```

---

### Script 2 — Pull AWS Service Cost by Month (`reporting/cost/run`)

```bash
#!/bin/bash
# ============================================================
# pull_service_cost.sh
# Pulls AWS service cost (platform + cloud) from reporting/cost/run
# One CSV per month, Jan 2025 → Feb 2026
# ============================================================
set -euo pipefail

API_KEY="your_api_key"
API_PASS="your_api_pass"
BASE_URL="https://api.cloudability.com/v3/reporting/cost/run"
OUTPUT_DIR="./chargeback/service"
mkdir -p "${OUTPUT_DIR}"

declare -a MONTHS=(
  "2025-01  2025-01-01  2025-01-31"
  "2025-02  2025-02-01  2025-02-28"
  "2025-03  2025-03-01  2025-03-31"
  "2025-04  2025-04-01  2025-04-30"
  "2025-05  2025-05-01  2025-05-31"
  "2025-06  2025-06-01  2025-06-30"
  "2025-07  2025-07-01  2025-07-31"
  "2025-08  2025-08-01  2025-08-31"
  "2025-09  2025-09-01  2025-09-30"
  "2025-10  2025-10-01  2025-10-31"
  "2025-11  2025-11-01  2025-11-30"
  "2025-12  2025-12-01  2025-12-31"
  "2026-01  2026-01-01  2026-01-31"
  "2026-02  2026-02-01  2026-02-28"
)

echo "================================================"
echo " Cloudability AWS Service Cost Pull"
echo "================================================"

for ENTRY in "${MONTHS[@]}"; do
  read -r MONTH START END <<< "${ENTRY}"
  OUT="${OUTPUT_DIR}/service_cost_${MONTH}.csv"
  echo -n "  [${MONTH}] ${START} → ${END} ... "

  HTTP_CODE=$(curl -k -s \
    -u "${API_KEY}:${API_PASS}" \
    -X GET \
    --header "Accept: text/csv" \
    -o "${OUT}" \
    -w "%{http_code}" \
    "https://api.cloudability.com/v3/reporting/cost/run?\
start_date=${START}\
&end_date=${END}\
&dimensions=service_name,usage_family\
&metrics=total_amortized_cost\
&sort=total_amortized_cost+DESC")

  if [ "${HTTP_CODE}" -eq 200 ]; then
    ROWS=$(( $(wc -l < "${OUT}") - 1 ))
    echo "✓ HTTP 200 — ${ROWS} service rows → ${OUT}"
  else
    echo "✗ FAILED — HTTP ${HTTP_CODE}"
    echo "  Response: $(cat "${OUT}")"
  fi

  sleep 1
done

echo ""
echo "Done. Files → ${OUTPUT_DIR}"
```

---

### Script 3 — Python: Consolidate + Chargeback by User + MoM Change

```python
#!/usr/bin/env python3
"""
consolidate_chargeback.py

Consolidates monthly namespace CSVs from containers/allocations
and service CSVs from reporting/cost/run into:
  1. chargeback_by_user.csv     — user cost per month + MoM delta
  2. service_cost_summary.csv   — AWS service cost per month
  3. chargeback_final.csv       — combined view
"""

import os
import glob
import pandas as pd

NS_DIR = "./chargeback/namespace"
SVC_DIR = "./chargeback/service"
OUTPUT_DIR = "./chargeback/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── Namespaces that are platform services, NOT user/modeller namespaces ────
SERVICE_NAMESPACES = {
    # Kubernetes system
    "kube-system", "kube-public", "kube-node-lease", "default",
    # Cloudability agent (always present on K8s clusters)
    "cloudability",
    # Observability
    "monitoring", "prometheus", "grafana", "alertmanager",
    # Logging
    "logging", "fluentd", "elasticsearch", "opensearch",
    # Service mesh
    "istio-system", "linkerd", "linkerd-viz",
    # Ingress / DNS
    "ingress-nginx", "traefik", "external-dns",
    # Certs / Secrets
    "cert-manager", "vault", "external-secrets",
    # AWS / EKS
    "aws-system", "amazon-cloudwatch", "aws-load-balancer-controller",
    "karpenter", "cluster-autoscaler",
    # EMR / Spark platform
    "spark-operator", "emr-system", "emr-operator", "emr-containers",
    # CI/CD
    "argocd", "flux-system", "jenkins",
}

MONTHS_ORDERED = [
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]


# ═══════════════════════════════════════════════════════════════
# PART 1 — Namespace (User) Cost
# ═══════════════════════════════════════════════════════════════

def load_namespace_data():
    frames = []
    for month in MONTHS_ORDERED:
        path = f"{NS_DIR}/namespace_cost_{month}.csv"
        if not os.path.exists(path):
            print(f"  MISSING: {path}")
            continue
        try:
            df = pd.read_csv(path)
            # Normalize column names
            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
            df["month"] = month
            frames.append(df)
            print(f"  Loaded {path}: {len(df)} rows, cols={list(df.columns)}")
        except Exception as e:
            print(f"  ERROR loading {path}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


print("\n── Loading namespace/user data ──")
ns_data = load_namespace_data()

if not ns_data.empty:
    # Print actual column names so you can verify mapping
    print(f"\nNamespace CSV columns: {list(ns_data.columns)}")

    # ── Adjust these to match your actual Cloudability CSV column names ──
    # Common names: 'namespace', 'k8s_namespace', 'container_group'
    NS_COL = "namespace"  # <-- verify against printed columns
    COST_COL = "adjusted_amortized_cost"  # <-- verify against printed columns

    # Split users vs platform services
    ns_data["is_service"] = ns_data[NS_COL].str.lower().isin(SERVICE_NAMESPACES)
    user_data = ns_data[~ns_data["is_service"]].copy()
    platform_data = ns_data[ns_data["is_service"]].copy()

    print(f"\nUser namespaces:     {user_data[NS_COL].nunique()} unique")
    print(f"Service namespaces:  {platform_data[NS_COL].nunique()} unique")
    print(f"Service namespaces found: {sorted(platform_data[NS_COL].unique())}")

    # ── Pivot: namespace × month ──
    user_pivot = (
        user_data
        .groupby([NS_COL, "month"])[COST_COL]
        .sum()
        .reset_index()
        .pivot(index=NS_COL, columns="month", values=COST_COL)
        .reindex(columns=MONTHS_ORDERED)  # enforce month order
        .fillna(0.0)
        .sort_index()
    )

    # ── Month-over-Month delta and % change ──
    available_months = [m for m in MONTHS_ORDERED if m in user_pivot.columns]
    for i in range(1, len(available_months)):
        prev = available_months[i - 1]
        curr = available_months[i]
        user_pivot[f"delta_{curr}"] = (user_pivot[curr] - user_pivot[prev]).round(2)
        user_pivot[f"pct_{curr}"] = (
            ((user_pivot[curr] - user_pivot[prev])
             / user_pivot[prev].replace(0, pd.NA) * 100)
            .round(1)
        )

    user_pivot["TOTAL"] = user_pivot[available_months].sum(axis=1).round(2)
    user_pivot = user_pivot.sort_values("TOTAL", ascending=False)

    out_user = f"{OUTPUT_DIR}/chargeback_by_user.csv"
    user_pivot.reset_index().to_csv(out_user, index=False)
    print(f"\n✓ User chargeback saved → {out_user}")

    # ── Platform cost summary ──
    platform_pivot = (
        platform_data
        .groupby([NS_COL, "month"])[COST_COL]
        .sum()
        .reset_index()
        .pivot(index=NS_COL, columns="month", values=COST_COL)
        .reindex(columns=MONTHS_ORDERED)
        .fillna(0.0)
    )
    platform_pivot["TOTAL"] = platform_pivot[available_months].sum(axis=1).round(2)
    out_platform = f"{OUTPUT_DIR}/platform_cost_by_namespace.csv"
    platform_pivot.reset_index().to_csv(out_platform, index=False)
    print(f"✓ Platform cost saved → {out_platform}")


# ═══════════════════════════════════════════════════════════════
# PART 2 — AWS Service Cost (from reporting/cost/run)
# ═══════════════════════════════════════════════════════════════

def load_service_data():
    frames = []
    for month in MONTHS_ORDERED:
        path = f"{SVC_DIR}/service_cost_{month}.csv"
        if not os.path.exists(path):
            print(f"  MISSING: {path}")
            continue
        try:
            df = pd.read_csv(path)
            df.columns = [c.lower().strip().replace(" ", "_") for c in df.columns]
            df["month"] = month
            frames.append(df)
        except Exception as e:
            print(f"  ERROR loading {path}: {e}")
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


print("\n── Loading AWS service cost data ──")
svc_data = load_service_data()

if not svc_data.empty:
    print(f"Service CSV columns: {list(svc_data.columns)}")

    # ── Adjust to match actual column names ──
    SVC_COL = "service_name"  # <-- verify
    FAMILY_COL = "usage_family"  # <-- verify
    SVC_COST_COL = "total_amortized_cost"  # <-- verify

    svc_pivot = (
        svc_data
        .groupby([SVC_COL, FAMILY_COL, "month"])[SVC_COST_COL]
        .sum()
        .reset_index()
        .pivot_table(
            index=[SVC_COL, FAMILY_COL],
            columns="month",
            values=SVC_COST_COL,
            aggfunc="sum"
        )
        .reindex(columns=MONTHS_ORDERED)
        .fillna(0.0)
    )
    svc_pivot["TOTAL"] = svc_pivot[
        [m for m in MONTHS_ORDERED if m in svc_pivot.columns]
    ].sum(axis=1).round(2)
    svc_pivot = svc_pivot.sort_values("TOTAL", ascending=False)

    out_svc = f"{OUTPUT_DIR}/service_cost_summary.csv"
    svc_pivot.reset_index().to_csv(out_svc, index=False)
    print(f"✓ Service cost saved → {out_svc}")

# ═══════════════════════════════════════════════════════════════
# PART 3 — Quick Console Summary
# ═══════════════════════════════════════════════════════════════

if not ns_data.empty and "user_pivot" in dir():
    print("\n" + "═" * 65)
    print(f"  CHARGEBACK SUMMARY — TOP 10 USERS (TOTAL SPEND)")
    print("═" * 65)
    top10 = user_pivot["TOTAL"].nlargest(10)
    for ns, cost in top10.items():
        print(f"  {ns:<35} ${cost:>12,.2f}")
    print("═" * 65)
    total_all = user_pivot["TOTAL"].sum()
    print(f"  {'ALL USERS TOTAL':<35} ${total_all:>12,.2f}")
    print("═" * 65)

print("\nAll done.")
```

---

### Output Files Produced

| File                                               | Contents                                             |
|----------------------------------------------------|------------------------------------------------------|
| `chargeback/namespace/namespace_cost_YYYY-MM.csv`  | Raw per-namespace cost from `containers/allocations` |
| `chargeback/service/service_cost_YYYY-MM.csv`      | Raw AWS service cost from `reporting/cost/run`       |
| `chargeback/output/chargeback_by_user.csv`         | **User pivot: cost + MoM delta + % change + total**  |
| `chargeback/output/platform_cost_by_namespace.csv` | Platform/system namespace costs separated out        |
| `chargeback/output/service_cost_summary.csv`       | AWS cost by service_name + usage_family pivot        |

---

### One Thing to Verify First

Run this one-off call to see the **exact column names** Cloudability returns in your environment before running the full
loop — column names can differ by tenant config:

```bash
curl -k -s \
  -u "${API_KEY}:${API_PASS}" \
  -X GET \
  --header "Accept: text/csv" \
  "https://api.cloudability.com/v3/containers/allocations?\
start=2025-01-01&end=2025-01-31\
&filters=cluster==1fe68867-f04b-4791-b7bb-9a5ef584c24b\
&costType=adjusted_amortized_cost" | head -3
```

The first line returned is the header row — use those exact names in `NS_COL` and `COST_COL` in the Python script.