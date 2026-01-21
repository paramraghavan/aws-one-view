# Snowflake ACCOUNT_USAGE API Guide

This document explains the Snowflake ACCOUNT_USAGE views and SQL queries used by the Resource Monitor. Understanding these APIs will help you customize queries, troubleshoot issues, and extend the monitoring capabilities.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites & Permissions](#prerequisites--permissions)
3. [Data Latency](#data-latency)
4. [ACCOUNT_USAGE Views Reference](#account_usage-views-reference)
   - [WAREHOUSE_METERING_HISTORY](#warehouse_metering_history)
   - [WAREHOUSE_LOAD_HISTORY](#warehouse_load_history)
   - [WAREHOUSES](#warehouses)
   - [QUERY_HISTORY](#query_history)
   - [DATABASE_STORAGE_USAGE_HISTORY](#database_storage_usage_history)
5. [Query Examples by Use Case](#query-examples-by-use-case)
6. [Customization Guide](#customization-guide)
7. [Troubleshooting](#troubleshooting)

---

## Overview

The Snowflake Resource Monitor uses the `SNOWFLAKE.ACCOUNT_USAGE` schema, which provides historical data about your Snowflake account's usage, performance, and configurations. This schema is part of the shared `SNOWFLAKE` database available in every Snowflake account.

### Why ACCOUNT_USAGE?

| Feature | ACCOUNT_USAGE | INFORMATION_SCHEMA |
|---------|---------------|-------------------|
| Data Retention | 1 year | 7 days to 6 months |
| Data Latency | 45 minutes to 3 hours | Real-time to 3 hours |
| Dropped Objects | Included | Not included |
| Access Method | Shared database | Per-database views |

ACCOUNT_USAGE is preferred for monitoring dashboards because of its longer retention and account-wide scope.

---

## Prerequisites & Permissions

### Required Privileges

To query ACCOUNT_USAGE views, users need the `IMPORTED PRIVILEGES` grant on the `SNOWFLAKE` database:

```sql
-- Grant to a role (run as ACCOUNTADMIN)
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE monitor_role;
```

### Creating a Dedicated Monitoring Role

Best practice is to create a dedicated role for monitoring:

```sql
-- Create monitoring role
USE ROLE ACCOUNTADMIN;

CREATE ROLE IF NOT EXISTS SNOWFLAKE_MONITOR_ROLE;

-- Grant access to ACCOUNT_USAGE
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE SNOWFLAKE_MONITOR_ROLE;

-- Grant warehouse usage for running queries
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE SNOWFLAKE_MONITOR_ROLE;

-- Create a monitoring user
CREATE USER IF NOT EXISTS monitor_user
  PASSWORD = 'SecurePassword123!'
  DEFAULT_ROLE = SNOWFLAKE_MONITOR_ROLE
  DEFAULT_WAREHOUSE = COMPUTE_WH;

GRANT ROLE SNOWFLAKE_MONITOR_ROLE TO USER monitor_user;
```

### Verifying Access

```sql
-- Test access
USE ROLE SNOWFLAKE_MONITOR_ROLE;
USE DATABASE SNOWFLAKE;
USE SCHEMA ACCOUNT_USAGE;

-- Should return results
SELECT COUNT(*) FROM QUERY_HISTORY WHERE START_TIME >= DATEADD(day, -1, CURRENT_TIMESTAMP());
```

---

## Data Latency

ACCOUNT_USAGE views have inherent latency. Data is not real-time:

| View | Typical Latency |
|------|----------------|
| WAREHOUSE_METERING_HISTORY | 2-3 hours |
| WAREHOUSE_LOAD_HISTORY | 2-3 hours |
| QUERY_HISTORY | 45 minutes |
| DATABASE_STORAGE_USAGE_HISTORY | Up to 3 hours |
| WAREHOUSES | Near real-time |

### Implications

- Dashboards show historical data, not live metrics
- Recent queries may not appear immediately
- For real-time monitoring, consider INFORMATION_SCHEMA or SHOW commands
- Plan refresh intervals accordingly (e.g., every 5-15 minutes is sufficient)

---

## ACCOUNT_USAGE Views Reference

### WAREHOUSE_METERING_HISTORY

Tracks credit consumption by warehouse over time.

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `START_TIME` | TIMESTAMP | Start of the metering period (hourly) |
| `END_TIME` | TIMESTAMP | End of the metering period |
| `WAREHOUSE_NAME` | VARCHAR | Name of the warehouse |
| `CREDITS_USED` | NUMBER | Total credits consumed |
| `CREDITS_USED_COMPUTE` | NUMBER | Credits for compute resources |
| `CREDITS_USED_CLOUD_SERVICES` | NUMBER | Credits for cloud services |

#### Example: Total Credits by Warehouse (Last 30 Days)

```sql
SELECT 
    WAREHOUSE_NAME,
    SUM(CREDITS_USED) as TOTAL_CREDITS,
    SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
    SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS,
    COUNT(DISTINCT DATE_TRUNC('day', START_TIME)) as ACTIVE_DAYS,
    AVG(CREDITS_USED) as AVG_HOURLY_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME
ORDER BY TOTAL_CREDITS DESC;
```

#### Example: Daily Cost Trends

```sql
SELECT 
    DATE_TRUNC('day', START_TIME) as DATE,
    SUM(CREDITS_USED) as TOTAL_CREDITS,
    SUM(CREDITS_USED_COMPUTE) as COMPUTE_CREDITS,
    SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_SERVICES_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY DATE_TRUNC('day', START_TIME)
ORDER BY DATE;
```

#### Example: Hourly Usage Pattern

```sql
SELECT 
    EXTRACT(HOUR FROM START_TIME) as HOUR_OF_DAY,
    EXTRACT(DAYOFWEEK FROM START_TIME) as DAY_OF_WEEK,
    AVG(CREDITS_USED) as AVG_CREDITS,
    SUM(CREDITS_USED) as TOTAL_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY EXTRACT(HOUR FROM START_TIME), EXTRACT(DAYOFWEEK FROM START_TIME)
ORDER BY DAY_OF_WEEK, HOUR_OF_DAY;
```

---

### WAREHOUSE_LOAD_HISTORY

Tracks query concurrency and load on warehouses.

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `START_TIME` | TIMESTAMP | Start of the measurement period |
| `END_TIME` | TIMESTAMP | End of the measurement period |
| `WAREHOUSE_NAME` | VARCHAR | Name of the warehouse |
| `AVG_RUNNING` | NUMBER | Average number of queries running |
| `AVG_QUEUED_LOAD` | NUMBER | Average queries queued due to load |
| `AVG_QUEUED_PROVISIONING` | NUMBER | Average queries waiting for cluster provisioning |
| `AVG_BLOCKED` | NUMBER | Average queries blocked by transactions |

#### Example: Cluster Concurrency Over Time

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
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME, DATE_TRUNC('hour', START_TIME)
ORDER BY HOUR DESC;
```

#### Example: Identify Warehouses with High Concurrency

```sql
SELECT 
    WAREHOUSE_NAME,
    AVG(AVG_RUNNING) as AVG_CONCURRENT,
    MAX(AVG_RUNNING) as PEAK_CONCURRENT,
    AVG(AVG_QUEUED_LOAD) as AVG_QUEUED,
    MAX(AVG_QUEUED_LOAD) as PEAK_QUEUED
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY WAREHOUSE_NAME
HAVING AVG_QUEUED > 1
ORDER BY AVG_QUEUED DESC;
```

---

### WAREHOUSES

Provides current warehouse configurations.

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `NAME` | VARCHAR | Warehouse name |
| `STATE` | VARCHAR | Current state (STARTED, SUSPENDED, etc.) |
| `TYPE` | VARCHAR | STANDARD or SNOWPARK-OPTIMIZED |
| `SIZE` | VARCHAR | Warehouse size (X-Small to 6X-Large) |
| `MIN_CLUSTER_COUNT` | NUMBER | Minimum clusters for multi-cluster |
| `MAX_CLUSTER_COUNT` | NUMBER | Maximum clusters for multi-cluster |
| `SCALING_POLICY` | VARCHAR | STANDARD or ECONOMY |
| `AUTO_SUSPEND` | NUMBER | Seconds until auto-suspend (NULL = disabled) |
| `AUTO_RESUME` | BOOLEAN | Whether auto-resume is enabled |
| `RESOURCE_MONITOR` | VARCHAR | Assigned resource monitor (if any) |
| `CREATED_ON` | TIMESTAMP | Creation timestamp |
| `DELETED` | TIMESTAMP | Deletion timestamp (NULL if active) |

#### Example: List All Warehouse Configurations

```sql
SELECT 
    NAME as WAREHOUSE_NAME,
    STATE,
    TYPE,
    SIZE,
    MIN_CLUSTER_COUNT,
    MAX_CLUSTER_COUNT,
    SCALING_POLICY,
    AUTO_SUSPEND,
    AUTO_RESUME,
    RESOURCE_MONITOR,
    CREATED_ON,
    OWNER
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSES
WHERE DELETED IS NULL
ORDER BY NAME;
```

#### Example: Find Warehouses with Suboptimal Auto-Suspend

```sql
-- Warehouses with auto-suspend disabled or set too high
SELECT 
    NAME,
    SIZE,
    AUTO_SUSPEND,
    CASE 
        WHEN AUTO_SUSPEND IS NULL THEN 'Disabled - HIGH RISK'
        WHEN AUTO_SUSPEND > 600 THEN 'Too Long (>10 min)'
        WHEN AUTO_SUSPEND > 300 THEN 'Consider Reducing'
        ELSE 'OK'
    END as RECOMMENDATION
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSES
WHERE DELETED IS NULL
AND (AUTO_SUSPEND IS NULL OR AUTO_SUSPEND > 300)
ORDER BY AUTO_SUSPEND DESC NULLS FIRST;
```

---

### QUERY_HISTORY

The most detailed view, containing information about every query executed.

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `QUERY_ID` | VARCHAR | Unique query identifier |
| `QUERY_TEXT` | VARCHAR | The SQL statement |
| `USER_NAME` | VARCHAR | User who executed the query |
| `WAREHOUSE_NAME` | VARCHAR | Warehouse used |
| `DATABASE_NAME` | VARCHAR | Target database |
| `SCHEMA_NAME` | VARCHAR | Target schema |
| `QUERY_TYPE` | VARCHAR | SELECT, INSERT, UPDATE, etc. |
| `EXECUTION_STATUS` | VARCHAR | SUCCESS, FAIL, INCIDENT |
| `ERROR_CODE` | NUMBER | Error code if failed |
| `ERROR_MESSAGE` | VARCHAR | Error message if failed |
| `START_TIME` | TIMESTAMP | Query start time |
| `END_TIME` | TIMESTAMP | Query end time |
| `TOTAL_ELAPSED_TIME` | NUMBER | Total time in milliseconds |
| `COMPILATION_TIME` | NUMBER | Parse/compile time in ms |
| `EXECUTION_TIME` | NUMBER | Execution time in ms |
| `QUEUED_PROVISIONING_TIME` | NUMBER | Time waiting for cluster provisioning (ms) |
| `QUEUED_OVERLOAD_TIME` | NUMBER | Time queued due to concurrency (ms) |
| `BYTES_SCANNED` | NUMBER | Bytes read from storage |
| `BYTES_WRITTEN` | NUMBER | Bytes written |
| `ROWS_PRODUCED` | NUMBER | Result rows |
| `BYTES_SPILLED_TO_LOCAL_STORAGE` | NUMBER | Memory spill to local disk |
| `BYTES_SPILLED_TO_REMOTE_STORAGE` | NUMBER | Memory spill to remote storage |
| `PARTITIONS_SCANNED` | NUMBER | Micro-partitions scanned |
| `PARTITIONS_TOTAL` | NUMBER | Total micro-partitions |
| `CREDITS_USED_CLOUD_SERVICES` | NUMBER | Cloud services credits |

#### Example: Long-Running Queries

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    DATABASE_NAME,
    SCHEMA_NAME,
    EXECUTION_STATUS,
    START_TIME,
    END_TIME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SECONDS,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
    ROWS_PRODUCED,
    COMPILATION_TIME / 1000 as COMPILATION_SECONDS,
    EXECUTION_TIME / 1000 as EXECUTION_SECONDS,
    QUEUED_PROVISIONING_TIME / 1000 as QUEUED_PROVISIONING_SECONDS,
    QUEUED_OVERLOAD_TIME / 1000 as QUEUED_OVERLOAD_SECONDS
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND TOTAL_ELAPSED_TIME > 60000  -- > 60 seconds
ORDER BY TOTAL_ELAPSED_TIME DESC
LIMIT 50;
```

#### Example: Expensive Queries by Data Scanned

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    DATABASE_NAME,
    START_TIME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SECONDS,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
    BYTES_WRITTEN / POWER(1024, 3) as GB_WRITTEN,
    ROWS_PRODUCED,
    PARTITIONS_SCANNED,
    PARTITIONS_TOTAL,
    ROUND(PARTITIONS_SCANNED / NULLIF(PARTITIONS_TOTAL, 0) * 100, 2) as PARTITION_SCAN_PCT
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND EXECUTION_STATUS = 'SUCCESS'
AND BYTES_SCANNED > 0
ORDER BY BYTES_SCANNED DESC
LIMIT 50;
```

#### Example: Queued Queries (Concurrency Bottleneck)

```sql
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    START_TIME,
    TOTAL_ELAPSED_TIME / 1000 as TOTAL_SEC,
    QUEUED_OVERLOAD_TIME / 1000 as QUEUE_SEC,
    QUEUED_PROVISIONING_TIME / 1000 as PROVISIONING_SEC,
    EXECUTION_TIME / 1000 as EXECUTION_SEC
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND (QUEUED_OVERLOAD_TIME > 1000 OR QUEUED_PROVISIONING_TIME > 1000)
ORDER BY QUEUED_OVERLOAD_TIME + QUEUED_PROVISIONING_TIME DESC
LIMIT 100;
```

#### Example: Queries with Memory Spilling

```sql
-- Queries that spilled to disk indicate memory pressure
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    WAREHOUSE_NAME,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SECONDS,
    BYTES_SPILLED_TO_LOCAL_STORAGE / POWER(1024, 3) as GB_SPILLED_LOCAL,
    BYTES_SPILLED_TO_REMOTE_STORAGE / POWER(1024, 3) as GB_SPILLED_REMOTE,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND (BYTES_SPILLED_TO_LOCAL_STORAGE > 0 OR BYTES_SPILLED_TO_REMOTE_STORAGE > 0)
ORDER BY BYTES_SPILLED_TO_LOCAL_STORAGE + BYTES_SPILLED_TO_REMOTE_STORAGE DESC
LIMIT 50;
```

#### Example: Failed Queries Analysis

```sql
SELECT 
    ERROR_CODE,
    ERROR_MESSAGE,
    COUNT(*) as FAILURE_COUNT,
    COUNT(DISTINCT USER_NAME) as AFFECTED_USERS,
    MIN(START_TIME) as FIRST_OCCURRENCE,
    MAX(START_TIME) as LAST_OCCURRENCE
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND EXECUTION_STATUS = 'FAIL'
GROUP BY ERROR_CODE, ERROR_MESSAGE
ORDER BY FAILURE_COUNT DESC
LIMIT 20;
```

#### Example: Query Patterns by Hour

```sql
SELECT 
    EXTRACT(HOUR FROM START_TIME) as HOUR_OF_DAY,
    COUNT(*) as QUERY_COUNT,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_ELAPSED_SEC,
    SUM(BYTES_SCANNED) / POWER(1024, 4) as TOTAL_TB_SCANNED
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY EXTRACT(HOUR FROM START_TIME)
ORDER BY HOUR_OF_DAY;
```

#### Example: Query Patterns by User

```sql
SELECT 
    USER_NAME,
    COUNT(*) as QUERY_COUNT,
    AVG(TOTAL_ELAPSED_TIME) / 1000 as AVG_ELAPSED_SEC,
    SUM(BYTES_SCANNED) / POWER(1024, 3) as TOTAL_GB_SCANNED,
    SUM(CREDITS_USED_CLOUD_SERVICES) as CLOUD_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
GROUP BY USER_NAME
ORDER BY QUERY_COUNT DESC
LIMIT 20;
```

---

### DATABASE_STORAGE_USAGE_HISTORY

Tracks storage consumption by database over time.

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `USAGE_DATE` | DATE | Date of the measurement |
| `DATABASE_NAME` | VARCHAR | Name of the database |
| `AVERAGE_DATABASE_BYTES` | NUMBER | Average storage bytes |
| `AVERAGE_FAILSAFE_BYTES` | NUMBER | Average failsafe storage |

#### Example: Current Storage by Database

```sql
SELECT 
    DATABASE_NAME,
    AVERAGE_DATABASE_BYTES / POWER(1024, 3) as DATABASE_GB,
    AVERAGE_FAILSAFE_BYTES / POWER(1024, 3) as FAILSAFE_GB,
    (AVERAGE_DATABASE_BYTES + AVERAGE_FAILSAFE_BYTES) / POWER(1024, 3) as TOTAL_GB
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE USAGE_DATE = (
    SELECT MAX(USAGE_DATE) 
    FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
)
ORDER BY TOTAL_GB DESC;
```

#### Example: Storage Growth Over Time

```sql
SELECT 
    USAGE_DATE,
    DATABASE_NAME,
    AVERAGE_DATABASE_BYTES / POWER(1024, 3) as DATABASE_GB
FROM SNOWFLAKE.ACCOUNT_USAGE.DATABASE_STORAGE_USAGE_HISTORY
WHERE USAGE_DATE >= DATEADD(day, -30, CURRENT_DATE())
ORDER BY DATABASE_NAME, USAGE_DATE;
```

---

## Query Examples by Use Case

### Use Case 1: Daily Cost Report

```sql
-- Generate a comprehensive daily cost summary
WITH daily_costs AS (
    SELECT 
        DATE_TRUNC('day', START_TIME) as DATE,
        WAREHOUSE_NAME,
        SUM(CREDITS_USED) as CREDITS
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', START_TIME), WAREHOUSE_NAME
)
SELECT 
    DATE,
    SUM(CREDITS) as TOTAL_CREDITS,
    LISTAGG(WAREHOUSE_NAME || ': ' || ROUND(CREDITS, 2), ', ') as BREAKDOWN
FROM daily_costs
GROUP BY DATE
ORDER BY DATE DESC;
```

### Use Case 2: Identify Optimization Opportunities

```sql
-- Find warehouses that might be oversized
SELECT 
    wh.NAME as WAREHOUSE_NAME,
    wh.SIZE,
    ROUND(AVG(wl.AVG_RUNNING), 2) as AVG_CONCURRENT_QUERIES,
    ROUND(MAX(wl.AVG_RUNNING), 2) as PEAK_CONCURRENT_QUERIES,
    CASE 
        WHEN AVG(wl.AVG_RUNNING) < 1 AND wh.SIZE IN ('Medium', 'Large', 'X-Large', '2X-Large', '3X-Large', '4X-Large') THEN 'Consider downsizing'
        WHEN MAX(wl.AVG_QUEUED_LOAD) > 2 THEN 'Consider upsizing or multi-cluster'
        ELSE 'Appropriately sized'
    END as RECOMMENDATION
FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSES wh
LEFT JOIN SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_LOAD_HISTORY wl 
    ON wh.NAME = wl.WAREHOUSE_NAME
    AND wl.START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
WHERE wh.DELETED IS NULL
GROUP BY wh.NAME, wh.SIZE;
```

### Use Case 3: Full Table Scan Detection

```sql
-- Find queries scanning 100% of partitions (full table scans)
SELECT 
    QUERY_ID,
    QUERY_TEXT,
    USER_NAME,
    DATABASE_NAME || '.' || SCHEMA_NAME as LOCATION,
    PARTITIONS_SCANNED,
    PARTITIONS_TOTAL,
    BYTES_SCANNED / POWER(1024, 3) as GB_SCANNED,
    TOTAL_ELAPSED_TIME / 1000 as ELAPSED_SEC
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())
AND PARTITIONS_TOTAL > 100  -- Tables with significant size
AND PARTITIONS_SCANNED = PARTITIONS_TOTAL  -- Full scan
AND EXECUTION_STATUS = 'SUCCESS'
ORDER BY BYTES_SCANNED DESC
LIMIT 50;
```

### Use Case 4: User Activity Audit

```sql
-- Detailed user activity report
SELECT 
    USER_NAME,
    COUNT(*) as TOTAL_QUERIES,
    COUNT(CASE WHEN EXECUTION_STATUS = 'SUCCESS' THEN 1 END) as SUCCESSFUL,
    COUNT(CASE WHEN EXECUTION_STATUS = 'FAIL' THEN 1 END) as FAILED,
    ROUND(SUM(TOTAL_ELAPSED_TIME) / 1000 / 3600, 2) as TOTAL_HOURS,
    ROUND(SUM(BYTES_SCANNED) / POWER(1024, 4), 4) as TB_SCANNED,
    MIN(START_TIME) as FIRST_QUERY,
    MAX(START_TIME) as LAST_QUERY
FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
GROUP BY USER_NAME
ORDER BY TOTAL_QUERIES DESC;
```

### Use Case 5: Credit Consumption Forecast

```sql
-- Simple linear forecast based on recent usage
WITH daily_usage AS (
    SELECT 
        DATE_TRUNC('day', START_TIME) as DATE,
        SUM(CREDITS_USED) as CREDITS
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, -30, CURRENT_TIMESTAMP())
    GROUP BY DATE_TRUNC('day', START_TIME)
)
SELECT 
    AVG(CREDITS) as AVG_DAILY_CREDITS,
    AVG(CREDITS) * 30 as PROJECTED_MONTHLY_CREDITS,
    AVG(CREDITS) * 365 as PROJECTED_ANNUAL_CREDITS
FROM daily_usage;
```

---

## Customization Guide

### Modifying Time Windows

All queries use `DATEADD()` to filter by time. Adjust the parameters:

```sql
-- Last 7 days
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())

-- Last 24 hours
WHERE START_TIME >= DATEADD(hour, -24, CURRENT_TIMESTAMP())

-- Last 90 days
WHERE START_TIME >= DATEADD(day, -90, CURRENT_TIMESTAMP())

-- Specific date range
WHERE START_TIME BETWEEN '2025-01-01' AND '2025-01-31'
```

### Adding Filters

Filter by warehouse, user, database, or query type:

```sql
-- Specific warehouse
AND WAREHOUSE_NAME = 'ANALYTICS_WH'

-- Multiple warehouses
AND WAREHOUSE_NAME IN ('ANALYTICS_WH', 'ETL_WH')

-- Specific user
AND USER_NAME = 'DATA_ENGINEER'

-- Query type
AND QUERY_TYPE = 'SELECT'

-- Exclude system queries
AND QUERY_TYPE NOT IN ('SHOW', 'DESCRIBE', 'USE')
```

### Creating Custom Thresholds

```sql
-- Custom thresholds for long-running queries
AND TOTAL_ELAPSED_TIME > 300000  -- > 5 minutes (in ms)

-- Custom threshold for expensive queries
AND BYTES_SCANNED > POWER(1024, 4)  -- > 1 TB

-- Custom threshold for spilling
AND BYTES_SPILLED_TO_LOCAL_STORAGE > POWER(1024, 3) * 10  -- > 10 GB
```

### Adding New Metrics

To add custom metrics, create new methods in `snowflake_connector.py`:

```python
def get_custom_metric(self, days: int = 7) -> List[Dict]:
    """Get custom metric."""
    query = f"""
    SELECT 
        -- Your columns here
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(day, -{days}, CURRENT_TIMESTAMP())
    -- Your conditions here
    """
    results = self.execute_query(query)
    return self._serialize_results(results)
```

Then add a corresponding endpoint in `app.py`:

```python
@app.route('/api/custom-metric')
def api_custom_metric():
    days = request.args.get('days', 7, type=int)
    try:
        monitor = get_monitor()
        data = monitor.get_custom_metric(days)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
```

---

## Troubleshooting

### Common Issues

#### 1. "Object does not exist" Error

```
SQL compilation error: Object 'SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY' does not exist
```

**Solution**: Grant IMPORTED PRIVILEGES:
```sql
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE your_role;
```

#### 2. Empty Results

ACCOUNT_USAGE views have latency. Recent data may not be available yet.

**Solution**: Check the most recent data:
```sql
SELECT MAX(START_TIME) FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY;
```

#### 3. Permission Denied

```
Insufficient privileges to operate on account 'ACCOUNT_USAGE'
```

**Solution**: Ensure you're using a role with IMPORTED PRIVILEGES on the SNOWFLAKE database.

#### 4. Query Timeout

Large queries on ACCOUNT_USAGE views can timeout.

**Solution**: 
- Add more specific filters (time range, warehouse name)
- Use a larger warehouse
- Add LIMIT clause

```sql
-- Add stricter time filter
WHERE START_TIME >= DATEADD(day, -7, CURRENT_TIMESTAMP())  -- Instead of -30

-- Add LIMIT
LIMIT 1000
```

#### 5. Missing Warehouse in WAREHOUSE_METERING_HISTORY

Suspended warehouses don't generate metering records.

**Solution**: Query WAREHOUSES view for configuration, WAREHOUSE_METERING_HISTORY only for active usage.

### Performance Tips

1. **Always filter by time**: ACCOUNT_USAGE views can contain millions of rows
2. **Use specific date ranges**: Avoid scanning unnecessary historical data
3. **Aggregate early**: Use GROUP BY to reduce data volume before analysis
4. **Limit results**: Use LIMIT for exploratory queries
5. **Schedule heavy queries**: Run comprehensive reports during off-peak hours

---

## Additional Resources

- [Snowflake ACCOUNT_USAGE Documentation](https://docs.snowflake.com/en/sql-reference/account-usage)
- [Snowflake Cost Management Best Practices](https://docs.snowflake.com/en/user-guide/cost-management-best-practices)
- [Query History View Reference](https://docs.snowflake.com/en/sql-reference/account-usage/query_history)
- [Warehouse Metering History Reference](https://docs.snowflake.com/en/sql-reference/account-usage/warehouse_metering_history)

---

## Quick Reference Card

### Common Calculations

```sql
-- Milliseconds to seconds
column_ms / 1000 as seconds

-- Bytes to GB
bytes / POWER(1024, 3) as gb

-- Bytes to TB  
bytes / POWER(1024, 4) as tb

-- Percentage
ROUND(part / total * 100, 2) as percentage

-- Hours from milliseconds
ms / 1000 / 3600 as hours
```

### Date Functions

```sql
-- Current timestamp
CURRENT_TIMESTAMP()

-- Days ago
DATEADD(day, -N, CURRENT_TIMESTAMP())

-- Truncate to day/hour
DATE_TRUNC('day', timestamp_col)
DATE_TRUNC('hour', timestamp_col)

-- Extract hour/day
EXTRACT(HOUR FROM timestamp_col)
EXTRACT(DAYOFWEEK FROM timestamp_col)
```

### Useful Aggregations

```sql
-- Count distinct
COUNT(DISTINCT column)

-- Conditional count
COUNT(CASE WHEN condition THEN 1 END)

-- Running total (window function)
SUM(credits) OVER (ORDER BY date ROWS UNBOUNDED PRECEDING)

-- Percentage of total
credits / SUM(credits) OVER () * 100
```
