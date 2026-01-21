# Email Alerts & Background Monitoring Setup

## Overview

The AWS Resource Monitor now supports:
- **Background Monitoring**: Automatic periodic checks of selected resources
- **Email Alerts**: Notifications when thresholds are exceeded

## Quick Start

### 1. Configure Email Settings

Create a `.env` file or set environment variables:

```bash
# Enable monitoring and alerts
export MONITORING_ENABLED=true
export ALERTS_ENABLED=true

# How often to check (in minutes)
export MONITORING_INTERVAL_MINUTES=15

# Email recipients (comma-separated)
export ALERT_RECIPIENTS="admin@example.com,ops@example.com"
```

### 2. Choose Email Method

#### Option A: Gmail (Simple)

```bash
export ALERT_METHOD=smtp
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@gmail.com
export SMTP_PASSWORD=your-app-password  # See Gmail Setup below
export SMTP_FROM_EMAIL=your-email@gmail.com
```

#### Option B: AWS SES (Recommended for Production)

```bash
export ALERT_METHOD=ses
export AWS_SES_REGION=us-east-1
export SMTP_FROM_EMAIL=verified@yourdomain.com
```

### 3. Start the Application

```bash
./run.sh
```

The background monitor will start automatically!

---

## Detailed Setup Instructions

### Gmail Setup

1. **Enable 2-Factor Authentication** on your Gmail account
2. **Create App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other (Custom name)"
   - Name it "AWS Monitor"
   - Copy the 16-character password
3. **Use App Password** as `SMTP_PASSWORD`

**Example:**
```bash
export SMTP_SERVER=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USERNAME=yourname@gmail.com
export SMTP_PASSWORD=abcd efgh ijkl mnop  # 16-char app password
export SMTP_FROM_EMAIL=yourname@gmail.com
```

### AWS SES Setup

1. **Verify Email Address**:
   ```bash
   aws ses verify-email-identity --email-address alerts@yourdomain.com
   ```

2. **Verify Domain** (optional, for production):
   ```bash
   aws ses verify-domain-identity --domain yourdomain.com
   ```

3. **Request Production Access**:
   - By default, SES is in sandbox mode (only verified emails)
   - Request production access in AWS Console: SES → Account Dashboard

4. **IAM Permissions**:
   Add to your IAM policy:
   ```json
   {
       "Effect": "Allow",
       "Action": [
           "ses:SendEmail",
           "ses:SendRawEmail"
       ],
       "Resource": "*"
   }
   ```

**Example:**
```bash
export ALERT_METHOD=ses
export AWS_SES_REGION=us-east-1
export SMTP_FROM_EMAIL=alerts@yourdomain.com
export ALERT_RECIPIENTS=team@yourdomain.com
```

### Other SMTP Providers

**Office 365:**
```bash
export SMTP_SERVER=smtp.office365.com
export SMTP_PORT=587
export SMTP_USERNAME=your-email@company.com
export SMTP_PASSWORD=your-password
```

**SendGrid:**
```bash
export SMTP_SERVER=smtp.sendgrid.net
export SMTP_PORT=587
export SMTP_USERNAME=apikey
export SMTP_PASSWORD=your-sendgrid-api-key
```

**Mailgun:**
```bash
export SMTP_SERVER=smtp.mailgun.org
export SMTP_PORT=587
export SMTP_USERNAME=postmaster@your-domain.mailgun.org
export SMTP_PASSWORD=your-mailgun-password
```

---

## How It Works

### Background Monitoring Flow

```
1. You select resources in the UI
2. Click "Add Selected to Background Monitoring"
3. Resources are added to monitoring list
4. Every 15 minutes (configurable):
   - Check CPU metrics for each resource
   - Compare against thresholds
   - If exceeded → Send email alert
```

### Alert Example

When CPU > 80%, you receive:

```
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
Resource: db-instance-1 (rds)
Region: us-west-2
Issue: CPU at 85.5% (threshold: 80%)
Time: 2025-01-21T14:30:00Z

View details: http://localhost:5000
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONITORING_ENABLED` | false | Enable background monitoring |
| `MONITORING_INTERVAL_MINUTES` | 15 | Check interval (minutes) |
| `ALERTS_ENABLED` | false | Enable email alerts |
| `ALERT_METHOD` | smtp | Email method: smtp or ses |
| `ALERT_RECIPIENTS` | - | Email addresses (comma-separated) |
| `SMTP_SERVER` | smtp.gmail.com | SMTP server address |
| `SMTP_PORT` | 587 | SMTP port |
| `SMTP_USE_TLS` | true | Use TLS encryption |
| `SMTP_USERNAME` | - | SMTP username |
| `SMTP_PASSWORD` | - | SMTP password |
| `SMTP_FROM_EMAIL` | - | From email address |
| `AWS_SES_REGION` | us-east-1 | AWS SES region |

### Custom Thresholds

When adding resources to monitoring, you can set custom thresholds:

```javascript
// In the UI, you'll be prompted for:
CPU Threshold: 80  // Alert when CPU > this value
```

---

## Usage

### Via Web Interface

1. **Start Monitoring**:
   - Click "Start Monitoring" button
   - Monitor status shows "Active"

2. **Add Resources**:
   - Load resources
   - Select resources (checkboxes)
   - Click "Add Selected to Background Monitoring"
   - Enter CPU threshold (e.g., 80)

3. **View Monitored Resources**:
   - See list in monitoring section
   - Remove resources as needed

4. **Test Alerts**:
   - Click "Send Test Alert"
   - Check your email

### Via API

**Start Monitoring:**
```bash
curl -X POST http://localhost:5000/api/monitoring/start
```

**Add Resource:**
```bash
curl -X POST http://localhost:5000/api/monitoring/add \
  -H "Content-Type: application/json" \
  -d '{
    "id": "i-1234567890",
    "type": "ec2",
    "region": "us-east-1",
    "cpu_threshold": 80
  }'
```

**Check Status:**
```bash
curl http://localhost:5000/api/monitoring/status
```

**Remove Resource:**
```bash
curl -X DELETE http://localhost:5000/api/monitoring/remove/i-1234567890
```

---

## Troubleshooting

### Test Email Not Received

**Gmail:**
1. Verify 2FA is enabled
2. Check app password is correct (no spaces)
3. Check "Less secure apps" is NOT needed (use app password)

**SES:**
1. Verify sender email in SES console
2. Check recipient email is verified (if in sandbox)
3. Check IAM permissions

**All Methods:**
1. Check spam folder
2. Check application logs for errors
3. Verify SMTP credentials

### Monitoring Not Starting

```bash
# Check if enabled
echo $MONITORING_ENABLED  # Should be "true"

# Check logs
python main.py
# Look for: "Background monitoring enabled"
```

### No Alerts Being Sent

1. **Check if alerts are enabled:**
   ```bash
   echo $ALERTS_ENABLED  # Should be "true"
   ```

2. **Verify recipients:**
   ```bash
   echo $ALERT_RECIPIENTS  # Should show emails
   ```

3. **Test manually:**
   - Click "Send Test Alert" button
   - Check for errors

4. **Check thresholds:**
   - Are resources actually exceeding thresholds?
   - Lower threshold temporarily to test

---

## Production Deployment

### Using Systemd

Create `/etc/systemd/system/aws-monitor.service`:

```ini
[Unit]
Description=AWS Resource Monitor
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/aws_monitor_clean
Environment="MONITORING_ENABLED=true"
Environment="ALERTS_ENABLED=true"
Environment="ALERT_RECIPIENTS=ops@company.com"
Environment="ALERT_METHOD=ses"
Environment="SMTP_FROM_EMAIL=aws-alerts@company.com"
ExecStart=/home/ubuntu/aws_monitor_clean/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 main:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Start service:
```bash
sudo systemctl enable aws-monitor
sudo systemctl start aws-monitor
sudo systemctl status aws-monitor
```

### Using Docker

Create `.env` file:
```
MONITORING_ENABLED=true
ALERTS_ENABLED=true
ALERT_RECIPIENTS=ops@company.com
ALERT_METHOD=ses
SMTP_FROM_EMAIL=alerts@company.com
```

Run:
```bash
docker build -t aws-monitor .
docker run -d -p 5000:5000 --env-file .env aws-monitor
```

---

## Best Practices

1. **Start Small**: Monitor 5-10 critical resources first
2. **Tune Thresholds**: Adjust based on normal usage patterns
3. **Use SES in Production**: More reliable than SMTP
4. **Set Reasonable Intervals**: 15-30 minutes is good
5. **Monitor the Monitor**: Set up alerts if monitoring stops
6. **Rotate Credentials**: Change SMTP passwords regularly
7. **Use Distribution Lists**: Send to team lists, not individuals

---

## Security Notes

- **Never commit credentials** to version control
- **Use app passwords** not your main account password
- **Restrict SES permissions** to only what's needed
- **Use TLS** for SMTP connections
- **Verify email addresses** before using SES
- **Monitor failed login attempts** on email accounts

---

## FAQ

**Q: How many resources can I monitor?**
A: Tested with 50+ resources. Limit depends on API rate limits.

**Q: Will I get an alert every check interval?**
A: No, only when status changes (OK → High CPU) or every 6 hours for ongoing issues.

**Q: Can I monitor different regions?**
A: Yes, add resources from any region.

**Q: What happens if monitoring stops?**
A: It only runs while the application is running. Use systemd/Docker for persistence.

**Q: Can I customize alert format?**
A: Yes, edit `app/alerts.py` → `_format_alert_email()`

**Q: Does this cost money?**
A: AWS API calls are free tier eligible. SES costs ~$0.10 per 1000 emails.

---

## Support

Check logs if issues occur:
```bash
tail -f /var/log/syslog  # If using systemd
docker logs aws-monitor  # If using Docker
```

Common solutions:
1. Verify all environment variables are set
2. Test email settings with "Send Test Alert"
3. Check AWS credentials are valid
4. Ensure CloudWatch has data for resources
