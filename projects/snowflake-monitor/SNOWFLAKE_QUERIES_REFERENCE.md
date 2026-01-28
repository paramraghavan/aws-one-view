# Snowflake Monitor - Query Reference Guide

This document explains all SQL queries used in the Snowflake Monitor application, the Snowflake views they query, and where each is used in the dashboard.

---

## Table of Contents

1. [Snowflake System Views Used](#snowflake-system-views-used)
2. [Overview Section Queries](#1-overview-section)
3. [Needs Attention Section Queries](#2-needs-attention-section)
4. [Database Deep Dive Queries](#3-database-deep-dive-section)
5. [Warehouses Section Queries](#4-warehouses-section)
6. [Users & Security Section Queries](#5-users--security-section)

---

## Snowflake System Views Used

All queries use the `SNOWFLAKE.ACCOUNT_USAGE` schema, which provides historical data with 45-minute to 2-hour latency.

| View | Purpose | Latency |
|------|---------|---------|
| `WAREHOUSE_METERING_HISTORY` | Credit consumption per warehouse | ~2 hours |
| `QUERY_HISTORY` | All executed queries with performance metrics | ~45 min |
| `DATABASE_STORAGE_USAGE_HISTORY` | Storage by database over time | ~2 hours |
| `WAREHOUSE_LOAD_HISTORY` | Concurrency and queuing metrics | ~2 hours |
| `LOGIN_HISTORY` | User login events and failures | ~2 hours |
| `TABLES` | Table metadata (row counts, sizes, clustering) | ~2 hours |
| `TABLE_STORAGE_METRICS` | Detailed storage breakdown per table | ~2 hours |
| `DATABASES` | Database metadata | ~2 hours |

**Note:** `SHOW WAREHOUSES` command is used for real-time warehouse configurations.

---

## 1. Overview Section

The Overview section displays high-level metrics at a glance.

### 1.1 Total Credits Used (30 days)

```sql
SELECT 
    COALESCE(SUM(CREDITS_USED), 0) as TOTAL_CREDITS,
    COUNT(DISTINCT WAREHOUSE_NAME) as ACTIVE_WAREHOUSES
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
```

**Dashboard Location:** Overview → "Total Credits (30d)" card  
**Purpose:** Shows total credit consumption and how many warehouses were active

---

### 1.2 Total Storage

```sql
SELECT 
    COALESCE(SUM(AVERAGE_DATABASE_BYTES + AVERAGE_FAILSAFE_BYTES), 0) / POWER(1024, 4) as TOTAL_STORAGE_TB
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE USAGE_DATE = (SELECT MAX(USAGE_DATE) FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY)
```

**Dashboard Location:** Overview → "Storage" card  
**Purpose:** Total storage including fail-safe (in TB)

---

### 1.3 Query Count & Performance (24 hours)

```sql
SELECT 
    COUNT(*) as QUERY_COUNT,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_TIME_SEC
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
```

**Dashboard Location:** Overview → "Queries (24h)" and "Avg Query Time" cards  
**Purpose:** Recent query activity and performance

---

### 1.4 Failed Queries (24 hours)

```sql
SELECT COUNT(*) as FAILED_QUERIES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())
AND EXECUTION_STATUS = 'FAIL'
```

**Dashboard Location:** Overview → "Failed Queries" card (highlighted in red)  
**Purpose:** Identify query failures for investigation

---

### 1.5 Credit Usage Trend

```sql
SELECT 
    DATE_TRUNC('day', START_TIME) as DATE,
    SUM(CREDITS_USED) as TOTAL_CREDITS,
    SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
    SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY DATE_TRUNC('day', START_TIME)
ORDER BY DATE
```

**Dashboard Location:** Overview → "Credit Usage Trend (30 days)" chart  
**Purpose:** Visualize daily credit consumption patterns

---

### 1.6 Storage Breakdown (Per-Database with DB/Failsafe Details)

```sql
SELECT 
    DATABASE_NAME,
    AVERAGE_DATABASE_BYTES / POWER(1024, 3) as DATABASE_GB,
    AVERAGE_FAILSAFE_BYTES / POWER(1024, 3) as FAILSAFE_GB,
    (AVERAGE_DATABASE_BYTES + AVERAGE_FAILSAFE_BYTES) / POWER(1024, 3) as TOTAL_GB
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE USAGE_DATE = (SELECT MAX(USAGE_DATE) FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY)
ORDER BY TOTAL_GB DESC
```

**Dashboard Location:** Overview → "Storage Breakdown" section  
**Purpose:** Shows storage distribution across databases with detailed breakdown

**Display Components:**
1. **Summary Boxes** (top row):
   - **Total DB Storage** (cyan) - Sum of all active database storage
   - **Total Failsafe** (orange) - Sum of all fail-safe storage (7-day recovery)

2. **Doughnut Chart** - Top 8 databases by total storage
   - **On Hover:** Shows detailed breakdown per database:
     - Total storage for that database
     - DB storage (active data)
     - Failsafe storage (recovery data)

---

## 2. Needs Attention Section

This section consolidates bottlenecks, issues, and optimization opportunities.

### 2.1 Query Queuing Analysis

```sql
SELECT 
    WAREHOUSE_NAME,
    SUM(CASE WHEN QUEUED_OVERLOAD_TIME > 0 THEN 1 ELSE 0 END) as QUEUED_QUERIES,
    AVG(QUEUED_OVERLOAD_TIME) / 1000 as AVG_QUEUE_TIME_SEC,
    MAX(QUEUED_OVERLOAD_TIME) / 1000 as MAX_QUEUE_TIME_SEC,
    COUNT(*) as TOTAL_QUERIES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME
HAVING QUEUED_QUERIES > 0
ORDER BY QUEUED_QUERIES DESC
```

**Dashboard Location:** Needs Attention → Critical/Warning issues  
**Purpose:** Identify warehouses where queries are waiting (need more capacity)

**Key Metrics:**
- `QUEUED_OVERLOAD_TIME` - Time spent waiting due to warehouse being too busy
- High queue times (>10s avg) indicate need for larger warehouse or more clusters

---

### 2.2 Memory Spilling Analysis

```sql
SELECT 
    WAREHOUSE_NAME,
    COUNT(*) as SPILLING_QUERIES,
    SUM(BYTES_SPILLED_TO_LOCAL_STORAGE) / POWER(1024, 3) as GB_SPILLED_LOCAL,
    SUM(BYTES_SPILLED_TO_REMOTE_STORAGE) / POWER(1024, 3) as GB_SPILLED_REMOTE
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND (BYTES_SPILLED_TO_LOCAL_STORAGE > 0 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0)
GROUP BY WAREHOUSE_NAME
ORDER BY SPILLING_QUERIES DESC
```

**Dashboard Location:** Needs Attention → Critical/Warning issues  
**Purpose:** Identify memory-constrained queries

**Key Concepts:**
- **Local Spilling** - Data spilled to warehouse local SSD (slower but not too expensive)
- **Remote Spilling** - Data spilled to S3/Azure Blob (EXPENSIVE and slow!)
- Solution: Use larger warehouse or optimize query

---

### 2.3 Query Compilation Issues

```sql
SELECT 
    WAREHOUSE_NAME,
    COUNT(*) as HIGH_COMPILE_QUERIES,
    AVG(COMPILATION_TIME) / 1000 as AVG_COMPILE_SEC,
    MAX(COMPILATION_TIME) / 1000 as MAX_COMPILE_SEC
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND COMPILATION_TIME > 5000  -- More than 5 seconds
GROUP BY WAREHOUSE_NAME
ORDER BY HIGH_COMPILE_QUERIES DESC
```

**Dashboard Location:** Needs Attention → Optimization opportunities  
**Purpose:** Find queries with complex compilation (often indicates inefficient SQL)

---

### 2.4 Failed Queries by Error

```sql
SELECT 
    ERROR_CODE,
    ERROR_MESSAGE,
    COUNT(*) as FAILURE_COUNT
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND EXECUTION_STATUS = 'FAIL'
GROUP BY ERROR_CODE, ERROR_MESSAGE
ORDER BY FAILURE_COUNT DESC
LIMIT 10
```

**Dashboard Location:** Needs Attention → Critical issues  
**Purpose:** Group failures by error type to identify patterns

---

### 2.5 Full Table Scan Detection

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    DATABASE_NAME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
    PARTITIONS_SCANNED,
    PARTITIONS_TOTAL,
    ROUND((PARTITIONS_SCANNED / NULLIF(PARTITIONS_TOTAL, 0)) * 100, 1) as PARTITION_SCAN_PCT
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND PARTITIONS_TOTAL > 100
AND PARTITIONS_SCANNED >= PARTITIONS_TOTAL * 0.9  -- Scanning 90%+ of partitions
AND TOTAL_ELAPSED_TIME > 30000  -- More than 30 seconds
ORDER BY BYTES_SCANNED DESC
LIMIT 20
```

**Dashboard Location:** Needs Attention → "Top 10 Queries to Fix" table  
**Purpose:** Find queries that scan entire tables (need clustering keys)

**Key Metrics:**
- `PARTITIONS_SCANNED` vs `PARTITIONS_TOTAL` - If scanning 90%+ of partitions, it's a full scan
- Solution: Add clustering key on filter columns (usually date/timestamp)

---

### 2.6 Memory Spilling Queries

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
    BYTES_SPILLED_TO_LOCAL_STORAGE / POWER(1024, 3) as LOCAL_SPILL_GB,
    BYTES_SPILLED_TO_REMOTE_STORAGE / POWER(1024, 3) as REMOTE_SPILL_GB
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND (BYTES_SPILLED_TO_LOCAL_STORAGE > 5368709120 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0)
ORDER BY BYTES_SPILLED_TO_REMOTE_STORAGE DESC
LIMIT 20
```

**Dashboard Location:** Needs Attention → "Top 10 Queries to Fix" table  
**Purpose:** Find specific queries causing expensive spilling

---

### 2.7 SELECT * Detection

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND QUERY_TYPE = 'SELECT'
AND QUERY_TEXT ILIKE '%SELECT *%FROM%'
AND BYTES_SCANNED > 1073741824  -- More than 1 GB
ORDER BY BYTES_SCANNED DESC
LIMIT 20
```

**Dashboard Location:** Needs Attention → "Top 10 Queries to Fix" table  
**Purpose:** Find inefficient SELECT * queries on large tables

---

### 2.8 Warehouse Sizing Recommendations

```sql
SELECT 
    WAREHOUSE_NAME,
    AVG(AVG_RUNNING) as AVG_CONCURRENT
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME
HAVING AVG_CONCURRENT < 0.2  -- Less than 20% utilized
```

**Dashboard Location:** Needs Attention → Recommendations  
**Purpose:** Identify oversized warehouses (low concurrency = wasting money)

---

### 2.9 High Queue Time Recommendations

```sql
SELECT 
    WAREHOUSE_NAME,
    AVG(QUEUED_OVERLOAD_TIME) / 1000 as AVG_QUEUE_SEC,
    COUNT(*) as AFFECTED_QUERIES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND QUEUED_OVERLOAD_TIME > 10000  -- More than 10 seconds queued
GROUP BY WAREHOUSE_NAME
HAVING AFFECTED_QUERIES > 10
ORDER BY AVG_QUEUE_SEC DESC
```

**Dashboard Location:** Needs Attention → Recommendations  
**Purpose:** Find warehouses that need more capacity

---

## 3. Database Deep Dive Section

Select a specific database for detailed analysis.

### 3.1 Database List

```sql
SELECT 
    DATABASE_NAME,
    DATABASE_OWNER,
    CREATED,
    LAST_ALTERED,
    COMMENT
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASES
WHERE DELETED IS NULL
ORDER BY DATABASE_NAME
```

**Dashboard Location:** Database Deep Dive → Database dropdown  
**Purpose:** Populate the database selector

---

### 3.2 Database Overview Metrics

```sql
SELECT 
    COUNT(*) as TOTAL_QUERIES,
    COUNT(DISTINCT USER_NAME) as UNIQUE_USERS,
    COUNT(DISTINCT WAREHOUSE_NAME) as WAREHOUSES_USED,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_SEC,
    SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_QUERY_HOURS,
    SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED,
    COUNT(CASE WHEN EXECUTION_STATUS = 'FAIL' THEN 1 END) as FAILED_QUERIES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
```

**Dashboard Location:** Database Deep Dive → Overview metrics cards  
**Purpose:** Summary stats for selected database

---

### 3.3 Database Cost by Warehouse

```sql
SELECT 
    WAREHOUSE_NAME,
    MAX(WAREHOUSE_SIZE) as WAREHOUSE_SIZE,
    COUNT(*) as QUERY_COUNT,
    SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
    -- Estimate credits based on warehouse size
    SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 * 
        CASE MAX(WAREHOUSE_SIZE)
            WHEN 'X-Small' THEN 1
            WHEN 'Small' THEN 2
            WHEN 'Medium' THEN 4
            WHEN 'Large' THEN 8
            WHEN 'X-Large' THEN 16
            WHEN '2X-Large' THEN 32
            WHEN '3X-Large' THEN 64
            WHEN '4X-Large' THEN 128
            ELSE 4
        END as ESTIMATED_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME
ORDER BY TOTAL_HOURS DESC
```

**Dashboard Location:** Database Deep Dive → Cost Analysis tab → Warehouse Usage chart  
**Purpose:** Estimate credit attribution per warehouse for this database

**Note:** Credits are charged at warehouse level, not database level. This is an estimate based on query time × warehouse credit rate.

---

### 3.4 Database Cost by User

```sql
SELECT 
    USER_NAME,
    COUNT(*) as QUERY_COUNT,
    SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_SEC,
    SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY USER_NAME
ORDER BY TOTAL_HOURS DESC
LIMIT 20
```

**Dashboard Location:** Database Deep Dive → Cost Analysis tab → User cost table  
**Purpose:** Identify which users consume most resources on this database

---

### 3.5 Database Slow Queries

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    QUERY_TYPE,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
    EXECUTION_TIME / 1000 as EXECUTION_SEC,
    QUEUED_OVERLOAD_TIME / 1000 as QUEUE_SEC,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
    EXECUTION_STATUS
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
AND TOTAL_ELAPSED_TIME >= {threshold_sec * 1000}
ORDER BY TOTAL_ELAPSED_TIME DESC
LIMIT 100
```

**Dashboard Location:** Database Deep Dive → Performance tab → Slow Queries table  
**Purpose:** List queries exceeding duration threshold (clickable to see full SQL)

---

### 3.6 Database Query Patterns by Hour

```sql
SELECT 
    EXTRACT(HOUR FROM START_TIME) as HOUR_OF_DAY,
    COUNT(*) as QUERY_COUNT,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY EXTRACT(HOUR FROM START_TIME)
ORDER BY HOUR_OF_DAY
```

**Dashboard Location:** Database Deep Dive → Performance tab → Query Volume by Hour chart  
**Purpose:** Identify peak usage hours for this database

---

### 3.7 Database Query Types

```sql
SELECT 
    QUERY_TYPE,
    COUNT(*) as QUERY_COUNT,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_DURATION_SEC,
    SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY QUERY_TYPE
ORDER BY QUERY_COUNT DESC
```

**Dashboard Location:** Database Deep Dive → Performance tab → Query Types chart  
**Purpose:** Breakdown of SELECT/INSERT/UPDATE/DELETE etc.

---

### 3.8 Database Bottlenecks - Queued Queries

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
    QUEUED_OVERLOAD_TIME / 1000 as QUEUE_SEC,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
AND QUEUED_OVERLOAD_TIME > 5000  -- More than 5 seconds queued
ORDER BY QUEUED_OVERLOAD_TIME DESC
LIMIT 20
```

**Dashboard Location:** Database Deep Dive → Bottlenecks tab → Top Queued Queries list  
**Purpose:** Show specific queries that had to wait (clickable)

---

### 3.9 Database Full Scan Details with Clustering Suggestions

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
    PARTITIONS_SCANNED,
    PARTITIONS_TOTAL,
    ROUND((PARTITIONS_SCANNED / NULLIF(PARTITIONS_TOTAL, 0)) * 100, 1) as SCAN_PCT
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE DATABASE_NAME = '{database_name}'
AND PARTITIONS_TOTAL > 100
AND PARTITIONS_SCANNED >= PARTITIONS_TOTAL * 0.9
AND TOTAL_ELAPSED_TIME > 10000
ORDER BY BYTES_SCANNED DESC
LIMIT 20
```

**Dashboard Location:** Database Deep Dive → Bottlenecks tab → Tables to Cluster section  
**Purpose:** Identify tables needing clustering keys

The application parses QUERY_TEXT to extract:
- Table name from `FROM` clause
- Suggested clustering columns from `WHERE` clause (date/timestamp/ID columns)

---

### 3.10 Unclustered Large Tables

```sql
SELECT 
    TABLE_SCHEMA,
    TABLE_NAME,
    ROW_COUNT,
    BYTES / POWER(1024, 3) as SIZE_GB
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
WHERE TABLE_CATALOG = '{database_name}'
AND DELETED IS NULL
AND TABLE_TYPE = 'BASE TABLE'
AND CLUSTERING_KEY IS NULL
AND BYTES > 1073741824  -- More than 1 GB
ORDER BY BYTES DESC
LIMIT 10
```

**Dashboard Location:** Database Deep Dive → Bottlenecks tab → "Large Tables Without Clustering" alert  
**Purpose:** Proactively identify tables that should have clustering keys

---

### 3.11 Database Table Analysis

```sql
SELECT 
    TABLE_SCHEMA,
    TABLE_NAME,
    ROW_COUNT,
    BYTES / POWER(1024, 3) as SIZE_GB,
    CLUSTERING_KEY,
    CREATED,
    LAST_ALTERED,
    DATEDIFF('day', LAST_ALTERED, CURRENT_TIMESTAMP()) as DAYS_SINCE_UPDATE,
    CASE 
        WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 24 THEN 'Fresh'
        WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 168 THEN 'Recent'
        WHEN DATEDIFF('hour', LAST_ALTERED, CURRENT_TIMESTAMP()) < 720 THEN 'Stale'
        ELSE 'Very Stale'
    END as FRESHNESS
FROM SNOWFLAKE.ACCOUNT_USAGE.TABLES
WHERE TABLE_CATALOG = '{database_name}'
AND DELETED IS NULL
AND TABLE_TYPE = 'BASE TABLE'
ORDER BY BYTES DESC
LIMIT 100
```

**Dashboard Location:** Database Deep Dive → Tables tab  
**Purpose:** Show all tables with size, clustering status, and freshness

---

## 4. Warehouses Section

### 4.1 Warehouse Configurations

```sql
SHOW WAREHOUSES
```

**Dashboard Location:** Warehouses → Configuration table  
**Purpose:** Get real-time warehouse settings (size, auto-suspend, scaling policy)

**Note:** This uses SHOW command, not ACCOUNT_USAGE view, for real-time data.

---

### 4.2 Cluster Concurrency Metrics

```sql
SELECT 
    WAREHOUSE_NAME,
    DATE_TRUNC('hour', START_TIME) as HOUR,
    AVG(AVG_RUNNING) as AVG_CONCURRENT_QUERIES,
    MAX(AVG_RUNNING) as MAX_CONCURRENT_QUERIES,
    AVG(AVG_QUEUED_LOAD) as AVG_QUEUED,
    MAX(AVG_QUEUED_LOAD) as MAX_QUEUED,
    AVG(AVG_QUEUED_PROVISIONING) as AVG_QUEUED_PROVISIONING,
    AVG(AVG_BLOCKED) as AVG_BLOCKED
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
ORDER BY HOUR DESC
```

**Dashboard Location:** Warehouses → Cluster Concurrency chart  
**Purpose:** Visualize warehouse load over time

**Key Metrics:**
- `AVG_RUNNING` - Average concurrent queries executing
- `AVG_QUEUED_LOAD` - Average queries waiting due to load
- `AVG_QUEUED_PROVISIONING` - Average queries waiting for cluster to start
- `AVG_BLOCKED` - Average queries blocked by locks

---

## 5. Users & Security Section

### 5.1 Top Users by Resource Usage

```sql
SELECT 
    USER_NAME,
    COUNT(*) as QUERY_COUNT,
    SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_QUERY_SEC,
    SUM(BYTES_SCANNED) / POWER(1024, 4) as TB_SCANNED,
    COUNT(CASE WHEN EXECUTION_STATUS = 'FAIL' THEN 1 END) as FAILED_QUERIES,
    COUNT(DISTINCT WAREHOUSE_NAME) as WAREHOUSES_USED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY USER_NAME
ORDER BY TOTAL_HOURS DESC
LIMIT 25
```

**Dashboard Location:** Users & Security → Top Users table  
**Purpose:** Identify heaviest resource consumers

---

### 5.2 User Activity Trend

```sql
SELECT 
    DATE_TRUNC('day', START_TIME) as DATE,
    COUNT(DISTINCT USER_NAME) as ACTIVE_USERS,
    COUNT(*) as TOTAL_QUERIES
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY DATE_TRUNC('day', START_TIME)
ORDER BY DATE
```

**Dashboard Location:** Users & Security → Active Users Trend chart  
**Purpose:** Track user adoption over time

---

### 5.3 Queries by Role

```sql
SELECT 
    ROLE_NAME,
    COUNT(*) as QUERY_COUNT,
    COUNT(DISTINCT USER_NAME) as UNIQUE_USERS,
    SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600 as TOTAL_HOURS
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY ROLE_NAME
ORDER BY QUERY_COUNT DESC
LIMIT 15
```

**Dashboard Location:** Users & Security → Queries by Role chart  
**Purpose:** Understand which roles are most active

---

### 5.4 Login Summary

```sql
SELECT 
    USER_NAME,
    COUNT(*) as LOGIN_COUNT,
    COUNT(DISTINCT CLIENT_IP) as UNIQUE_IPS,
    MAX(EVENT_TIMESTAMP) as LAST_LOGIN,
    COUNT(CASE WHEN IS_SUCCESS = 'NO' THEN 1 END) as FAILED_LOGINS
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE EVENT_TIMESTAMP >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
GROUP BY USER_NAME
ORDER BY LOGIN_COUNT DESC
LIMIT 25
```

**Dashboard Location:** Users & Security → Login Summary table  
**Purpose:** Monitor user login patterns

---

### 5.5 Failed Login Attempts

```sql
SELECT 
    EVENT_TIMESTAMP,
    USER_NAME,
    CLIENT_IP,
    REPORTED_CLIENT_TYPE,
    ERROR_CODE,
    ERROR_MESSAGE
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE EVENT_TIMESTAMP >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
AND IS_SUCCESS = 'NO'
ORDER BY EVENT_TIMESTAMP DESC
LIMIT 50
```

**Dashboard Location:** Users & Security → Failed Login Attempts list  
**Purpose:** Security monitoring - detect brute force or compromised accounts

---

### 5.6 Login Activity by Hour

```sql
SELECT 
    EXTRACT(HOUR FROM EVENT_TIMESTAMP) as HOUR_OF_DAY,
    COUNT(*) as LOGIN_COUNT
FROM SNOWFLAKE.ACCOUNT_USAGE.LOGIN_HISTORY
WHERE EVENT_TIMESTAMP >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
AND IS_SUCCESS = 'YES'
GROUP BY EXTRACT(HOUR FROM EVENT_TIMESTAMP)
ORDER BY HOUR_OF_DAY
```

**Dashboard Location:** Users & Security → Login Activity by Hour chart  
**Purpose:** Understand when users typically log in

---

## Query Performance Tips

### Understanding Time Metrics (all in milliseconds in Snowflake)

| Metric | Description |
|--------|-------------|
| `TOTAL_ELAPSED_TIME` | Total wall-clock time |
| `EXECUTION_TIME` | Time spent executing |
| `COMPILATION_TIME` | Time spent parsing and optimizing |
| `QUEUED_OVERLOAD_TIME` | Time waiting because warehouse was busy |
| `QUEUED_PROVISIONING_TIME` | Time waiting for cluster to start |

### Understanding Partition Metrics

| Metric | Description |
|--------|-------------|
| `PARTITIONS_TOTAL` | Total partitions in table |
| `PARTITIONS_SCANNED` | Partitions actually read |
| Ratio near 1.0 = Full table scan = BAD |

### Understanding Spilling Metrics

| Metric | Description | Cost Impact |
|--------|-------------|-------------|
| `BYTES_SPILLED_TO_LOCAL_STORAGE` | Data spilled to local SSD | Moderate |
| `BYTES_SPILLED_TO_REMOTE_STORAGE` | Data spilled to cloud storage | HIGH |

---

## Permissions Required

To run these queries, your Snowflake user needs:

```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE your_role;
```

Or specifically:

```sql
GRANT USAGE ON DATABASE SNOWFLAKE TO ROLE your_role;
GRANT USAGE ON SCHEMA SNOWFLAKE.ACCOUNT_USAGE TO ROLE your_role;
GRANT SELECT ON ALL VIEWS IN SCHEMA SNOWFLAKE.ACCOUNT_USAGE TO ROLE your_role;
```

---

## Data Latency Notes

- **QUERY_HISTORY**: ~45 minutes latency
- **WAREHOUSE_METERING_HISTORY**: ~2 hours latency
- **WAREHOUSE_LOAD_HISTORY**: ~2 hours latency
- **LOGIN_HISTORY**: ~2 hours latency
- **TABLES**: ~2 hours latency
- **DATABASE_STORAGE_USAGE_HISTORY**: ~2 hours latency

For real-time data, use `INFORMATION_SCHEMA` or `SHOW` commands instead.
