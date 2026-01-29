# Config-Based Monitoring Guide

## Overview

The config-based monitoring system allows you to define monitoring jobs in YAML configuration files and run them with a standard Python script. This approach is perfect for:

- **Scheduled monitoring**: Run via cron at specific intervals
- **Multiple environments**: Different configs for prod, dev, staging
- **Team-specific monitoring**: Each team has their own configs
- **Reproducible monitoring**: Version control your monitoring configs

---

## Quick Start

### 1. Create a Config File

```yaml
# configs/my-monitoring.yaml
job_name: "my-monitoring"
description: "Monitor my resources"

aws_profile: "monitor"
regions:
  - us-east-1

resource_types:
  - ec2
  - rds

checks:
  performance:
    enabled: true
  cost:
    enabled: true
  alerts:
    enabled: true

output:
  console: true
  log_file: "logs/my-monitoring.log"
```

### 2. Run the Monitoring Script

```bash
# Install dependencies first
pip install PyYAML

# Run single config
python run_monitor.py configs/my-monitoring.yaml

# Run multiple configs
python run_monitor.py configs/prod.yaml configs/dev.yaml

# Run all configs
python run_monitor.py --all
```

### 3. Schedule with Cron

```bash
# Edit crontab
crontab -e

# Add monitoring jobs
*/15 * * * * /usr/bin/python3 /path/to/run_monitor.py /path/to/configs/production-monitoring.yaml
0 */6 * * * /usr/bin/python3 /path/to/run_monitor.py /path/to/configs/cost-monitoring.yaml
```

---

## Configuration File Format

### Complete Example

```yaml
# Job Information
job_name: "production-monitoring"
description: "Monitor production EC2 and RDS in us-east-1"

# AWS Configuration
aws_profile: "monitor"
role_arn: "arn:aws:iam::123456789012:role/MonitoringRole"  # Optional
session_name: "AWSMonitorSession"

# Regions to Monitor
regions:
  - us-east-1
  - us-west-2

# Resource Types to Discover
resource_types:
  - ec2
  - rds
  - eks
  - lambda
  - s3
  - emr
  - ebs

# Filters (Optional)
filters:
  tags:
    Environment: production
    Team: backend
  names:
    - web-server-1
    - web-server-2
  ids:
    - i-1234567890abcdef0

# Monitoring Checks
checks:
  performance:
    enabled: true
    period: 300  # 5 minutes
    
  cost:
    enabled: true
    days: 7  # Last 7 days
    
  alerts:
    enabled: true
    thresholds:
      cpu: 80
      memory: 85
      storage: 90
      connections: 90

# Notifications
notifications:
  email:
    enabled: true
    to: "ops-team@example.com"
    
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
    
  sns:
    enabled: true
    topic_arn: "arn:aws:sns:us-east-1:123456789012:monitoring-alerts"

# Output Options
output:
  console: true
  log_file: "logs/production-monitoring.log"
  json_file: "output/production-monitoring.json"
  format: "detailed"  # Options: detailed, summary, json

# Scheduling (documentation only)
schedule:
  frequency: "*/15 * * * *"  # Cron format
  description: "Run every 15 minutes"
```

### Configuration Sections

#### Job Information
```yaml
job_name: "my-job"          # Required: Unique job identifier
description: "Description"  # Optional: Human-readable description
```

#### AWS Configuration
```yaml
aws_profile: "monitor"      # Required: AWS profile name
role_arn: null              # Optional: IAM role to assume
session_name: "Session"     # Optional: Session name for role assumption
```

#### Regions
```yaml
regions:                    # Required: List of AWS regions
  - us-east-1
  - us-west-2
  - eu-west-1
```

#### Resource Types
```yaml
resource_types:             # Required: Which resources to monitor
  - ec2                     # EC2 instances
  - rds                     # RDS databases
  - s3                      # S3 buckets
  - lambda                  # Lambda functions
  - ebs                     # EBS volumes
  - eks                     # EKS clusters
  - emr                     # EMR clusters
```

#### Filters
```yaml
filters:
  tags:                     # Filter by tags
    Environment: production
    CostCenter: engineering
  names:                    # Filter by names (exact match)
    - web-server-1
    - app-server-1
  ids:                      # Filter by IDs
    - i-1234567890abcdef0
    - vol-1234567890abcdef0
```

#### Checks
```yaml
checks:
  performance:
    enabled: true
    period: 300             # Seconds (5 min, 15 min, 1 hour)
    
  cost:
    enabled: true
    days: 7                 # 7, 30, or 90 days
    
  alerts:
    enabled: true
    thresholds:
      cpu: 80               # CPU threshold (%)
      memory: 85            # Memory threshold (%)
      storage: 90           # Storage threshold (%)
      connections: 90       # DB connections threshold (%)
```

#### Notifications
```yaml
notifications:
  email:
    enabled: true
    to: "team@example.com"
    
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/..."
    
  sns:
    enabled: true
    topic_arn: "arn:aws:sns:..."
```

#### Output
```yaml
output:
  console: true                           # Print to console
  log_file: "logs/job.log"               # Log file path
  json_file: "output/job.json"           # JSON output file
  format: "detailed"                      # detailed, summary, or json
```

---

## Usage Examples

### Example 1: Production Monitoring

**File**: `configs/production-monitoring.yaml`

```yaml
job_name: "production-monitoring"
description: "Monitor production resources every 15 minutes"

aws_profile: "monitor"
regions:
  - us-east-1
  - us-west-2

resource_types:
  - ec2
  - rds
  - eks

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
  alerts:
    enabled: true
    thresholds:
      cpu: 80
      memory: 85

notifications:
  email:
    enabled: true
    to: "ops-team@example.com"

output:
  console: false
  log_file: "logs/production.log"
  json_file: "output/production.json"
```

**Schedule**:
```bash
# Run every 15 minutes
*/15 * * * * python3 /path/to/run_monitor.py /path/to/configs/production-monitoring.yaml
```

---

### Example 2: Database-Only Monitoring

**File**: `configs/database-monitoring.yaml`

```yaml
job_name: "database-monitoring"
description: "Monitor all RDS databases"

aws_profile: "monitor"
regions:
  - us-east-1
  - us-west-2
  - eu-west-1

resource_types:
  - rds  # Only databases

checks:
  performance:
    enabled: true
    period: 900  # 15 minutes
  alerts:
    enabled: true
    thresholds:
      cpu: 75
      memory: 80
      storage: 85
      connections: 90

notifications:
  slack:
    enabled: true
    webhook_url: "https://hooks.slack.com/services/..."

output:
  console: true
  log_file: "logs/database.log"
```

**Schedule**:
```bash
# Run every 30 minutes
*/30 * * * * python3 /path/to/run_monitor.py /path/to/configs/database-monitoring.yaml
```

---

### Example 3: Cost Tracking

**File**: `configs/cost-monitoring.yaml`

```yaml
job_name: "cost-monitoring"
description: "Track costs daily"

aws_profile: "monitor"
regions:
  - us-east-1

resource_types:
  - ec2
  - rds
  - s3

checks:
  cost:
    enabled: true
    days: 30  # Last 30 days

notifications:
  email:
    enabled: true
    to: "finance-team@example.com"

output:
  console: false
  log_file: "logs/cost.log"
  json_file: "output/cost.json"
```

**Schedule**:
```bash
# Run once daily at 9 AM
0 9 * * * python3 /path/to/run_monitor.py /path/to/configs/cost-monitoring.yaml
```

---

### Example 4: Multi-Environment Monitoring

**Structure**:
```
configs/
├── prod-monitoring.yaml
├── dev-monitoring.yaml
└── staging-monitoring.yaml
```

**Run all environments**:
```bash
# Run all configs
python run_monitor.py --all

# Or run specific environments
python run_monitor.py configs/prod-monitoring.yaml configs/dev-monitoring.yaml
```

**Schedule**:
```bash
# Production: Every 10 minutes
*/10 * * * * python3 /path/to/run_monitor.py /path/to/configs/prod-monitoring.yaml

# Development: Every hour
0 * * * * python3 /path/to/run_monitor.py /path/to/configs/dev-monitoring.yaml

# Staging: Every 30 minutes
*/30 * * * * python3 /path/to/run_monitor.py /path/to/configs/staging-monitoring.yaml
```

---

## Running Multiple Configs

### Option 1: Multiple Arguments
```bash
python run_monitor.py \
  configs/prod.yaml \
  configs/dev.yaml \
  configs/staging.yaml
```

### Option 2: Wildcard
```bash
python run_monitor.py configs/*.yaml
```

### Option 3: --all Flag
```bash
python run_monitor.py --all
```

### Option 4: Custom Config Directory
```bash
python run_monitor.py --all --config-dir /path/to/configs
```

---

## Output Files

### Log Files

**Location**: Defined in `output.log_file`

**Example**: `logs/production-monitoring.log`

```
2024-01-28 12:00:00 - production-monitoring - INFO - Starting job: production-monitoring
2024-01-28 12:00:01 - production-monitoring - INFO - Creating AWS session with profile: monitor
2024-01-28 12:00:02 - production-monitoring - INFO - Discovering resources: ['ec2', 'rds'] in ['us-east-1']
2024-01-28 12:00:05 - production-monitoring - INFO - Found 5 EC2 instances in us-east-1
2024-01-28 12:00:07 - production-monitoring - INFO - Found 3 RDS instances in us-east-1
2024-01-28 12:00:10 - production-monitoring - INFO - Collecting performance metrics
2024-01-28 12:00:15 - production-monitoring - INFO - Analyzing costs
2024-01-28 12:00:20 - production-monitoring - INFO - Checking alerts
2024-01-28 12:00:21 - production-monitoring - INFO - Results saved to: output/production.json
2024-01-28 12:00:21 - production-monitoring - INFO - Job completed: production-monitoring
```

### JSON Output Files

**Location**: Defined in `output.json_file`

**Example**: `output/production-monitoring.json`

```json
{
  "job_name": "production-monitoring",
  "timestamp": "2024-01-28T12:00:21Z",
  "config_file": "configs/production-monitoring.yaml",
  "resources": {
    "us-east-1": {
      "ec2": [
        {
          "id": "i-1234567890abcdef0",
          "name": "web-server-1",
          "type": "t3.medium",
          "state": "running"
        }
      ],
      "rds": [
        {
          "id": "prod-db-1",
          "engine": "postgres",
          "status": "available"
        }
      ]
    }
  },
  "metrics": {
    "us-east-1": {
      "i-1234567890abcdef0": {
        "cpu_avg": 45.2,
        "cpu_max": 67.8
      }
    }
  },
  "costs": {
    "period_days": 7,
    "total_cost": 234.56,
    "daily_average": 33.51
  },
  "alerts": [
    {
      "severity": "warning",
      "resource": "i-1234567890abcdef0",
      "region": "us-east-1",
      "message": "High CPU utilization: 67.8%",
      "threshold": 80
    }
  ],
  "errors": []
}
```

---

## Scheduling with Cron

### Cron Format
```
* * * * * command
│ │ │ │ │
│ │ │ │ └─── Day of week (0-7, Sunday = 0 or 7)
│ │ │ └───── Month (1-12)
│ │ └─────── Day of month (1-31)
│ └───────── Hour (0-23)
└─────────── Minute (0-59)
```

### Common Cron Examples

```bash
# Every 5 minutes
*/5 * * * * python3 /path/to/run_monitor.py /path/to/config.yaml

# Every 15 minutes
*/15 * * * * python3 /path/to/run_monitor.py /path/to/config.yaml

# Every hour
0 * * * * python3 /path/to/run_monitor.py /path/to/config.yaml

# Every 6 hours
0 */6 * * * python3 /path/to/run_monitor.py /path/to/config.yaml

# Once daily at 9 AM
0 9 * * * python3 /path/to/run_monitor.py /path/to/config.yaml

# Business hours only (9 AM - 6 PM, Mon-Fri)
*/15 9-18 * * 1-5 python3 /path/to/run_monitor.py /path/to/config.yaml

# Weekends only
0 */6 * * 0,6 python3 /path/to/run_monitor.py /path/to/config.yaml
```

### Setup Cron Jobs

```bash
# Edit crontab
crontab -e

# Add your jobs
*/15 * * * * /usr/bin/python3 /opt/aws-monitor/run_monitor.py /opt/aws-monitor/configs/production.yaml >> /var/log/aws-monitor-cron.log 2>&1

# List current cron jobs
crontab -l

# Remove all cron jobs
crontab -r
```

---

## Best Practices

### 1. Organize Configs by Purpose

```
configs/
├── production/
│   ├── ec2-monitoring.yaml
│   ├── database-monitoring.yaml
│   └── cost-tracking.yaml
├── development/
│   └── dev-monitoring.yaml
└── shared/
    └── compliance-check.yaml
```

### 2. Use Meaningful Job Names

```yaml
# Good
job_name: "prod-ec2-performance"
job_name: "database-cost-tracking"
job_name: "eks-cluster-health"

# Bad
job_name: "job1"
job_name: "monitor"
job_name: "test"
```

### 3. Set Appropriate Monitoring Intervals

```yaml
# High-frequency (5-15 minutes): Critical production resources
period: 300

# Medium-frequency (30-60 minutes): Development environments
period: 1800

# Low-frequency (6-24 hours): Cost tracking, compliance
period: 21600
```

### 4. Enable Logging

```yaml
output:
  console: false  # In cron, console output emails you
  log_file: "logs/job-name.log"  # Always log to file
  json_file: "output/job-name.json"  # For analysis
```

### 5. Rotate Log Files

```bash
# Add to logrotate
cat > /etc/logrotate.d/aws-monitor << EOF
/opt/aws-monitor/logs/*.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
}
EOF
```

### 6. Monitor the Monitor

```bash
# Check if monitoring jobs are running
ps aux | grep run_monitor.py

# Check recent logs
tail -f logs/production-monitoring.log

# Check for errors
grep ERROR logs/*.log

# Verify output files are being created
ls -ltr output/
```

---

## Troubleshooting

### Issue: "Config file not found"

**Solution**:
```bash
# Use absolute paths in cron
/usr/bin/python3 /full/path/to/run_monitor.py /full/path/to/config.yaml
```

### Issue: "Module 'yaml' not found"

**Solution**:
```bash
pip install PyYAML
```

### Issue: "No AWS credentials"

**Solution**:
```bash
# In crontab, set HOME
HOME=/home/username
*/15 * * * * python3 /path/to/run_monitor.py /path/to/config.yaml
```

### Issue: "Permission denied"

**Solution**:
```bash
chmod +x run_monitor.py
```

### Issue: Job runs but produces no output

**Solution**:
```bash
# Check cron logs
tail -f /var/log/syslog | grep CRON

# Run manually to see errors
python3 run_monitor.py configs/my-config.yaml
```

---

## Summary

**Config-based monitoring provides**:
- ✅ Reproducible monitoring jobs
- ✅ Version-controlled configurations
- ✅ Easy scheduling with cron
- ✅ Multiple environment support
- ✅ Team-specific monitoring
- ✅ Automated alerting
- ✅ Comprehensive logging

**Quick Start**:
1. Create config file
2. Test: `python run_monitor.py config.yaml`
3. Schedule: Add to crontab
4. Monitor: Check logs and output files

**Next Steps**:
- Create configs for your environments
- Test configs manually first
- Schedule with appropriate intervals
- Set up log rotation
- Configure notifications
- Monitor the monitor!
