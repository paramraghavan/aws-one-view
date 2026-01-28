# Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: Script Generation Error - "name 'json' is not defined"

**Problem**: When generating a monitoring script, you get an error about json not being defined.

**Solution**: ✅ **FIXED** - The json module import has been added to the script generator.

**Verification**: Generate a script again. It should download successfully.

---

### Issue 2: EKS Clusters Not Showing Up

**Problem**: No EKS (Kubernetes) clusters appear in the discovered resources.

**Possible Causes**:

1. **No EKS clusters exist** in the selected regions
   - Check AWS Console → EKS to verify clusters exist
   - Try selecting different regions

2. **Missing IAM permissions** for EKS
   - Required permissions:
     ```json
     {
       "Effect": "Allow",
       "Action": [
         "eks:ListClusters",
         "eks:DescribeCluster",
         "eks:ListNodegroups",
         "eks:DescribeNodegroup"
       ],
       "Resource": "*"
     }
     ```

3. **Region doesn't support EKS**
   - Not all regions have EKS available
   - Check: https://aws.amazon.com/eks/features/

**Test EKS Access**:
```bash
# List clusters with AWS CLI
aws eks list-clusters --region us-east-1 --profile monitor

# If this returns empty [], you have no clusters
# If this returns error, you need permissions
```

**Solution**:
- If no clusters: This is expected - EKS won't show up
- If permission error: Add EKS permissions to your IAM policy
- If you see clusters in CLI but not in app: Check filters (tags, names, IDs)

---

### Issue 3: Other Resource Types Not Showing

**For each resource type, verify**:

**EC2**:
```bash
aws ec2 describe-instances --region us-east-1 --profile monitor
```

**RDS**:
```bash
aws rds describe-db-instances --region us-east-1 --profile monitor
```

**S3** (global):
```bash
aws s3 ls --profile monitor
```

**Lambda**:
```bash
aws lambda list-functions --region us-east-1 --profile monitor
```

**EMR**:
```bash
aws emr list-clusters --region us-east-1 --profile monitor
```

If any return errors about permissions, add the required IAM permissions.

---

### Issue 4: "No Resources Found" But They Exist

**Problem**: You know resources exist, but nothing shows up.

**Causes**:

1. **Wrong AWS profile**
   - Verify: The app uses profile 'monitor'
   - Check: `cat ~/.aws/credentials | grep -A 3 "\[monitor\]"`

2. **Wrong region selected**
   - Resources exist in different regions
   - Try: Click "Load All Regions" and select more regions

3. **Filters are too restrictive**
   - Clear all filters (tags, names, IDs)
   - Try discovering without any filters first

4. **Resources filtered out**
   - Check your tag filters match exactly
   - Names and IDs are case-sensitive

**Solution**: Start simple - no filters, just select regions and discover.

---

### Issue 5: Performance Metrics Not Clickable

**Problem**: Previously, metric items couldn't be clicked for details.

**Solution**: ✅ **FIXED** - Metric items are now clickable and show detailed information in a popup modal.

**Usage**:
1. Select resources and click "Get Metrics"
2. Click on any metric item (CPU, Memory, etc.)
3. A popup shows all metric details (current, max, avg)

---

### Issue 6: All Resource Groups Open at Once

**Problem**: Previously, all resource types were displayed expanded, making it hard to navigate.

**Solution**: ✅ **FIXED** - Resources are now grouped by type with collapsible sections.

**Features**:
- Resources grouped by type (EC2, RDS, EKS, etc.)
- Click header to expand/collapse
- All sections start collapsed
- Shows resource count in header

---

### Issue 7: Can't See Detailed Resource Information

**Problem**: No way to see all details of a resource.

**Solution**: ✅ **FIXED** - Added "Details" button for each resource.

**Usage**:
1. Expand a resource type section
2. Click "Details" button in the Actions column
3. Popup shows all resource properties

---

### Issue 8: Role Assumption Fails

**Problem**: Error when using `--role-arn` parameter.

**Error**: "User is not authorized to perform: sts:AssumeRole"

**Solution**:
```json
{
  "Effect": "Allow",
  "Action": "sts:AssumeRole",
  "Resource": "arn:aws:iam::TARGET_ACCOUNT:role/MonitoringRole"
}
```

Add this policy to your base 'monitor' user/role.

**Error**: "Access Denied"

**Solution**: Update the role's trust policy:
```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::YOUR_ACCOUNT:user/YOUR_USER"
  },
  "Action": "sts:AssumeRole"
}
```

---

### Issue 9: Credentials Expired

**Problem**: "The security token included in the request is expired"

**Cause**: Temporary credentials from role assumption expired (1 hour duration).

**Solution**:
- Web UI: Restart the application
- Generated scripts: Re-run the script
- Credentials automatically refresh on restart

---

### Issue 10: Cost Explorer Not Working

**Problem**: Error when clicking "Analyze Costs"

**Error**: "AccessDeniedException" or "Cost Explorer is not enabled"

**Solution**:
1. Enable Cost Explorer in AWS Console
   - Billing → Cost Explorer → Enable
2. Wait 24 hours for data to populate
3. Add permission:
   ```json
   {
     "Effect": "Allow",
     "Action": "ce:GetCostAndUsage",
     "Resource": "*"
   }
   ```

---

### Issue 11: Connection Refused / Can't Access UI

**Problem**: Browser shows "Connection refused" at localhost:5000

**Solutions**:

1. **Check if app is running**:
   ```bash
   ps aux | grep "python.*main.py"
   ```

2. **Check port 5000 is free**:
   ```bash
   lsof -i :5000
   ```

3. **Use different port**:
   ```bash
   python main.py --port 8080
   ```

4. **Check firewall**:
   - Allow port 5000 (or your chosen port)
   - On cloud instances, check security groups

---

### Issue 12: SSL/TLS Errors

**Problem**: SSL certificate verification errors

**Cause**: Corporate proxy or network filtering

**Solution**:
```bash
# Not recommended for production, but for testing:
export AWS_CA_BUNDLE=/path/to/ca-bundle.crt

# Or disable SSL verification (testing only):
export BOTO_DISABLE_SSL_VERIFICATION=true
```

---

### Issue 13: Rate Limiting / Throttling

**Problem**: "Rate exceeded" or throttling errors

**Cause**: Too many API calls in short time

**Solution**:
- Reduce number of selected regions
- Increase monitoring interval (if using scripts)
- Add delays between API calls (in custom scripts)
- Request AWS service quota increase

---

### Issue 14: Empty Metrics / No Data Points

**Problem**: Metrics section shows "No data points"

**Causes**:

1. **CloudWatch monitoring not enabled**
   - EC2: Enable detailed monitoring
   - RDS: Enabled by default
   - Lambda: Enabled by default

2. **No recent activity**
   - Resource hasn't been used recently
   - Try different time period

3. **Wrong metric period**
   - Try 15 minutes or 1 hour instead of 5 minutes

**Solution**: Wait for some activity, or check CloudWatch console directly.

---

## Quick Diagnostic Commands

### Test AWS Access
```bash
# Get caller identity
aws sts get-caller-identity --profile monitor

# List regions
aws ec2 describe-regions --profile monitor

# Test EC2 access
aws ec2 describe-instances --region us-east-1 --profile monitor --max-items 1

# Test Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-02 \
  --granularity DAILY \
  --metrics UnblendedCost \
  --profile monitor
```

### Check Python and Dependencies
```bash
# Python version (need 3.8+)
python3 --version

# Check if dependencies installed
pip list | grep -E '(flask|boto3)'

# Reinstall if needed
pip install -r requirements.txt --upgrade
```

### Check Application Logs
```bash
# If running in terminal, logs appear in console

# If running as service/background:
tail -f /var/log/aws_monitor.log

# Check generated script logs:
tail -f aws_monitor.log  # In same directory as script
```

---

## Still Having Issues?

### Enable Debug Mode
```bash
python main.py --debug
```

This provides detailed logging for troubleshooting.

### Test Role Assumption
```bash
python main.py --role-arn arn:aws:iam::123456:role/MonitoringRole --debug
```

Check console output for specific errors.

### Test Generated Script
```bash
# Add debug logging to script
# Edit the generated aws_monitor_job.py:
# Change logging.basicConfig(level=logging.INFO)
# To:     logging.basicConfig(level=logging.DEBUG)

python3 aws_monitor_job.py
```

### Check Browser Console
- Open browser DevTools (F12)
- Check Console tab for JavaScript errors
- Check Network tab for API errors

---

## Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| NoCredentialsError | No AWS credentials | Configure profile 'monitor' |
| AccessDenied | Missing IAM permissions | Add required permissions |
| UnauthorizedOperation | No permission for action | Update IAM policy |
| RegionDisabledException | Region needs opt-in | Opt-in to region in AWS Console |
| InvalidParameterValue | Invalid input | Check filter values |
| ResourceNotFoundException | Resource doesn't exist | Verify resource ID/name |
| ThrottlingException | Too many API calls | Add delays, reduce frequency |

---

## Getting Help

1. **Check logs** for specific error messages
2. **Test with AWS CLI** to isolate issues
3. **Verify permissions** using IAM policy simulator
4. **Try without filters** to see if filters are the issue
5. **Test in different region** to rule out regional issues

---

## Success Checklist

✅ AWS profile 'monitor' configured  
✅ IAM permissions added  
✅ Python 3.8+ installed  
✅ Dependencies installed (flask, boto3)  
✅ Port 5000 available (or use --port)  
✅ Resources exist in selected regions  
✅ Filters match resource tags/names/IDs  
✅ CloudWatch monitoring enabled (for metrics)  
✅ Cost Explorer enabled (for costs)  

If all checked, application should work!
