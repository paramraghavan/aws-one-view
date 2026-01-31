# AWS Monitor - Complete Guide

## 📚 Table of Contents

1. [Quick Start](#quick-start)
2. [Features](#features)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Configuration](#configuration)
6. [API Reference](#api-reference)
7. [Troubleshooting](#troubleshooting)
8. [FAQ](#faq)

---

## Quick Start

### 30-Second Setup

```bash
# 1. Extract
tar -xzf aws_monitor_simple.tar.gz
cd aws_monitor_simple

# 2. Setup
./setup.sh

# 3. Start
./start.sh

# 4. Open browser
http://localhost:5000
```

---

## Features

### Core Features

✅ **Multi-Region Monitoring** - Monitor resources across all AWS regions
✅ **7 Resource Types** - EC2, RDS, S3, Lambda, EBS, EKS, EMR
✅ **Performance Metrics** - Real-time CloudWatch metrics (CPU, Network, Disk)
✅ **Memory Metrics** - Support for CloudWatch agent memory metrics
✅ **Cost Analysis** - Track spending by service and region
✅ **Health Scores** - Instant overview of resource health
✅ **Quick Filters** - Filter by status, resource type instantly
✅ **Real-Time Search** - Find resources by name or ID
✅ **CSV Export** - Download all data to Excel
✅ **Config-Based Monitoring** - YAML configs for scheduled jobs

### MVP Features

🔄 **Refresh Button** - One-click re-discovery
📥 **Export CSV** - Instant Excel download
🗑️ **Clear Results** - Clean workspace
🔍 **Search** - Find any resource in 2 seconds
📊 **Stats Dashboard** - Total, Running, Stopped counts
🏷️ **Filters** - All, Running, Stopped, by Type
⏰ **Timestamps** - Always know data freshness

---

## Installation

### Prerequisites

- Python 3.8+
- AWS CLI (optional but recommended)
- AWS credentials configured

### Setup

```bash
# Run setup script
./setup.sh
```

**What it does**:
- Creates virtual environment
- Installs dependencies (Flask, boto3, PyYAML)
- Creates directories (logs, output, configs)
- Checks AWS configuration

### AWS Credentials

```bash
# Configure AWS profile
aws configure --profile monitor

# Or manually edit ~/.aws/credentials
[monitor]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
region = us-east-1
```

### IAM Permissions Required

Minimum IAM policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
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
    ]
}
```

---

## Usage

### Start the App

```bash
./start.sh
```

**Options**:
```bash
# Custom port
./start.sh --port 8080

# Network access (WARNING: Use on trusted networks only!)
./start.sh --host 0.0.0.0

# With IAM role
./start.sh --role-arn arn:aws:iam::123456:role/MonitoringRole
```

### Basic Workflow

1. **Select Regions** - Choose regions to monitor
2. **Select Resource Types** - EC2, RDS, S3, etc.
3. **Add Filters** (optional) - Filter by tags, names, IDs
4. **Discover** - Click "Discover Resources"
5. **View Results** - See stats dashboard and resource list
6. **Interact** - Use filters, search, export

### Quick Actions

**After discovering**:

```
🔄 Refresh    - Re-discover with same settings
📥 Export     - Download CSV
🗑️ Clear      - Clear all results
```

### Filters

**One-click filtering**:
- **All** - Show everything
- **Running** - Only running/active resources
- **Stopped** - Only stopped resources
- **By Type** - EC2, RDS, S3, Lambda, etc.

### Search

**Real-time search**:
```
🔍 Search by name or ID...
```

Type to instantly filter:
- Resource names: "web-server"
- Resource IDs: "i-abc123"
- Status: "running"

---

## Configuration

### Config-Based Monitoring

Run monitoring jobs from YAML config files.

#### Create Config

**File**: `configs/my-monitoring.yaml`

```yaml
job_name: "production-monitoring"
aws_profile: "monitor"
regions:
  - us-east-1
  - us-west-2
resource_types:
  - ec2
  - rds
  - s3
filters:
  tags:
    Environment: production
checks:
  performance:
    enabled: true
    period: 300
  cost:
    enabled: true
    days: 7
output:
  console: true
  log_file: "logs/production.log"
  json_file: "output/production.json"
```

#### Run Config

```bash
# Run manually
python run_monitor.py configs/my-monitoring.yaml

# Multiple configs
python run_monitor.py configs/*.yaml

# All configs
python run_monitor.py --all
```

#### Schedule with Cron

```bash
# Edit crontab
crontab -e

# Add job (every 15 minutes)
*/15 * * * * cd /path/to/aws-monitor && python run_monitor.py configs/production.yaml >> logs/cron.log 2>&1

# Daily at 9 AM
0 9 * * * cd /path/to/aws-monitor && python run_monitor.py configs/daily-report.yaml

# Every 6 hours
0 */6 * * * cd /path/to/aws-monitor && python run_monitor.py configs/cost-tracking.yaml
```

---

## Memory Metrics

### EC2 Memory Metrics

**⚠️ Important**: EC2 does NOT provide memory metrics by default.

**Why**: EC2 instances are customer-managed, AWS doesn't have access to OS-level metrics.

**Solution**: Install CloudWatch agent

#### Setup CloudWatch Agent

```bash
# On EC2 instance
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -i amazon-cloudwatch-agent.rpm

# Configure
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard

# Start
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json
```

**After installation**:
- Memory metrics appear in AWS Monitor automatically
- Namespace: `CWAgent` (custom)
- Metrics: `mem_used_percent`, `mem_used`, `mem_available`

### RDS Memory Metrics

**✅ Available by default** - RDS is a managed service

RDS provides:
- `FreeableMemory` - Available memory in bytes
- No agent installation needed

---

## API Reference

See **[BOTO3_REFERENCE.md](BOTO3_REFERENCE.md)** for complete boto3 API documentation.

### Quick Reference

**Services Used**:
- EC2 (instances, volumes, regions)
- RDS (databases)
- S3 (buckets)
- Lambda (functions)
- EKS (Kubernetes clusters)
- EMR (analytics clusters)
- CloudWatch (metrics)
- Cost Explorer (costs)

**Total APIs**: 16 boto3 APIs

---

## Troubleshooting

### App Won't Start

**Check Python**:
```bash
python3 --version  # Need 3.8+
```

**Check Dependencies**:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

**Check Port**:
```bash
# See if port 5000 is in use
lsof -i :5000

# Use different port
./start.sh --port 8080
```

### AWS Credentials Not Working

**Test credentials**:
```bash
aws sts get-caller-identity --profile monitor
```

**Configure**:
```bash
aws configure --profile monitor
```

**Or edit manually**: `~/.aws/credentials`
```ini
[monitor]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
region = us-east-1
```

### No Resources Found

**Possible causes**:
1. No resources exist in selected regions
2. IAM permissions missing
3. Filters too restrictive
4. Selected wrong resource types

**Solutions**:
1. Try different regions
2. Check IAM policy
3. Remove filters
4. Select all resource types

### Memory Metrics Missing

**For EC2**:
- Memory requires CloudWatch agent
- Install agent on instances
- See [Memory Metrics Setup](#memory-metrics)

**For RDS**:
- Memory is available by default
- Check "Get Metrics" tab

### High Disk Usage

**Check sizes**:
```bash
du -sh logs/
du -sh output/
```

**Clean up**:
```bash
./deployment/cleanup-logs.sh
```

---

## FAQ

### General

**Q: Is this free?**
A: Yes, the tool is free. You only pay for AWS resources you monitor.

**Q: Does it modify my AWS resources?**
A: No, it's read-only. It only views resources, never modifies them.

**Q: Can I monitor multiple accounts?**
A: Yes, use IAM role assumption (see ROLE_ASSUMPTION.md).

**Q: Does it work on Windows?**
A: The Flask app works on Windows, but setup scripts are for Linux/Mac.

### Features

**Q: Can I get memory metrics?**
A: For EC2, install CloudWatch agent. For RDS, they're built-in.

**Q: Can I schedule monitoring?**
A: Yes, use config files with cron. See [Configuration](#configuration).

**Q: Can I export data?**
A: Yes, click "Export CSV" button for Excel download.

**Q: Can I filter results?**
A: Yes, use quick filters or search box for instant filtering.

### Performance

**Q: How fast is discovery?**
A: Depends on region/resource count. Typically 5-30 seconds.

**Q: Can I speed it up?**
A: Select fewer regions and resource types.

**Q: How often should I refresh?**
A: For monitoring: every 15-30 minutes. For analysis: as needed.

### Security

**Q: Is my data secure?**
A: Yes, all data stays on your machine. Nothing sent to external servers.

**Q: What permissions does it need?**
A: Read-only permissions for discovery, metrics, and costs. See [IAM Permissions](#iam-permissions-required).

**Q: Can I use it in production?**
A: Yes, it's designed for production use.

---

## Additional Resources

### Documentation

- **README.md** - Main documentation (this file)
- **ADMIN_GUIDE.md** - Admin/deployment guide
- **BOTO3_REFERENCE.md** - Complete boto3 API reference
- **CONFIG_MONITORING.md** - Config-based monitoring guide
- **TROUBLESHOOTING.md** - Detailed troubleshooting
- **ADMIN_QUICKREF.md** - Quick reference card
- **CONFIG_CHEATSHEET.md** - Config quick reference

### External Links

- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS CLI Setup](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
- [CloudWatch Agent](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)

---

## Support

**Issues?**
1. Check [Troubleshooting](#troubleshooting)
2. Check FAQ above
3. Review TROUBLESHOOTING.md

**Need more help?**
- Check documentation in `docs/` directory
- Review example configs in `configs/` directory

---

## Version

**Current Version**: 1.4.0 (MVP Release)

**Features**:
- Multi-region resource discovery
- 7 resource types
- Performance metrics (with memory support)
- Cost analysis
- Config-based monitoring
- Quick filters and search
- CSV export
- Health dashboard

---

## Summary

### What AWS Monitor Does

1. **Discovers** AWS resources across regions
2. **Shows** health scores and statuses
3. **Collects** CloudWatch metrics (CPU, memory*, network, disk)
4. **Analyzes** costs by service and region
5. **Exports** data to CSV
6. **Filters** results instantly
7. **Searches** resources in real-time
8. **Schedules** monitoring via configs

*Memory requires CloudWatch agent for EC2

### Why Use AWS Monitor

✅ **Fast** - See everything in one view
✅ **Simple** - No complex setup
✅ **Powerful** - Production-ready features
✅ **Flexible** - Web UI or config-based
✅ **Portable** - Runs anywhere Python runs
✅ **Safe** - Read-only, no modifications

---

**Get started in 30 seconds!**

```bash
./setup.sh && ./start.sh
```

**Happy monitoring!** 🚀
