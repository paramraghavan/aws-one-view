# AWS ~$70K Service Breakdown & Attribution Strategy

**Total AWS Cost:** ~$192K  
**Blue Cluster (freddie-eks-ckf-blue):** ~$118K  
**Remaining Services (this document):** ~$70K

---

## Summary

| Category                                | Estimated Cost | Approach                                   |
|-----------------------------------------|----------------|--------------------------------------------|
| Safe to distribute proportionally       | ~$5,900        | Distribute by namespace compute cost share |
| Needs investigation before distributing | ~$37,200       | Tag/verify ownership first                 |
| Direct attribution only                 | ~$17,600       | Attribute to specific team/namespace owner |
| **Total**                               | **~$60,700**   | + CloudWatch (TBD)                         |

---

## Tier 1 — Proportional ✅

*Safe to distribute by namespace compute cost share immediately.*

| Service              | Usage Type                                                            | Cost    | What It Is                                                                            |
|----------------------|-----------------------------------------------------------------------|---------|---------------------------------------------------------------------------------------|
| AWS EKS              | USE1-AmazonEKS-Hours:extendedSupport, USE1-AmazonEKS-Hours:perCluster | ~$4,000 | Control plane flat fees + extended K8s version support — pure shared cluster overhead |
| AWS KMS              | us-east-1-KMS-Keys                                                    | $1,269  | Encryption key management — genuinely shared infrastructure                           |
| AWS CloudWatch       | (partial — cut off in data)                                           | TBD     | Shared observability and logging overhead                                             |
| AWS EC2 DataTransfer | DataTransfer-Regional-Bytes                                           | ~$632   | Cross-AZ data transfer — hard to attribute directly                                   |

**Action:** Distribute these costs proportionally using each namespace's share of total `total_amortized_cost` from the
Cloudability container allocation API.

---

## Tier 2 — Investigate First ⚠️

*Proportional distribution is acceptable only after verifying ownership and improving tagging.*

| Service | Usage Type                                                                                                  | Cost     | What It Is                                                                                                      | Action                          |
|---------|-------------------------------------------------------------------------------------------------------------|----------|-----------------------------------------------------------------------------------------------------------------|---------------------------------|
| AWS EBS | VolumeUsage.gp3 (multiple entries), VolumeP-IOPS.gp3, VolumeP-IOPS.piops, VolumeP-Throughput.gp3            | ~$16,500 | Node root volumes → proportional OK. PVCs should be tagged to owning namespace                                  | Tag PVCs to namespace first     |
| AWS EBS | EBS:SnapshotUsage                                                                                           | $11,497  | Backup snapshots — large enough to warrant tracing back to the volume/namespace that owns them                  | Trace to volume/namespace owner |
| AWS EFS | USE1-TimedStorage-ByteHrs, USE1-ETDataAccess-Bytes, USE1-IATimedStorage-ET-ByteHrs, USE1-IADataAccess-Bytes | ~$5,736  | Shared NFS file system. Proportional OK if truly shared; otherwise tag mount points to namespaces               | Check mount point ownership     |
| AWS S3  | TimedStorage-ByteHrs                                                                                        | $2,763   | Object storage. Should be attributed by bucket ownership tags, not spread across all namespaces                 | Tag S3 buckets to owning teams  |
| AWS ELB | LoadBalancerUsage                                                                                           | $662     | Load balancers. If namespace-tagged (type:LoadBalancer services), attribute directly; else proportional is fine | Check LB tags                   |

**Key risk:** The $11,497 EBS snapshot cost is the largest single item here — tracing snapshots back to their source
volumes/namespaces before distributing is strongly recommended.

---

## Tier 3 — Direct Attribution Only ❌

*Do not distribute proportionally. These services have specific owners and blind distribution would incorrectly bill
unrelated namespaces.*

| Service      | Usage Type                                                                                                      | Cost     | What It Is                                                                                                                                                          | Action                                                                          |
|--------------|-----------------------------------------------------------------------------------------------------------------|----------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| AWS EC2      | r5b.16xlarge, m5.4xlarge, c6i.16xlarge, c6i.8xlarge, m5.12xlarge, m5.8xlarge (multiple entries)                 | ~$15,000 | Large instances NOT tagged to the blue cluster — likely a separate cluster or untagged nodes. Distributing to blue cluster namespaces would be incorrect            | **Identify which cluster these belong to before including in any distribution** |
| AWS RDS      | ExtendedSupport:Yr1-Yr2:PostgreSQL11, InstanceUsage:db.r5.large, Multi-AZUsage:db.m5.xl, InstanceUsage:db.m5.xl | ~$2,437  | Real running DB instances (not just support fees). Each database is owned by a specific team — spreading across all namespaces bills teams that don't use these DBs | Attribute each DB instance to its owning team/namespace                         |
| AWS DynamoDB | WriteCapacityUnit-Hrs                                                                                           | $138     | NoSQL table writes — table has a specific owning team/namespace                                                                                                     | Attribute to table owner                                                        |

**Critical note on EC2 (~$15K):** The multiple entries of large instance types (r5b, m5, c6i in varying sizes) strongly
suggest these are worker nodes from a **separate cluster** (not the blue cluster). Including them in blue cluster
namespace distribution would inflate every namespace's cost incorrectly. Confirm cluster membership via AWS tags or Cost
Explorer before proceeding.

**Critical note on RDS (~$2.4K):** This includes actual running database instances (`db.r5.large`, Multi-AZ `db.m5.xl`),
not just extended support fees. These are owned by specific teams and should be attributed directly.

---

## Recommended Distribution Logic

### Step 1 — Separate by tier

Filter your Cloudability service cost results into the three tiers above before running any allocation.

### Step 2 — Direct attribution (Tier 3)

Identify owning team/namespace for each RDS instance, DynamoDB table, and untagged EC2. Apply cost directly to those
namespaces.

### Step 3 — Tagging cleanup (Tier 2)

Before next month's allocation run:

- Tag EBS PVCs with `namespace` labels
- Tag S3 buckets with owning team
- Confirm EFS mount ownership
- Verify ELB namespace tags

### Step 4 — Proportional distribution (Tier 1 + cleared Tier 2)

Use the Cloudability container allocation API with `container_namespace` dimension. Calculate each namespace's weight:

```
namespace_weight = namespace_total_amortized_cost / sum_of_all_namespace_costs

allocated_cost_for_namespace = shared_service_cost × namespace_weight
```

### Step 5 — Verify untagged EC2

Run the following Cloudability query to check cluster membership of the untagged EC2 instances:

```
GET /v3/reporting/cost/run
  ?start_date=${START_OF_PREV_MONTH}
  &end_date=${END_OF_PREV_MONTH}
  &dimensions=service_name,usage_family,container_cluster_name
  &metrics=total_amortized_cost
  &filters=enhanced_service_name==AWS EC2
  &sort=total_amortized_cost:DESC
```

If `container_cluster_name` is blank or points to a different cluster, exclude those EC2 costs from the blue cluster
namespace distribution entirely.


