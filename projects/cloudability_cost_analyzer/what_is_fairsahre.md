# `cost:fairshare` Explained with Example

---

## The Cluster Setup

Imagine a cluster with **3 nodes**, each costing **$100/hr** = **$300/hr total cluster cost**

3 teams are running workloads:

| Team                       | CPU Requested (allocation) |
|----------------------------|----------------------------|
| Team A                     | 40 cores                   |
| Team B                     | 30 cores                   |
| Team C                     | 10 cores                   |
| **Total Requested**        | **80 cores**               |
| **Total Cluster Capacity** | **100 cores**              |
| **Idle (unallocated)**     | **20 cores**               |

---

### Step 1 — `cost:allocation`

Cost based purely on what each team requested:

```
Total allocation cost = $240  (80% of $300, 20 cores idle)

Team A allocation = (40/80) × $240 = $120
Team B allocation = (30/80) × $240 = $90
Team C allocation = (10/80) × $240 = $30
```

---

### Step 2 — `cost:fairshare`

Idle $60 (20 cores × $3/core) gets **redistributed proportionally**:

```
Team A fairshare = $120 + (40/80) × $60 = $120 + $30 = $150
Team B fairshare = $90  + (30/80) × $60 = $90  + $23 = $113
Team C fairshare = $30  + (10/80) × $60 = $30  + $8  = $38

Total fairshare = $150 + $113 + $38 = $301 ≈ $300 ✅
```

---

## What This Means Per Team

| Team   | allocation | fairshare | Idle Tax Absorbed    |
|--------|------------|-----------|----------------------|
| Team A | $120       | $150      | $30 — pays most idle |
| Team B | $90        | $113      | $23                  |
| Team C | $30        | $38       | $8 — pays least idle |

---

## Key Insight

```
cost:fairshare = cost:allocation + your proportional share of idle waste
```

- **Fairshare is never less than allocation** when `unallocated = 0`
- The **bigger your allocation**, the **more idle tax** you absorb
- Total fairshare always sums to **total cluster cost** — no dollar is left unaccounted

This is why fairshare is used for **chargeback** — it ensures the full cluster cost is always recovered across all
tenants.