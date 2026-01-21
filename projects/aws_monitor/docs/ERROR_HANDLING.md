# Error Handling Guide

## Overview

The AWS Resource Monitor is designed to **fail gracefully** - if it can't access one resource type or region, it logs the error and continues with others.

## Design Philosophy

### ✅ **Do:**
- Log errors clearly
- Continue with other resources
- Show what we could access
- Give helpful error messages

### ❌ **Don't:**
- Crash the entire application
- Stop scanning other resources
- Show generic error messages
- Leave users confused

---

## How Errors Are Handled

### Scenario 1: No Permission for RDS

**What Happens:**
```
User clicks "Load Resources" for regions: us-east-1, us-west-2
```

**Behind the Scenes:**
```
✅ us-east-1 EC2: Found 5 instances
✅ us-east-1 RDS: Found 2 databases
⚠️  us-east-1 Lambda: AccessDenied - No permission
✅ us-east-1 EBS: Found 3 volumes
✅ us-west-2 EC2: Found 8 instances
⚠️  us-west-2 RDS: AccessDenied - No permission
✅ us-west-2 Lambda: Found 4 functions
✅ us-west-2 EBS: Found 6 volumes
✅ S3: Found 10 buckets
```

**What You See:**
- Table showing all EC2 instances (13 total)
- Table showing RDS databases (2 from us-east-1 only)
- Table showing Lambda functions (4 from us-west-2 only)
- Table showing EBS volumes (9 total)
- Table showing S3 buckets (10 total)

**In Logs:**
```
2025-01-21 10:15:30 - INFO - Scanning region: us-east-1
2025-01-21 10:15:31 - INFO - Found 5 EC2 instances in us-east-1
2025-01-21 10:15:32 - INFO - Found 2 RDS instances in us-east-1
2025-01-21 10:15:33 - WARNING - Cannot access Lambda in us-east-1: AccessDeniedException. Continuing with other resources...
2025-01-21 10:15:34 - INFO - Found 3 EBS volumes in us-east-1
2025-01-21 10:15:35 - INFO - Scanning region: us-west-2
...
2025-01-21 10:15:45 - INFO - Successfully retrieved 32 total resources
```

---

### Scenario 2: Region Not Enabled

**What Happens:**
```
User selects: us-east-1, ap-southeast-3 (not enabled in account)
```

**Behind the Scenes:**
```
✅ us-east-1 EC2: Found 5 instances
✅ us-east-1 RDS: Found 2 databases
⚠️  ap-southeast-3 EC2: OptInRequired - Region not enabled
⚠️  ap-southeast-3 RDS: OptInRequired - Region not enabled
...
```

**What You See:**
- All resources from us-east-1
- Empty for ap-southeast-3

**In Logs:**
```
2025-01-21 10:20:15 - INFO - Region ap-southeast-3 is not enabled in your account
2025-01-21 10:20:15 - WARNING - Cannot access EC2 in ap-southeast-3: ...Continuing with other resources...
```

---

### Scenario 3: Cost Explorer Not Enabled

**What Happens:**
```
User clicks "Load Costs"
```

**If Cost Explorer is disabled:**

**Behind the Scenes:**
```
⚠️  Cost Explorer: OptInRequired - Not enabled
```

**What You See:**
- Error message: "Cost Explorer not enabled. Enable it in AWS Console → Billing → Cost Explorer."

**In Logs:**
```
2025-01-21 10:25:00 - WARNING - Cost Explorer not enabled. Enable it in AWS Console.
```

---

### Scenario 4: Partial Metrics Failure

**What Happens:**
```
User selects 3 instances and clicks "Load Metrics"
```

**Behind the Scenes:**
```
✅ i-12345: Retrieved CPU metrics
⚠️  i-67890: Resource not found (maybe terminated?)
✅ i-abcde: Retrieved CPU metrics
```

**What You See:**
- Chart with data for 2 instances
- Note: "Could not retrieve metrics for i-67890"

**In Logs:**
```
2025-01-21 10:30:15 - INFO - Successfully retrieved metrics for i-12345
2025-01-21 10:30:16 - WARNING - No permission to get metrics for i-67890
2025-01-21 10:30:17 - INFO - Successfully retrieved metrics for i-abcde
```

---

## Common Error Codes

### AWS Error Codes

| Error Code | Meaning | What We Do |
|------------|---------|------------|
| `UnauthorizedOperation` | No IAM permission | Log warning, continue |
| `AccessDenied` | No permission | Log warning, continue |
| `AccessDeniedException` | No permission | Log warning, continue |
| `OptInRequired` | Region not enabled | Log info, continue |
| `InvalidInstanceID.NotFound` | Resource doesn't exist | Log error, continue |
| `Throttling` | Too many requests | Log error, may retry |

### Application Behavior

```python
try:
    # Try to get resources
    ec2_instances = get_ec2_instances(region)
    resources['ec2'].extend(ec2_instances)
    logger.info(f"Found {len(ec2_instances)} EC2 instances in {region}")
    
except ClientError as e:
    # AWS returned an error
    error_code = e.response['Error']['Code']
    
    if error_code == 'UnauthorizedOperation':
        logger.warning(f"No permission to access EC2 in {region}")
    elif error_code == 'OptInRequired':
        logger.info(f"Region {region} is not enabled")
    else:
        logger.error(f"AWS error: {error_code}")
    
    # DON'T crash - continue to next resource type

except Exception as e:
    # Unexpected error
    logger.error(f"Unexpected error: {e}")
    # Still don't crash - continue
```

---

## Where to Find Error Information

### 1. Application Logs (Console)

When running the app, you'll see:
```bash
$ python main.py

2025-01-21 10:15:30 - aws_client - INFO - Scanning region: us-east-1
2025-01-21 10:15:31 - aws_client - INFO - Found 5 EC2 instances in us-east-1
2025-01-21 10:15:32 - aws_client - WARNING - Cannot access RDS in us-east-1: AccessDenied
2025-01-21 10:15:33 - aws_client - INFO - Successfully retrieved 5 total resources
```

### 2. Browser Console (F12)

In the browser developer tools:
```javascript
Resource discovery completed
Warning: Some resources could not be accessed
Loaded 5 EC2 instances, 0 RDS databases
```

### 3. Response Messages

The API returns helpful information:
```json
{
    "success": true,
    "data": {
        "ec2": [...],
        "rds": [],
        "warnings": [
            "Could not access RDS in us-east-1: Access Denied"
        ]
    }
}
```

---

## Examples of Good Error Messages

### ✅ Good: Clear and Actionable

```
WARNING - Cannot access Lambda in us-east-1: AccessDeniedException. 
Continuing with other resources...

Suggestion: Add 'lambda:ListFunctions' permission to your IAM role
```

### ✅ Good: Informative

```
INFO - Region ap-southeast-3 is not enabled in your account

This is normal - enable the region in AWS Console if needed
```

### ✅ Good: User-Friendly

```
Cost Explorer not enabled. 
Enable it in AWS Console → Billing → Cost Explorer.
First request per day is free.
```

### ❌ Bad: Vague

```
Error getting resources
```

### ❌ Bad: Technical Jargon

```
boto3.exceptions.ClientError: An error occurred (UnauthorizedOperation) 
when calling the DescribeInstances operation: You are not authorized 
to perform this operation. Encoded authorization failure message: 
[very long encoded string]
```

---

## Error Handling Flow Chart

```
┌─────────────────────────┐
│ User Clicks             │
│ "Load Resources"        │
└──────────┬──────────────┘
           │
           ↓
┌─────────────────────────┐
│ For Each Region         │
└──────────┬──────────────┘
           │
           ↓
┌─────────────────────────┐
│ Try: Get EC2            │
└──────────┬──────────────┘
           │
      ┌────┴────┐
      │         │
   Success    Error
      │         │
      │         ↓
      │    Log Warning
      │    Continue
      │         │
      └────┬────┘
           │
           ↓
┌─────────────────────────┐
│ Try: Get RDS            │
└──────────┬──────────────┘
           │
      ┌────┴────┐
      │         │
   Success    Error
      │         │
      │         ↓
      │    Log Warning
      │    Continue
      │         │
      └────┬────┘
           │
           ↓
     [Continue for
      all services]
           │
           ↓
┌─────────────────────────┐
│ Return All             │
│ Successfully           │
│ Retrieved Resources    │
└─────────────────────────┘
```

---

## Best Practices

### For Users

1. **Check logs first** when something seems missing
2. **Review IAM permissions** if warnings appear
3. **Enable regions** you want to monitor
4. **Enable Cost Explorer** for cost data

### For Developers

1. **Always use try-except** blocks
2. **Log at appropriate levels**:
   - `INFO`: Normal operations
   - `WARNING`: Missing permissions, disabled features
   - `ERROR`: Unexpected failures
3. **Continue processing** after errors
4. **Provide context** in error messages
5. **Return partial results** rather than nothing

---

## Testing Error Handling

### Test 1: Missing Permissions

Remove a permission and verify:
```bash
# Remove RDS permission
# Run app
# Check logs show: "Cannot access RDS: AccessDenied"
# Verify EC2, S3, Lambda still work
```

### Test 2: Invalid Region

Select a region not enabled:
```bash
# Select ap-southeast-3 (if not enabled)
# Run app
# Check logs show: "Region not enabled"
# Verify other regions still work
```

### Test 3: Cost Explorer Disabled

Try to get costs without enabling:
```bash
# Don't enable Cost Explorer
# Click "Load Costs"
# Check error message: "Enable Cost Explorer in AWS Console"
# Verify other features still work
```

---

## Monitoring for Errors

### Production Monitoring

**Watch for these log patterns:**
```bash
# Check for frequent errors
grep -i "error" app.log | wc -l

# Check for specific permission issues
grep "AccessDenied" app.log

# Check success rate
grep "Successfully retrieved" app.log | tail -n 10
```

### Alerting

Set up alerts for:
- More than 5 errors per minute
- Any CRITICAL level logs
- 3+ consecutive failures for same resource type

---

## Summary

### Key Points

1. **Application never crashes** due to one resource failure
2. **Errors are logged clearly** with context
3. **Partial results are returned** - show what we can access
4. **Users get actionable messages** - what to fix and how
5. **Processing continues** - one failure doesn't stop everything

### What This Means for You

- ✅ Can monitor resources even with partial permissions
- ✅ No need to grant all permissions upfront
- ✅ Easy to diagnose permission issues
- ✅ Application remains reliable
- ✅ Gradual permission granting works fine

### Example Scenario

**Day 1:** Only EC2 permissions
- ✅ EC2 works perfectly
- ⚠️  RDS, Lambda show "Access Denied"
- Application still useful!

**Day 2:** Add RDS permissions
- ✅ EC2 works
- ✅ RDS now works!
- ⚠️  Lambda still shows "Access Denied"
- More functionality unlocked

**Day 3:** Add all permissions
- ✅ Everything works!

At no point did the application crash or stop working. You could use it with any level of permissions and gradually expand access.
