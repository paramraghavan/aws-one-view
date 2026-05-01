## Simplified Chargeback — Small Functions, Clear Logic

---

### The Whole Problem in Plain English

```
WHAT WE HAVE:
  API1 → K8s costs split by namespace (user + platform)
  API2 → AWS bill (EC2, EKS, Artifactory, Licenses, etc.)

WHAT WE WANT:
  Monthly cost per user (Cxxxxx / Fxxxxx)

THE RULE:
  API1 already contains EC2 + EKS costs (split by namespace)
  So from API2 we only add: Artifactory + License + Bronze + NonProd
  Everything else in API2 is already in API1 → skip it
```

---

### Cost Model — One Diagram

```
User Bill = 
  direct_cost          (API1: their namespace)
+ platform_share       (API1: platform namespaces × their %)
+ extras_share         (API2: Artifactory+License+Bronze+NonProd × their %)

their % = their direct cost / total of all users direct cost
```

---

### Code — Small Functions

```python
#!/usr/bin/env python3
"""
chargeback.py  —  Simple version, small functions
"""

import re
import glob
import pandas as pd
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────────────

API1_DIR = "./output/api1_allocations"  # one CSV per month
API2_DIR = "./output/api2_service_costs"  # one CSV per month
OUTPUT_DIR = "./output/reports"

# User namespaces look like Cxxxxxxx or Fxxxxxxx
USER_PATTERN = re.compile(r'^[CFcf][a-zA-Z0-9]+$')

# Known platform/system namespaces
PLATFORM_NS = {
    "kube-system", "kube-public", "kube-node-lease", "default",
    "monitoring", "prometheus", "grafana", "logging", "fluentd",
    "istio-system", "cert-manager", "ingress-nginx", "spark-operator",
    "emr-system", "emr-operator", "aws-system", "amazon-cloudwatch",
    "cluster-autoscaler", "external-dns", "vault", "cloudability",
}

MONTHS = [
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05", "2025-06",
    "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12",
    "2026-01", "2026-02",
]

# API1 cost column (total cost per namespace row)
API1_COST_COL = "costs:allocation"

# API2 columns that are NET NEW (not already in API1)
# EC2 + EKS costs are EXCLUDED — already captured in API1
API2_EXTRA_COLS = {
    "artifactory": "Artifactory Cost",
    "license": "License Cost",
    "bronze": "Bronze Cost",
    "nonprod": "Non-Prod Cost",
}


# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — LOAD DATA
# ═══════════════════════════════════════════════════════════════════════

def load_monthly_csvs(folder, prefix):
    """Load all monthly CSV files from a folder into one DataFrame."""
    frames = []
    for fp in sorted(glob.glob(f"{folder}/{prefix}_*.csv")):
        month = re.search(r'(\d{4}-\d{2})', fp).group(1)
        df = pd.read_csv(fp, low_memory=False)
        df.columns = df.columns.str.strip()
        df["month"] = month
        frames.append(df)
        print(f"  loaded {month}: {len(df)} rows")
    return pd.concat(frames, ignore_index=True)


def load_api1():
    print("\n--- Loading API1 (container allocations) ---")
    df = load_monthly_csvs(API1_DIR, "api1_allocations")
    df[API1_COST_COL] = pd.to_numeric(
        df[API1_COST_COL], errors="coerce").fillna(0.0)
    return df


def load_api2():
    print("\n--- Loading API2 (service costs) ---")
    df = load_monthly_csvs(API2_DIR, "api2_services")
    for col in API2_EXTRA_COLS.values():
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r'[$,]', '', regex=True),
                errors="coerce").fillna(0.0)
    return df


# ═══════════════════════════════════════════════════════════════════════
# STEP 2 — CLASSIFY NAMESPACES
# ═══════════════════════════════════════════════════════════════════════

def classify(namespace):
    """Return 'user', 'platform', based on namespace name."""
    if not isinstance(namespace, str):
        return "platform"
    ns = namespace.strip()
    if USER_PATTERN.match(ns):
        return "user"
    if ns.lower() in PLATFORM_NS:
        return "platform"
    return "platform"  # unknown → treat as platform overhead


def split_api1(api1):
    """Split API1 rows into user namespaces and platform namespaces."""
    api1["ns_type"] = api1["namespace"].apply(classify)
    api1["employee_id"] = api1["namespace"].str.upper().str.strip()

    user_df = api1[api1["ns_type"] == "user"].copy()
    platform_df = api1[api1["ns_type"] == "platform"].copy()

    print(f"\nNamespaces found:")
    print(f"  User namespaces    : "
          f"{user_df['namespace'].nunique()} unique")
    print(f"  Platform namespaces: "
          f"{platform_df['namespace'].nunique()} unique")
    print(f"\n  Platform list:")
    for ns in sorted(platform_df["namespace"].unique()):
        total = platform_df[platform_df["namespace"] == ns][API1_COST_COL].sum()
        print(f"    {ns:<40} ${total:>12,.2f}")

    return user_df, platform_df


# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — MONTHLY COST POOLS
# ═══════════════════════════════════════════════════════════════════════

def get_user_direct_costs(user_df):
    """Monthly direct cost per user from API1."""
    return (
        user_df.groupby(["employee_id", "month"])[API1_COST_COL]
        .sum().round(2).reset_index()
        .rename(columns={API1_COST_COL: "direct_cost"})
    )


def get_platform_pool(platform_df):
    """Monthly platform namespace cost from API1 (shared overhead)."""
    return (
        platform_df.groupby("month")[API1_COST_COL]
        .sum().round(2)
        .rename("platform_pool")
    )


def get_extras_pool(api2):
    """
    Monthly extra costs from API2 — Artifactory, License, Bronze, NonProd.
    EC2 and EKS are intentionally excluded (already in API1).
    """
    available = {k: v for k, v in API2_EXTRA_COLS.items()
                 if v in api2.columns}
    missing = set(API2_EXTRA_COLS) - set(available)
    if missing:
        print(f"  WARNING: API2 missing columns: {missing}")

    pool = api2.groupby("month")[list(available.values())].sum().round(2)
    pool.columns = [k for k in available]  # rename to short keys
    pool["extras_total"] = pool.sum(axis=1).round(2)
    return pool


# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — CALCULATE CHARGEBACK
# ═══════════════════════════════════════════════════════════════════════

def calc_user_share(direct_cost, total_direct):
    """What % of cluster spend does this user represent?"""
    if total_direct > 0:
        return round(direct_cost / total_direct * 100, 4)
    return 0.0


def build_chargeback(user_costs, platform_pool, extras_pool):
    """
    For each user × month:
      total = direct + (platform × share%) + (extras × share%)
    """
    # Monthly total direct cost = denominator for share %
    monthly_totals = (
        user_costs.groupby("month")["direct_cost"]
        .sum().rename("total_direct")
    )

    rows = []
    for _, row in user_costs.iterrows():
        emp = row["employee_id"]
        month = row["month"]
        dc = row["direct_cost"]

        total = monthly_totals.get(month, 0)
        share = dc / total if total > 0 else 0  # decimal, e.g. 0.032

        plat = float(platform_pool.get(month, 0))
        extras = extras_pool.loc[month] if month in extras_pool.index
            else pd.Series(dtype=float)

        plat_share = round(share * plat, 2)
        ext_detail = {
            k: round(share * float(extras.get(k, 0)), 2)
            for k in API2_EXTRA_COLS
        }
        ext_total = round(sum(ext_detail.values()), 2)

        rows.append({
            "employee_id": emp,
            "month": month,
            "direct_cost": round(dc, 2),
            "user_share_pct": round(share * 100, 2),
            "platform_share": plat_share,
            **ext_detail,
            "extras_total": ext_total,
            "total_chargeback": round(dc + plat_share + ext_total, 2),
        })

    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — PIVOT TO MONTHLY COLUMNS + MoM CHANGE
# ═══════════════════════════════════════════════════════════════════════

def pivot_by_month(df, value_col, months):
    """Rows = employee, columns = months. Add MoM Δ columns."""
    pivot = (
        df.pivot_table(
            index="employee_id",
            columns="month",
            values=value_col,
            aggfunc="sum"
        )
        .reindex(columns=[m for m in months if m in df["month"].values])
        .fillna(0.0)
        .round(2)
    )

    # Month-over-month change
    live_months = [m for m in months if m in pivot.columns]
    for i in range(1, len(live_months)):
        prev, curr = live_months[i - 1], live_months[i]
        delta = (pivot[curr] - pivot[prev]).round(2)
        pct = (delta / pivot[prev].replace(0, pd.NA) * 100).round(1)
        pivot[f"chg_{curr}"] = delta
        pivot[f"chg%_{curr}"] = pct

    pivot["TOTAL"] = pivot[live_months].sum(axis=1).round(2)
    pivot["AVG_MONTH"] = pivot[live_months].mean(axis=1).round(2)
    return pivot.sort_values("TOTAL", ascending=False)


# ═══════════════════════════════════════════════════════════════════════
# STEP 6 — RECONCILIATION (sanity check)
# ═══════════════════════════════════════════════════════════════════════

def reconcile(chargeback_df, platform_pool, extras_pool, months):
    """
    Month-level summary to verify totals make sense.
    direct + platform_pool + extras_pool should = sum of all user chargebacks
    """
    rows = []
    for month in months:
        m = chargeback_df[chargeback_df["month"] == month]
        if m.empty:
            continue
        ext_total = float(extras_pool.loc[month, "extras_total"])
            if month in extras_pool.index else 0
        rows.append({
            "month": month,
            "num_users": len(m),
            "direct_total": m["direct_cost"].sum().round(2),
            "platform_pool": round(float(platform_pool.get(month, 0)), 2),
            "extras_pool": round(ext_total, 2),
            "sum_chargeback": m["total_chargeback"].sum().round(2),
        })
    return pd.DataFrame(rows)


# ═══════════════════════════════════════════════════════════════════════
# STEP 7 — SAVE + PRINT
# ═══════════════════════════════════════════════════════════════════════

def save(df, filename):
    path = f"{OUTPUT_DIR}/{filename}"
    df.to_csv(path, index=True)
    print(f"  saved: {path}")


def print_summary(chargeback_pivot, recon_df):
    live = [c for c in chargeback_pivot.columns
            if re.match(r'\d{4}-\d{2}', c)]

    print("\n" + "=" * 65)
    print("MONTHLY SUMMARY")
    print("=" * 65)
    print(f"\n{'Month':<10} {'Users':>6} {'Direct':>12} "
          f"{'Platform':>12} {'Extras':>10} {'TOTAL CB':>14}")
    print("-" * 66)
    for _, r in recon_df.iterrows():
        print(f"{r['month']:<10} {r['num_users']:>6} "
              f"${r['direct_total']:>11,.0f} "
              f"${r['platform_pool']:>11,.0f} "
              f"${r['extras_pool']:>9,.0f} "
              f"${r['sum_chargeback']:>13,.0f}")

    print("\n" + "=" * 65)
    print("TOP 10 USERS — TOTAL CHARGEBACK")
    print("=" * 65)
    print(f"\n{'Employee':<14}", end="")
    for m in live[:6]:
        print(f" {m:>10}", end="")
    print(f" {'TOTAL':>12}  {'AVG/MO':>9}")
    print("-" * (14 + 11 * min(6, len(live)) + 24))
    for emp, row in chargeback_pivot.head(10).iterrows():
        print(f"{emp:<14}", end="")
        for m in live[:6]:
            print(f" ${row[m]:>9,.0f}", end="")
        print(f" ${row['TOTAL']:>11,.0f}  ${row['AVG_MONTH']:>8,.0f}")


# ═══════════════════════════════════════════════════════════════════════
# MAIN — wire it all together
# ═══════════════════════════════════════════════════════════════════════

def main():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # 1. Load
    api1 = load_api1()
    api2 = load_api2()

    # 2. Classify namespaces
    user_df, platform_df = split_api1(api1)

    # 3. Cost pools
    user_costs = get_user_direct_costs(user_df)
    platform_pool = get_platform_pool(platform_df)
    extras_pool = get_extras_pool(api2)

    # 4. Chargeback per user per month
    chargeback_df = build_chargeback(user_costs, platform_pool, extras_pool)

    # 5. Pivot to wide format with MoM change
    chargeback_pivot = pivot_by_month(chargeback_df, "total_chargeback", MONTHS)
    direct_pivot = pivot_by_month(chargeback_df, "direct_cost", MONTHS)

    # 6. Reconciliation
    recon_df = reconcile(chargeback_df, platform_pool, extras_pool, MONTHS)

    # 7. Save
    save(chargeback_pivot, "chargeback_by_user.csv")
    save(direct_pivot, "direct_cost_by_user.csv")
    save(chargeback_df, "chargeback_detail.csv")
    save(recon_df.set_index("month"), "monthly_reconciliation.csv")

    # 8. Print
    print_summary(chargeback_pivot, recon_df)


if __name__ == "__main__":
    main()
```

---

### What Each Function Does — One Line Each

| Function                | Does                                                         |
|-------------------------|--------------------------------------------------------------|
| `load_monthly_csvs`     | reads all monthly CSVs from a folder into one DataFrame      |
| `load_api1`             | calls above + converts cost column to numeric                |
| `load_api2`             | calls above + converts API2 cost columns to numeric          |
| `classify`              | returns `"user"` or `"platform"` for a namespace string      |
| `split_api1`            | applies classify to every row, separates into two DataFrames |
| `get_user_direct_costs` | sums API1 cost by employee + month                           |
| `get_platform_pool`     | sums API1 platform namespace cost by month                   |
| `get_extras_pool`       | sums API2 Artifactory+License+Bronze+NonProd by month        |
| `calc_user_share`       | user direct ÷ all users direct = their %                     |
| `build_chargeback`      | applies share% to each pool, produces one row per user×month |
| `pivot_by_month`        | rotates to wide format (rows=users, cols=months) + MoM Δ     |
| `reconcile`             | monthly totals sanity check table                            |
| `save`                  | writes DataFrame to CSV                                      |
| `print_summary`         | prints console report                                        |
| `main`                  | calls all of the above in order                              |

---

### Output Files

| File                         | Contents                                                     |
|------------------------------|--------------------------------------------------------------|
| `chargeback_by_user.csv`     | Final bill per user per month + MoM change                   |
| `direct_cost_by_user.csv`    | Raw API1 cost only (before shared allocation)                |
| `chargeback_detail.csv`      | Every user × month with direct / platform / extras breakdown |
| `monthly_reconciliation.csv` | Month-level totals to verify nothing is missing              |