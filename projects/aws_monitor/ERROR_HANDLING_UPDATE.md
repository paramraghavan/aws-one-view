# Update: Graceful Error Handling

## What Changed

The application now handles errors gracefully - if one resource type or region fails, it **logs the error and continues** with others instead of crashing.

## Key Improvements

### Before
```python
# If RDS fails, entire scan stops
resources['ec2'] = get_ec2()
resources['rds'] = get_rds()  # ❌ Crashes here if no permission
resources['s3'] = get_s3()    # Never reached
```

### After
```python
# Each resource type is independent
try:
    resources['ec2'] = get_ec2()
    logger.info("✅ EC2: Success")
except Exception as e:
    logger.warning(f"⚠️  EC2 failed: {e}. Continuing...")
    resources['ec2'] = []

try:
    resources['rds'] = get_rds()
    logger.info("✅ RDS: Success")
except Exception as e:
    logger.warning(f"⚠️  RDS failed: {e}. Continuing...")
    resources['rds'] = []

try:
    resources['s3'] = get_s3()
    logger.info("✅ S3: Success")
except Exception as e:
    logger.warning(f"⚠️  S3 failed: {e}. Continuing...")
    resources['s3'] = []

# All three attempted, show what we got
```

---

## Real-World Example

### Scenario: Limited Permissions

You have permissions for EC2 and S3, but not RDS or Lambda.

**What Happens:**
```
User clicks "Load Resources" from us-east-1, us-west-2
```

**Console Output:**
```
2025-01-21 10:15:30 - INFO - Scanning region: us-east-1
2025-01-21 10:15:31 - INFO - Found 5 EC2 instances in us-east-1
2025-01-21 10:15:32 - WARNING - Cannot access RDS in us-east-1: AccessDenied. Continuing...
2025-01-21 10:15:33 - WARNING - Cannot access Lambda in us-east-1: AccessDenied. Continuing...
2025-01-21 10:15:34 - INFO - Found 3 EBS volumes in us-east-1

2025-01-21 10:15:35 - INFO - Scanning region: us-west-2
2025-01-21 10:15:36 - INFO - Found 8 EC2 instances in us-west-2
2025-01-21 10:15:37 - WARNING - Cannot access RDS in us-west-2: AccessDenied. Continuing...
2025-01-21 10:15:38 - WARNING - Cannot access Lambda in us-west-2: AccessDenied. Continuing...
2025-01-21 10:15:39 - INFO - Found 6 EBS volumes in us-west-2

2025-01-21 10:15:40 - INFO - Found 10 S3 buckets
2025-01-21 10:15:41 - INFO - Successfully retrieved 32 total resources
```

**Dashboard Shows:**
- ✅ 13 EC2 instances (5 + 8)
- ⚠️  0 RDS databases (with note: "Access denied")
- ✅ 10 S3 buckets
- ⚠️  0 Lambda functions (with note: "Access denied")
- ✅ 9 EBS volumes (3 + 6)

**Application:** Still fully functional with partial data!

---

## Error Types Handled

### 1. Permission Errors
- `UnauthorizedOperation`
- `AccessDenied`
- `AccessDeniedException`

**Action:** Log warning, continue

### 2. Configuration Errors
- `OptInRequired` (region not enabled)
- Region not available

**Action:** Log info, continue

### 3. Resource Not Found
- Instance terminated
- Resource deleted

**Action:** Log error, continue

### 4. Service Unavailable
- Throttling
- Service outage

**Action:** Log error, continue

---

## Benefits

### ✅ Reliability
- Application never crashes due to missing permissions
- Partial results are better than no results
- One failing region doesn't affect others

### ✅ Debugging
- Clear log messages explain what failed
- Specific error codes help diagnose issues
- Easy to identify permission problems

### ✅ Flexibility
- Works with any level of permissions
- Can gradually expand access
- Start monitoring immediately with minimal permissions

### ✅ User Experience
- Shows what data is available
- Explains what's missing
- Provides actionable guidance

---

## Code Changes

### File: `app/aws_client.py`

**Added:**
- Import `ClientError` from `botocore.exceptions`
- Individual try-except for each resource type
- Detailed error logging with error codes
- Continue processing on failures
- Summary logging

**Updated Methods:**
- `get_all_resources()` - Wraps each resource call in try-except
- `_get_ec2_instances()` - Better error messages
- `_get_rds_instances()` - Better error messages
- `_get_s3_buckets()` - Better error messages
- `_get_lambda_functions()` - Better error messages
- `_get_ebs_volumes()` - Better error messages
- `get_metrics()` - Continues if one resource fails
- `get_costs()` - Specific error for Cost Explorer issues

---

## Log Levels Used

### INFO
- Successful operations
- Resource counts
- Progress updates

```
INFO - Found 5 EC2 instances in us-east-1
INFO - Successfully retrieved 32 total resources
```

### WARNING
- Missing permissions (expected in some cases)
- Features not enabled
- Non-critical failures

```
WARNING - Cannot access RDS in us-east-1: AccessDenied
WARNING - Cost Explorer not enabled
```

### ERROR
- Unexpected failures
- Service errors
- Critical issues

```
ERROR - AWS error getting EC2 instances: InternalError
ERROR - Unexpected error: ConnectionTimeout
```

---

## Testing

### Test 1: Remove RDS Permission

```bash
# In IAM, remove rds:DescribeDBInstances
# Run application
# Expected: EC2, S3, Lambda work; RDS shows warning
```

### Test 2: Invalid Region

```bash
# Select ap-southeast-3 (if not enabled)
# Run application
# Expected: Other regions work; ap-southeast-3 shows info message
```

### Test 3: No Permissions

```bash
# Use credentials with no permissions
# Run application
# Expected: All show warnings, app doesn't crash
```

---

## Migration Guide

### If you have the old version:

1. **Extract new version**
   ```bash
   tar -xzf aws_monitor_clean_v2.tar.gz
   ```

2. **No configuration changes needed**
   - Error handling is automatic
   - Works with existing setup

3. **Check logs for warnings**
   ```bash
   python main.py
   # Look for WARNING messages
   # Add permissions for services showing warnings
   ```

4. **Gradually add permissions**
   - Start with what works
   - Add more permissions over time
   - Application adapts automatically

---

## Documentation

### New File: `docs/ERROR_HANDLING.md`
Complete guide to error handling:
- How it works
- Common scenarios
- Error codes
- Troubleshooting
- Best practices

### Updated File: `app/aws_client.py`
- Better error handling
- Clearer logging
- Graceful failures
- Continues processing

---

## Example Logs

### Successful Scan
```
2025-01-21 10:15:30 - INFO - Scanning region: us-east-1
2025-01-21 10:15:31 - INFO - Found 5 EC2 instances in us-east-1
2025-01-21 10:15:32 - INFO - Found 2 RDS instances in us-east-1
2025-01-21 10:15:33 - INFO - Found 4 Lambda functions in us-east-1
2025-01-21 10:15:34 - INFO - Found 3 EBS volumes in us-east-1
2025-01-21 10:15:35 - INFO - Found 10 S3 buckets
2025-01-21 10:15:36 - INFO - Successfully retrieved 24 total resources
```

### Partial Permissions
```
2025-01-21 10:15:30 - INFO - Scanning region: us-east-1
2025-01-21 10:15:31 - INFO - Found 5 EC2 instances in us-east-1
2025-01-21 10:15:32 - WARNING - No permission to access RDS in us-east-1
2025-01-21 10:15:32 - WARNING - Cannot access RDS in us-east-1: AccessDenied. Continuing...
2025-01-21 10:15:33 - INFO - Found 4 Lambda functions in us-east-1
2025-01-21 10:15:34 - INFO - Found 3 EBS volumes in us-east-1
2025-01-21 10:15:35 - INFO - Found 10 S3 buckets
2025-01-21 10:15:36 - INFO - Successfully retrieved 22 total resources
```

### Region Not Enabled
```
2025-01-21 10:15:30 - INFO - Scanning region: ap-southeast-3
2025-01-21 10:15:31 - INFO - Region ap-southeast-3 is not enabled in your account
2025-01-21 10:15:31 - WARNING - Cannot access EC2 in ap-southeast-3: OptInRequired. Continuing...
2025-01-21 10:15:32 - INFO - Region ap-southeast-3 is not enabled in your account
2025-01-21 10:15:32 - WARNING - Cannot access RDS in ap-southeast-3: OptInRequired. Continuing...
```

---

## Summary

### Before This Update
- ❌ One failure = entire scan fails
- ❌ Generic error messages
- ❌ Application crashes
- ❌ No partial results

### After This Update
- ✅ One failure = log and continue
- ✅ Specific, actionable error messages
- ✅ Application always completes
- ✅ Shows all available data

### Result
**More reliable, more flexible, easier to debug!**

The application now works even with minimal permissions and provides clear guidance on what additional permissions would unlock more features.
