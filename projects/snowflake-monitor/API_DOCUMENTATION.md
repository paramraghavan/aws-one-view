# Snowflake Resource Monitor - API Documentation

This document provides complete documentation for all API endpoints available in the Snowflake Resource Monitor. Each endpoint returns JSON data that can be consumed by the dashboard UI or integrated into your own applications.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Response Format](#response-format)
3. [API Endpoints](#api-endpoints)
   - [Overview](#get-apioverview)
   - [Warehouse Costs](#get-apiwarehouse-costs)
   - [Warehouse Usage](#get-apiwarehouse-usage)
   - [Long-Running Queries](#get-apilong-running-queries)
   - [Expensive Queries](#get-apiexpensive-queries)
   - [Storage Usage](#get-apistorage-usage)
   - [Cluster Load](#get-apicluster-load)
   - [Warehouse Configuration](#get-apiwarehouse-config)
   - [Query Patterns](#get-apiquery-patterns)
   - [Cost Trends](#get-apicost-trends)
   - [Bottleneck Analysis](#get-apibottleneck-analysis)
   - [Database Costs](#get-apidatabase-costs)
   - [Recommendations](#get-apirecommendations)
   - [Queued Queries](#get-apiqueued-queries)
   - [Hourly Credit Usage](#get-apicredit-usage-hourly)
4. [Error Handling](#error-handling)
5. [Integration Examples](#integration-examples)

---

## Getting Started

### Base URL

When running locally, the base URL is:

```
http://localhost:5000
```

### Authentication

The API does not require authentication for requests. However, the server must be configured with valid Snowflake credentials via environment variables.

### Making Requests

All endpoints use HTTP GET requests. Parameters are passed as query strings.

```bash
# Basic request
curl http://localhost:5000/api/overview

# Request with parameters
curl "http://localhost:5000/api/warehouse-costs?days=30"
```

---

## Response Format

All API responses follow a consistent JSON structure:

### Successful Response

```json
{
  "success": true,
  "data": { ... }
}
```

### Error Response

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

---

## API Endpoints

---

### GET /api/overview

Returns high-level metrics for the dashboard overview, including total credits used, query counts, and storage information.

#### Parameters

None

#### Example Request

```bash
curl http://localhost:5000/api/overview
```

#### Example Response

```json
{
  "success": true,
  "data": {
    "total_credits_30d": 1542.75,
    "total_credits_7d": 387.25,
    "total_queries_24h": 15234,
    "failed_queries_24h": 23,
    "avg_query_time_24h": 4.52,
    "total_storage_tb": 2.34,
    "active_warehouses": 8,
    "total_users_24h": 47
  }
}
```

#### Use Cases

- Populating dashboard summary cards
- Quick health check of Snowflake account
- Executive-level reporting

---

### GET /api/warehouse-costs

Returns credit consumption breakdown by warehouse for a specified time period.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Number of days to analyze (1-90) |

#### Example Request

```bash
# Last 30 days (default)
curl http://localhost:5000/api/warehouse-costs

# Last 7 days
curl "http://localhost:5000/api/warehouse-costs?days=7"

# Last 90 days
curl "http://localhost:5000/api/warehouse-costs?days=90"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "warehouse_name": "ANALYTICS_WH",
      "total_credits": 892.45,
      "compute_credits": 845.20,
      "cloud_services_credits": 47.25,
      "percentage_of_total": 57.8
    },
    {
      "warehouse_name": "ETL_WH",
      "total_credits": 423.15,
      "compute_credits": 401.80,
      "cloud_services_credits": 21.35,
      "percentage_of_total": 27.4
    },
    {
      "warehouse_name": "REPORTING_WH",
      "total_credits": 227.15,
      "compute_credits": 215.50,
      "cloud_services_credits": 11.65,
      "percentage_of_total": 14.8
    }
  ]
}
```

#### Use Cases

- Identifying most expensive warehouses
- Cost allocation by team/department
- Capacity planning

---

### GET /api/warehouse-usage

Returns warehouse usage statistics including execution time and query volumes.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to analyze |

#### Example Request

```bash
curl "http://localhost:5000/api/warehouse-usage?days=7"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "warehouse_name": "ANALYTICS_WH",
      "total_queries": 45234,
      "total_execution_time_hrs": 127.5,
      "avg_execution_time_sec": 10.14,
      "avg_queued_time_sec": 0.85
    },
    {
      "warehouse_name": "ETL_WH",
      "total_queries": 12456,
      "total_execution_time_hrs": 89.3,
      "avg_execution_time_sec": 25.82,
      "avg_queued_time_sec": 2.15
    }
  ]
}
```

#### Use Cases

- Understanding warehouse utilization patterns
- Identifying underutilized warehouses
- Performance benchmarking

---

### GET /api/long-running-queries

Returns queries that exceeded a specified execution time threshold.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `threshold` | integer | 60 | Minimum execution time in seconds |
| `limit` | integer | 50 | Maximum number of results (1-500) |

#### Example Request

```bash
# Queries over 60 seconds (default)
curl http://localhost:5000/api/long-running-queries

# Queries over 5 minutes, limit 100
curl "http://localhost:5000/api/long-running-queries?threshold=300&limit=100"

# Queries over 30 seconds
curl "http://localhost:5000/api/long-running-queries?threshold=30"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "query_id": "01b2c3d4-5678-90ab-cdef-123456789abc",
      "query_text": "SELECT * FROM large_table WHERE ...",
      "user_name": "ANALYTICS_USER",
      "warehouse_name": "ANALYTICS_WH",
      "execution_time_sec": 342.5,
      "bytes_scanned": 15234567890,
      "rows_produced": 1523456,
      "start_time": "2025-01-20T14:32:15Z",
      "end_time": "2025-01-20T14:38:17Z",
      "query_type": "SELECT",
      "error_code": null,
      "error_message": null
    },
    {
      "query_id": "02c3d4e5-6789-01bc-def2-234567890bcd",
      "query_text": "INSERT INTO target_table SELECT ...",
      "user_name": "ETL_SERVICE",
      "warehouse_name": "ETL_WH",
      "execution_time_sec": 287.3,
      "bytes_scanned": 8765432100,
      "rows_produced": 987654,
      "start_time": "2025-01-20T15:10:00Z",
      "end_time": "2025-01-20T15:14:47Z",
      "query_type": "INSERT",
      "error_code": null,
      "error_message": null
    }
  ]
}
```

#### Use Cases

- Identifying queries needing optimization
- Finding runaway queries
- Performance troubleshooting

---

### GET /api/expensive-queries

Returns queries ranked by resource consumption (credits, bytes scanned).

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to analyze |
| `limit` | integer | 50 | Maximum number of results (1-500) |

#### Example Request

```bash
# Last 7 days, top 50 (default)
curl http://localhost:5000/api/expensive-queries

# Last 30 days, top 100
curl "http://localhost:5000/api/expensive-queries?days=30&limit=100"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "query_id": "01b2c3d4-5678-90ab-cdef-123456789abc",
      "query_text": "SELECT * FROM very_large_table ...",
      "user_name": "DATA_SCIENTIST",
      "warehouse_name": "ANALYTICS_WH",
      "execution_time_sec": 523.7,
      "bytes_scanned": 52345678901,
      "bytes_scanned_gb": 48.75,
      "credits_used": 2.45,
      "partitions_scanned": 15234,
      "partitions_total": 15234,
      "start_time": "2025-01-19T09:15:00Z"
    }
  ]
}
```

#### Use Cases

- Cost optimization initiatives
- Identifying inefficient queries (full table scans)
- User training opportunities

---

### GET /api/storage-usage

Returns storage consumption breakdown by database.

#### Parameters

None

#### Example Request

```bash
curl http://localhost:5000/api/storage-usage
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "database_name": "PRODUCTION_DB",
      "average_bytes": 1523456789012,
      "storage_tb": 1.39,
      "failsafe_bytes": 152345678901,
      "failsafe_tb": 0.14
    },
    {
      "database_name": "ANALYTICS_DB",
      "average_bytes": 876543210987,
      "storage_tb": 0.80,
      "failsafe_bytes": 87654321098,
      "failsafe_tb": 0.08
    }
  ]
}
```

#### Use Cases

- Storage cost management
- Capacity planning
- Identifying databases for cleanup

---

### GET /api/cluster-load

Returns warehouse cluster utilization and concurrency metrics over time.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to analyze |

#### Example Request

```bash
curl "http://localhost:5000/api/cluster-load?days=7"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "warehouse_name": "ANALYTICS_WH",
      "timestamp": "2025-01-20T14:00:00Z",
      "avg_running": 3.5,
      "avg_queued": 0.8,
      "avg_blocked": 0.1,
      "max_running": 8,
      "max_queued": 12
    },
    {
      "warehouse_name": "ANALYTICS_WH",
      "timestamp": "2025-01-20T15:00:00Z",
      "avg_running": 5.2,
      "avg_queued": 2.1,
      "avg_blocked": 0.3,
      "max_running": 8,
      "max_queued": 25
    }
  ]
}
```

#### Use Cases

- Identifying peak usage periods
- Right-sizing warehouses
- Scaling policy optimization

---

### GET /api/warehouse-config

Returns current configuration for all warehouses.

#### Parameters

None

#### Example Request

```bash
curl http://localhost:5000/api/warehouse-config
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "warehouse_name": "ANALYTICS_WH",
      "warehouse_size": "LARGE",
      "min_cluster_count": 1,
      "max_cluster_count": 4,
      "auto_suspend_seconds": 300,
      "auto_resume": true,
      "scaling_policy": "STANDARD",
      "state": "STARTED",
      "created_on": "2024-06-15T10:00:00Z",
      "owner": "SYSADMIN"
    },
    {
      "warehouse_name": "ETL_WH",
      "warehouse_size": "XLARGE",
      "min_cluster_count": 1,
      "max_cluster_count": 1,
      "auto_suspend_seconds": 60,
      "auto_resume": true,
      "scaling_policy": "STANDARD",
      "state": "SUSPENDED",
      "created_on": "2024-03-01T08:00:00Z",
      "owner": "SYSADMIN"
    }
  ]
}
```

#### Use Cases

- Configuration auditing
- Identifying warehouses with suboptimal settings
- Documentation and compliance

---

### GET /api/query-patterns

Analyzes query execution patterns by hour, type, and user.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to analyze |

#### Example Request

```bash
curl "http://localhost:5000/api/query-patterns?days=7"
```

#### Example Response

```json
{
  "success": true,
  "data": {
    "by_hour": [
      {"hour": 0, "query_count": 1234, "avg_execution_time": 5.2},
      {"hour": 1, "query_count": 987, "avg_execution_time": 4.8},
      {"hour": 9, "query_count": 8756, "avg_execution_time": 7.3},
      {"hour": 14, "query_count": 12453, "avg_execution_time": 8.1}
    ],
    "by_type": [
      {"query_type": "SELECT", "query_count": 125634, "percentage": 78.5},
      {"query_type": "INSERT", "query_count": 23456, "percentage": 14.6},
      {"query_type": "UPDATE", "query_count": 8765, "percentage": 5.5},
      {"query_type": "DELETE", "query_count": 2234, "percentage": 1.4}
    ],
    "by_user": [
      {"user_name": "ETL_SERVICE", "query_count": 45678, "total_credits": 234.5},
      {"user_name": "BI_TOOL", "query_count": 34567, "total_credits": 156.7},
      {"user_name": "DATA_SCIENTIST", "query_count": 12345, "total_credits": 89.3}
    ]
  }
}
```

#### Use Cases

- Understanding workload distribution
- Capacity planning by time of day
- User activity monitoring

---

### GET /api/cost-trends

Returns daily credit consumption trends over time.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Number of days to analyze |

#### Example Request

```bash
# Last 30 days (default)
curl http://localhost:5000/api/cost-trends

# Last 90 days
curl "http://localhost:5000/api/cost-trends?days=90"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "date": "2025-01-20",
      "total_credits": 52.34,
      "compute_credits": 49.50,
      "cloud_services_credits": 2.84
    },
    {
      "date": "2025-01-19",
      "total_credits": 48.76,
      "compute_credits": 46.20,
      "cloud_services_credits": 2.56
    },
    {
      "date": "2025-01-18",
      "total_credits": 31.25,
      "compute_credits": 29.50,
      "cloud_services_credits": 1.75
    }
  ]
}
```

#### Use Cases

- Budget tracking and forecasting
- Identifying cost anomalies
- Trend analysis for planning

---

### GET /api/bottleneck-analysis

Returns comprehensive analysis of performance bottlenecks including queuing, spilling, compilation time, and failures.

#### Parameters

None

#### Example Request

```bash
curl http://localhost:5000/api/bottleneck-analysis
```

#### Example Response

```json
{
  "success": true,
  "data": {
    "queuing_issues": [
      {
        "warehouse_name": "ANALYTICS_WH",
        "queries_with_queue_time": 1234,
        "avg_queue_time_sec": 3.45,
        "max_queue_time_sec": 45.2,
        "total_queue_time_hrs": 1.18
      }
    ],
    "spilling_issues": [
      {
        "query_id": "01b2c3d4-...",
        "query_text": "SELECT ...",
        "local_spill_gb": 2.5,
        "remote_spill_gb": 0.8,
        "execution_time_sec": 234.5
      }
    ],
    "compilation_issues": [
      {
        "query_id": "02c3d4e5-...",
        "query_text": "SELECT ...",
        "compilation_time_sec": 12.5,
        "execution_time_sec": 45.2,
        "compilation_percentage": 27.7
      }
    ],
    "failure_analysis": [
      {
        "error_code": "100183",
        "error_message": "Statement reached its statement or warehouse timeout",
        "failure_count": 23,
        "affected_users": 5
      },
      {
        "error_code": "90030",
        "error_message": "Division by zero",
        "failure_count": 12,
        "affected_users": 3
      }
    ]
  }
}
```

#### Use Cases

- Proactive performance management
- Identifying resource constraints
- Root cause analysis

---

### GET /api/database-costs

Returns credit consumption attributed to each database.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 30 | Number of days to analyze |

#### Example Request

```bash
curl "http://localhost:5000/api/database-costs?days=30"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "database_name": "PRODUCTION_DB",
      "query_count": 234567,
      "total_execution_time_hrs": 456.7,
      "estimated_credits": 892.34,
      "percentage_of_total": 58.2
    },
    {
      "database_name": "ANALYTICS_DB",
      "query_count": 123456,
      "total_execution_time_hrs": 234.5,
      "estimated_credits": 456.78,
      "percentage_of_total": 29.8
    }
  ]
}
```

#### Use Cases

- Cost allocation by project/team
- Identifying expensive databases
- Chargeback reporting

---

### GET /api/recommendations

Returns auto-generated optimization recommendations based on current usage patterns.

#### Parameters

None

#### Example Request

```bash
curl http://localhost:5000/api/recommendations
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "category": "warehouse_sizing",
      "severity": "high",
      "title": "Downsize ANALYTICS_WH",
      "description": "ANALYTICS_WH is running at only 15% average utilization. Consider downsizing from LARGE to MEDIUM to reduce costs by approximately 50%.",
      "potential_savings": "~$500/month",
      "warehouse_name": "ANALYTICS_WH"
    },
    {
      "category": "auto_suspend",
      "severity": "medium",
      "title": "Reduce auto-suspend timeout for DEV_WH",
      "description": "DEV_WH has auto-suspend set to 600 seconds but averages only 2 queries per session. Reducing to 60 seconds could save credits.",
      "potential_savings": "~$150/month",
      "warehouse_name": "DEV_WH"
    },
    {
      "category": "query_optimization",
      "severity": "high",
      "title": "Optimize high-spill queries",
      "description": "15 queries in the past week spilled to remote storage, indicating insufficient memory. Consider larger warehouse or query optimization.",
      "affected_queries": 15
    },
    {
      "category": "concurrency",
      "severity": "medium",
      "title": "Enable multi-cluster for ETL_WH",
      "description": "ETL_WH experienced queue times averaging 5.2 seconds during peak hours. Enabling multi-cluster scaling could improve performance.",
      "warehouse_name": "ETL_WH"
    }
  ]
}
```

#### Use Cases

- Guided optimization workflow
- Cost reduction initiatives
- Performance improvement planning

---

### GET /api/queued-queries

Returns queries that experienced queuing delays due to concurrency limits.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to analyze |

#### Example Request

```bash
curl "http://localhost:5000/api/queued-queries?days=7"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {
      "query_id": "01b2c3d4-...",
      "query_text": "SELECT ...",
      "user_name": "BI_TOOL",
      "warehouse_name": "ANALYTICS_WH",
      "queued_time_sec": 12.5,
      "execution_time_sec": 3.2,
      "start_time": "2025-01-20T14:32:15Z"
    },
    {
      "query_id": "02c3d4e5-...",
      "query_text": "INSERT INTO ...",
      "user_name": "ETL_SERVICE",
      "warehouse_name": "ETL_WH",
      "queued_time_sec": 8.7,
      "execution_time_sec": 45.6,
      "start_time": "2025-01-20T15:10:00Z"
    }
  ]
}
```

#### Use Cases

- Identifying concurrency bottlenecks
- Multi-cluster warehouse decisions
- User experience optimization

---

### GET /api/credit-usage-hourly

Returns credit consumption patterns by hour of day.

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `days` | integer | 7 | Number of days to analyze |

#### Example Request

```bash
curl "http://localhost:5000/api/credit-usage-hourly?days=7"
```

#### Example Response

```json
{
  "success": true,
  "data": [
    {"hour": 0, "avg_credits": 1.25, "total_credits": 8.75},
    {"hour": 1, "avg_credits": 0.95, "total_credits": 6.65},
    {"hour": 8, "avg_credits": 4.50, "total_credits": 31.50},
    {"hour": 9, "avg_credits": 6.75, "total_credits": 47.25},
    {"hour": 14, "avg_credits": 7.80, "total_credits": 54.60},
    {"hour": 15, "avg_credits": 7.25, "total_credits": 50.75}
  ]
}
```

#### Use Cases

- Identifying peak usage hours
- Scheduling optimization
- Capacity planning

---

## Error Handling

### Common Error Responses

**Connection Error**
```json
{
  "success": false,
  "error": "Failed to connect to Snowflake: 250001: Could not connect to Snowflake backend"
}
```

**Permission Error**
```json
{
  "success": false,
  "error": "SQL access control error: Insufficient privileges to operate on schema 'ACCOUNT_USAGE'"
}
```

**Invalid Parameter**
```json
{
  "success": false,
  "error": "Invalid value for parameter 'days': must be a positive integer"
}
```

### Handling Errors in Your Application

```python
import requests

response = requests.get('http://localhost:5000/api/overview')
data = response.json()

if data['success']:
    metrics = data['data']
    print(f"Total credits: {metrics['total_credits_30d']}")
else:
    print(f"Error: {data['error']}")
```

```javascript
// JavaScript
fetch('/api/overview')
  .then(response => response.json())
  .then(data => {
    if (data.success) {
      console.log('Total credits:', data.data.total_credits_30d);
    } else {
      console.error('API Error:', data.error);
    }
  })
  .catch(error => console.error('Network Error:', error));
```

---

## Integration Examples

### Python Script for Daily Cost Report

```python
import requests
from datetime import datetime

BASE_URL = 'http://localhost:5000'

def get_daily_cost_report():
    # Get cost trends
    response = requests.get(f'{BASE_URL}/api/cost-trends?days=7')
    data = response.json()
    
    if not data['success']:
        print(f"Error: {data['error']}")
        return
    
    print("=" * 50)
    print("DAILY COST REPORT")
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)
    
    total_week = 0
    for day in data['data']:
        total_week += day['total_credits']
        print(f"{day['date']}: {day['total_credits']:.2f} credits")
    
    print("-" * 50)
    print(f"Weekly Total: {total_week:.2f} credits")
    
    # Get recommendations
    response = requests.get(f'{BASE_URL}/api/recommendations')
    recs = response.json()
    
    if recs['success'] and recs['data']:
        print("\n" + "=" * 50)
        print("OPTIMIZATION RECOMMENDATIONS")
        print("=" * 50)
        for rec in recs['data']:
            print(f"\n[{rec['severity'].upper()}] {rec['title']}")
            print(f"  {rec['description']}")

if __name__ == '__main__':
    get_daily_cost_report()
```

### Slack Alert for Long-Running Queries

```python
import requests
import json

SLACK_WEBHOOK = 'https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
MONITOR_URL = 'http://localhost:5000'

def check_long_running_queries(threshold_minutes=10):
    response = requests.get(
        f'{MONITOR_URL}/api/long-running-queries',
        params={'threshold': threshold_minutes * 60, 'limit': 10}
    )
    data = response.json()
    
    if not data['success']:
        return
    
    queries = data['data']
    if not queries:
        return
    
    # Build Slack message
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"⚠️ {len(queries)} Long-Running Queries Detected"
            }
        }
    ]
    
    for query in queries[:5]:  # Top 5 only
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Query ID:* `{query['query_id'][:8]}...`\n"
                        f"*User:* {query['user_name']}\n"
                        f"*Warehouse:* {query['warehouse_name']}\n"
                        f"*Duration:* {query['execution_time_sec']:.1f}s"
            }
        })
    
    # Send to Slack
    requests.post(SLACK_WEBHOOK, json={"blocks": blocks})

if __name__ == '__main__':
    check_long_running_queries(threshold_minutes=10)
```

### Grafana Integration (JSON Data Source)

You can integrate these APIs with Grafana using the JSON API data source plugin:

1. Install the "JSON API" data source plugin in Grafana
2. Configure a new data source with URL: `http://localhost:5000`
3. Create a dashboard with queries like:

**Credit Trends Panel:**
- URL Path: `/api/cost-trends?days=30`
- JSONPath: `$.data[*]`
- Fields: `date` (time), `total_credits` (number)

**Warehouse Costs Panel:**
- URL Path: `/api/warehouse-costs?days=30`
- JSONPath: `$.data[*]`
- Fields: `warehouse_name` (string), `total_credits` (number)

### Cron Job for Automated Monitoring

```bash
#!/bin/bash
# save as: /opt/snowflake-monitor/check_bottlenecks.sh

MONITOR_URL="http://localhost:5000"
ALERT_EMAIL="admin@company.com"

# Check for high queue times
QUEUE_DATA=$(curl -s "$MONITOR_URL/api/bottleneck-analysis" | jq '.data.queuing_issues')

# Check if any warehouse has avg queue time > 10 seconds
HIGH_QUEUE=$(echo $QUEUE_DATA | jq '[.[] | select(.avg_queue_time_sec > 10)] | length')

if [ "$HIGH_QUEUE" -gt 0 ]; then
    echo "High queue times detected" | mail -s "Snowflake Alert: Queue Times" $ALERT_EMAIL
fi
```

Add to crontab:
```bash
# Run every 15 minutes
*/15 * * * * /opt/snowflake-monitor/check_bottlenecks.sh
```

---

## Rate Limiting and Best Practices

1. **Caching**: Consider implementing client-side caching for endpoints that don't change frequently (e.g., `/api/warehouse-config`)

2. **Polling Frequency**: For dashboard auto-refresh, 30-60 second intervals are recommended

3. **Data Latency**: ACCOUNT_USAGE views have a 45-minute latency; real-time data is not available

4. **Batch Requests**: If you need multiple metrics, consider calling `/api/overview` first as it aggregates common metrics

5. **Error Retries**: Implement exponential backoff for failed requests

---

## Support

For issues or feature requests, please contact your Snowflake administrator or submit an issue to the project repository.
