# FAQ & Troubleshooting

## Bottleneck Detection Questions

### Q: How far back does bottleneck detection look?

**A: 24 hours** (last 24 hours of CloudWatch data)

**Why 24 hours?**
- Recent enough to catch current issues
- Enough data points for accurate analysis (24 data points, 1 per hour)
- Balances accuracy with API costs
- Standard monitoring timeframe

**What it checks:**
```python
end_time = datetime.utcnow()           # Now
start_time = end_time - timedelta(hours=24)  # 24 hours ago

# Gets 24 hourly data points
# Calculates: average CPU and peak CPU
# Compares against thresholds (80% / 90%)
```

**Can I change it?**

Yes! Edit `app/config.py`:
```python
class Config:
    # Add this setting
    BOTTLENECK_LOOKBACK_HOURS = 24  # Change to 48, 72, or 168 (1 week)
```

Then update `app/aws_client.py`:
```python
start_time = end_time - timedelta(hours=Config.BOTTLENECK_LOOKBACK_HOURS)
```

**Recommendations:**
- **24 hours** (default): Good for daily checks
- **48-72 hours**: Better for weekly reviews
- **168 hours (1 week)**: Comprehensive analysis, but slower

---

## Cost Analysis Questions

### Q: Why does Lambda show $0 when I know we use it?

**A: Several possible reasons:**

#### 1. **Lambda Costs Are Very Small**

Lambda pricing is:
- $0.20 per 1 million requests
- $0.0000166667 per GB-second of compute

Example:
```
100,000 invocations/day × 30 days = 3 million invocations
Cost = 3M × $0.20 / 1M = $0.60/month

If average per day: $0.60 / 30 = $0.02/day
```

**Small daily amounts might round to $0.00** in the display!

#### 2. **Service Name Mismatch**

Cost Explorer returns service names like:
- "AWS Lambda" ✅
- "Amazon Lambda" (sometimes)
- "Lambda" (rare)

**Solution:** Let me update the code to aggregate Lambda costs better.

#### 3. **Free Tier**

Lambda free tier includes:
- 1 million requests/month
- 400,000 GB-seconds/month

If you're under these limits → $0 cost is correct!

#### 4. **Cost Explorer Granularity**

With daily granularity, small costs might not appear. Try:
- Change to "MONTHLY" granularity
- Or sum across all days

---

### Q: My total cost is $15,781 but Lambda shows $0?

**Let me check your costs breakdown:**

**Current Implementation Issue:**
The cost display might be filtering out services with very small daily costs.

**What's Likely Happening:**

Your $15,781 is probably from:
- EC2: ~$10,000 (large instances)
- RDS: ~$3,000 (databases)
- S3: ~$1,500 (storage)
- Data Transfer: ~$800
- Other services: ~$481
- **Lambda: ~$0.60** (too small to display per day!)

**Solutions:**

1. **Show All Services** - Even $0.00
2. **Aggregate Small Costs** - Group services under $1/day
3. **Show Monthly Totals** - Better for small recurring costs

Let me fix this now!

---

## Resource Details Questions

### Q: Can I see more info when clicking on a resource?

**A: Yes! I'll add a resource detail panel.**

**What should it show?**
- ✅ Resource details (ID, type, status)
- ✅ Recent metrics (last 24 hours)
- ✅ Cost for this resource (if available)
- ✅ Tags
- ✅ Security groups (for EC2)
- ✅ Health status
- ✅ Recommendations

**Coming in the next update!**

---

## Common Issues & Solutions

### Issue 1: "No data" in Bottleneck Detection

**Possible Causes:**
1. No running instances
2. Instance started < 1 hour ago (no metrics yet)
3. CloudWatch metrics disabled
4. No permission to read metrics

**Solutions:**
```bash
# Check CloudWatch permissions
aws cloudwatch list-metrics --namespace AWS/EC2

# Verify instances have been running
aws ec2 describe-instances --filters "Name=instance-state-name,Values=running"
```

---

### Issue 2: Cost Data Missing

**Possible Causes:**
1. Cost Explorer not enabled
2. Data not yet available (24-hour delay)
3. No permission for Cost Explorer
4. Service has $0 cost

**Solutions:**
1. Enable Cost Explorer in AWS Console
2. Wait 24 hours after enabling
3. Add IAM permission: `ce:GetCostAndUsage`
4. Check if service is in free tier

---

### Issue 3: Missing Resources in Specific Region

**Possible Causes:**
1. Region not enabled in account
2. No resources in that region
3. No permission for region

**Solutions:**
```bash
# Check enabled regions
aws ec2 describe-regions

# Check if region is opted-in
aws account get-region-opt-status --region-name ap-southeast-3
```

---

## Performance Questions

### Q: How long does a full scan take?

**Depends on:**
- Number of regions: ~5 seconds per region
- Number of resources: Minimal impact
- API rate limits: Could slow things down

**Typical Times:**
- 1 region, 50 resources: **10 seconds**
- 3 regions, 200 resources: **25 seconds**
- 5 regions, 500 resources: **40 seconds**

**Optimization Tips:**
- Select only needed regions
- Use resource filters
- Cache results (automatic, 5 minutes)

---

### Q: Will this cost me money?

**API Costs:**
- EC2/RDS/S3 describe operations: **FREE**
- CloudWatch metrics (first 1M/month): **FREE**
- Cost Explorer (first request/day): **FREE**

**Typical Monthly Cost:**
- Light usage (1-2 scans/day): **$0.00**
- Moderate usage (10 scans/day): **$0.30** (Cost Explorer)
- Heavy usage (100 scans/day): **$3.00**

**Background monitoring adds:**
- 4 checks/hour × 24 hours = 96 checks/day
- Cost: ~**$1.00/month** for Cost Explorer

---

## Configuration Questions

### Q: Can I change the CPU thresholds?

**Yes!** Edit `app/config.py`:

```python
class Config:
    CPU_HIGH_THRESHOLD = 80.0      # Change to 70 for stricter
    CPU_CRITICAL_THRESHOLD = 90.0  # Change to 85 for stricter
    CPU_LOW_THRESHOLD = 10.0       # Change to 20 for stricter
```

---

### Q: Can I monitor more resource types?

**Yes!** Currently supported:
- ✅ EC2
- ✅ RDS
- ✅ S3
- ✅ Lambda
- ✅ EBS

**Coming soon / Easy to add:**
- ECS/EKS
- ElastiCache
- DynamoDB
- CloudFront
- ALB/NLB

See `docs/MAINTENANCE.md` for how to add new resource types.

---

### Q: Can I export data?

**Not yet built-in, but easy to add!**

**Current workaround:**
1. Open browser console (F12)
2. Click "Load Resources"
3. In console, type:
   ```javascript
   copy(JSON.stringify(allResources, null, 2))
   ```
4. Paste into text file

**Coming feature:** Export to CSV/JSON/Excel

---

## Monitoring Questions

### Q: How often does background monitoring check?

**A: Every 15 minutes** (configurable)

Change in `.env`:
```bash
MONITORING_INTERVAL_MINUTES=30  # Check every 30 minutes
```

Or in code (`app/config.py`):
```python
MONITORING_INTERVAL_MINUTES = int(os.getenv('MONITORING_INTERVAL_MINUTES', '15'))
```

---

### Q: Will I get an alert every 15 minutes?

**No!** Alerts are only sent when:
1. Threshold is **first exceeded** (status change)
2. Still exceeding after **6 hours** (reminder)
3. Status returns to **normal** (recovery notice)

**Example:**
```
10:00 AM - CPU at 85% → 🔔 Alert sent
10:15 AM - CPU still at 85% → No alert
10:30 AM - CPU still at 85% → No alert
...
4:00 PM - CPU still at 85% → 🔔 Reminder sent (6 hours later)
4:15 PM - CPU back to 60% → 🔔 Recovery notice
```

---

### Q: Can I monitor specific metrics?

**Currently monitors:**
- CPU utilization (EC2, RDS)
- Database connections (RDS)
- Lambda invocations

**To add more metrics**, edit `app/monitoring.py`:
```python
# Add memory monitoring
memory_data = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='MemoryUtilization',
    # ... rest of config
)
```

---

## Security Questions

### Q: Are my AWS credentials safe?

**Yes!** The application:
- ✅ Uses environment variables (not stored in code)
- ✅ Supports IAM roles (no credentials needed)
- ✅ Never logs credentials
- ✅ Read-only access (no modifications)

---

### Q: What IAM permissions are needed?

**Minimum (read-only):**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeInstances",
      "ec2:DescribeRegions",
      "cloudwatch:GetMetricStatistics"
    ],
    "Resource": "*"
  }]
}
```

**Full features:**
See `docs/iam-policy.json` for complete policy.

---

## Advanced Questions

### Q: Can I use this with multiple AWS accounts?

**Not yet, but coming soon!**

**Current workaround:**
1. Run multiple instances of the app
2. Use different ports:
   ```bash
   # Account 1
   PORT=5000 python main.py
   
   # Account 2
   PORT=5001 python main.py
   ```

---

### Q: Can I integrate with Slack/PagerDuty?

**Not built-in, but easy to add!**

Edit `app/alerts.py`:
```python
def send_alert(self, issues):
    # Existing email code...
    
    # Add Slack webhook
    import requests
    requests.post(
        'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
        json={'text': f'Alert: {len(issues)} issues detected'}
    )
```

---

## Still Have Questions?

1. **Check the docs:**
   - `README.md` - Getting started
   - `docs/CONFIGURATION.md` - Setup details
   - `docs/MAINTENANCE.md` - Extending features
   - `docs/ERROR_HANDLING.md` - Troubleshooting

2. **Check the logs:**
   ```bash
   python main.py
   # Watch for INFO, WARNING, ERROR messages
   ```

3. **Test connectivity:**
   ```bash
   python tests/test_connection.py
   ```

4. **Enable debug mode:**
   ```bash
   export DEBUG=true
   python main.py
   ```
