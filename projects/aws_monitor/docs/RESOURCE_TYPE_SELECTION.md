# Resource Type Selection Feature

## Overview

You can now select which resource types to discover, making discovery faster and more focused.

## Why This Feature?

### Benefits
- ⚡ **Faster Discovery**: Only scan for resources you need
- 💰 **Fewer API Calls**: Save on AWS API rate limits
- 🎯 **Focused Results**: See only relevant resources
- 🔒 **Granular Permissions**: Can work with limited IAM permissions

### Use Cases

**Example 1: Only Need EC2 and RDS**
- Uncheck S3, Lambda, EBS, EKS, EMR
- Discovery completes in ~5 seconds instead of ~30 seconds
- Only 2 API calls per region instead of 7

**Example 2: Limited IAM Permissions**
- User only has EC2 and S3 permissions
- Disable RDS, Lambda, EBS, EKS, EMR to avoid permission errors
- Clean results without error messages

**Example 3: Quick EC2 Check**
- Only check EC2
- Instantly see all EC2 instances
- No waiting for other resource types

## How to Use

### In the Web UI

#### Step 1: Select Regions
```
☑ us-east-1
☑ us-west-2
```

#### Step 2: Select Resource Types
```
☑ EC2 Instances
☑ RDS Databases
☐ S3 Buckets
☐ Lambda Functions
☐ EBS Volumes
☐ EKS Clusters (Kubernetes)
☐ EMR Clusters
```

#### Quick Selection Buttons
- **Select All**: Check all resource types
- **Deselect All**: Uncheck all resource types
- **Common Only**: Select only EC2, RDS, and S3 (most commonly used)

#### Step 3: Click "Discover Resources"

Results will only include selected resource types.

---

### In Generated Scripts

When generating a monitoring script, resource types you select will be included in the script:

```python
# In generated script
RESOURCE_TYPES = ['ec2', 'rds']  # Only selected types

# Discovery only runs for these types
for resource_type in RESOURCE_TYPES:
    if resource_type == 'ec2':
        discover_ec2()
    elif resource_type == 'rds':
        discover_rds()
```

---

### Via API

You can also specify resource types in API calls:

```bash
curl -X POST http://localhost:5000/api/discover \
  -H "Content-Type: application/json" \
  -d '{
    "regions": ["us-east-1"],
    "resource_types": ["ec2", "rds"],
    "filters": {}
  }'
```

**Available Resource Types**:
- `ec2` - EC2 Instances
- `rds` - RDS Databases
- `s3` - S3 Buckets
- `lambda` - Lambda Functions
- `ebs` - EBS Volumes
- `eks` - EKS Clusters (Kubernetes)
- `emr` - EMR Clusters

**Default**: If `resource_types` is not provided, all types are discovered.

---

## Performance Comparison

### Discovery Time Comparison

| Resource Types Selected | API Calls | Time (est.) |
|------------------------|-----------|-------------|
| All (7 types) | 7 per region | ~30 seconds |
| EC2, RDS, S3 (3 types) | 3 per region | ~12 seconds |
| EC2 only (1 type) | 1 per region | ~5 seconds |

**Example**: 2 regions, EC2 only
- Before: 14 API calls, 60 seconds
- After: 2 API calls, 10 seconds
- **Improvement: 83% faster**

---

## Common Scenarios

### Scenario 1: Quick EC2 Status Check

**Goal**: Quickly see all EC2 instances

**Setup**:
1. Select regions
2. **Only check**: EC2 Instances
3. Click Discover

**Result**: See all EC2 instances in ~5 seconds

---

### Scenario 2: Database Monitoring

**Goal**: Monitor only databases

**Setup**:
1. Select regions
2. **Only check**: RDS Databases
3. Click Discover
4. Get metrics for databases

**Result**: Focused database monitoring without noise

---

### Scenario 3: Kubernetes Clusters

**Goal**: Check EKS cluster health

**Setup**:
1. Select regions
2. **Only check**: EKS Clusters (Kubernetes)
3. Click Discover

**Result**: See all EKS clusters with node groups

---

### Scenario 4: Limited Permissions

**Goal**: Monitor with restricted IAM permissions

**Problem**: User only has EC2 and S3 permissions

**Setup**:
1. Select regions
2. **Only check**: EC2 Instances, S3 Buckets
3. Uncheck RDS, Lambda, EBS, EKS, EMR
4. Click Discover

**Result**: No permission errors, clean results

---

## IAM Permissions

You only need permissions for resource types you select:

### Minimal EC2-Only Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeRegions",
      "ec2:DescribeInstances"
    ],
    "Resource": "*"
  }]
}
```

### EC2 + RDS Only Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "ec2:DescribeRegions",
      "ec2:DescribeInstances",
      "rds:DescribeDBInstances",
      "rds:ListTagsForResource"
    ],
    "Resource": "*"
  }]
}
```

**Tip**: Only request permissions for resource types you'll actually monitor!

---

## Troubleshooting

### Issue: "Please select at least one resource type"

**Problem**: All resource types are unchecked

**Solution**: Check at least one resource type before clicking "Discover Resources"

---

### Issue: Some resource types show no results

**Possible Causes**:
1. **No resources of that type exist** in selected regions
   - Expected behavior if you don't have those resources

2. **Missing IAM permissions** for that resource type
   - Check CloudTrail or application logs for AccessDenied errors
   - Add required permissions or uncheck that resource type

3. **Filters too restrictive**
   - Try discovering without filters first
   - Then add filters if needed

---

### Issue: Discovery still slow

**Solutions**:
1. **Select fewer resource types**: Uncheck types you don't need
2. **Select fewer regions**: Focus on primary regions
3. **Use filters**: Filter by tags/names to reduce results

---

## Best Practices

### 1. Start Small
```
First time:
- Select 1 region
- Select 1-2 resource types
- No filters

Then expand as needed.
```

### 2. Use Quick Selection Buttons
```
For most users: Click "Common Only"
- Selects EC2, RDS, S3
- Covers 80% of use cases
```

### 3. Match Your IAM Permissions
```
If you have limited permissions:
- Only check resource types you have access to
- Avoids permission errors
```

### 4. Focus on Your Needs
```
Compute monitoring: EC2, Lambda, EKS
Database monitoring: RDS only
Storage monitoring: S3, EBS only
```

### 5. Generate Focused Scripts
```
When generating monitoring scripts:
- Only select resource types you'll monitor regularly
- Smaller scripts run faster
- Easier to maintain
```

---

## Summary

**Key Features**:
- ✅ Select specific resource types to discover
- ✅ Quick selection buttons (All, None, Common)
- ✅ Faster discovery with fewer API calls
- ✅ Works with limited IAM permissions
- ✅ Included in generated scripts

**Default Behavior**:
- All resource types selected by default
- Backward compatible - works like before if you don't change selections

**When to Use**:
- ✅ You only need specific resource types
- ✅ You want faster discovery
- ✅ You have limited IAM permissions
- ✅ You want focused results

**When Not Needed**:
- If you want to discover everything (keep all checked)
- If discovery time doesn't matter
- If you have full IAM permissions

---

## Example Workflow

### Quick Start: EC2 Only
1. Open http://localhost:5000
2. **Step 1**: Select regions (us-east-1, us-west-2)
3. **Step 2**: Click "Deselect All", then check only "EC2 Instances"
4. **Step 3**: Skip filters (optional)
5. **Step 4**: Click "🔍 Discover Resources"
6. **Result**: See all EC2 instances in ~10 seconds

### Full Discovery: Everything
1. Open http://localhost:5000
2. **Step 1**: Select regions
3. **Step 2**: Leave all resource types checked (default)
4. **Step 3**: Add filters if needed
5. **Step 4**: Click "🔍 Discover Resources"
6. **Result**: See all resources in ~30 seconds

---

## API Reference

### Request Format
```json
{
  "regions": ["us-east-1", "us-west-2"],
  "resource_types": ["ec2", "rds"],  // Optional
  "filters": {
    "tags": {"Environment": "production"},
    "names": ["web-server"],
    "ids": ["i-1234567"]
  }
}
```

### Response Format
```json
{
  "timestamp": "2024-01-28T12:00:00Z",
  "regions": {
    "us-east-1": {
      "ec2": [...],
      "rds": [...]
      // Only requested types included
    }
  },
  "summary": {
    "ec2": 5,
    "rds": 3
    // Only requested types in summary
  }
}
```

---

## Conclusion

Resource type selection gives you:
- **Control** over what to discover
- **Speed** with focused discovery
- **Flexibility** with limited permissions
- **Clarity** with targeted results

Use it to make monitoring faster and more efficient!
