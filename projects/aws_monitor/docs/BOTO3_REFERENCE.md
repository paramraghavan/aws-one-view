# Boto3 API Reference - AWS Monitor

## Overview

This document catalogs all boto3 API calls used in AWS Monitor, including parameters, return values, and IAM permissions required.

---

## Table of Contents

1. [EC2 APIs](#ec2-apis)
2. [RDS APIs](#rds-apis)
3. [S3 APIs](#s3-apis)
4. [Lambda APIs](#lambda-apis)
5. [EKS APIs](#eks-apis)
6. [EMR APIs](#emr-apis)
7. [CloudWatch APIs](#cloudwatch-apis)
8. [Cost Explorer APIs](#cost-explorer-apis)
9. [STS APIs (IAM Role Assumption)](#sts-apis)
10. [Required IAM Permissions](#required-iam-permissions)

---

## EC2 APIs

### 1. describe_regions

**Purpose**: Get list of all AWS regions

**Code**:
```python
ec2 = boto3.client('ec2', region_name='us-east-1')
response = ec2.describe_regions()
regions = [r['RegionName'] for r in response['Regions']]
```

**Returns**:
```python
{
    'Regions': [
        {
            'RegionName': 'us-east-1',
            'Endpoint': 'ec2.us-east-1.amazonaws.com',
            'OptInStatus': 'opt-in-not-required'
        },
        # ...more regions
    ]
}
```

**IAM Permission**: `ec2:DescribeRegions`

---

### 2. describe_instances

**Purpose**: Get EC2 instance details

**Code**:
```python
ec2 = boto3.client('ec2', region_name=region)
response = ec2.describe_instances(
    Filters=[
        {'Name': 'tag:Environment', 'Values': ['production']},
        {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
    ]
)
```

**Returns**:
```python
{
    'Reservations': [
        {
            'Instances': [
                {
                    'InstanceId': 'i-1234567890abcdef0',
                    'InstanceType': 't2.micro',
                    'State': {'Name': 'running'},
                    'PrivateIpAddress': '10.0.1.5',
                    'PublicIpAddress': '54.1.2.3',
                    'LaunchTime': datetime(2024, 1, 1),
                    'Tags': [
                        {'Key': 'Name', 'Value': 'web-server'},
                        {'Key': 'Environment', 'Value': 'production'}
                    ]
                }
            ]
        }
    ]
}
```

**IAM Permission**: `ec2:DescribeInstances`

**Filters Used**:
- `tag:KEY` - Filter by tag
- `instance-state-name` - Filter by state
- `instance-id` - Filter by instance ID

---

### 3. describe_volumes

**Purpose**: Get EBS volume details

**Code**:
```python
ec2 = boto3.client('ec2', region_name=region)
response = ec2.describe_volumes()
```

**Returns**:
```python
{
    'Volumes': [
        {
            'VolumeId': 'vol-1234567890abcdef0',
            'Size': 100,  # GB
            'VolumeType': 'gp3',
            'State': 'in-use',
            'AvailabilityZone': 'us-east-1a',
            'Encrypted': True,
            'Attachments': [
                {
                    'InstanceId': 'i-1234567890abcdef0',
                    'State': 'attached',
                    'Device': '/dev/sda1'
                }
            ],
            'Tags': [
                {'Key': 'Name', 'Value': 'root-volume'}
            ]
        }
    ]
}
```

**IAM Permission**: `ec2:DescribeVolumes`

---

## RDS APIs

### describe_db_instances

**Purpose**: Get RDS database instance details

**Code**:
```python
rds = boto3.client('rds', region_name=region)
response = rds.describe_db_instances()
```

**Returns**:
```python
{
    'DBInstances': [
        {
            'DBInstanceIdentifier': 'production-db',
            'DBInstanceClass': 'db.t3.micro',
            'Engine': 'mysql',
            'EngineVersion': '8.0.28',
            'DBInstanceStatus': 'available',
            'Endpoint': {
                'Address': 'production-db.abc123.us-east-1.rds.amazonaws.com',
                'Port': 3306
            },
            'AllocatedStorage': 100,
            'StorageType': 'gp2',
            'MultiAZ': False,
            'PubliclyAccessible': False,
            'InstanceCreateTime': datetime(2024, 1, 1),
            'TagList': [
                {'Key': 'Environment', 'Value': 'production'}
            ]
        }
    ]
}
```

**IAM Permission**: `rds:DescribeDBInstances`

---

## S3 APIs

### 1. list_buckets

**Purpose**: Get list of all S3 buckets

**Code**:
```python
s3 = boto3.client('s3')
response = s3.list_buckets()
```

**Returns**:
```python
{
    'Buckets': [
        {
            'Name': 'my-data-bucket',
            'CreationDate': datetime(2024, 1, 1)
        },
        # ...more buckets
    ],
    'Owner': {
        'DisplayName': 'account-name',
        'ID': '1234567890abcdef'
    }
}
```

**IAM Permission**: `s3:ListAllMyBuckets`

---

### 2. get_bucket_location

**Purpose**: Get bucket region

**Code**:
```python
s3 = boto3.client('s3')
response = s3.get_bucket_location(Bucket='my-bucket')
region = response['LocationConstraint'] or 'us-east-1'
```

**Returns**:
```python
{
    'LocationConstraint': 'us-west-2'  # None for us-east-1
}
```

**IAM Permission**: `s3:GetBucketLocation`

---

### 3. get_bucket_tagging

**Purpose**: Get bucket tags

**Code**:
```python
s3 = boto3.client('s3')
response = s3.get_bucket_tagging(Bucket='my-bucket')
tags = {t['Key']: t['Value'] for t in response['TagSet']}
```

**Returns**:
```python
{
    'TagSet': [
        {'Key': 'Environment', 'Value': 'production'},
        {'Key': 'Owner', 'Value': 'data-team'}
    ]
}
```

**IAM Permission**: `s3:GetBucketTagging`

**Note**: Raises `ClientError` if bucket has no tags

---

## Lambda APIs

### 1. list_functions

**Purpose**: Get list of Lambda functions

**Code**:
```python
lambda_client = boto3.client('lambda', region_name=region)
response = lambda_client.list_functions()
```

**Returns**:
```python
{
    'Functions': [
        {
            'FunctionName': 'my-function',
            'FunctionArn': 'arn:aws:lambda:us-east-1:123456789012:function:my-function',
            'Runtime': 'python3.9',
            'MemorySize': 128,
            'Timeout': 30,
            'LastModified': '2024-01-01T12:00:00.000+0000',
            'CodeSize': 1234567,
            'Handler': 'lambda_function.lambda_handler'
        }
    ]
}
```

**IAM Permission**: `lambda:ListFunctions`

---

### 2. list_tags

**Purpose**: Get Lambda function tags

**Code**:
```python
lambda_client = boto3.client('lambda', region_name=region)
response = lambda_client.list_tags(
    Resource='arn:aws:lambda:us-east-1:123456789012:function:my-function'
)
tags = response['Tags']
```

**Returns**:
```python
{
    'Tags': {
        'Environment': 'production',
        'Team': 'backend'
    }
}
```

**IAM Permission**: `lambda:ListTags`

---

## EKS APIs

### 1. list_clusters

**Purpose**: Get list of EKS clusters

**Code**:
```python
eks = boto3.client('eks', region_name=region)
response = eks.list_clusters()
cluster_names = response['clusters']
```

**Returns**:
```python
{
    'clusters': [
        'production-cluster',
        'staging-cluster'
    ]
}
```

**IAM Permission**: `eks:ListClusters`

---

### 2. describe_cluster

**Purpose**: Get EKS cluster details

**Code**:
```python
eks = boto3.client('eks', region_name=region)
response = eks.describe_cluster(name='production-cluster')
cluster = response['cluster']
```

**Returns**:
```python
{
    'cluster': {
        'name': 'production-cluster',
        'arn': 'arn:aws:eks:us-east-1:123456789012:cluster/production-cluster',
        'createdAt': datetime(2024, 1, 1),
        'version': '1.27',
        'endpoint': 'https://ABC123.gr7.us-east-1.eks.amazonaws.com',
        'status': 'ACTIVE',
        'platformVersion': 'eks.3',
        'tags': {
            'Environment': 'production'
        }
    }
}
```

**IAM Permission**: `eks:DescribeCluster`

---

## EMR APIs

### 1. list_clusters

**Purpose**: Get list of EMR clusters

**Code**:
```python
emr = boto3.client('emr', region_name=region)
response = emr.list_clusters(
    ClusterStates=['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING']
)
```

**Returns**:
```python
{
    'Clusters': [
        {
            'Id': 'j-1234567890ABC',
            'Name': 'analytics-cluster',
            'Status': {
                'State': 'RUNNING',
                'Timeline': {
                    'CreationDateTime': datetime(2024, 1, 1)
                }
            },
            'NormalizedInstanceHours': 100
        }
    ]
}
```

**IAM Permission**: `elasticmapreduce:ListClusters`

---

### 2. describe_cluster

**Purpose**: Get EMR cluster details

**Code**:
```python
emr = boto3.client('emr', region_name=region)
response = emr.describe_cluster(ClusterId='j-1234567890ABC')
cluster = response['Cluster']
```

**Returns**:
```python
{
    'Cluster': {
        'Id': 'j-1234567890ABC',
        'Name': 'analytics-cluster',
        'Status': {
            'State': 'RUNNING',
            'Timeline': {
                'CreationDateTime': datetime(2024, 1, 1),
                'ReadyDateTime': datetime(2024, 1, 1)
            }
        },
        'ReleaseLabel': 'emr-6.10.0',
        'Tags': [
            {'Key': 'Environment', 'Value': 'production'}
        ]
    }
}
```

**IAM Permission**: `elasticmapreduce:DescribeCluster`

---

## CloudWatch APIs

### get_metric_statistics

**Purpose**: Get CloudWatch metrics for resources

**Code**:
```python
cloudwatch = boto3.client('cloudwatch', region_name=region)
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[
        {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}
    ],
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow(),
    Period=300,  # 5 minutes
    Statistics=['Average', 'Maximum', 'Minimum']
)
```

**Returns**:
```python
{
    'Datapoints': [
        {
            'Timestamp': datetime(2024, 1, 1, 12, 0, 0),
            'Average': 45.2,
            'Maximum': 78.5,
            'Minimum': 12.3,
            'Unit': 'Percent'
        },
        # ...more datapoints
    ],
    'Label': 'CPUUtilization'
}
```

**IAM Permission**: `cloudwatch:GetMetricStatistics`

---

### Available Metrics by Service

#### EC2 Metrics
- `CPUUtilization` - Percentage
- `NetworkIn` - Bytes
- `NetworkOut` - Bytes
- `DiskReadBytes` - Bytes
- `DiskWriteBytes` - Bytes

**Note**: Memory metrics (MemoryUtilization, MemoryUsed) are **NOT available by default**. They require the CloudWatch agent to be installed on the instance. See [Memory Metrics Setup](#memory-metrics-setup).

#### RDS Metrics
- `CPUUtilization` - Percentage
- `DatabaseConnections` - Count
- `FreeStorageSpace` - Bytes
- `ReadLatency` - Seconds
- `WriteLatency` - Seconds
- `FreeableMemory` - Bytes (this IS available for RDS!)

#### Lambda Metrics
- `Invocations` - Count
- `Errors` - Count
- `Duration` - Milliseconds
- `Throttles` - Count

#### EKS Metrics
- `cluster_failed_node_count` - Count
- `cluster_node_count` - Count
- `namespace_number_of_running_pods` - Count

---

## Memory Metrics Setup

### ⚠️ Important: EC2 Memory Metrics

**EC2 does NOT provide memory metrics by default.** To get memory metrics:

1. **Install CloudWatch Agent** on EC2 instances
2. **Configure the agent** to collect memory metrics
3. **Metrics will appear** in custom namespace

**Installation**:
```bash
# On EC2 instance
wget https://s3.amazonaws.com/amazoncloudwatch-agent/amazon_linux/amd64/latest/amazon-cloudwatch-agent.rpm
sudo rpm -i amazon-cloudwatch-agent.rpm

# Configure
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-config-wizard

# Start
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
    -a fetch-config \
    -m ec2 \
    -s \
    -c file:/opt/aws/amazon-cloudwatch-agent/bin/config.json
```

**Available Memory Metrics (with agent)**:
- `mem_used_percent` - Percentage
- `mem_used` - Bytes
- `mem_available` - Bytes
- `mem_total` - Bytes

**Namespace**: `CWAgent` (custom namespace)

**Code to get memory metrics**:
```python
cloudwatch = boto3.client('cloudwatch', region_name=region)
response = cloudwatch.get_metric_statistics(
    Namespace='CWAgent',  # Custom namespace!
    MetricName='mem_used_percent',
    Dimensions=[
        {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}
    ],
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow(),
    Period=300,
    Statistics=['Average', 'Maximum']
)
```

**Why RDS has memory but EC2 doesn't**:
- RDS is a managed service - AWS controls the instances
- EC2 instances are customer-managed - AWS doesn't access them
- EC2 requires explicit agent installation for memory metrics

---

## Cost Explorer APIs

### get_cost_and_usage

**Purpose**: Get AWS costs by service and region

**Code**:
```python
ce = boto3.client('ce', region_name='us-east-1')  # Always us-east-1
response = ce.get_cost_and_usage(
    TimePeriod={
        'Start': '2024-01-01',
        'End': '2024-01-31'
    },
    Granularity='MONTHLY',
    Metrics=['UnblendedCost'],
    GroupBy=[
        {'Type': 'DIMENSION', 'Key': 'SERVICE'},
        {'Type': 'DIMENSION', 'Key': 'REGION'}
    ]
)
```

**Returns**:
```python
{
    'ResultsByTime': [
        {
            'TimePeriod': {
                'Start': '2024-01-01',
                'End': '2024-01-31'
            },
            'Total': {
                'UnblendedCost': {
                    'Amount': '1234.56',
                    'Unit': 'USD'
                }
            },
            'Groups': [
                {
                    'Keys': ['Amazon Elastic Compute Cloud', 'us-east-1'],
                    'Metrics': {
                        'UnblendedCost': {
                            'Amount': '500.00',
                            'Unit': 'USD'
                        }
                    }
                }
            ]
        }
    ]
}
```

**IAM Permission**: `ce:GetCostAndUsage`

**Note**: Cost Explorer API is only available in `us-east-1` region

---

## STS APIs

### assume_role

**Purpose**: Assume IAM role for cross-account access

**Code**:
```python
sts = boto3.client('sts')
response = sts.assume_role(
    RoleArn='arn:aws:iam::123456789012:role/MonitoringRole',
    RoleSessionName='aws-monitor-session',
    DurationSeconds=3600
)

credentials = response['Credentials']

# Create session with assumed role
session = boto3.Session(
    aws_access_key_id=credentials['AccessKeyId'],
    aws_secret_access_key=credentials['SecretAccessKey'],
    aws_session_token=credentials['SessionToken']
)
```

**Returns**:
```python
{
    'Credentials': {
        'AccessKeyId': 'ASIA...',
        'SecretAccessKey': '...',
        'SessionToken': '...',
        'Expiration': datetime(2024, 1, 1, 13, 0, 0)
    },
    'AssumedRoleUser': {
        'AssumedRoleId': 'AROA...:aws-monitor-session',
        'Arn': 'arn:aws:sts::123456789012:assumed-role/MonitoringRole/aws-monitor-session'
    }
}
```

**IAM Permission**: `sts:AssumeRole`

---

## Required IAM Permissions

### Minimum Policy for AWS Monitor

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeRegions",
                "ec2:DescribeInstances",
                "ec2:DescribeVolumes",
                "rds:DescribeDBInstances",
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "s3:GetBucketTagging",
                "lambda:ListFunctions",
                "lambda:ListTags",
                "eks:ListClusters",
                "eks:DescribeCluster",
                "elasticmapreduce:ListClusters",
                "elasticmapreduce:DescribeCluster",
                "cloudwatch:GetMetricStatistics",
                "ce:GetCostAndUsage"
            ],
            "Resource": "*"
        }
    ]
}
```

### For IAM Role Assumption

**Trust Policy** (on the role to be assumed):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::YOUR_ACCOUNT:user/monitor-user"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```

**User Policy** (on the user assuming the role):
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "sts:AssumeRole",
            "Resource": "arn:aws:iam::TARGET_ACCOUNT:role/MonitoringRole"
        }
    ]
}
```

---

## Error Handling

### Common Exceptions

```python
from botocore.exceptions import ClientError, NoCredentialsError

try:
    response = ec2.describe_instances()
except NoCredentialsError:
    # No AWS credentials found
    print("AWS credentials not configured")
except ClientError as e:
    error_code = e.response['Error']['Code']
    
    if error_code == 'UnauthorizedOperation':
        # IAM permission denied
        print("Permission denied")
    elif error_code == 'InvalidInstanceID.NotFound':
        # Resource not found
        print("Instance not found")
    elif error_code == 'RequestLimitExceeded':
        # API rate limit exceeded
        print("Too many requests")
    else:
        print(f"AWS error: {error_code}")
```

### Common Error Codes

- `UnauthorizedOperation` - IAM permission denied
- `InvalidInstanceID.NotFound` - EC2 instance not found
- `DBInstanceNotFound` - RDS instance not found
- `NoSuchBucket` - S3 bucket not found
- `NoSuchTagSet` - S3 bucket has no tags
- `ResourceNotFoundException` - Lambda function not found
- `RequestLimitExceeded` - API rate limit exceeded
- `AccessDenied` - General access denied

---

## Rate Limits

### API Throttling

AWS APIs have rate limits. Common limits:

| API | Limit | Burst |
|-----|-------|-------|
| `describe_instances` | 100 requests/second | 200 |
| `describe_db_instances` | 100 requests/second | 200 |
| `list_buckets` | 100 requests/second | 200 |
| `get_metric_statistics` | 400 requests/second | 1000 |
| `get_cost_and_usage` | 10 requests/second | 20 |

**Best Practices**:
- Use pagination for large result sets
- Implement exponential backoff on throttling errors
- Cache results when appropriate
- Use filters to reduce response sizes

---

## Code Examples

### Complete Discovery Example

```python
import boto3
from datetime import datetime, timedelta

# Create session
session = boto3.Session(profile_name='monitor')

# Discover EC2 instances
ec2 = session.client('ec2', region_name='us-east-1')
response = ec2.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
)

for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        instance_id = instance['InstanceId']
        instance_type = instance['InstanceType']
        state = instance['State']['Name']
        
        # Get metrics
        cloudwatch = session.client('cloudwatch', region_name='us-east-1')
        metrics = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=datetime.utcnow() - timedelta(hours=1),
            EndTime=datetime.utcnow(),
            Period=300,
            Statistics=['Average']
        )
        
        if metrics['Datapoints']:
            avg_cpu = sum(d['Average'] for d in metrics['Datapoints']) / len(metrics['Datapoints'])
            print(f"{instance_id} ({instance_type}): {avg_cpu:.1f}% CPU")
```

---

## Summary

### APIs Used in AWS Monitor

| Service | APIs | Count |
|---------|------|-------|
| **EC2** | describe_regions, describe_instances, describe_volumes | 3 |
| **RDS** | describe_db_instances | 1 |
| **S3** | list_buckets, get_bucket_location, get_bucket_tagging | 3 |
| **Lambda** | list_functions, list_tags | 2 |
| **EKS** | list_clusters, describe_cluster | 2 |
| **EMR** | list_clusters, describe_cluster | 2 |
| **CloudWatch** | get_metric_statistics | 1 |
| **Cost Explorer** | get_cost_and_usage | 1 |
| **STS** | assume_role | 1 |
| **Total** | | **16 APIs** |

### Key Takeaways

1. **Memory Metrics**: EC2 memory requires CloudWatch agent; RDS has it built-in
2. **Cost Explorer**: Always use `us-east-1` region
3. **S3 Tagging**: Handle `NoSuchTagSet` exception
4. **IAM Permissions**: Use least-privilege principle
5. **Error Handling**: Always catch `ClientError` and `NoCredentialsError`
6. **Rate Limits**: Implement backoff for high-volume operations

---

## Additional Resources

- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS Service Quotas](https://docs.aws.amazon.com/general/latest/gr/aws_service_limits.html)
- [CloudWatch Agent Setup](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
