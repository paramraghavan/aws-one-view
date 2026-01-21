# AWS APIs Quick Reference Cheat Sheet

## 🎯 The Big Picture

```
Your Computer                AWS Cloud
┌─────────────┐             ┌──────────────────┐
│  Browser    │  HTTP       │                  │
│             │────────────→│  Flask App       │
└─────────────┘             │  (main.py)       │
                            └────────┬─────────┘
                                     │ Boto3
                            ┌────────▼─────────┐
                            │  AWS Services    │
                            │  • EC2           │
                            │  • RDS           │
                            │  • S3            │
                            │  • CloudWatch    │
                            │  • Cost Explorer │
                            └──────────────────┘
```

---

## 📋 Common API Calls

### 1️⃣ Resource Discovery

| What You Want | Service | API Call | Code |
|---------------|---------|----------|------|
| All regions | EC2 | `describe_regions()` | `ec2.describe_regions()` |
| EC2 instances | EC2 | `describe_instances()` | `ec2.describe_instances()` |
| RDS databases | RDS | `describe_db_instances()` | `rds.describe_db_instances()` |
| S3 buckets | S3 | `list_buckets()` | `s3.list_buckets()` |
| Lambda functions | Lambda | `list_functions()` | `lambda_client.list_functions()` |
| EBS volumes | EC2 | `describe_volumes()` | `ec2.describe_volumes()` |

### 2️⃣ Performance Metrics

| Metric | Service | Namespace | Metric Name | Dimension |
|--------|---------|-----------|-------------|-----------|
| EC2 CPU | CloudWatch | `AWS/EC2` | `CPUUtilization` | `InstanceId` |
| RDS CPU | CloudWatch | `AWS/RDS` | `CPUUtilization` | `DBInstanceIdentifier` |
| RDS Connections | CloudWatch | `AWS/RDS` | `DatabaseConnections` | `DBInstanceIdentifier` |
| Lambda Invocations | CloudWatch | `AWS/Lambda` | `Invocations` | `FunctionName` |
| Lambda Duration | CloudWatch | `AWS/Lambda` | `Duration` | `FunctionName` |

### 3️⃣ Cost Analysis

| What You Want | API Call | Parameters |
|---------------|----------|------------|
| Daily costs | `get_cost_and_usage()` | `Granularity='DAILY'` |
| Monthly costs | `get_cost_and_usage()` | `Granularity='MONTHLY'` |
| By service | `get_cost_and_usage()` | `GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]` |
| By region | `get_cost_and_usage()` | `GroupBy=[{'Type': 'DIMENSION', 'Key': 'REGION'}]` |

---

## 🔑 Authentication

### Option 1: Environment Variables
```bash
export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
export AWS_DEFAULT_REGION="us-east-1"
```

### Option 2: AWS CLI Configuration
```bash
aws configure
# Enter credentials when prompted
```

### Option 3: Credentials File
```
~/.aws/credentials:
[default]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
```

---

## 📊 CloudWatch Metrics Explained

### Basic Pattern
```python
cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',           # Which service?
    MetricName='CPUUtilization',   # What metric?
    Dimensions=[                   # Which resource?
        {'Name': 'InstanceId', 'Value': 'i-12345'}
    ],
    StartTime=start,               # From when?
    EndTime=end,                   # Until when?
    Period=3600,                   # Group by how long? (seconds)
    Statistics=['Average']         # What calculation?
)
```

### Period Options
- `60` = 1 minute intervals
- `300` = 5 minute intervals
- `3600` = 1 hour intervals
- `86400` = 1 day intervals

### Statistics Options
- `Average` = Mean value
- `Maximum` = Peak value
- `Minimum` = Lowest value
- `Sum` = Total (for counts)
- `SampleCount` = Number of data points

---

## 💰 Cost Explorer Granularity

```python
# Daily breakdown
Granularity='DAILY'
# Returns: 30 data points for 30 days

# Monthly breakdown
Granularity='MONTHLY'
# Returns: 1 data point per month

# Hourly breakdown
Granularity='HOURLY'
# Returns: 720 data points for 30 days
```

---

## 🚀 Common Usage Patterns

### Pattern 1: Get CPU for Last 24 Hours
```python
from datetime import datetime, timedelta

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[{'Name': 'InstanceId', 'Value': 'i-12345'}],
    StartTime=datetime.utcnow() - timedelta(hours=24),
    EndTime=datetime.utcnow(),
    Period=3600,  # 1 hour buckets
    Statistics=['Average', 'Maximum']
)

# Process results
for datapoint in response['Datapoints']:
    print(f"{datapoint['Timestamp']}: {datapoint['Average']}% CPU")
```

### Pattern 2: Get Costs for Last 30 Days
```python
from datetime import date, timedelta

ce = boto3.client('ce', region_name='us-east-1')

end_date = date.today()
start_date = end_date - timedelta(days=30)

response = ce.get_cost_and_usage(
    TimePeriod={
        'Start': start_date.strftime('%Y-%m-%d'),
        'End': end_date.strftime('%Y-%m-%d')
    },
    Granularity='DAILY',
    Metrics=['UnblendedCost'],
    GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
)

# Process results
total = 0
for day in response['ResultsByTime']:
    for group in day['Groups']:
        service = group['Keys'][0]
        cost = float(group['Metrics']['UnblendedCost']['Amount'])
        total += cost
        print(f"{service}: ${cost:.2f}")

print(f"Total: ${total:.2f}")
```

### Pattern 3: Find All Running Instances
```python
ec2 = boto3.client('ec2', region_name='us-east-1')

response = ec2.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
)

for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        print(f"Instance: {instance['InstanceId']}")
        print(f"Type: {instance['InstanceType']}")
        print(f"State: {instance['State']['Name']}")
        print("---")
```

### Pattern 4: Check If CPU Is High
```python
# Get metrics
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[{'Name': 'InstanceId', 'Value': 'i-12345'}],
    StartTime=datetime.utcnow() - timedelta(hours=24),
    EndTime=datetime.utcnow(),
    Period=3600,
    Statistics=['Average', 'Maximum']
)

# Analyze
if response['Datapoints']:
    avg_cpu = sum(d['Average'] for d in response['Datapoints']) / len(response['Datapoints'])
    max_cpu = max(d['Maximum'] for d in response['Datapoints'])
    
    if max_cpu > 80:
        print(f"⚠️  HIGH CPU: {max_cpu}%")
    elif avg_cpu < 10:
        print(f"💡 UNDERUTILIZED: {avg_cpu}%")
    else:
        print(f"✅ OK: {avg_cpu}%")
```

---

## 🎓 Key Concepts

### Regional vs Global Services

**Regional** (must specify region):
- EC2
- RDS
- Lambda
- CloudWatch

**Global** (use us-east-1):
- S3
- IAM
- Cost Explorer

### API Response Structure

Most AWS APIs return this structure:
```python
{
    "ResourceName": [
        {
            "Property1": "value",
            "Property2": "value",
            "Nested": {
                "SubProperty": "value"
            }
        }
    ],
    "ResponseMetadata": {
        "RequestId": "...",
        "HTTPStatusCode": 200
    }
}
```

### Error Handling

```python
try:
    response = ec2.describe_instances()
except ClientError as e:
    error_code = e.response['Error']['Code']
    
    if error_code == 'UnauthorizedOperation':
        print("No permission!")
    elif error_code == 'InvalidInstanceID.NotFound':
        print("Instance doesn't exist!")
    else:
        print(f"Error: {error_code}")
```

---

## 💡 Pro Tips

### 1. Use Filters
```python
# Instead of getting all and filtering locally
response = ec2.describe_instances()  # Gets everything

# Use server-side filters
response = ec2.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']},
        {'Name': 'instance-type', 'Values': ['t2.micro', 't3.micro']}
    ]
)
```

### 2. Handle Pagination
```python
# For resources with 100+ items
paginator = ec2.get_paginator('describe_instances')

for page in paginator.paginate():
    for reservation in page['Reservations']:
        for instance in reservation['Instances']:
            process(instance)
```

### 3. Cache Results
```python
# Don't call AWS repeatedly
resources = ec2.describe_instances()  # Call once
# Store in memory or database
# Refresh every 5 minutes
```

### 4. Batch Requests
```python
# Instead of one call per resource
for instance_id in instance_ids:
    get_metrics(instance_id)  # 100 API calls!

# Get multiple at once
get_metrics(instance_ids)  # 1 API call!
```

---

## 📈 Cost Awareness

| API Call | Cost | Free Tier |
|----------|------|-----------|
| `describe_instances()` | FREE | ✅ Always free |
| `describe_regions()` | FREE | ✅ Always free |
| `list_buckets()` | FREE | ✅ Always free |
| `get_metric_statistics()` | FREE | ✅ First 1M requests/month |
| `get_cost_and_usage()` | $0.01 | ✅ First request/day free |

**Bottom line:** Normal monitoring is essentially FREE!

---

## 🔍 Debugging

### Check What's Being Sent
```python
import logging

# Enable debug logging
boto3.set_stream_logger('boto3.resources', logging.DEBUG)

# Now you'll see all API calls
ec2.describe_instances()
# Shows: Making request to https://ec2.us-east-1.amazonaws.com/...
```

### Validate Credentials
```python
sts = boto3.client('sts')
identity = sts.get_caller_identity()

print(f"Account: {identity['Account']}")
print(f"User ARN: {identity['Arn']}")
# If this works, credentials are valid
```

---

## 📚 Resources

- **Boto3 Docs**: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- **AWS API Reference**: https://docs.aws.amazon.com/
- **CloudWatch Metrics**: https://docs.aws.amazon.com/cloudwatch/
- **Cost Explorer**: https://docs.aws.amazon.com/cost-management/

---

## 🎯 Quick Test

Test your understanding:

```python
# 1. Connect to EC2
ec2 = boto3.client('ec2', region_name='us-east-1')

# 2. Get instances
instances = ec2.describe_instances()

# 3. Connect to CloudWatch
cw = boto3.client('cloudwatch', region_name='us-east-1')

# 4. Get CPU for an instance
cpu = cw.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[{'Name': 'InstanceId', 'Value': 'i-12345'}],
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow(),
    Period=300,
    Statistics=['Average']
)

# 5. Print results
for dp in cpu['Datapoints']:
    print(f"{dp['Timestamp']}: {dp['Average']}%")
```

That's all you need to know! 🎉
