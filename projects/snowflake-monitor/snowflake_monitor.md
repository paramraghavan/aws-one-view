# Snowflake Concepts & Terminology Guide

This guide explains the Snowflake-specific terminology and metrics used throughout the Resource Monitor. Understanding these concepts will help you interpret the dashboard data and make informed optimization decisions.

---

## Table of Contents

1. [Snowflake Credit System](#snowflake-credit-system)
   - [What is a Credit?](#what-is-a-credit)
   - [Compute Credits](#compute-credits)
   - [Cloud Services Credits](#cloud-services-credits)
   - [Total Credits](#total-credits)
   - [Credit Pricing](#credit-pricing)
2. [Virtual Warehouses](#virtual-warehouses)
   - [What is a Warehouse?](#what-is-a-warehouse)
   - [Warehouse Sizes](#warehouse-sizes)
   - [Multi-Cluster Warehouses](#multi-cluster-warehouses)
   - [Auto-Suspend & Auto-Resume](#auto-suspend--auto-resume)
   - [Scaling Policy](#scaling-policy)
   - [Warehouse States](#warehouse-states)
3. [Query Performance Metrics](#query-performance-metrics)
   - [Execution Time](#execution-time)
   - [Queue Time](#queue-time)
   - [Compilation Time](#compilation-time)
   - [Bytes Scanned](#bytes-scanned)
   - [Rows Produced](#rows-produced)
   - [Partitions Scanned](#partitions-scanned)
   - [Spilling (Local & Remote)](#spilling-local--remote)
4. [Storage Concepts](#storage-concepts)
   - [Active Storage](#active-storage)
   - [Time Travel Storage](#time-travel-storage)
   - [Fail-safe Storage](#fail-safe-storage)
5. [Concurrency & Load Metrics](#concurrency--load-metrics)
   - [Running Queries](#running-queries)
   - [Queued Queries](#queued-queries)
   - [Blocked Queries](#blocked-queries)
6. [ACCOUNT_USAGE Views](#account_usage-views)
7. [Common Bottlenecks Explained](#common-bottlenecks-explained)
8. [Optimization Glossary](#optimization-glossary)

---

## Snowflake Credit System

### What is a Credit?

A **credit** is Snowflake's unit of billing for compute resources. Think of it like a "compute token" - you consume credits whenever your virtual warehouses are running and processing queries.

```
1 Credit = 1 hour of compute on an X-Small warehouse
```

**Key Points:**
- Credits are consumed only when warehouses are **running** (not suspended)
- Larger warehouses consume more credits per hour
- Credits are billed per-second with a 60-second minimum
- You don't consume credits for storage (that's billed separately by TB)

### Compute Credits

**Compute credits** are consumed by your virtual warehouses when executing queries. This is typically 90-95% of your total credit consumption.

| Warehouse Size | Credits per Hour |
|----------------|------------------|
| X-Small        | 1                |
| Small          | 2                |
| Medium         | 4                |
| Large          | 8                |
| X-Large        | 16               |
| 2X-Large       | 32               |
| 3X-Large       | 64               |
| 4X-Large       | 128              |
| 5X-Large       | 256              |
| 6X-Large       | 512              |

**Example:**
```
A LARGE warehouse running for 30 minutes consumes:
8 credits/hour × 0.5 hours = 4 credits
```

**In the API Response:**
```json
{
  "warehouse_name": "ANALYTICS_WH",
  "compute_credits": 845.20,    // Credits from query execution
  "total_credits": 892.45
}
```

### Cloud Services Credits

**Cloud services credits** are consumed by Snowflake's background services that support your operations:

| Service | Description |
|---------|-------------|
| **Authentication** | Login and session management |
| **Infrastructure Management** | Metadata operations, access control |
| **Query Parsing & Optimization** | SQL compilation and query planning |
| **Metadata Operations** | SHOW, DESCRIBE, LIST commands |
| **Result Set Caching** | Query result cache management |

**Important:** Snowflake provides a **10% allowance** - you're only charged for cloud services that exceed 10% of your daily compute credits.

**Example:**
```
Daily compute credits: 100
Cloud services used: 8 credits
Allowance (10%): 10 credits
Billed cloud services: 0 credits (8 < 10)

Daily compute credits: 100
Cloud services used: 15 credits
Allowance (10%): 10 credits
Billed cloud services: 5 credits (15 - 10)
```

**In the API Response:**
```json
{
  "warehouse_name": "ANALYTICS_WH",
  "cloud_services_credits": 47.25,  // Background services
  "compute_credits": 845.20
}
```

### Total Credits

**Total credits** = Compute Credits + Cloud Services Credits

This represents your complete compute billing for a warehouse or time period.

**In the API Response:**
```json
{
  "total_credits_30d": 1542.75,  // All credits consumed in 30 days
  "total_credits_7d": 387.25     // All credits consumed in 7 days
}
```

### Credit Pricing

Credit prices vary by cloud provider, region, and Snowflake edition:

| Edition | Approximate Price per Credit (USD) |
|---------|-----------------------------------|
| Standard | $2.00 - $2.50 |
| Enterprise | $3.00 - $3.70 |
| Business Critical | $4.00 - $5.00 |

**To estimate costs:**
```
Monthly Cost = Total Credits × Price per Credit

Example: 1,500 credits × $3.00 = $4,500/month
```

---

## Virtual Warehouses

### What is a Warehouse?

A **virtual warehouse** is a cluster of compute resources that executes your SQL queries. Key characteristics:

- **Independent scaling** - Each warehouse scales separately
- **Isolated workloads** - Queries in one warehouse don't affect others
- **On-demand** - Start and stop as needed (no queries = no cost when suspended)
- **Instant provisioning** - Warehouses start in seconds

**Analogy:** Think of a warehouse like a "team of workers." A larger warehouse has more workers who can process your data faster.

### Warehouse Sizes

Warehouse size determines compute power and credit consumption:

| Size | Credits/Hour | Relative Power | Best For |
|------|--------------|----------------|----------|
| X-Small | 1 | 1x | Light queries, development |
| Small | 2 | 2x | Small datasets, simple analytics |
| Medium | 4 | 4x | Moderate workloads |
| Large | 8 | 8x | Production analytics, BI tools |
| X-Large | 16 | 16x | Heavy ETL, complex joins |
| 2X-Large | 32 | 32x | Large data transformations |
| 3X-Large+ | 64+ | 64x+ | Massive datasets, data science |

**In the API Response:**
```json
{
  "warehouse_name": "ANALYTICS_WH",
  "warehouse_size": "LARGE",      // Size category
  "state": "STARTED"              // Currently running
}
```

### Multi-Cluster Warehouses

A **multi-cluster warehouse** can automatically spin up additional clusters to handle concurrent query load.

```
Single Cluster:     [Cluster 1] → Max 8 concurrent queries
                    
Multi-Cluster:      [Cluster 1] → 8 queries
(max_clusters=3)    [Cluster 2] → 8 queries (auto-scaled)
                    [Cluster 3] → 8 queries (auto-scaled)
                    = Up to 24 concurrent queries
```

**Configuration Parameters:**

| Parameter | Description |
|-----------|-------------|
| `min_cluster_count` | Minimum clusters always running (1 = standard) |
| `max_cluster_count` | Maximum clusters that can scale up to |

**In the API Response:**
```json
{
  "warehouse_name": "ANALYTICS_WH",
  "min_cluster_count": 1,    // Always have at least 1 cluster
  "max_cluster_count": 4,    // Can scale up to 4 clusters
  "scaling_policy": "STANDARD"
}
```

### Auto-Suspend & Auto-Resume

**Auto-Suspend** automatically suspends (stops) a warehouse after a period of inactivity to save credits.

**Auto-Resume** automatically starts a suspended warehouse when a query arrives.

| Setting | Recommendation |
|---------|----------------|
| 60 seconds | ETL/batch warehouses with irregular usage |
| 300 seconds (5 min) | General purpose, BI tools |
| 600 seconds (10 min) | Interactive dashboards with active users |
| Never (0) | Continuous workloads only |

**In the API Response:**
```json
{
  "warehouse_name": "ETL_WH",
  "auto_suspend_seconds": 60,   // Suspend after 60 seconds idle
  "auto_resume": true           // Start automatically on query
}
```

**Cost Impact Example:**
```
Warehouse: LARGE (8 credits/hour)
Queries: 10 minutes of work, then 50 minutes idle

With auto_suspend = 60 seconds:
  Billed time: ~11 minutes = 1.47 credits

With auto_suspend = never:
  Billed time: 60 minutes = 8 credits

Savings: 6.53 credits (82% reduction!)
```

### Scaling Policy

For multi-cluster warehouses, the **scaling policy** determines how aggressively clusters are added:

| Policy | Behavior |
|--------|----------|
| **STANDARD** | Adds clusters only when queries start queuing. Conservative, cost-optimized. |
| **ECONOMY** | Waits longer before adding clusters. More queuing, lower cost. |

**In the API Response:**
```json
{
  "scaling_policy": "STANDARD"
}
```

### Warehouse States

| State | Description | Billing |
|-------|-------------|---------|
| **STARTED** | Running and ready for queries | Consuming credits |
| **SUSPENDED** | Stopped, no compute resources | No credits |
| **RESIZING** | Changing size (up or down) | Credits at new size |
| **RESUMING** | Starting up from suspended | Credits once started |

**In the API Response:**
```json
{
  "state": "STARTED"   // or "SUSPENDED"
}
```

---

## Query Performance Metrics

### Execution Time

**Execution time** is how long a query took to run, from start to finish.

```
Total Duration = Queue Time + Execution Time
```

| Metric | What It Measures |
|--------|------------------|
| `execution_time_sec` | Actual processing time |
| `total_elapsed_time` | Queue time + execution time |

**In the API Response:**
```json
{
  "query_id": "01b2c3d4-...",
  "execution_time_sec": 342.5,  // 5 minutes 42 seconds
  "start_time": "2025-01-20T14:32:15Z",
  "end_time": "2025-01-20T14:38:17Z"
}
```

**Performance Guidelines:**
- < 1 second: Excellent (likely cached or small data)
- 1-10 seconds: Good for moderate queries
- 10-60 seconds: Acceptable for complex analytics
- \> 60 seconds: Consider optimization

### Queue Time

**Queue time** is how long a query waited before execution began. This happens when all warehouse resources are busy.

**Causes of Queue Time:**
1. All query slots are occupied (concurrency limit reached)
2. Warehouse is starting up (resuming from suspended)
3. Resource contention from concurrent queries

**In the API Response:**
```json
{
  "queued_time_sec": 12.5,     // Waited 12.5 seconds
  "execution_time_sec": 3.2    // Then ran for 3.2 seconds
}
```

**Red Flags:**
- Average queue time > 5 seconds: Consider larger warehouse or multi-cluster
- Frequent queuing: Indicates concurrency bottleneck

### Compilation Time

**Compilation time** is how long Snowflake spent parsing and optimizing your SQL before execution.

**What Happens During Compilation:**
1. SQL parsing and validation
2. Query optimization and planning
3. Code generation for execution

**In the API Response:**
```json
{
  "compilation_time_sec": 12.5,    // Time to compile
  "execution_time_sec": 45.2,      // Time to execute
  "compilation_percentage": 27.7   // % of total time spent compiling
}
```

**High Compilation Time Causes:**
- Very complex queries with many joins
- Queries with hundreds of columns
- Views with deep nesting
- First execution of a new query (not cached)

**Optimization Tips:**
- Simplify complex queries
- Use materialized views for repeated patterns
- Reduce number of referenced columns

### Bytes Scanned

**Bytes scanned** is the amount of data Snowflake read from storage to execute your query.

```
bytes_scanned = Amount of data read from disk/cache
bytes_scanned_gb = bytes_scanned / 1,073,741,824
```

**Why It Matters:**
- Directly correlates with query cost and duration
- High bytes scanned may indicate missing partition pruning
- Full table scans have very high bytes scanned

**In the API Response:**
```json
{
  "bytes_scanned": 52345678901,   // Raw bytes
  "bytes_scanned_gb": 48.75       // Converted to GB
}
```

**Optimization Tips:**
- Add WHERE clauses on partitioned columns (usually date)
- Select only needed columns (avoid SELECT *)
- Use clustering keys effectively

### Rows Produced

**Rows produced** is the number of rows returned by the query.

**In the API Response:**
```json
{
  "rows_produced": 1523456   // 1.5 million rows returned
}
```

**Performance Insight:**
```
bytes_scanned: 50 GB
rows_produced: 100

This ratio suggests heavy filtering - good partition pruning!

bytes_scanned: 50 GB  
rows_produced: 50,000,000

This ratio suggests a full table scan - needs optimization!
```

### Partitions Scanned

**Partitions** are how Snowflake organizes data for efficient access. Each partition is a ~16 MB block of data.

| Metric | Description |
|--------|-------------|
| `partitions_scanned` | Number of partitions read |
| `partitions_total` | Total partitions in the table |

**In the API Response:**
```json
{
  "partitions_scanned": 152,     // Read 152 partitions
  "partitions_total": 15234     // Table has 15,234 total
}
```

**Partition Pruning Efficiency:**
```
Efficiency = 1 - (partitions_scanned / partitions_total)

Example: 1 - (152 / 15234) = 99% pruning efficiency ✓

Example: 1 - (15000 / 15234) = 1.5% efficiency ✗ (full scan!)
```

### Spilling (Local & Remote)

**Spilling** occurs when a query needs more memory than available, forcing data to be written to disk.

| Type | Location | Performance Impact |
|------|----------|-------------------|
| **Local Spill** | Warehouse's local SSD | Moderate slowdown (2-3x) |
| **Remote Spill** | Cloud storage (S3/Azure/GCS) | Severe slowdown (10x+) |

**In the API Response:**
```json
{
  "local_spill_gb": 2.5,    // Spilled 2.5 GB to local SSD
  "remote_spill_gb": 0.8    // Spilled 0.8 GB to cloud storage
}
```

**Causes:**
- Warehouse too small for data volume
- Large sorts, joins, or aggregations
- Inefficient query patterns

**Solutions:**
- Use a larger warehouse
- Optimize query to reduce intermediate data
- Add filters earlier in the query

---

## Storage Concepts

### Active Storage

**Active storage** is the current size of your data in Snowflake tables.

**In the API Response:**
```json
{
  "database_name": "PRODUCTION_DB",
  "average_bytes": 1523456789012,  // ~1.5 TB
  "storage_tb": 1.39               // Converted
}
```

**Billing:** Billed per TB per month (varies by region, typically $23-$40/TB/month)

### Time Travel Storage

**Time Travel** allows you to query historical data and recover from mistakes. Snowflake stores previous versions of your data.

**Retention Periods:**
- Standard Edition: 1 day
- Enterprise Edition: Up to 90 days

**Storage Impact:**
- Every UPDATE/DELETE creates a new version
- High-churn tables use more Time Travel storage
- Dropped tables count toward Time Travel

### Fail-safe Storage

**Fail-safe** is Snowflake's disaster recovery protection - a 7-day period of non-queryable data backup.

**In the API Response:**
```json
{
  "failsafe_bytes": 152345678901,
  "failsafe_tb": 0.14
}
```

**Key Points:**
- Always 7 days (cannot be changed)
- Not accessible by users (Snowflake support only)
- Additional storage cost
- Kicks in after Time Travel period ends

**Storage Timeline:**
```
Day 0: Data modified
Days 0-7: Time Travel (queryable, recoverable by you)
Days 7-14: Fail-safe (Snowflake recovery only)
Day 14+: Data permanently deleted
```

---

## Concurrency & Load Metrics

### Running Queries

**Running queries** are actively executing on the warehouse.

Each warehouse size has a default concurrency limit:

| Warehouse Size | Max Concurrent Queries |
|----------------|----------------------|
| X-Small to Large | 8 |
| X-Large to 4X-Large | 16 |
| 5X-Large+ | 32+ |

**In the API Response:**
```json
{
  "avg_running": 3.5,   // Average queries running
  "max_running": 8      // Peak concurrent queries
}
```

### Queued Queries

**Queued queries** are waiting for a slot to execute.

**In the API Response:**
```json
{
  "avg_queued": 0.8,    // Average queries waiting
  "max_queued": 12      // Peak queue depth
}
```

**Interpretation:**
- `avg_queued` > 0: Some queries experiencing delays
- `avg_queued` > 2: Significant concurrency issue
- `max_queued` > 10: Consider multi-cluster or larger warehouse

### Blocked Queries

**Blocked queries** are waiting for locks held by other transactions (usually DML operations).

**In the API Response:**
```json
{
  "avg_blocked": 0.1    // Average queries blocked
}
```

**Common Causes:**
- Concurrent INSERT/UPDATE/DELETE on same table
- Long-running transactions holding locks
- DDL operations (ALTER TABLE, etc.)

---

## ACCOUNT_USAGE Views

The Resource Monitor queries Snowflake's **ACCOUNT_USAGE** schema, which provides historical metadata about your account.

| View | Data Provided | Latency |
|------|--------------|---------|
| `WAREHOUSE_METERING_HISTORY` | Credit consumption by warehouse | 1-2 hours |
| `WAREHOUSE_LOAD_HISTORY` | Concurrency metrics (running/queued) | 1-2 hours |
| `QUERY_HISTORY` | Detailed query execution data | 45 minutes |
| `DATABASE_STORAGE_USAGE_HISTORY` | Storage by database over time | 1-2 hours |
| `WAREHOUSES` | Current warehouse configurations | Real-time |

**Important:** ACCOUNT_USAGE data has a **45-minute to 2-hour latency**. You won't see real-time data in the monitor.

**Required Privileges:**
```sql
-- Grant access to ACCOUNT_USAGE
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE monitor_role;
```

---

## Common Bottlenecks Explained

### Queuing Bottleneck

**Symptom:** High `avg_queue_time_sec` in queries

**Cause:** More queries than the warehouse can handle concurrently

**Solutions:**
1. Enable multi-cluster warehouses
2. Increase warehouse size
3. Distribute workloads across multiple warehouses

### Spilling Bottleneck

**Symptom:** High `local_spill_gb` or `remote_spill_gb`

**Cause:** Queries need more memory than available

**Solutions:**
1. Use larger warehouse
2. Optimize queries to reduce memory usage
3. Add filters to reduce data volume

### Compilation Bottleneck

**Symptom:** High `compilation_time_sec` relative to execution

**Cause:** Complex queries requiring extensive optimization

**Solutions:**
1. Simplify query structure
2. Reduce number of joins
3. Use stored procedures for complex logic

### Full Scan Bottleneck

**Symptom:** `partitions_scanned` ≈ `partitions_total`

**Cause:** Missing or ineffective clustering, no partition pruning

**Solutions:**
1. Add clustering keys
2. Include partition columns in WHERE clause
3. Use micro-partitioning effectively

---

## Optimization Glossary

| Term | Definition |
|------|------------|
| **Clustering Key** | Column(s) used to organize data physically for faster queries |
| **Micro-partition** | Snowflake's storage unit (~16 MB compressed) |
| **Partition Pruning** | Skipping irrelevant partitions based on filters |
| **Result Cache** | Cached query results reused for identical queries (24 hours) |
| **Metadata Cache** | Cached table metadata for faster planning |
| **Data Cache** | Warehouse-local SSD cache of frequently accessed data |
| **Query Profile** | Detailed execution plan and metrics for a query |
| **Serverless** | Snowflake-managed compute (e.g., Snowpipe, Tasks) |
| **Credit Quota** | Spending limit set on resource monitors |
| **Resource Monitor** | Snowflake feature to track and limit credit usage |

---

## Quick Reference Card

### Credit Cost Estimation

```
Hourly Cost = Warehouse Size Credits × $Credit_Price

Daily Cost = Hourly Cost × Active Hours

Monthly Estimate = Daily Cost × Working Days
```

### Performance Red Flags

| Metric | Warning | Critical |
|--------|---------|----------|
| Queue Time | > 2 sec avg | > 10 sec avg |
| Compilation Time | > 5 sec | > 20 sec |
| Local Spill | > 1 GB | > 10 GB |
| Remote Spill | Any | > 1 GB |
| Partition Pruning | < 50% | < 10% |

### Warehouse Sizing Guide

| Use Case | Recommended Size |
|----------|------------------|
| Development/Testing | X-Small to Small |
| Light BI Queries | Small to Medium |
| Production Analytics | Medium to Large |
| Heavy ETL | Large to X-Large |
| Data Science / ML | X-Large to 2X-Large |
| Massive Transformations | 2X-Large+ |

---

## Need More Help?

- **Snowflake Documentation:** https://docs.snowflake.com
- **Query Profile:** Run any query, then click "Query Profile" in the UI
- **EXPLAIN Plans:** Use `EXPLAIN SELECT ...` to see query plans
- **Support:** Contact your Snowflake account team
