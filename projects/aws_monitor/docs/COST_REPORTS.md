# Cost Reports Feature Guide

## Overview

The Cost Reports feature allows you to generate and schedule automated cost reports for specific AWS resources. Get daily, weekly, or monthly cost breakdowns sent directly to your email.

---

## Features

### ✅ Manual Report Generation
- Select specific resources
- Generate instant cost reports
- Choose period: Daily, Weekly, or Monthly
- View or email reports

### ✅ Scheduled Reports
- Automate recurring reports
- Daily, weekly, or monthly schedules
- Custom time configuration
- Email delivery

### ✅ Cost Tracking
- Per-resource cost breakdown
- Actual costs (with tags) or estimates
- Total and individual costs
- Cost trends over time

---

## How It Works

### Cost Calculation Methods

**Method 1: Actual Costs (Recommended)**
- Uses AWS Cost Explorer with cost allocation tags
- 100% accurate costs from AWS billing
- Requires setup (see below)

**Method 2: Estimated Costs**
- Calculates based on instance type and usage
- Fallback when tags aren't configured
- Approximate costs (usually within 10%)

---

## Quick Start

### 1. **Generate a Manual Report**

1. **Select Resources:**
   - Click checkboxes next to resources (EC2, RDS, Lambda)
   - Can select from any region

2. **Configure Report:**
   - Choose period: Daily/Weekly/Monthly
   - Check "Email Report" if you want it sent

3. **Generate:**
   - Click "Generate Report"
   - View results on screen
   - Check email if selected

**Example Output:**
```
Weekly Cost Report - 2025-01-14 to 2025-01-21
=============================================
Total Cost: $45.67
Resources: 5

Cost Breakdown:
  Web Server (i-12345): $25.30
  Database (db-prod): $15.20
  API Function (api-lambda): $3.17
  Storage Volume (vol-abc): $1.50
  Backup Volume (vol-def): $0.50
```

---

### 2. **Schedule Automated Reports**

1. **Select Resources:**
   - Choose resources to monitor

2. **Configure Schedule:**
   - Name: "Weekly Production Costs"
   - Period: Weekly
   - Schedule: "Every Monday at 9 AM"

3. **Schedule:**
   - Click "Schedule Report"
   - Report will run automatically

4. **Receive Emails:**
   - Get reports via email on schedule
   - No manual intervention needed

---

## Setup for Accurate Costs

### Enable Cost Allocation Tags (One-Time Setup)

**Why:** Get actual costs instead of estimates

**Steps:**

1. **Enable Cost Allocation Tags:**
   ```bash
   # Via AWS CLI
   aws ce create-cost-category-definition \
     --name ResourceId \
     --rules file://tag-rules.json
   ```

   Or via AWS Console:
   - Go to AWS Console → Billing → Cost Allocation Tags
   - Find "ResourceId" tag
   - Click "Activate"

2. **Tag Your Resources:**
   ```bash
   # Tag an EC2 instance
   aws ec2 create-tags \
     --resources i-1234567890 \
     --tags Key=ResourceId,Value=i-1234567890
   
   # Tag an RDS database
   aws rds add-tags-to-resource \
     --resource-name arn:aws:rds:us-east-1:123456789012:db:my-database \
     --tags Key=ResourceId,Value=db-my-database
   ```

3. **Wait 24 Hours:**
   - Cost Explorer updates daily
   - Tagged costs appear next day

4. **Verify:**
   - Generate a test report
   - Look for "(estimated)" vs actual costs

---

## Report Schedules

### Available Schedules

| Schedule | Description | Example |
|----------|-------------|---------|
| `daily` | Every day at 9 AM | Daily spending report |
| `weekly_monday` | Every Monday at 9 AM | Weekly team update |
| `weekly_friday` | Every Friday at 9 AM | Week-end summary |
| `monthly_1st` | 1st of month at 9 AM | Monthly cost review |
| `custom_06:00` | Every day at 6 AM | Early morning report |
| `custom_18:00` | Every day at 6 PM | End-of-day report |

### Custom Schedules

Format: `custom_HH:MM`

Examples:
- `custom_00:00` - Midnight
- `custom_12:00` - Noon
- `custom_23:00` - 11 PM

---

## Cost Estimation Details

### When Estimates Are Used

- Cost allocation tags not configured
- New resources (< 24 hours old)
- Resources without tags

### Estimation Methods

**EC2 Instances:**
```
Cost = Instance Type Hourly Rate × Hours Running

Example:
  t2.micro: $0.0116/hour
  Running 24 hours
  Cost = $0.0116 × 24 = $0.28/day
```

**RDS Databases:**
```
Cost = Instance Cost + Storage Cost

Example:
  db.t3.small: $0.034/hour × 24 = $0.82/day
  50 GB storage: $0.115/GB/month × 50 = $5.75/month ÷ 30 = $0.19/day
  Total = $0.82 + $0.19 = $1.01/day
```

**Lambda Functions:**
```
Cost = Request Cost + Compute Cost

Example:
  100,000 invocations
  Request cost = 100,000 / 1,000,000 × $0.20 = $0.02
  Compute cost = ~$0.001 (depends on memory/duration)
  Total = ~$0.021
```

---

## Email Configuration

### Required Settings

```bash
# Enable alerts
export ALERTS_ENABLED=true

# Email configuration
export ALERT_RECIPIENTS="team@company.com,manager@company.com"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT=587
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM_EMAIL="your-email@gmail.com"
```

### Email Format

```
Subject: AWS Cost Report: Weekly Cost Report

AWS COST REPORT
======================================================================

Weekly Cost Report - 2025-01-14 to 2025-01-21
Period: 2025-01-14 to 2025-01-21
Generated: 2025-01-21 09:00:00 UTC

======================================================================

SUMMARY
-------
Total Cost: $45.67
Resources Monitored: 5

======================================================================

COST BREAKDOWN BY RESOURCE
---------------------------

Resource: Web Server
  ID: i-1234567890
  Type: ec2
  Region: us-east-1
  Cost: $25.30

Resource: Production Database
  ID: db-prod-main
  Type: rds
  Region: us-east-1
  Cost: $15.20

...

======================================================================
NOTES
-----
* 2 resource(s) have estimated costs
* 3 resource(s) have actual costs from AWS Cost Explorer

To get actual costs for all resources:
1. Enable Cost Allocation Tags
2. Tag resources with 'ResourceId'
3. Wait 24 hours
======================================================================
```

---

## Usage Examples

### Example 1: Daily Production Costs

**Scenario:** Monitor your 3 production servers daily

**Setup:**
1. Select 3 EC2 instances
2. Name: "Production Servers Daily"
3. Period: Daily
4. Schedule: Every day at 6 AM

**Result:**
- Email every morning at 6 AM
- Shows yesterday's costs
- Track cost trends

---

### Example 2: Weekly Team Update

**Scenario:** Weekly cost summary for the team

**Setup:**
1. Select all production resources (EC2, RDS, Lambda)
2. Name: "Weekly Team Cost Report"
3. Period: Weekly
4. Schedule: Every Friday at 5 PM

**Result:**
- Email every Friday at 5 PM
- Shows last 7 days of costs
- Good for team meetings

---

### Example 3: Monthly Budget Review

**Scenario:** Monthly cost analysis for management

**Setup:**
1. Select all resources
2. Name: "Monthly Budget Report"
3. Period: Monthly
4. Schedule: 1st of month at 9 AM

**Result:**
- Email on 1st of each month
- Shows full month costs
- Compare to budget

---

## API Usage

### Generate Manual Report

```bash
curl -X POST http://localhost:5000/api/reports/generate \
  -H "Content-Type: application/json" \
  -d '{
    "resources": [
      {"id": "i-12345", "type": "ec2", "region": "us-east-1", "name": "Web Server"}
    ],
    "period": "weekly",
    "send_email": true
  }'
```

### Schedule Report

```bash
curl -X POST http://localhost:5000/api/reports/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weekly EC2 Report",
    "resources": [...],
    "period": "weekly",
    "schedule": "weekly_monday"
  }'
```

### List Scheduled Reports

```bash
curl http://localhost:5000/api/reports/scheduled
```

### Remove Scheduled Report

```bash
curl -X DELETE http://localhost:5000/api/reports/scheduled/Weekly%20EC2%20Report
```

---

## Troubleshooting

### Issue: All Costs Show as Estimated

**Cause:** Cost allocation tags not configured

**Solution:**
1. Enable cost allocation tags in AWS Console
2. Tag resources with `ResourceId=<resource-id>`
3. Wait 24 hours
4. Re-generate report

---

### Issue: Lambda Costs Show $0

**Cause:** Very low usage or free tier

**Solution:**
- Check if under free tier (1M requests/month)
- Lambda costs are very small ($0.20 per 1M requests)
- May need monthly report to see costs

---

### Issue: Report Not Sent

**Cause:** Email not configured or monitoring not started

**Solution:**
1. Verify email settings (see Email Configuration)
2. Start monitoring: Click "Start Monitoring"
3. Test email: Click "Send Test Alert"
4. Check logs for errors

---

### Issue: Costs Don't Match AWS Bill

**Possible Reasons:**
1. Using estimates instead of actual costs → Enable tags
2. Different time periods → Check report period
3. Reserved instances → Estimates use on-demand pricing
4. Data transfer costs → Not included in estimates

**Solution:**
- Enable cost allocation tags for 100% accuracy
- Compare same time periods
- Use actual costs for billing accuracy

---

## Best Practices

### 1. **Tag Resources**
- Always tag for accurate costs
- Use consistent naming
- Update tags when creating resources

### 2. **Start Simple**
- Begin with daily reports for critical resources
- Expand to weekly/monthly as needed
- Don't over-report (email fatigue)

### 3. **Review Regularly**
- Check reports weekly
- Look for cost spikes
- Identify optimization opportunities

### 4. **Set Expectations**
- Estimated costs are ~90% accurate
- Actual costs may take 24-48 hours
- Monthly reports are most accurate

### 5. **Automate Wisely**
- Daily: Critical production resources
- Weekly: Team updates
- Monthly: Budget reviews

---

## Pricing Impact

### API Costs

**Cost Explorer:**
- First request per day: FREE
- Additional requests: $0.01 each

**Typical Usage:**
- Daily report: 1 request/day = $0.00
- Weekly report: 1 request/week = ~$0.04/month
- Monthly report: 1 request/month = $0.01

**CloudWatch:**
- Metrics queries: FREE (first 1M/month)

**Total Cost:**
- Light usage: $0.00/month
- Moderate usage: $0.10/month
- Heavy usage: $1.00/month

---

## FAQ

**Q: Can I get reports for specific tags?**
A: Not yet - select resources manually. Coming in future update.

**Q: Can I export reports to CSV?**
A: Not yet - email only. Coming in future update.

**Q: How far back can I go?**
A: Up to 90 days (Cost Explorer limit)

**Q: Can I compare month-to-month?**
A: Not in current version - manual comparison needed

**Q: Do costs include taxes?**
A: Shows AWS charges only, not taxes

**Q: Can I schedule multiple reports?**
A: Yes! Schedule as many as needed

---

## Summary

### Key Features
- ✅ Manual and scheduled reports
- ✅ Daily/weekly/monthly periods
- ✅ Email delivery
- ✅ Actual or estimated costs
- ✅ Per-resource breakdown
- ✅ Easy configuration

### Next Steps
1. Select resources
2. Generate test report
3. Set up cost allocation tags (optional)
4. Schedule automated reports
5. Monitor costs regularly

Happy cost monitoring! 💰
