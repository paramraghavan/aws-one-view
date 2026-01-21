# New Features Added: Background Monitoring & Email Alerts

## What Was Added

### 🎯 Background Monitoring
- Automatic periodic checks of selected resources
- Runs every 15 minutes (configurable)
- Monitors CPU utilization and other metrics
- No manual intervention required once configured

### 📧 Email Alerts
- Sends notifications when thresholds exceeded
- Supports Gmail, AWS SES, and other SMTP providers
- Customizable alert recipients
- Test alert functionality

## New Files

1. **`app/monitoring.py`** (380 lines)
   - Background scheduler using APScheduler
   - Resource checking logic
   - Threshold detection

2. **`app/alerts.py`** (220 lines)
   - Email alert formatting
   - SMTP and SES support
   - Test alert functionality

3. **`docs/ALERTS_SETUP.md`** (500+ lines)
   - Complete setup guide
   - Gmail, SES, and other providers
   - Troubleshooting guide
   - Production deployment

## Updated Files

1. **`main.py`**
   - Added monitoring API endpoints:
     - `/api/monitoring/status` - Get monitoring status
     - `/api/monitoring/start` - Start monitoring
     - `/api/monitoring/stop` - Stop monitoring
     - `/api/monitoring/add` - Add resource to monitor
     - `/api/monitoring/remove/<id>` - Remove from monitoring
     - `/api/alerts/test` - Send test alert

2. **`app/config.py`**
   - Added monitoring configuration:
     - `MONITORING_ENABLED`
     - `MONITORING_INTERVAL_MINUTES`
     - `ALERTS_ENABLED`
     - `ALERT_METHOD` (smtp/ses)
     - SMTP settings
     - SES settings

3. **`templates/index.html`**
   - Added monitoring section at top
   - Status indicator (active/inactive)
   - Start/Stop buttons
   - List of monitored resources
   - "Add to Monitoring" button
   - "Send Test Alert" button

4. **`static/css/style.css`**
   - Monitoring card styles
   - Status indicator with pulse animation
   - Monitored resources list styles
   - Button styles

5. **`static/js/app.js`**
   - Monitoring status loading
   - Start/stop monitoring functions
   - Add/remove resources from monitoring
   - Test alert function
   - UI updates

6. **`requirements.txt`**
   - Added `APScheduler==3.10.4`

7. **`README.md`**
   - Updated with monitoring & alerts info
   - Quick setup guide

## How It Works

### Architecture

```
┌─────────────────┐
│   Web Browser   │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Flask App     │ (main.py)
│  - API Routes   │
└────────┬────────┘
         │
         ├─────────→ ┌─────────────────┐
         │           │  AWS Client     │
         │           │  (aws_client.py)│
         │           └─────────────────┘
         │
         ↓
┌─────────────────┐       ┌─────────────────┐
│  Monitor        │───────→│  Alert Manager  │
│  (monitoring.py)│       │  (alerts.py)    │
└─────────────────┘       └─────────────────┘
         │                         │
         ↓                         ↓
    CloudWatch                  Email
    (Metrics)                   (SMTP/SES)
```

### Flow

1. **User adds resources** via web UI
2. **Resources stored** in memory with thresholds
3. **Background scheduler** runs every 15 minutes
4. **Checks metrics** from CloudWatch
5. **Compares** against thresholds
6. **Sends alert** if threshold exceeded

## Configuration Examples

### Minimal (Gmail)

```bash
export MONITORING_ENABLED=true
export ALERTS_ENABLED=true
export ALERT_RECIPIENTS="admin@company.com"
export SMTP_USERNAME="your-gmail@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM_EMAIL="your-gmail@gmail.com"
```

### Production (AWS SES)

```bash
export MONITORING_ENABLED=true
export ALERTS_ENABLED=true
export MONITORING_INTERVAL_MINUTES=15
export ALERT_METHOD=ses
export AWS_SES_REGION=us-east-1
export ALERT_RECIPIENTS="ops@company.com,sre@company.com"
export SMTP_FROM_EMAIL="aws-alerts@company.com"
```

## Usage

### Via Web UI

1. Open dashboard
2. See monitoring section at top (purple card)
3. Click "Start Monitoring" 
4. Load resources and select some
5. Click "Add Selected to Background Monitoring"
6. Enter CPU threshold (e.g., 80)
7. Resources now monitored automatically

### Via API

```bash
# Start monitoring
curl -X POST http://localhost:5000/api/monitoring/start

# Add resource
curl -X POST http://localhost:5000/api/monitoring/add \
  -H "Content-Type: application/json" \
  -d '{
    "id": "i-1234567890",
    "type": "ec2",
    "region": "us-east-1",
    "cpu_threshold": 80
  }'

# Check status
curl http://localhost:5000/api/monitoring/status

# Test alert
curl -X POST http://localhost:5000/api/alerts/test
```

## Alert Example

```
From: aws-alerts@company.com
To: ops@company.com
Subject: AWS Alert: 2 issue(s) detected

AWS Resource Monitor Alert
============================================================

Detected 2 issue(s) with your AWS resources.

🔴 CRITICAL ISSUES:
------------------------------------------------------------
Resource: i-1234567890 (ec2)
Region: us-east-1
Issue: CPU at 95.2% (threshold: 80%)
Time: 2025-01-21T14:30:00Z

⚠️  HIGH PRIORITY:
------------------------------------------------------------
Resource: db-prod-main (rds)
Region: us-west-2
Issue: CPU at 85.5% (threshold: 80%)
Time: 2025-01-21T14:30:00Z

View details: http://localhost:5000

This is an automated alert from AWS Resource Monitor.
```

## Key Features

### Monitoring
- ✅ Background scheduling (APScheduler)
- ✅ Per-resource custom thresholds
- ✅ Multiple resource types (EC2, RDS, Lambda)
- ✅ Multiple regions
- ✅ Configurable check interval
- ✅ Start/stop control via UI

### Alerts
- ✅ Email notifications
- ✅ SMTP support (Gmail, Office365, etc.)
- ✅ AWS SES support
- ✅ Multiple recipients
- ✅ Severity levels (critical/high)
- ✅ Test alert functionality
- ✅ Clean email formatting

### UI
- ✅ Monitoring status indicator
- ✅ List of monitored resources
- ✅ Add/remove resources
- ✅ Start/stop monitoring
- ✅ Test alerts
- ✅ Visual feedback

## Benefits

### Before
- ❌ Had to manually check dashboard
- ❌ Could miss critical issues
- ❌ No after-hours monitoring
- ❌ Reactive approach

### After
- ✅ Automatic 24/7 monitoring
- ✅ Immediate email alerts
- ✅ Configurable thresholds
- ✅ Proactive approach
- ✅ Team-wide notifications

## Production Deployment

### Systemd Service

```ini
[Unit]
Description=AWS Resource Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/aws_monitor_clean
Environment="MONITORING_ENABLED=true"
Environment="ALERTS_ENABLED=true"
EnvironmentFile=/opt/aws_monitor_clean/.env
ExecStart=/opt/aws_monitor_clean/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker Compose

```yaml
version: '3.8'
services:
  aws-monitor:
    build: .
    ports:
      - "5000:5000"
    env_file:
      - .env
    restart: unless-stopped
    environment:
      - MONITORING_ENABLED=true
      - ALERTS_ENABLED=true
```

## Security Considerations

1. **Email credentials** stored in environment variables
2. **No credentials** in code or version control
3. **TLS encryption** for SMTP
4. **App passwords** recommended over main passwords
5. **AWS SES** uses IAM permissions (no password needed)
6. **Monitored resources** stored in memory (not persistent)

## Limitations

- Monitoring state not persistent (restart clears monitored resources)
- Email-only alerts (no SMS, Slack, PagerDuty)
- Fixed check interval (not event-based)
- Basic threshold checking (CPU only for now)

## Future Enhancements

Possible additions:
- Persistent storage (database)
- Multiple alert channels (Slack, SMS)
- Event-based triggers (CloudWatch Events)
- More metrics (memory, disk, network)
- Alert deduplication
- Escalation policies
- Custom alert templates
- Web dashboard for alert history

## Summary

This update transforms the AWS Resource Monitor from a **manual dashboard** into an **automated monitoring system** with proactive alerting. Perfect for production environments where you need continuous oversight without constant manual checking.

## Total Changes

- **New Files**: 3
- **Updated Files**: 7
- **Lines Added**: ~1,200
- **Dependencies Added**: 1 (APScheduler)
- **New API Endpoints**: 6
- **Time to Setup**: 5 minutes
