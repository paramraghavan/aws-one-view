# AWS Monitor - Simple & Powerful

A clean, production-ready AWS monitoring tool with web UI and scheduled monitoring support.

## ✨ Features

✅ **Multi-Region Discovery** - Monitor EC2, RDS, S3, Lambda, EBS, EKS, EMR across all regions  
✅ **Performance Metrics** - CPU, Network, Disk, Memory* (*with CloudWatch agent)  
✅ **Cost Analysis** - Track spending by service and region  
✅ **Health Dashboard** - Instant overview with stats and filters  
✅ **Real-Time Search** - Find resources by name or ID in seconds  
✅ **Quick Filters** - Filter by status (Running/Stopped) or resource type  
✅ **CSV Export** - Download all data to Excel with one click  
✅ **Config-Based** - YAML configs for scheduled monitoring with cron  
✅ **IAM Role Support** - Cross-account monitoring via role assumption  

---

## 🚀 Quick Start (30 Seconds)

```bash
# 1. Extract and setup
tar -xzf aws_monitor_simple.tar.gz
cd aws_monitor_simple
./setup.sh

# 2. Configure AWS credentials
aws configure --profile monitor

# 3. Start the web UI
./start.sh

# 4. Open browser
http://localhost:5000
```

**That's it!** No Docker, no services, just a simple Flask app.

---

## 📖 Documentation

### Essential Guides

| Document | Description |
|----------|-------------|
| **[COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)** | Complete user guide - everything you need |
| **[BOTO3_REFERENCE.md](docs/BOTO3_REFERENCE.md)** | All boto3 APIs used, with examples |
| **[CONFIG_MONITORING.md](docs/CONFIG_MONITORING.md)** | Schedule monitoring with YAML configs |
| **[ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)** | Deployment and maintenance guide |

### Quick References

| Document | Description |
|----------|-------------|
| **[ADMIN_QUICKREF.md](docs/ADMIN_QUICKREF.md)** | One-page admin command reference |
| **[CONFIG_CHEATSHEET.md](docs/CONFIG_CHEATSHEET.md)** | Quick config examples |
| **[docs/README.md](docs/README.md)** | Complete documentation index |

### Specialized Topics

| Document | Description |
|----------|-------------|
| **[ROLE_ASSUMPTION.md](docs/ROLE_ASSUMPTION.md)** | Cross-account monitoring setup |
| **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** | Common issues and solutions |
| **[MVP_FEATURES.md](docs/MVP_FEATURES.md)** | All MVP features explained |

---

## 💡 Common Tasks

### Start the App

```bash
# Basic
./start.sh

# Custom port
./start.sh --port 8080

# With IAM role
./start.sh --role-arn arn:aws:iam::123456:role/MonitoringRole
```

### Schedule Monitoring

```bash
# Create config file
cp configs/production-monitoring.yaml configs/my-monitoring.yaml
# Edit config as needed

# Run manually
python run_monitor.py configs/my-monitoring.yaml

# Schedule with cron
crontab -e
# Add: */15 * * * * cd /path/to/aws-monitor && python run_monitor.py configs/my-monitoring.yaml
```

### Use the Web UI

1. **Discover** - Select regions and resource types, click "Discover Resources"
2. **View Stats** - See total resources, running count, stopped count
3. **Filter** - Click "Running", "Stopped", or resource type (EC2, RDS, etc.)
4. **Search** - Type name or ID in search box
5. **Export** - Click "Export CSV" to download data
6. **Refresh** - Click "Refresh" to update data

---

## 🔧 Requirements

- **Python 3.8+**
- **AWS CLI** (optional but recommended)
- **AWS Credentials** configured

### IAM Permissions Needed

```json
{
    "Effect": "Allow",
    "Action": [
        "ec2:DescribeRegions",
        "ec2:DescribeInstances",
        "ec2:DescribeVolumes",
        "rds:DescribeDBInstances",
        "s3:ListAllMyBuckets",
        "s3:GetBucketLocation",
        "s3:GetBucketTagging",
        "lambda:ListFunctions",
        "lambda:ListTags",
        "eks:ListClusters",
        "eks:DescribeCluster",
        "elasticmapreduce:ListClusters",
        "elasticmapreduce:DescribeCluster",
        "cloudwatch:GetMetricStatistics",
        "ce:GetCostAndUsage"
    ],
    "Resource": "*"
}
```

See **[COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)** for complete IAM policy.

---

## 📊 CloudWatch Metrics

### Available by Default

**EC2**: CPU, Network, Disk  
**RDS**: CPU, Connections, Storage, Latency, **Memory** ✅  
**Lambda**: Invocations, Errors, Duration, Throttles  

### Memory Metrics for EC2

**⚠️ EC2 memory requires CloudWatch agent installation.**

EC2 instances are customer-managed, so AWS doesn't have access to memory metrics by default.

**Quick setup:**
```bash
# On EC2 instance
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -i amazon-cloudwatch-agent.rpm
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard
```

After installation, memory metrics appear automatically in AWS Monitor.

See **[BOTO3_REFERENCE.md](docs/BOTO3_REFERENCE.md)** for complete setup instructions.

---

## 🎯 Use Cases

### Interactive Monitoring
Start the web UI and explore your infrastructure visually.

### Scheduled Monitoring  
Create YAML configs and schedule with cron for automated monitoring.

### Cost Tracking
Run cost analysis daily to track spending trends.

### Cross-Account Monitoring
Use IAM role assumption to monitor multiple AWS accounts.

### Health Checks
Quick filters show running vs stopped resources at a glance.

### Compliance Auditing
Export all resources to CSV for compliance reports.

---

## 🏗️ Architecture

**Simple & Clean**:
- Flask web application (main.py)
- Boto3 for AWS API calls
- YAML configs for scheduled jobs
- No database required
- No background processes
- All data in memory or JSON files

---

## 🔐 Security

- ✅ **Read-only** - Never modifies AWS resources
- ✅ **Local** - All data stays on your machine
- ✅ **IAM Roles** - Support for temporary credentials
- ✅ **No External** - No data sent to external servers
- ✅ **Credentials** - Uses standard AWS credential chain

---

## 🐛 Troubleshooting

### App Won't Start

```bash
# Check Python version
python3 --version  # Need 3.8+

# Check dependencies
source venv/bin/activate
pip install -r requirements.txt

# Check port
lsof -i :5000  # See if port in use
./start.sh --port 8080  # Use different port
```

### No Resources Found

- Check AWS credentials: `aws sts get-caller-identity --profile monitor`
- Check IAM permissions (see above)
- Try different regions
- Remove filters

### Memory Metrics Missing

- **EC2**: Requires CloudWatch agent (see above)
- **RDS**: Available by default

See **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** for complete guide.

---

## 📦 What's Included

```
aws_monitor_simple/
├── start.sh                 # Start the web UI
├── setup.sh                 # First-time setup
├── main.py                  # Flask application
├── run_monitor.py           # Config-based monitoring
├── app/                     # Application code
│   └── resources.py         # AWS API calls (boto3)
├── configs/                 # Example YAML configs
├── docs/                    # Complete documentation
│   ├── COMPLETE_GUIDE.md   # Master guide
│   ├── BOTO3_REFERENCE.md  # API reference
│   ├── ADMIN_GUIDE.md      # Admin manual
│   └── ...more docs
├── deployment/              # Helper scripts
│   ├── backup.sh
│   ├── cleanup-logs.sh
│   ├── check-status.sh
│   └── validate-config.py
└── static/                  # Web UI assets
```

---

## 📈 Version

**Current**: 1.4.0 (MVP Release)

**New in 1.4.0**:
- Quick stats dashboard (Total, Running, Stopped)
- Real-time search (find resources instantly)
- Quick filters (Running, Stopped, by type)
- Quick actions (Refresh, Export CSV, Clear)
- Empty state handling
- Memory metrics support (with CloudWatch agent)
- Improved cost analysis display
- Enhanced clickable metrics
- Complete boto3 API reference
- Consolidated documentation

---

## 🎉 Why AWS Monitor?

**Simple**: No Docker, no database, no complex setup  
**Fast**: Discover resources in seconds  
**Powerful**: Production-ready features  
**Flexible**: Web UI or config-based monitoring  
**Complete**: Comprehensive documentation  
**Safe**: Read-only, no resource modifications  

---

## 📚 Learn More

- **New User?** Start with **[COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)**
- **Deploying?** Read **[ADMIN_GUIDE.md](docs/ADMIN_GUIDE.md)**
- **Scheduling?** See **[CONFIG_MONITORING.md](docs/CONFIG_MONITORING.md)**
- **Developing?** Check **[BOTO3_REFERENCE.md](docs/BOTO3_REFERENCE.md)**
- **All Docs**: **[docs/README.md](docs/README.md)**

---

**Get started in 30 seconds!**

```bash
./setup.sh && ./start.sh
```

**Happy monitoring!** 🚀

- ✅ Better audit trail and compliance

See **[docs/ROLE_ASSUMPTION.md](docs/ROLE_ASSUMPTION.md)** for detailed setup guide.

## Usage Guide

### Step 1: Select Regions
- Default: us-east-1 and us-west-2 are pre-selected
- Click "Load All Regions" to see all available regions
- Select/deselect regions as needed

**Note**: Your AWS profile has global access to all regions (if you have permissions)

### Step 2: Select Resource Types
- **NEW**: Choose which resource types to discover
- Options: EC2, RDS, S3, Lambda, EBS, EKS, EMR
- Quick buttons:
  - **Select All**: Discover all resource types
  - **Deselect All**: Clear all selections
  - **Common Only**: Select EC2, RDS, S3 (most common)

**Benefits**:
- ⚡ Faster discovery (only scan what you need)
- 🎯 Focused results (no noise from unused resources)
- 💰 Fewer API calls (better rate limit usage)

**Example**: Select only EC2 and RDS for 83% faster discovery

### Step 3: Filter Resources (Optional)
Filter resources by:
- **Tags**: `Environment=production`, `Team=backend`
- **Names**: Comma-separated list
- **IDs**: Comma-separated list (instance IDs, volume IDs, etc.)

### Step 4: Discover Resources
Click "🔍 Discover Resources" to scan selected regions for:
- EC2 instances
- RDS databases
- S3 buckets
- Lambda functions
- EBS volumes
- EKS clusters (Kubernetes)
- EMR clusters

Results show:
- Resource summary by type
- Detailed resource tables (grouped by type, collapsible)
- Select specific resources for metrics/alerts

**NEW**: Click "Details" button to see complete resource information!

### Step 5: Get Performance Metrics
1. Select resources using checkboxes
2. Choose metric period (5min, 15min, 1hr)
3. Click "📊 Get Metrics"

View metrics:
- **EC2**: CPU, Network, Disk I/O
- **RDS**: CPU, Connections, Storage, Latency
- **Lambda**: Invocations, Errors, Duration, Throttles
- **EMR**: Cluster idle status, Running apps

**NEW**: Click any metric item to see detailed breakdown!

**NEW**: Click any metric item to see detailed breakdown!

### Step 6: Analyze Costs
Click "💰 Analyze Costs" to see:
- Total costs for period (7, 30, or 90 days)
- Daily average spend
- Top 10 services by cost
- Cost breakdown by region

**Note**: Requires Cost Explorer API access

### Step 7: Check Alerts & Health
1. Select resources using checkboxes
2. Set thresholds (CPU: 80%, Memory: 85%)
3. Click "⚠️ Check Alerts"

Alerts detect:
- High CPU utilization
- Lambda errors
- RDS connection issues
- RDS Multi-AZ not configured
- EKS node group issues

### Step 8: Generate Monitoring Script
Create a Python script to schedule with cron or Python scheduler:

1. Select regions to monitor
2. Choose resource types (EC2, RDS, Lambda, EKS, EMR)
3. Select resource filters (tags, names, IDs)
4. Choose checks (Performance, Cost, Alerts)
5. Set thresholds
6. Enter email for notifications (optional)
7. Click "📝 Generate Script"

Script downloads as `aws_monitor_job.py`.

**Schedule with Cron:**
```bash
# Every 5 minutes
*/5 * * * * /usr/bin/python3 /path/to/aws_monitor_job.py >> /var/log/aws_monitor.log 2>&1

# Every hour
0 * * * * /usr/bin/python3 /path/to/aws_monitor_job.py

# Daily at 8 AM
0 8 * * * /usr/bin/python3 /path/to/aws_monitor_job.py
```

**Schedule with Python APScheduler:**
```python
from apscheduler.schedulers.blocking import BlockingScheduler
from aws_monitor_job import main

scheduler = BlockingScheduler()
scheduler.add_job(main, 'interval', minutes=5)
scheduler.start()
```

## Architecture

```
aws_monitor_simple/
├── main.py                  # Flask application
├── app/
│   ├── resources.py         # Resource discovery and monitoring
│   └── script_generator.py  # Script generation
├── templates/
│   └── index.html           # Web UI
├── static/
│   ├── css/style.css        # Styling
│   └── js/app.js            # UI logic
├── docs/
│   └── BOTO3_API_REFERENCE.md  # Complete boto3 API documentation
└── README.md
```

## API Endpoints

### GET /
Main dashboard UI

### POST /api/discover
Discover resources across regions
```json
{
  "regions": ["us-east-1", "us-west-2"],
  "filters": {
    "tags": {"Environment": "production"},
    "names": ["web-server"],
    "ids": ["i-1234567"]
  }
}
```

### POST /api/metrics
Get performance metrics
```json
{
  "resources": [
    {"type": "ec2", "id": "i-1234567", "region": "us-east-1"}
  ],
  "period": 300
}
```

### POST /api/costs
Analyze costs
```json
{
  "regions": ["us-east-1"],
  "days": 7
}
```

### POST /api/alerts
Check alerts
```json
{
  "resources": [...],
  "thresholds": {"cpu": 80, "memory": 85}
}
```

### POST /api/generate-script
Generate monitoring script (downloads file)
```json
{
  "regions": ["us-east-1"],
  "resources": {
    "types": ["ec2", "rds"],
    "filters": {...}
  },
  "checks": ["performance", "cost", "alerts"],
  "thresholds": {...},
  "notification": {"email": "admin@example.com"}
}
```

### GET /api/regions
Get available AWS regions

## AWS Permissions

The `monitor` profile needs these IAM permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeRegions",
      "ec2:DescribeInstances",
      "ec2:DescribeVolumes",
      "rds:DescribeDBInstances",
      "rds:ListTagsForResource",
      "s3:ListAllMyBuckets",
      "s3:GetBucketLocation",
      "s3:GetBucketTagging",
      "lambda:ListFunctions",
      "lambda:ListTags",
      "eks:ListClusters",
      "eks:DescribeCluster",
      "eks:ListNodegroups",
      "eks:DescribeNodegroup",
      "elasticmapreduce:ListClusters",
      "elasticmapreduce:DescribeCluster",
      "cloudwatch:GetMetricStatistics",
      "ce:GetCostAndUsage",
      "iam:GetUser"
    ],
    "Resource": "*"
  }]
}
```

**Note**: These are read-only permissions. The monitor cannot modify resources.

## Region Access FAQ

**Q**: When the UI auto-selects us-east-1 and us-west-2, does my AWS profile need special access?

**A**: No. AWS IAM permissions are **global**. If your `monitor` profile has the permissions above, it can access resources in **all AWS regions**. Regions are not separately access-controlled.

However:
- Some newer regions require opt-in (Middle East, Africa)
- If you haven't opted in, API calls to those regions will fail
- The application handles this gracefully

## Supported Resource Types

| Type | Discovery | Metrics | Alerts | Notes |
|------|-----------|---------|--------|-------|
| EC2 | ✅ | ✅ | ✅ | Instances |
| RDS | ✅ | ✅ | ✅ | Databases, Multi-AZ check |
| S3 | ✅ | ❌ | ❌ | Buckets (global) |
| Lambda | ✅ | ✅ | ✅ | Functions |
| EBS | ✅ | ❌ | ❌ | Volumes, encryption check |
| EKS | ✅ | ⚠️ | ✅ | Kubernetes clusters, node groups |
| EMR | ✅ | ✅ | ❌ | Hadoop/Spark clusters |

⚠️ EKS metrics require Container Insights to be enabled

## Troubleshooting

### Download Blocked / Insecure Connection Error
**Problem:** Browser blocks script downloads with "insecure connection" error

**Solution:** Run with HTTPS
```bash
./generate_cert.sh  # One-time setup
python main.py --ssl
# Access: https://localhost:5000
```

**See:** [QUICK_FIX_DOWNLOADS.md](QUICK_FIX_DOWNLOADS.md) for detailed solutions

### No Resources Found
- Check AWS profile configuration: `aws configure --profile monitor`
- Verify IAM permissions
- Ensure resources exist in selected regions
- Try without filters first

### EKS Not Showing
- Verify EKS clusters exist: `aws eks list-clusters --region us-east-1 --profile monitor`
- Check IAM permissions for EKS (ListClusters, DescribeCluster)
- EKS may not be available in all regions

### Cost Explorer Error
- Enable Cost Explorer in AWS Console (takes 24 hours)
- Ensure `ce:GetCostAndUsage` permission

### Region Access Error
- Check if region requires opt-in
- Verify profile has access to that region

### Script Won't Run
- Check Python version (3.8+)
- Install dependencies: `pip install boto3`
- Verify AWS credentials are configured

### Can't See Resource Details
- Click "Details" button in the Actions column
- Resource sections start collapsed - click headers to expand
- Metric items are clickable - click for detailed information

**See [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for complete troubleshooting guide**

## Development

Run in debug mode:
```bash
export FLASK_ENV=development
python main.py
```

Run tests:
```bash
# TODO: Add tests
```

## Documentation

- **[BOTO3_API_REFERENCE.md](docs/BOTO3_API_REFERENCE.md)**: Complete guide to all boto3 APIs used
  - Every API call explained
  - Parameters and return values
  - Common patterns and best practices
  - Region access explained

## License

MIT License - Feel free to modify and use as needed

## Support

For issues or questions:
1. Check [BOTO3_API_REFERENCE.md](docs/BOTO3_API_REFERENCE.md) for API details
2. Verify AWS permissions
3. Check CloudWatch and Cost Explorer access
4. Review generated script for errors

## Roadmap

Future enhancements (not included in simplified version):
- Database storage for historical data
- Advanced alerting with SNS/Email
- Resource recommendations
- Cost optimization suggestions
- Custom dashboards
- Multi-account support
