# Boto3 API Reference - Complete Guide

This document explains every boto3 API call used in the AWS Monitor application.

## Table of Contents
1. [Session and Client Setup](#session-and-client-setup)
2. [EC2 APIs](#ec2-apis)
3. [RDS APIs](#rds-apis)
4. [S3 APIs](#s3-apis)
5. [Lambda APIs](#lambda-apis)
6. [EKS (Kubernetes) APIs](#eks-kubernetes-apis)
7. [EMR APIs](#emr-apis)
8. [CloudWatch APIs](#cloudwatch-apis)
9. [Cost Explorer APIs](#cost-explorer-apis)
10. [IAM APIs](#iam-apis)

---

## Session and Client Setup

### boto3.Session()
```python
session = boto3.Session(profile_name='monitor', region_name='us-east-1')
```
**Purpose**: Create a session with specific AWS profile and region  
**Parameters**:
- `profile_name`: AWS CLI profile name (we use 'monitor')
- `region_name`: AWS region (e.g., 'us-east-1')

**Returns**: Session object used to create service clients  
**AWS Profile**: The 'monitor' profile must be configured in `~/.aws/credentials`

### session.client()
```python
ec2 = session.client('ec2')
```
**Purpose**: Create a low-level service client  
**Parameters**:
- Service name (e.g., 'ec2', 'rds', 's3', 'cloudwatch')

**Returns**: Service client object  
**Note**: Clients provide access to AWS service APIs

### session.get_available_regions()
```python
regions = session.get_available_regions('ec2')
```
**Purpose**: Get list of all AWS regions for a service  
**Parameters**:
- Service name

**Returns**: List of region names (e.g., ['us-east-1', 'us-west-2', ...])

---

## EC2 APIs

### describe_regions()
```python
response = ec2.describe_regions()
```
**Purpose**: List all available AWS regions  
**Parameters**: None (optional: Filters, MaxResults)  
**Returns**:
```python
{
    'Regions': [
        {'RegionName': 'us-east-1', 'Endpoint': '...'},
        {'RegionName': 'us-west-2', 'Endpoint': '...'}
    ]
}
```
**Use Case**: Dynamically load all regions in UI

### describe_instances()
```python
response = ec2.describe_instances(
    Filters=[
        {'Name': 'tag:Environment', 'Values': ['production']},
        {'Name': 'instance-id', 'Values': ['i-1234567']}
    ]
)
```
**Purpose**: Describe EC2 instances with optional filters  
**Parameters**:
- `Filters`: List of filter dicts (optional)
  - Filter by tags: `{'Name': 'tag:KEY', 'Values': ['VALUE']}`
  - Filter by instance ID: `{'Name': 'instance-id', 'Values': [...]}`
  - Filter by state: `{'Name': 'instance-state-name', 'Values': ['running']}`

**Returns**:
```python
{
    'Reservations': [
        {
            'Instances': [
                {
                    'InstanceId': 'i-1234567',
                    'InstanceType': 't2.micro',
                    'State': {'Name': 'running'},
                    'PrivateIpAddress': '10.0.0.5',
                    'PublicIpAddress': '54.1.2.3',
                    'Placement': {'AvailabilityZone': 'us-east-1a'},
                    'LaunchTime': datetime(...),
                    'Tags': [{'Key': 'Name', 'Value': 'web-server'}],
                    'Monitoring': {'State': 'disabled'},
                    'VpcId': 'vpc-123'
                }
            ]
        }
    ]
}
```
**Use Case**: Discover all EC2 instances, optionally filtered by name, tag, or ID

### describe_volumes()
```python
response = ec2.describe_volumes(
    Filters=[
        {'Name': 'tag:Name', 'Values': ['data-volume']},
        {'Name': 'volume-id', 'Values': ['vol-1234567']}
    ]
)
```
**Purpose**: Describe EBS volumes  
**Parameters**:
- `Filters`: Optional filters (same format as describe_instances)

**Returns**:
```python
{
    'Volumes': [
        {
            'VolumeId': 'vol-1234567',
            'Size': 100,  # GB
            'VolumeType': 'gp3',
            'State': 'in-use',
            'AvailabilityZone': 'us-east-1a',
            'Encrypted': True,
            'Attachments': [
                {'InstanceId': 'i-1234567', 'Device': '/dev/sdf'}
            ],
            'Tags': [...]
        }
    ]
}
```
**Use Case**: List EBS volumes, check encryption, find unattached volumes

---

## RDS APIs

### describe_db_instances()
```python
response = rds.describe_db_instances(
    DBInstanceIdentifier='mydb'  # Optional - omit to list all
)
```
**Purpose**: Describe RDS database instances  
**Parameters**:
- `DBInstanceIdentifier`: Specific DB name (optional)

**Returns**:
```python
{
    'DBInstances': [
        {
            'DBInstanceIdentifier': 'mydb',
            'DBInstanceClass': 'db.t3.micro',
            'Engine': 'postgres',
            'EngineVersion': '14.5',
            'DBInstanceStatus': 'available',
            'AvailabilityZone': 'us-east-1a',
            'MultiAZ': False,
            'AllocatedStorage': 20,  # GB
            'Endpoint': {
                'Address': 'mydb.abc123.us-east-1.rds.amazonaws.com',
                'Port': 5432
            },
            'DbiResourceId': 'db-ABC123',
            'DBInstanceArn': 'arn:aws:rds:...',
            'StorageEncrypted': True
        }
    ]
}
```
**Use Case**: Discover RDS instances, check Multi-AZ, get connection endpoints

### list_tags_for_resource()
```python
response = rds.list_tags_for_resource(
    ResourceName='arn:aws:rds:us-east-1:123456789012:db:mydb'
)
```
**Purpose**: Get tags for RDS resource  
**Parameters**:
- `ResourceName`: ARN of RDS resource

**Returns**:
```python
{
    'TagList': [
        {'Key': 'Environment', 'Value': 'production'},
        {'Key': 'Owner', 'Value': 'team-a'}
    ]
}
```
**Use Case**: Filter RDS instances by tags

---

## S3 APIs

### list_buckets()
```python
response = s3.list_buckets()
```
**Purpose**: List all S3 buckets  
**Parameters**: None  
**Returns**:
```python
{
    'Buckets': [
        {
            'Name': 'my-bucket',
            'CreationDate': datetime(...)
        }
    ]
}
```
**Use Case**: Discover all S3 buckets

### get_bucket_location()
```python
response = s3.get_bucket_location(Bucket='my-bucket')
```
**Purpose**: Get bucket's region  
**Parameters**:
- `Bucket`: Bucket name

**Returns**:
```python
{
    'LocationConstraint': 'us-west-2'  # None for us-east-1
}
```
**Use Case**: Determine which region a bucket is in

### get_bucket_tagging()
```python
response = s3.get_bucket_tagging(Bucket='my-bucket')
```
**Purpose**: Get tags for S3 bucket  
**Parameters**:
- `Bucket`: Bucket name

**Returns**:
```python
{
    'TagSet': [
        {'Key': 'Environment', 'Value': 'production'}
    ]
}
```
**Exceptions**: Raises `ClientError` if no tags exist  
**Use Case**: Filter buckets by tags

---

## Lambda APIs

### list_functions()
```python
response = lambda_client.list_functions()
```
**Purpose**: List all Lambda functions  
**Parameters**: None (optional: MaxItems)  
**Returns**:
```python
{
    'Functions': [
        {
            'FunctionName': 'my-function',
            'FunctionArn': 'arn:aws:lambda:...',
            'Runtime': 'python3.11',
            'MemorySize': 128,  # MB
            'Timeout': 3,  # seconds
            'LastModified': '2024-01-01T12:00:00.000+0000'
        }
    ]
}
```
**Use Case**: Discover all Lambda functions

### list_tags()
```python
response = lambda_client.list_tags(
    Resource='arn:aws:lambda:us-east-1:123456789012:function:my-function'
)
```
**Purpose**: Get tags for Lambda function  
**Parameters**:
- `Resource`: Function ARN

**Returns**:
```python
{
    'Tags': {
        'Environment': 'production',
        'Team': 'backend'
    }
}
```
**Use Case**: Filter functions by tags

---

## EKS (Kubernetes) APIs

### list_clusters()
```python
response = eks.list_clusters()
```
**Purpose**: List all EKS clusters  
**Parameters**: None (optional: maxResults)  
**Returns**:
```python
{
    'clusters': ['cluster-1', 'cluster-2']
}
```
**Use Case**: Discover EKS clusters

### describe_cluster()
```python
response = eks.describe_cluster(name='my-cluster')
```
**Purpose**: Get detailed cluster information  
**Parameters**:
- `name`: Cluster name

**Returns**:
```python
{
    'cluster': {
        'name': 'my-cluster',
        'arn': 'arn:aws:eks:...',
        'version': '1.28',
        'status': 'ACTIVE',
        'endpoint': 'https://ABC123.eks.us-east-1.amazonaws.com',
        'createdAt': datetime(...),
        'tags': {'Environment': 'production'}
    }
}
```
**Use Case**: Get cluster details, check status

### list_nodegroups()
```python
response = eks.list_nodegroups(clusterName='my-cluster')
```
**Purpose**: List node groups in cluster  
**Parameters**:
- `clusterName`: Cluster name

**Returns**:
```python
{
    'nodegroups': ['ng-1', 'ng-2']
}
```
**Use Case**: Discover node groups

### describe_nodegroup()
```python
response = eks.describe_nodegroup(
    clusterName='my-cluster',
    nodegroupName='ng-1'
)
```
**Purpose**: Get node group details  
**Parameters**:
- `clusterName`: Cluster name
- `nodegroupName`: Node group name

**Returns**:
```python
{
    'nodegroup': {
        'nodegroupName': 'ng-1',
        'status': 'ACTIVE',
        'instanceTypes': ['t3.medium'],
        'scalingConfig': {
            'desiredSize': 3,
            'minSize': 1,
            'maxSize': 5
        }
    }
}
```
**Use Case**: Check node group health and capacity

---

## EMR APIs

### list_clusters()
```python
response = emr.list_clusters(
    ClusterStates=['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING']
)
```
**Purpose**: List EMR clusters  
**Parameters**:
- `ClusterStates`: List of states to filter (optional)

**Returns**:
```python
{
    'Clusters': [
        {
            'Id': 'j-ABC123',
            'Name': 'my-emr-cluster',
            'Status': {
                'State': 'RUNNING',
                'Timeline': {
                    'CreationDateTime': datetime(...)
                }
            }
        }
    ]
}
```
**Use Case**: Discover active EMR clusters

### describe_cluster()
```python
response = emr.describe_cluster(ClusterId='j-ABC123')
```
**Purpose**: Get detailed cluster information  
**Parameters**:
- `ClusterId`: Cluster ID

**Returns**:
```python
{
    'Cluster': {
        'Id': 'j-ABC123',
        'Name': 'my-emr-cluster',
        'Status': {'State': 'RUNNING'},
        'ReleaseLabel': 'emr-6.10.0',
        'MasterPublicDnsName': 'ec2-54-1-2-3.compute-1.amazonaws.com',
        'NormalizedInstanceHours': 10,
        'Tags': [{'Key': 'Environment', 'Value': 'production'}]
    }
}
```
**Use Case**: Get EMR cluster details and configuration

---

## CloudWatch APIs

### get_metric_statistics()
```python
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[
        {'Name': 'InstanceId', 'Value': 'i-1234567'}
    ],
    StartTime=datetime.utcnow() - timedelta(hours=1),
    EndTime=datetime.utcnow(),
    Period=300,  # 5 minutes
    Statistics=['Average', 'Maximum']
)
```
**Purpose**: Get metric statistics for a resource  
**Parameters**:
- `Namespace`: AWS service namespace
  - EC2: 'AWS/EC2'
  - RDS: 'AWS/RDS'
  - Lambda: 'AWS/Lambda'
  - EKS: 'ContainerInsights'
  - EMR: 'AWS/ElasticMapReduce'
- `MetricName`: Metric to query (see table below)
- `Dimensions`: Resource identifier
- `StartTime`, `EndTime`: Time range
- `Period`: Aggregation period in seconds
- `Statistics`: ['Average', 'Maximum', 'Minimum', 'Sum']

**Returns**:
```python
{
    'Datapoints': [
        {
            'Timestamp': datetime(...),
            'Average': 45.5,
            'Maximum': 78.2,
            'Unit': 'Percent'
        }
    ]
}
```

**Common Metrics by Service**:

| Service | Metric Name | Dimension | Description |
|---------|-------------|-----------|-------------|
| EC2 | CPUUtilization | InstanceId | CPU usage % |
| EC2 | NetworkIn | InstanceId | Network bytes in |
| EC2 | NetworkOut | InstanceId | Network bytes out |
| EC2 | DiskReadBytes | InstanceId | Disk read bytes |
| EC2 | DiskWriteBytes | InstanceId | Disk write bytes |
| RDS | CPUUtilization | DBInstanceIdentifier | CPU usage % |
| RDS | DatabaseConnections | DBInstanceIdentifier | Active connections |
| RDS | FreeStorageSpace | DBInstanceIdentifier | Available storage |
| RDS | ReadLatency | DBInstanceIdentifier | Read latency (ms) |
| RDS | WriteLatency | DBInstanceIdentifier | Write latency (ms) |
| Lambda | Invocations | FunctionName | Invocation count |
| Lambda | Errors | FunctionName | Error count |
| Lambda | Duration | FunctionName | Execution time (ms) |
| Lambda | Throttles | FunctionName | Throttled invocations |
| EMR | IsIdle | JobFlowId | Cluster idle (1/0) |
| EMR | ContainerPending | JobFlowId | Pending containers |
| EMR | AppsRunning | JobFlowId | Running applications |

**Use Case**: Monitor resource performance, detect bottlenecks

---

## Cost Explorer APIs

### get_cost_and_usage()
```python
response = ce.get_cost_and_usage(
    TimePeriod={
        'Start': '2024-01-01',
        'End': '2024-01-08'
    },
    Granularity='DAILY',
    Metrics=['UnblendedCost'],
    GroupBy=[
        {'Type': 'DIMENSION', 'Key': 'SERVICE'},
        {'Type': 'DIMENSION', 'Key': 'REGION'}
    ]
)
```
**Purpose**: Get cost and usage data  
**Parameters**:
- `TimePeriod`: Start and end dates (YYYY-MM-DD format)
- `Granularity`: 'DAILY', 'MONTHLY', or 'HOURLY'
- `Metrics`: ['UnblendedCost', 'BlendedCost', 'UsageQuantity']
- `GroupBy`: Group results by dimension or tag
  - Dimensions: SERVICE, REGION, AVAILABILITY_ZONE, INSTANCE_TYPE, etc.
  - Tags: {'Type': 'TAG', 'Key': 'Environment'}

**Returns**:
```python
{
    'ResultsByTime': [
        {
            'TimePeriod': {'Start': '2024-01-01', 'End': '2024-01-02'},
            'Groups': [
                {
                    'Keys': ['Amazon Elastic Compute Cloud - Compute', 'us-east-1'],
                    'Metrics': {
                        'UnblendedCost': {
                            'Amount': '15.23',
                            'Unit': 'USD'
                        }
                    }
                }
            ]
        }
    ]
}
```
**Use Case**: Analyze costs by service, region, or custom tags

---

## IAM APIs

### get_user()
```python
response = iam.get_user()
```
**Purpose**: Get current IAM user information  
**Parameters**: None  
**Returns**:
```python
{
    'User': {
        'UserName': 'monitor-user',
        'UserId': 'AIDAI...',
        'Arn': 'arn:aws:iam::123456789012:user/monitor-user',
        'CreateDate': datetime(...)
    }
}
```
**Use Case**: Test IAM connectivity and permissions

---

## Common Patterns and Best Practices

### Error Handling
```python
from botocore.exceptions import ClientError, NoCredentialsError

try:
    response = ec2.describe_instances()
except NoCredentialsError:
    # AWS credentials not found
    print("Configure AWS credentials")
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'UnauthorizedOperation':
        # No permission
        print("Missing IAM permissions")
    elif error_code == 'InvalidParameterValue':
        # Invalid parameter
        print("Invalid parameter")
```

### Pagination
Many APIs return paginated results:
```python
# Manual pagination
paginator = ec2.get_paginator('describe_instances')
for page in paginator.paginate():
    for reservation in page['Reservations']:
        for instance in reservation['Instances']:
            # Process instance
            pass
```

### Filtering Best Practices
- Use server-side filters when possible (Filters parameter)
- Filter by tags: `{'Name': 'tag:KEY', 'Values': ['VALUE']}`
- Multiple filters = AND logic
- Multiple values in one filter = OR logic

### Cost Optimization
- Use `describe_` calls only when needed (they're free but can be rate-limited)
- CloudWatch metrics are charged per request
- Cost Explorer API: First request per day is free, then $0.01/request
- Use caching for frequently accessed data

---

## Required IAM Permissions

The 'monitor' AWS profile needs these permissions:

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
                "rds:ListTagsForResource",
                "s3:ListAllMyBuckets",
                "s3:GetBucketLocation",
                "s3:GetBucketTagging",
                "lambda:ListFunctions",
                "lambda:ListTags",
                "eks:ListClusters",
                "eks:DescribeCluster",
                "eks:ListNodegroups",
                "eks:DescribeNodegroup",
                "elasticmapreduce:ListClusters",
                "elasticmapreduce:DescribeCluster",
                "cloudwatch:GetMetricStatistics",
                "cloudwatch:ListMetrics",
                "ce:GetCostAndUsage",
                "iam:GetUser"
            ],
            "Resource": "*"
        }
    ]
}
```

---

## Region Access

**Question**: When UI starts and selects 2 regions automatically (us-east-1, us-west-2), does the AWS profile need access to both regions?

**Answer**: **NO, regions are not access-controlled separately**. If your AWS profile 'monitor' has the IAM permissions listed above, it can access resources in **ALL AWS regions**. The permissions are global.

However, there are 3 caveats:

1. **Opt-in Regions**: Some newer regions require explicit opt-in (e.g., Middle East, Africa). If you haven't opted in, API calls to those regions will fail.

2. **Regional Services**: Some services are regional and must be called in the correct region:
   - EC2, RDS, Lambda, EKS, EMR: Regional - create separate clients for each region
   - S3: Global namespace but regional storage - can list all buckets from any region
   - Cost Explorer: Must be called from us-east-1

3. **Service Endpoints**: Each region has its own API endpoints:
   - `ec2.us-east-1.amazonaws.com`
   - `ec2.us-west-2.amazonaws.com`
   - boto3 handles this automatically when you specify `region_name`

**Example**:
```python
# Same profile, different regions - works fine
session = boto3.Session(profile_name='monitor')

# Create clients for different regions
ec2_east = session.client('ec2', region_name='us-east-1')
ec2_west = session.client('ec2', region_name='us-west-2')

# Both work if IAM permissions allow
instances_east = ec2_east.describe_instances()
instances_west = ec2_west.describe_instances()
```

---

## Summary

- **Session Setup**: Use `boto3.Session(profile_name='monitor')` for all API calls
- **Regional Resources**: Create separate clients for each region (EC2, RDS, etc.)
- **Global Resources**: S3, IAM - can access from any region
- **Metrics**: CloudWatch `get_metric_statistics()` for performance monitoring
- **Costs**: Cost Explorer `get_cost_and_usage()` for cost analysis
- **Permissions**: The 'monitor' profile needs read-only permissions across all services
- **Region Access**: IAM permissions are global - you can access all regions you have permissions for

