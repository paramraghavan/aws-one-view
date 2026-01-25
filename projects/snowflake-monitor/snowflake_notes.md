In the `SnowflakeMonitor` class, queries are primarily targeted at the `SNOWFLAKE.ACCOUNT_USAGE` shared database to
extract metadata about usage, costs, and performance.

Below are the unique queries extracted from the class, grouped by their analytical purpose. Similar or redundant
queries (like those that aggregate daily credits in multiple methods) have been consolidated for clarity.

### 1. Account Consumption & Cost Metrics

These queries calculate the "bottom line" for credit and storage usage across the entire account.

* **Total Credits and Active Warehouses:**

```sql
SELECT COALESCE(SUM(CREDITS_USED), 0) as TOTAL_CREDITS, COUNT(DISTINCT WAREHOUSE_NAME) as ACTIVE_WAREHOUSES
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())

```

**Explanation:** Aggregates total credit consumption and counts distinct warehouses active over the last 30 days.

* **Warehouse Cost Breakdown:**

```sql
SELECT WAREHOUSE_NAME, SUM(CREDITS_USED) as TOTAL_CREDITS, SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS, SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
GROUP BY WAREHOUSE_NAME

```

**Explanation:** Pinpoints which warehouses are driving costs, specifically distinguishing between "Compute" (virtual
warehouse power) and "Cloud Services" (metadata, management).

* **Total Account Storage:**

```sql
SELECT COALESCE(SUM(AVERAGE_DATABASE_BYTES + AVERAGE_FAILSAFE_BYTES), 0) / POWER(1024, 4) as TOTAL_STORAGE_TB
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE USAGE_DATE = (SELECT MAX(USAGE_DATE) FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY)

```

**Explanation:** Calculates the current total storage footprint in Terabytes, including "Fail-safe" bytes which are
often overlooked but billable.

### 2. Performance & Bottleneck Analysis

These queries identify technical inefficiencies that slow down the system or indicate resource contention.

* **Queuing Analysis (Resource Contention):**

```sql
SELECT WAREHOUSE_NAME, AVG(QUEUED_OVERLOAD_TIME) / 1000 as AVG_QUEUE_TIME_SEC, COUNT(*) as TOTAL_QUERIES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE QUEUED_OVERLOAD_TIME > 0
GROUP BY WAREHOUSE_NAME

```

**Explanation:** Identifies warehouses where queries are waiting to be executed because the warehouse is at capacity,
signaling a need for resizing or multi-cluster scaling.

* **Disk Spilling Detection (Memory Pressure):**

```sql
SELECT WAREHOUSE_NAME, SUM(BYTES_SPILLED_TO_LOCAL_STORAGE) as GB_SPILLED_LOCAL, SUM(BYTES_SPILLED_TO_REMOTE_STORAGE) as GB_SPILLED_REMOTE
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE BYTES_SPILLED_TO_LOCAL_STORAGE > 0 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0
GROUP BY WAREHOUSE_NAME

```

**Explanation:** Detects when a warehouse runs out of RAM and must "spill" data to disk. Local spilling is slow; remote
spilling is very slow and usually indicates the warehouse size is too small for the data volume.

* **High Compilation Time:**

```sql
SELECT WAREHOUSE_NAME, COUNT(*) as HIGH_COMPILE_QUERIES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE COMPILATION_TIME > 5000
GROUP BY WAREHOUSE_NAME

```

**Explanation:** Flags queries that take more than 5 seconds just to plan/compile, often due to massive metadata or
extremely complex views.

### 3. Query Efficiency & Optimization

These queries act as a "SQL code review" to find expensive or poorly written queries.

* **Full Table Scan Identification:**

```sql
SELECT QUERY_ID, QUERY_TEXT, ROUND((PARTITIONS_SCANNED / NULLIF(PARTITIONS_TOTAL, 0)) * 100, 1) as PARTITION_SCAN_PCT
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE PARTITIONS_TOTAL > 100 AND PARTITIONS_SCANNED >= PARTITIONS_TOTAL * 0.9

```

**Explanation:** Targets queries scanning >90% of a large table's partitions. This suggests missing filters or the need
for better "Clustering Keys."

* **Query Fingerprinting:**

```sql
SELECT QUERY_PARAMETERIZED_HASH, COUNT(*), AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
GROUP BY QUERY_PARAMETERIZED_HASH

```

**Explanation:** Groups logically identical queries (different parameters, same structure) to identify repetitive, heavy
patterns that offer the best "bang for your buck" if optimized.

### 4. Storage & Data Management

These queries monitor the health and "freshness" of the data stored in Snowflake.

* **Data Freshness (Stale Tables):**

```sql
SELECT TABLE_NAME, LAST_ALTERED, DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) as HOURS_SINCE_UPDATE
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
WHERE TABLE_TYPE = 'BASE TABLE'

```

**Explanation:** Tracks when tables were last modified to categorize data as "Fresh," "Stale," or "Very Stale," helping
to identify broken data pipelines.

* **Table Storage Details:**

```sql
SELECT TABLE_NAME, ACTIVE_BYTES, TIME_TRAVEL_BYTES, FAILSAFE_BYTES
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLE_STORAGE_METRICS

```

**Explanation:** Breaks down storage costs per table, specifically identifying how much you are paying for "Time Travel"
and "Fail-safe" history.

### 5. Security & User Analytics

These queries track system access and potential security risks.

* **Login History & Failures:**

```sql
SELECT USER_NAME, COUNT(*) as LOGIN_COUNT, COUNT(CASE WHEN IS_SUCCESS = 'NO' THEN 1 END) as FAILED_LOGINS
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
GROUP BY USER_NAME

```

**Explanation:** Summarizes login activity and flags failed attempts per user, which can indicate brute-force attempts
or expired service account credentials.