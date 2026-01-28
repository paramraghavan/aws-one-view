# AWS Monitor - Simplified

A clean, simple AWS multi-region monitoring tool with support for EC2, RDS, S3, Lambda, EBS, Kubernetes (EKS), and EMR.

## Features

✅ **Multi-Region Monitoring**: Monitor resources across multiple AWS regions  
✅ **7 Resource Types**: EC2, RDS, S3, Lambda, EBS, Kubernetes (EKS), EMR  
✅ **Performance Metrics**: Real-time CloudWatch metrics  
✅ **Cost Analysis**: Track spending by service and region  
✅ **Alerts & Health**: Detect issues and failures  
✅ **Script Generator**: Create Python scripts for cron/scheduler  
✅ **Flexible Filtering**: Filter by tags, names, or IDs  
✅ **No Background Jobs**: On-demand monitoring only

## What's Different from Complex Versions?

This is a **simplified, clean version**:
- ❌ No background monitoring
- ❌ No database required
- ❌ No complex configuration files
- ❌ No automated actions (start/stop instances)
- ✅ Simple on-demand monitoring
- ✅ Easy script generation for scheduling
- ✅ Clean, focused UI
- ✅ Clear documentation

## Quick Start

### 1. Prerequisites

```bash
# Python 3.8+
python --version

# Install dependencies
pip install flask boto3
```

### 2. Configure AWS Profile

Create AWS profile named `monitor`:

```bash
aws configure --profile monitor
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

Or manually edit `~/.aws/credentials`:
```ini
[monitor]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
region = us-east-1
```

### 3. Run Application

**Basic usage** (using profile directly):
```bash
cd aws_monitor_simple
python main.py
```

**With IAM role assumption** (recommended for production):
```bash
python main.py --role-arn arn:aws:iam::123456789012:role/MonitoringRole
```

**With custom options**:
```bash
python main.py \
  --role-arn arn:aws:iam::123456789012:role/MonitoringRole \
  --session-name MySession \
  --port 8080 \
  --debug
```

Open browser: `http://localhost:5000`

### 4. Optional: IAM Role Assumption

For enhanced security and cross-account monitoring, you can use IAM role assumption. This allows:
- ✅ Using temporary credentials (expire after 1 hour)
- ✅ Separating authentication from authorization
- ✅ Cross-account resource monitoring
- ✅ Better audit trail and compliance

See **[docs/ROLE_ASSUMPTION.md](docs/ROLE_ASSUMPTION.md)** for detailed setup guide.

## Usage Guide

### Step 1: Select Regions
- Default: us-east-1 and us-west-2 are pre-selected
- Click "Load All Regions" to see all available regions
- Select/deselect regions as needed

**Note**: Your AWS profile has global access to all regions (if you have permissions)

### Step 2: Filter Resources (Optional)
Filter resources by:
- **Tags**: `Environment=production`, `Team=backend`
- **Names**: Comma-separated list
- **IDs**: Comma-separated list (instance IDs, volume IDs, etc.)

### Step 3: Discover Resources
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
- Detailed resource tables
- Select specific resources for metrics/alerts

### Step 4: Get Performance Metrics
1. Select resources using checkboxes
2. Choose metric period (5min, 15min, 1hr)
3. Click "📊 Get Metrics"

View metrics:
- **EC2**: CPU, Network, Disk I/O
- **RDS**: CPU, Connections, Storage, Latency
- **Lambda**: Invocations, Errors, Duration, Throttles
- **EMR**: Cluster idle status, Running apps

### Step 5: Analyze Costs
Click "💰 Analyze Costs" to see:
- Total costs for period (7, 30, or 90 days)
- Daily average spend
- Top 10 services by cost
- Cost breakdown by region

**Note**: Requires Cost Explorer API access

### Step 6: Check Alerts & Health
1. Select resources using checkboxes
2. Set thresholds (CPU: 80%, Memory: 85%)
3. Click "⚠️ Check Alerts"

Alerts detect:
- High CPU utilization
- Lambda errors
- RDS connection issues
- RDS Multi-AZ not configured
- EKS node group issues

### Step 7: Generate Monitoring Script
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

### No Resources Found
- Check AWS profile configuration: `aws configure --profile monitor`
- Verify IAM permissions
- Ensure resources exist in selected regions

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
