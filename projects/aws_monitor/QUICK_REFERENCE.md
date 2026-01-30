# Quick Reference

## Setup (One Time)

```bash
# 1. Configure AWS profile
aws configure --profile monitor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start application

# Basic (using profile directly)
python main.py

# With IAM role assumption (recommended for production)
python main.py --role-arn arn:aws:iam::123456789012:role/MonitoringRole

# With custom options
python main.py \
  --role-arn arn:aws:iam::123456789012:role/MonitoringRole \
  --session-name MySession \
  --port 8080 \
  --debug

# 4. Open browser
http://localhost:5000
```

## Command Line Options

```bash
# View all options
python main.py --help

# Common options
--role-arn        ARN of IAM role to assume (optional)
--session-name    Session name for role assumption (default: AWSMonitorSession)
--port           Port to run on (default: 5000)
--host           Host to bind to (default: 0.0.0.0)
--debug          Enable debug mode
```

## Common Tasks

### Monitor Production Resources
1. Select regions: us-east-1, us-west-2
2. Filter by tag: `Environment = production`
3. Click "Discover Resources"
4. Select resources
5. Click "Get Metrics"

### Check Costs
1. Select regions
2. Choose period: 7, 30, or 90 days
3. Click "Analyze Costs"
4. View spending by service and region

### Generate Monitoring Script
1. Select regions and resource types
2. Add filters (optional)
3. Choose checks: Performance, Cost, Alerts
4. Set thresholds
5. Enter email (optional)
6. Click "Generate Script"
7. Save as `aws_monitor_job.py`

### Schedule with Cron
```bash
# Edit crontab
crontab -e

# Add line (every 5 minutes)
*/5 * * * * /usr/bin/python3 /path/to/aws_monitor_job.py >> /var/log/aws_monitor.log 2>&1

# Save and exit
```

### Schedule with Python
```python
from apscheduler.schedulers.blocking import BlockingScheduler
from aws_monitor_job import main

scheduler = BlockingScheduler()
scheduler.add_job(main, 'interval', minutes=5)
scheduler.start()
```

## Filtering Examples

### By Tag
```
Tag Key: Environment
Tag Value: production
```

### By Multiple Names
```
Names: web-server, api-server, db-master
```

### By Multiple IDs
```
IDs: i-1234567, i-7654321, vol-abc123
```

## API Calls (For Scripts)

### Discover Resources
```bash
curl -X POST http://localhost:5000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"regions": ["us-east-1"], "filters": {}}'
```

### Get Metrics
```bash
curl -X POST http://localhost:5000/api/metrics \
  -H "Content-Type: application/json" \
  -d '{
    "resources": [{"type": "ec2", "id": "i-123", "region": "us-east-1"}],
    "period": 300
  }'
```

### Analyze Costs
```bash
curl -X POST http://localhost:5000/api/costs \
  -H "Content-Type: application/json" \
  -d '{"regions": ["us-east-1"], "days": 7}'
```

## Troubleshooting

### No Resources Found
```bash
# Check AWS credentials
aws sts get-caller-identity --profile monitor

# List regions
aws ec2 describe-regions --profile monitor

# Test EC2 access
aws ec2 describe-instances --profile monitor --region us-east-1
```

### Cost Explorer Not Working
```bash
# Enable in AWS Console:
# Billing → Cost Explorer → Enable

# Wait 24 hours for data to populate
```

### Script Generation Fails
```bash
# Check Flask is running
curl http://localhost:5000/api/health

# Check write permissions
ls -la /path/to/download/directory
```

## Resource Types

| Type | Example ID | Example Name |
|------|-----------|--------------|
| EC2 | i-1234567890abcdef0 | web-server |
| RDS | database-1 | prod-db |
| S3 | my-bucket-name | logs-bucket |
| Lambda | my-function | data-processor |
| EBS | vol-1234567890abcdef0 | data-volume |
| EKS | my-cluster | prod-k8s |
| EMR | j-1234567890ABC | spark-cluster |

## CloudWatch Metrics

### EC2
- CPUUtilization (%)
- NetworkIn/Out (bytes)
- DiskReadBytes/DiskWriteBytes

### RDS
- CPUUtilization (%)
- DatabaseConnections (count)
- FreeStorageSpace (bytes)
- ReadLatency/WriteLatency (ms)

### Lambda
- Invocations (count)
- Errors (count)
- Duration (ms)
- Throttles (count)

### EMR
- IsIdle (0/1)
- ContainerPending (count)
- AppsRunning (count)

## Alert Thresholds

| Metric | Default | Recommended |
|--------|---------|-------------|
| CPU | 80% | 70-85% |
| Memory | 85% | 80-90% |
| DB Connections | 100 | 70-80% of max |
| Disk | 90% | 85-90% |

## Cron Syntax

```
* * * * * command
│ │ │ │ │
│ │ │ │ └─ Day of week (0-7)
│ │ │ └─── Month (1-12)
│ │ └───── Day (1-31)
│ └─────── Hour (0-23)
└───────── Minute (0-59)
```

### Examples
```
*/5 * * * *    Every 5 minutes
0 * * * *      Every hour
0 9 * * *      Daily at 9 AM
0 9 * * 1-5    Weekdays at 9 AM
0 0 1 * *      First of month at midnight
```

## IAM Permissions Quick Check

```bash
# Test EC2 access
aws ec2 describe-instances --profile monitor --region us-east-1

# Test RDS access
aws rds describe-db-instances --profile monitor --region us-east-1

# Test Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-02 \
  --granularity DAILY \
  --metrics UnblendedCost \
  --profile monitor
```

## File Locations

```
~/.aws/credentials    AWS credentials
~/.aws/config        AWS configuration
/var/log/aws_monitor.log    Monitor logs (cron)
/tmp/aws_monitor_*.json     Script output files
```

## Support

1. Check README.md for setup
2. Check BOTO3_API_REFERENCE.md for API details
3. Check CHANGELOG.md for what changed
4. Verify AWS permissions
5. Test AWS CLI access

## Quick Debug

```bash
# Check Python version
python3 --version

# Check dependencies
pip list | grep -E '(flask|boto3)'

# Check AWS profile
cat ~/.aws/credentials | grep -A 3 "\[monitor\]"

# Test AWS connectivity
python3 -c "import boto3; print(boto3.Session(profile_name='monitor').client('ec2').describe_regions())"

# Check Flask
curl http://localhost:5000/api/health
```

## Best Practices

1. **Use Read-Only IAM Policy** - Never give write access to monitor
2. **Schedule Wisely** - Don't monitor every minute (CloudWatch charges)
3. **Filter Resources** - Only monitor what you need
4. **Set Reasonable Thresholds** - 80% CPU is usually good
5. **Log to Files** - Keep audit trail of monitoring runs
6. **Test First** - Try UI before scheduling scripts
7. **Start Small** - Monitor one region/resource type first
8. **Review Costs** - CloudWatch and Cost Explorer have costs

---

**Remember**: This is a simplified monitoring tool. For advanced features, use AWS CloudWatch Dashboards, CloudTrail, or Config.
