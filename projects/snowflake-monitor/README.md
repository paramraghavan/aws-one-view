# ❄️ Snowflake Resource Monitor

A comprehensive Flask-based monitoring dashboard for Snowflake administrators to track costs, identify performance bottlenecks, and optimize resource utilization.

![Dashboard Preview](https://img.shields.io/badge/Python-3.9+-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3+-green?style=flat-square&logo=flask)
![Snowflake](https://img.shields.io/badge/Snowflake-Connector-29B5E8?style=flat-square&logo=snowflake)

## 🎯 Features

### ⚙️ Configurable Thresholds (MVP Feature)
All monitoring thresholds are configurable via the Settings panel:

| Threshold | Default | Description |
|-----------|---------|-------------|
| Slow Query | 30s | Queries slower than this are flagged |
| Full Scan | 90% | Partition scan threshold for full table scan detection |
| Compilation Warning | 5s | High compilation time warning |
| Queue Time Warning | 10s | Queue time warning threshold |
| Queue Time Critical | 30s | Queue time critical threshold |
| Local Spill Warning | 50 GB | Local disk spill warning |
| Remote Spill Critical | 10 GB | Remote storage spill (expensive!) |
| Failures Warning | 20 | Query failure count for warning |
| Failures Critical | 100 | Query failure count for critical |

### 💡 Interactive Tooltips
Hover over any metric or column header to see detailed explanations:
- What the metric means
- Why it matters
- Recommended actions
- Cost implications

### Cost Analysis
- **Credit usage tracking** - Monitor total credits consumed over customizable time periods
- **Warehouse cost breakdown** - See which warehouses are consuming the most credits
- **Database cost analysis** - Track resource usage by database
- **Hourly usage patterns** - Identify peak usage times for cost optimization
- **Cost trends** - Visualize spending patterns over 30/60/90 days

### Query Performance
- **Long-running queries** - Identify queries exceeding duration thresholds
- **Expensive queries** - Find queries consuming the most resources
- **Queued queries** - Detect concurrency bottlenecks
- **Query details modal** - View full query text for any query

### Warehouse Management
- **Warehouse configurations** - View all warehouse settings at a glance
- **Cluster concurrency** - Monitor how many queries run simultaneously per warehouse
  - High concurrency with queuing → Need more clusters or larger warehouse
  - Consistently low concurrency → May be over-provisioned, consider downsizing
  - Spiky patterns → Use STANDARD scaling policy for fast response
- **Auto-suspend settings** - Ensure warehouses are configured efficiently
- **State monitoring** - Track warehouse running/suspended states
- **Size guide** - Credits/hour: X-Small=1, Small=2, Medium=4, Large=8, X-Large=16

### Bottleneck Detection
- **Query queuing analysis** - Identify warehouses with queue backlogs
- **Disk spilling detection** - Find queries spilling to local/remote storage
- **Compilation time analysis** - Detect queries with high compilation overhead
- **Failure tracking** - Monitor query failures by error type

### Recommendations
- **Auto-generated insights** - Get actionable optimization suggestions
- **Right-sizing recommendations** - Identify over/under-provisioned warehouses
- **Cost optimization tips** - Reduce spending with targeted advice

## 📋 Prerequisites

- Python 3.9+
- Snowflake account with ACCOUNTADMIN role (or appropriate privileges)
- Access to `SNOWFLAKE.ACCOUNT_USAGE` schema

### Required Snowflake Privileges

The monitoring user needs access to the following views in `SNOWFLAKE.ACCOUNT_USAGE`:

```sql
-- Grant necessary privileges
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE your_role;
```

Or specifically:
- `WAREHOUSE_METERING_HISTORY`
- `WAREHOUSE_LOAD_HISTORY`
- `QUERY_HISTORY`
- `DATABASE_STORAGE_USAGE_HISTORY`
- `WAREHOUSES`

## 🚀 Installation

### 1. Clone/Download the Application

```bash
# Create project directory
mkdir snowflake-monitor
cd snowflake-monitor
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Snowflake Credentials

#### Option A: Environment Variables (Recommended)

```bash
export SNOWFLAKE_ACCOUNT="your_account_identifier"
export SNOWFLAKE_USER="your_username"
export SNOWFLAKE_PASSWORD="your_password"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
export SNOWFLAKE_DATABASE="SNOWFLAKE"
export SNOWFLAKE_SCHEMA="ACCOUNT_USAGE"
export SNOWFLAKE_ROLE="ACCOUNTADMIN"
```

#### Option B: Create a `.env` file

```bash
# .env
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SNOWFLAKE
SNOWFLAKE_SCHEMA=ACCOUNT_USAGE
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

Then modify `app.py` to use `python-dotenv`:

```python
from dotenv import load_dotenv
load_dotenv()
```

#### Option C: Direct Configuration

Edit the `SNOWFLAKE_CONFIG` dictionary in `app.py`:

```python
SNOWFLAKE_CONFIG = {
    'account': 'your_account_identifier',
    'user': 'your_username',
    'password': 'your_password',
    'warehouse': 'COMPUTE_WH',
    'database': 'SNOWFLAKE',
    'schema': 'ACCOUNT_USAGE',
    'role': 'ACCOUNTADMIN'
}
```

### 4. Run the Application

```bash
python app.py
```

The dashboard will be available at `http://localhost:5000`

## 📁 Project Structure

```
snowflake-monitor/
├── app.py                    # Main Flask application
├── snowflake_connector.py    # Snowflake queries and data access
├── requirements.txt          # Python dependencies
├── templates/
│   └── dashboard.html        # Main dashboard template
└── static/
    ├── css/
    │   └── style.css         # Dashboard styling
    └── js/
        └── app.js            # Frontend JavaScript
```

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/api/overview` | GET | High-level metrics |
| `/api/warehouse-costs` | GET | Warehouse cost breakdown |
| `/api/warehouse-usage` | GET | Warehouse usage statistics |
| `/api/long-running-queries` | GET | Queries exceeding threshold |
| `/api/expensive-queries` | GET | Most resource-intensive queries |
| `/api/storage-usage` | GET | Storage by database |
| `/api/cluster-load` | GET | Cluster concurrency metrics |
| `/api/warehouse-config` | GET | Warehouse configurations |
| `/api/query-patterns` | GET | Query pattern analysis |
| `/api/cost-trends` | GET | Daily cost trends |
| `/api/bottleneck-analysis` | GET | Comprehensive bottleneck analysis |
| `/api/database-costs` | GET | Cost by database |
| `/api/recommendations` | GET | Optimization recommendations |
| `/api/queued-queries` | GET | Queries with queue time |
| `/api/credit-usage-hourly` | GET | Hourly usage patterns |

### Query Parameters

Most endpoints accept optional query parameters:

- `days` - Number of days to look back (default: 7 or 30)
- `threshold` - Duration threshold in seconds (for queries)
- `limit` - Maximum results to return

Example:
```
/api/long-running-queries?threshold=120&limit=100
```

## 🎨 Dashboard Sections

### Overview
- Total credits (30 days)
- Storage utilization
- Query count (24h)
- Active warehouses
- Average query time
- Failed queries

### Cost Analysis
- Warehouse cost breakdown (stacked bar chart)
- Database cost distribution (pie chart)
- Hourly usage patterns (bar chart)
- Detailed warehouse cost table

### Query Performance
- Long-running queries table
- Most expensive queries table
- Queued queries table
- Click any query ID to view full SQL

### Warehouses
- Complete warehouse configuration table
- Cluster concurrency timeline chart
- Auto-suspend/resume settings

### Bottlenecks
- Query queuing analysis
- Disk spilling detection
- High compilation time queries
- Query failure breakdown
- Query volume by hour
- Query type distribution

### Recommendations
- Auto-generated optimization suggestions
- Severity-coded cards (High/Medium/Low)
- Actionable improvement steps

## 🔧 Customization

### Modify Thresholds

Edit `snowflake_connector.py` to adjust detection thresholds:

```python
# In get_recommendations method
- Auto-suspend threshold: 300 seconds
- Queue time threshold: 10 seconds
- Spill threshold: 1GB
- Compilation time threshold: 5 seconds
```

### Add Custom Queries

Add new methods to `SnowflakeMonitor` class:

```python
def get_custom_metric(self) -> List[Dict]:
    query = """
    SELECT ...
    FROM SNOWFLAKE.ACCOUNT_USAGE.YOUR_VIEW
    """
    return self._serialize_results(self.execute_query(query))
```

Then add a corresponding API endpoint in `app.py`.

### Styling

Modify `static/css/style.css` to change:
- Color palette (CSS variables at top)
- Layout and spacing
- Chart colors

## 🔒 Security Considerations

1. **Never commit credentials** - Use environment variables
2. **Use read-only roles** - Create a dedicated monitoring role
3. **Network security** - Run behind a reverse proxy in production
4. **HTTPS** - Enable SSL/TLS for production deployments

### Create a Read-Only Monitoring Role

```sql
-- Create a dedicated monitoring role
CREATE ROLE SNOWFLAKE_MONITOR_ROLE;

-- Grant access to account usage
GRANT IMPORTED PRIVILEGES ON DATABASE SNOWFLAKE TO ROLE SNOWFLAKE_MONITOR_ROLE;

-- Grant usage on a small warehouse
GRANT USAGE ON WAREHOUSE MONITORING_WH TO ROLE SNOWFLAKE_MONITOR_ROLE;

-- Assign to user
GRANT ROLE SNOWFLAKE_MONITOR_ROLE TO USER monitor_user;
```

## 🐳 Docker Deployment (Optional)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000
CMD ["python", "app.py"]
```

Build and run:

```bash
docker build -t snowflake-monitor .
docker run -p 5000:5000 \
  -e SNOWFLAKE_ACCOUNT=xxx \
  -e SNOWFLAKE_USER=xxx \
  -e SNOWFLAKE_PASSWORD=xxx \
  snowflake-monitor
```

## 📊 Metrics Explained

### Credits
- **Compute Credits**: Processing resources used
- **Cloud Services Credits**: Metadata operations, query parsing, etc.

### Bottleneck Types
- **Queuing**: Queries waiting for warehouse resources
- **Spilling**: Queries exceeding memory, writing to disk
- **Compilation**: Time to parse and optimize queries
- **Provisioning**: Time to start/scale warehouse

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

MIT License - feel free to use and modify for your needs.

## 🆘 Troubleshooting

### Common Issues

**Connection Errors**
- Verify account identifier format (e.g., `abc12345.us-east-1`)
- Check network connectivity to Snowflake
- Ensure role has required privileges

**No Data Showing**
- ACCOUNT_USAGE views have 45-minute latency
- Verify queries are running in your account
- Check the selected time range

**Slow Dashboard**
- Reduce time range for queries
- Consider creating a dedicated XS warehouse for monitoring
- Cache results for frequently accessed data

---

Built with ❄️ for Snowflake Administrators
