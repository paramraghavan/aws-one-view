# Config-Based Monitoring - Quick Cheat Sheet

## 🚀 Quick Start (30 Seconds)

```bash
# 1. Install dependency
pip install PyYAML

# 2. Run example config
python run_monitor.py configs/production-monitoring.yaml

# 3. Schedule it (every 15 minutes)
crontab -e
*/15 * * * * python3 /path/to/run_monitor.py /path/to/configs/production-monitoring.yaml
```

Done! ✅

---

## 📁 Minimal Config

```yaml
# configs/my-monitor.yaml
job_name: "my-monitor"

aws_profile: "monitor"

regions:
  - us-east-1

resource_types:
  - ec2

checks:
  performance: {enabled: true}

output:
  console: true
```

Run: `python run_monitor.py configs/my-monitor.yaml`

---

## 🎯 Common Commands

```bash
# Run single config
python run_monitor.py configs/prod.yaml

# Run multiple configs
python run_monitor.py configs/prod.yaml configs/dev.yaml

# Run all configs
python run_monitor.py --all

# Run configs in custom directory
python run_monitor.py --all --config-dir /path/to/configs
```

---

## ⏰ Cron Examples

```bash
# Every 5 minutes
*/5 * * * * python3 run_monitor.py configs/critical.yaml

# Every 15 minutes
*/15 * * * * python3 run_monitor.py configs/production.yaml

# Every hour
0 * * * * python3 run_monitor.py configs/database.yaml

# Every 6 hours
0 */6 * * * python3 run_monitor.py configs/cost.yaml

# Daily at 9 AM
0 9 * * * python3 run_monitor.py configs/daily-report.yaml

# Business hours only (9 AM - 6 PM, Mon-Fri)
*/30 9-18 * * 1-5 python3 run_monitor.py configs/business-hours.yaml
```

---

## 📝 Config Template

```yaml
# Required
job_name: "unique-job-name"
aws_profile: "monitor"
regions: [us-east-1]
resource_types: [ec2]

# Optional - AWS Role
role_arn: "arn:aws:iam::123456:role/MonitoringRole"
session_name: "MySession"

# Optional - Filters
filters:
  tags: {Environment: production}
  names: [web-1, web-2]
  ids: [i-123, i-456]

# Optional - Checks
checks:
  performance:
    enabled: true
    period: 300  # 5 min
  cost:
    enabled: true
    days: 7
  alerts:
    enabled: true
    thresholds:
      cpu: 80
      memory: 85

# Optional - Notifications
notifications:
  email:
    enabled: true
    to: "team@example.com"
  slack:
    enabled: true
    webhook_url: "https://..."
  sns:
    enabled: true
    topic_arn: "arn:aws:sns:..."

# Optional - Output
output:
  console: true
  log_file: "logs/job.log"
  json_file: "output/job.json"
  format: "detailed"  # detailed|summary|json
```

---

## 🎨 Enhanced UI Quick Reference

### New Features

**Health Scores** - Green/Yellow/Red indicators per resource type

**Status Dots** - 🟢 Green = running, 🟡 Yellow = stopped, 🔴 Red = failed

**Copy Buttons** - `📋 54.123.45.67` → Click to copy IP/endpoint

**Resource Age** - Shows "45 days old" under resource name

**Tag Tooltips** - Hover over "3 tags" to see all tags

**Export CSV** - Click `📥 Export to CSV` button

**Console Links** - `🔗 Console` → Opens resource in AWS Console

**Collapsible Sections** - All resource types start collapsed, click to expand

### Quick Actions

| Action | Method |
|--------|--------|
| Copy IP | Click 📋 button next to IP |
| Copy Endpoint | Click 📋 button next to endpoint |
| See Tags | Hover over tag count |
| Resource Details | Click "Details" button |
| AWS Console | Click "🔗 Console" |
| Export All | Click "📥 Export to CSV" |
| Health Check | Look at color-coded health score |

---

## 📊 Output Files

### Log File
**Location**: `logs/job-name.log`

**Contains**:
- Timestamped events
- Discovered resources
- Metrics collected
- Errors

### JSON File
**Location**: `output/job-name.json`

**Contains**:
- Complete results
- Resources discovered
- Metrics collected
- Costs analyzed
- Alerts generated

---

## 🔧 Troubleshooting

```bash
# Test config file
python run_monitor.py configs/test.yaml

# Check logs
tail -f logs/production.log

# Verify cron job
crontab -l

# Check cron execution
grep CRON /var/log/syslog

# Test AWS access
aws sts get-caller-identity --profile monitor
```

---

## 💡 Best Practices

✅ **Start small** - Test with one config first

✅ **Use meaningful names** - `prod-ec2-monitor` not `job1`

✅ **Log everything** - Always set `log_file` in config

✅ **Version control** - Keep configs in Git

✅ **Monitor different intervals** - Critical=5min, Cost=daily

✅ **Separate environments** - Different configs for prod/dev/staging

✅ **Test before scheduling** - Run manually first

✅ **Rotate logs** - Use logrotate for log files

---

## 📂 Recommended Structure

```
project/
├── configs/
│   ├── production/
│   │   ├── ec2-monitoring.yaml
│   │   ├── database-monitoring.yaml
│   │   └── cost-tracking.yaml
│   ├── development/
│   │   └── dev-monitoring.yaml
│   └── staging/
│       └── staging-monitoring.yaml
├── logs/
│   ├── production-ec2.log
│   ├── production-database.log
│   └── ...
├── output/
│   ├── production-ec2.json
│   ├── production-database.json
│   └── ...
└── run_monitor.py
```

---

## 🎯 Use Case Examples

### Production Monitoring
```bash
# Every 10 minutes
*/10 * * * * python3 run_monitor.py configs/prod/ec2.yaml
```

### Database Health Check
```bash
# Every 30 minutes
*/30 * * * * python3 run_monitor.py configs/prod/database.yaml
```

### Daily Cost Report
```bash
# 9 AM every day
0 9 * * * python3 run_monitor.py configs/cost-report.yaml
```

### Multi-Environment
```bash
# Run all environments hourly
0 * * * * python3 run_monitor.py configs/prod/*.yaml configs/dev/*.yaml
```

---

## 🆚 Config vs UI

**Use Config-Based (run_monitor.py) for**:
- ✅ Automated/scheduled monitoring
- ✅ Multiple environments
- ✅ CI/CD integration
- ✅ Version-controlled monitoring
- ✅ Batch processing
- ✅ Headless servers

**Use UI (main.py) for**:
- ✅ Interactive exploration
- ✅ Ad-hoc queries
- ✅ Visual analysis
- ✅ One-time checks
- ✅ Quick resource discovery
- ✅ Copy/paste operations

**Both support**:
- ✅ Same resource types
- ✅ Same filters
- ✅ Same checks
- ✅ Same AWS profile/role
- ✅ Multi-region

---

## 📚 Full Documentation

- **CONFIG_MONITORING.md** - Complete config guide (20+ pages)
- **RELEASE_v1.3.0.md** - All new features explained
- **TROUBLESHOOTING.md** - Common issues and solutions
- **README.md** - Main documentation

---

## ⚡ Quick Reference Card

### Commands
```bash
# UI
python main.py

# Config
python run_monitor.py config.yaml

# Multiple
python run_monitor.py *.yaml

# All
python run_monitor.py --all
```

### Config Sections
```yaml
job_name: "..."          # Required
aws_profile: "..."       # Required
regions: [...]           # Required
resource_types: [...]    # Required
filters: {...}           # Optional
checks: {...}            # Optional
notifications: {...}     # Optional
output: {...}            # Optional
```

### Resource Types
`ec2`, `rds`, `s3`, `lambda`, `ebs`, `eks`, `emr`

### Check Types
`performance`, `cost`, `alerts`

### Notification Types
`email`, `slack`, `sns`

---

**That's it! Start monitoring in 30 seconds.** 🚀

See **CONFIG_MONITORING.md** for complete documentation.
