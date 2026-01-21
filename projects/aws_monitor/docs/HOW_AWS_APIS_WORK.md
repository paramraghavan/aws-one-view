# AWS APIs Explained: Step-by-Step for Beginners

## Overview: How It All Works

Think of AWS APIs as a **restaurant menu system**:
- You (the app) → **Place orders** (API requests)
- AWS → **Kitchen** (processes your request)
- AWS → **Delivers food** (returns data)

Our application uses **Boto3** (AWS SDK for Python) to place these "orders" with AWS.

---

## Part 1: Resource Discovery - "What Do I Have?"

### Step 1: Connect to AWS

```python
import boto3

# Create a session (like logging into AWS)
session = boto3.Session()

# Connect to EC2 service in us-east-1
ec2 = session.client('ec2', region_name='us-east-1')
```

**What happened:**
- Boto3 reads your AWS credentials (from environment variables or ~/.aws/credentials)
- Creates a connection to AWS EC2 service
- Ready to make API calls

---

### Step 2: List All Regions

**API Call:** `describe_regions()`

```python
# Ask AWS: "What regions are available?"
response = ec2.describe_regions()

print(response)
```

**AWS Returns:**
```json
{
    "Regions": [
        {"RegionName": "us-east-1", "Endpoint": "ec2.us-east-1.amazonaws.com"},
        {"RegionName": "us-west-2", "Endpoint": "ec2.us-west-2.amazonaws.com"},
        {"RegionName": "eu-west-1", "Endpoint": "ec2.eu-west-1.amazonaws.com"}
    ]
}
```

**Our code extracts:**
```python
regions = [region['RegionName'] for region in response['Regions']]
# Result: ['us-east-1', 'us-west-2', 'eu-west-1', ...]
```

---

### Step 3: Find EC2 Instances

**API Call:** `describe_instances()`

```python
# Connect to EC2 in a specific region
ec2 = boto3.client('ec2', region_name='us-east-1')

# Ask AWS: "Show me all EC2 instances"
response = ec2.describe_instances()

print(response)
```

**AWS Returns (simplified):**
```json
{
    "Reservations": [
        {
            "Instances": [
                {
                    "InstanceId": "i-1234567890abcdef0",
                    "InstanceType": "t2.micro",
                    "State": {"Name": "running"},
                    "LaunchTime": "2025-01-01T10:00:00Z",
                    "Tags": [
                        {"Key": "Name", "Value": "Web Server"}
                    ]
                },
                {
                    "InstanceId": "i-0987654321fedcba0",
                    "InstanceType": "t3.large",
                    "State": {"Name": "stopped"}
                }
            ]
        }
    ]
}
```

**Our code processes it:**
```python
instances = []
for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        instances.append({
            'id': instance['InstanceId'],
            'type': instance['InstanceType'],
            'state': instance['State']['Name'],
            'region': 'us-east-1'
        })

# Result: 
# [
#   {'id': 'i-1234...', 'type': 't2.micro', 'state': 'running', 'region': 'us-east-1'},
#   {'id': 'i-0987...', 'type': 't3.large', 'state': 'stopped', 'region': 'us-east-1'}
# ]
```

---

### Step 4: Find RDS Databases

**API Call:** `describe_db_instances()`

```python
# Connect to RDS service
rds = boto3.client('rds', region_name='us-east-1')

# Ask AWS: "Show me all databases"
response = rds.describe_db_instances()

print(response)
```

**AWS Returns:**
```json
{
    "DBInstances": [
        {
            "DBInstanceIdentifier": "prod-database",
            "DBInstanceClass": "db.t3.medium",
            "Engine": "mysql",
            "DBInstanceStatus": "available",
            "AllocatedStorage": 100
        }
    ]
}
```

**Our code processes it:**
```python
databases = []
for db in response['DBInstances']:
    databases.append({
        'id': db['DBInstanceIdentifier'],
        'class': db['DBInstanceClass'],
        'engine': db['Engine'],
        'status': db['DBInstanceStatus'],
        'storage_gb': db['AllocatedStorage']
    })

# Result:
# [{'id': 'prod-database', 'class': 'db.t3.medium', 'engine': 'mysql', ...}]
```

---

### Step 5: Find S3 Buckets

**API Call:** `list_buckets()`

```python
# Connect to S3 (global service)
s3 = boto3.client('s3')

# Ask AWS: "Show me all S3 buckets"
response = s3.list_buckets()

print(response)
```

**AWS Returns:**
```json
{
    "Buckets": [
        {
            "Name": "my-website-bucket",
            "CreationDate": "2024-06-15T08:30:00Z"
        },
        {
            "Name": "backup-bucket",
            "CreationDate": "2024-12-01T14:20:00Z"
        }
    ]
}
```

**Our code processes it:**
```python
buckets = []
for bucket in response['Buckets']:
    buckets.append({
        'id': bucket['Name'],
        'created': bucket['CreationDate'].isoformat()
    })

# Result:
# [
#   {'id': 'my-website-bucket', 'created': '2024-06-15T08:30:00Z'},
#   {'id': 'backup-bucket', 'created': '2024-12-01T14:20:00Z'}
# ]
```

---

## Part 2: Performance Monitoring - "How Are My Resources Doing?"

### Step 1: Get CPU Metrics from CloudWatch

**API Call:** `get_metric_statistics()`

```python
from datetime import datetime, timedelta

# Connect to CloudWatch
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

# Define time range
end_time = datetime.utcnow()
start_time = end_time - timedelta(hours=24)  # Last 24 hours

# Ask AWS: "Show me CPU usage for instance i-1234567890"
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',              # We want EC2 metrics
    MetricName='CPUUtilization',      # Specifically CPU
    Dimensions=[                      # For this specific instance
        {'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}
    ],
    StartTime=start_time,             # From 24 hours ago
    EndTime=end_time,                 # Until now
    Period=3600,                      # Group by 1 hour (3600 seconds)
    Statistics=['Average', 'Maximum'] # Get average and peak values
)

print(response)
```

**AWS Returns:**
```json
{
    "Datapoints": [
        {
            "Timestamp": "2025-01-21T00:00:00Z",
            "Average": 45.5,
            "Maximum": 68.2,
            "Unit": "Percent"
        },
        {
            "Timestamp": "2025-01-21T01:00:00Z",
            "Average": 52.1,
            "Maximum": 75.3,
            "Unit": "Percent"
        },
        {
            "Timestamp": "2025-01-21T02:00:00Z",
            "Average": 38.7,
            "Maximum": 55.9,
            "Unit": "Percent"
        }
        // ... 21 more hours
    ]
}
```

**What this means:**
- From 00:00-01:00 → Average CPU was 45.5%, peaked at 68.2%
- From 01:00-02:00 → Average CPU was 52.1%, peaked at 75.3%
- And so on...

**Our code processes it:**
```python
# Sort by timestamp
datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])

# Extract for charting
times = [dp['Timestamp'] for dp in datapoints]
averages = [dp['Average'] for dp in datapoints]
peaks = [dp['Maximum'] for dp in datapoints]

# Now we can plot a chart showing CPU usage over 24 hours
```

---

### Step 2: Get RDS Connection Metrics

**API Call:** `get_metric_statistics()` (for RDS)

```python
# Ask AWS: "How many database connections are active?"
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/RDS',                    # RDS metrics
    MetricName='DatabaseConnections',       # Number of connections
    Dimensions=[
        {'Name': 'DBInstanceIdentifier', 'Value': 'prod-database'}
    ],
    StartTime=start_time,
    EndTime=end_time,
    Period=3600,
    Statistics=['Average']
)
```

**AWS Returns:**
```json
{
    "Datapoints": [
        {"Timestamp": "2025-01-21T00:00:00Z", "Average": 15.0},
        {"Timestamp": "2025-01-21T01:00:00Z", "Average": 23.5},
        {"Timestamp": "2025-01-21T02:00:00Z", "Average": 18.2}
    ]
}
```

**What this means:**
- Hour 1: Average of 15 database connections
- Hour 2: Average of 23.5 connections
- Hour 3: Average of 18.2 connections

---

### Step 3: Get Lambda Invocations

**API Call:** `get_metric_statistics()` (for Lambda)

```python
# Ask AWS: "How many times was my Lambda function called?"
response = cloudwatch.get_metric_statistics(
    Namespace='AWS/Lambda',
    MetricName='Invocations',
    Dimensions=[
        {'Name': 'FunctionName', 'Value': 'my-function'}
    ],
    StartTime=start_time,
    EndTime=end_time,
    Period=3600,
    Statistics=['Sum']  # Total invocations per hour
)
```

**AWS Returns:**
```json
{
    "Datapoints": [
        {"Timestamp": "2025-01-21T00:00:00Z", "Sum": 1250},
        {"Timestamp": "2025-01-21T01:00:00Z", "Sum": 2341},
        {"Timestamp": "2025-01-21T02:00:00Z", "Sum": 1876}
    ]
}
```

**What this means:**
- Hour 1: Function called 1,250 times
- Hour 2: Function called 2,341 times
- Hour 3: Function called 1,876 times

---

## Part 3: Cost Analysis - "How Much Am I Spending?"

### Step 1: Get Cost Data from Cost Explorer

**API Call:** `get_cost_and_usage()`

```python
from datetime import date

# Connect to Cost Explorer (always us-east-1)
ce = boto3.client('ce', region_name='us-east-1')

# Define time period
end_date = date.today()
start_date = end_date - timedelta(days=30)  # Last 30 days

# Ask AWS: "How much did I spend in the last 30 days?"
response = ce.get_cost_and_usage(
    TimePeriod={
        'Start': start_date.strftime('%Y-%m-%d'),
        'End': end_date.strftime('%Y-%m-%d')
    },
    Granularity='DAILY',              # Show me daily costs
    Metrics=['UnblendedCost'],        # The actual cost (not estimates)
    GroupBy=[                         # Break down by service
        {'Type': 'DIMENSION', 'Key': 'SERVICE'}
    ]
)

print(response)
```

**AWS Returns:**
```json
{
    "ResultsByTime": [
        {
            "TimePeriod": {"Start": "2025-01-01", "End": "2025-01-02"},
            "Groups": [
                {
                    "Keys": ["Amazon Elastic Compute Cloud - Compute"],
                    "Metrics": {
                        "UnblendedCost": {"Amount": "15.43", "Unit": "USD"}
                    }
                },
                {
                    "Keys": ["Amazon Relational Database Service"],
                    "Metrics": {
                        "UnblendedCost": {"Amount": "8.92", "Unit": "USD"}
                    }
                },
                {
                    "Keys": ["Amazon Simple Storage Service"],
                    "Metrics": {
                        "UnblendedCost": {"Amount": "2.15", "Unit": "USD"}
                    }
                }
            ]
        },
        {
            "TimePeriod": {"Start": "2025-01-02", "End": "2025-01-03"},
            "Groups": [
                // ... costs for Jan 2
            ]
        }
        // ... 28 more days
    ]
}
```

**What this means:**
- **Jan 1**: Spent $15.43 on EC2, $8.92 on RDS, $2.15 on S3
- **Jan 2**: (Similar breakdown)
- Total for 30 days: Sum all amounts

**Our code processes it:**
```python
total_cost = 0.0
costs_by_service = {}

for day in response['ResultsByTime']:
    for group in day['Groups']:
        service = group['Keys'][0]
        cost = float(group['Metrics']['UnblendedCost']['Amount'])
        
        total_cost += cost
        
        if service not in costs_by_service:
            costs_by_service[service] = 0.0
        costs_by_service[service] += cost

# Result:
# total_cost = 789.50
# costs_by_service = {
#     "Amazon EC2": 450.30,
#     "Amazon RDS": 267.80,
#     "Amazon S3": 71.40
# }
```

---

## Part 4: Bottleneck Detection - "What's Having Problems?"

This combines multiple API calls to analyze performance.

### Step 1: Get All Running Instances

```python
# Ask AWS: "Show me only running instances"
response = ec2.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running']}
    ]
)
```

**AWS Returns:** (Only running instances)

---

### Step 2: Check Each Instance's CPU

For each running instance, we get CPU metrics:

```python
for reservation in response['Reservations']:
    for instance in reservation['Instances']:
        instance_id = instance['InstanceId']
        
        # Get CPU metrics
        cpu_data = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=datetime.utcnow() - timedelta(hours=24),
            EndTime=datetime.utcnow(),
            Period=3600,
            Statistics=['Average', 'Maximum']
        )
```

---

### Step 3: Analyze the Data

```python
if cpu_data['Datapoints']:
    # Calculate average and peak
    avg_cpu = sum(d['Average'] for d in cpu_data['Datapoints']) / len(cpu_data['Datapoints'])
    max_cpu = max(d['Maximum'] for d in cpu_data['Datapoints'])
    
    # Check for problems
    if max_cpu > 80:
        # HIGH CPU PROBLEM!
        print(f"⚠️ {instance_id} has high CPU: {max_cpu}%")
        # Add to bottlenecks list
        
    elif avg_cpu < 10:
        # UNDERUTILIZED!
        print(f"💡 {instance_id} is underutilized: {avg_cpu}%")
        # Suggest downsizing
```

---

## Complete Flow: User Clicks "Load Resources"

Here's what happens step-by-step:

### 1. User Action
```
User clicks "Load Resources" button in browser
```

### 2. Browser → Flask Server
```javascript
// Frontend (JavaScript)
$.ajax({
    url: '/api/resources',
    method: 'GET',
    data: { regions: ['us-east-1', 'us-west-2'] }
});
```

### 3. Flask Server → AWS
```python
# Backend (main.py)
@app.route('/api/resources')
def get_resources():
    regions = request.args.getlist('regions')
    
    # Call AWS client
    resources = aws_client.get_all_resources(regions)
    
    return jsonify({'success': True, 'data': resources})
```

### 4. AWS Client Makes API Calls
```python
# app/aws_client.py
def get_all_resources(self, regions):
    for region in regions:
        # API Call 1: Get EC2 instances
        ec2 = boto3.client('ec2', region_name=region)
        ec2_response = ec2.describe_instances()
        
        # API Call 2: Get RDS databases
        rds = boto3.client('rds', region_name=region)
        rds_response = rds.describe_db_instances()
        
        # API Call 3: Get Lambda functions
        lambda_client = boto3.client('lambda', region_name=region)
        lambda_response = lambda_client.list_functions()
        
        # ... process all responses
    
    # API Call 4: Get S3 buckets (global)
    s3 = boto3.client('s3')
    s3_response = s3.list_buckets()
    
    return resources
```

### 5. AWS Responds
```
AWS → Boto3 → Flask → JSON → Browser
```

### 6. Browser Displays
```javascript
// Frontend receives response
success: function(response) {
    displayResources(response.data);
    // Shows table with all resources
}
```

---

## API Summary Table

| Task | AWS Service | API Call | What It Does |
|------|-------------|----------|--------------|
| List regions | EC2 | `describe_regions()` | Get all AWS regions |
| List EC2 | EC2 | `describe_instances()` | Get all virtual servers |
| List RDS | RDS | `describe_db_instances()` | Get all databases |
| List S3 | S3 | `list_buckets()` | Get all storage buckets |
| List Lambda | Lambda | `list_functions()` | Get all serverless functions |
| Get CPU metrics | CloudWatch | `get_metric_statistics()` | Get performance data |
| Get costs | Cost Explorer | `get_cost_and_usage()` | Get spending data |

---

## Authentication Flow

### How AWS Knows It's You

```
1. You set credentials:
   export AWS_ACCESS_KEY_ID="AKIAIOSFODNN7EXAMPLE"
   export AWS_SECRET_ACCESS_KEY="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"

2. Boto3 reads these automatically

3. Every API call includes:
   - Your Access Key ID (like a username)
   - A signature (like a password, but encrypted)
   - Timestamp
   
4. AWS verifies:
   - Is this key valid?
   - Does this user have permission?
   - Is the signature correct?
   
5. If yes → Returns data
   If no → Returns "Access Denied" error
```

---

## Real Example: Complete Monitoring Flow

### User Action: "Show me CPU for instance i-12345"

**Step 1:** User selects instance and clicks "Load Metrics"

**Step 2:** Browser sends request:
```javascript
GET /api/metrics?resource_ids=i-12345&resource_type=ec2&region=us-east-1&hours=24
```

**Step 3:** Flask receives and calls AWS Client:
```python
metrics = aws_client.get_metrics(
    resource_type='ec2',
    resource_ids=['i-12345'],
    region='us-east-1',
    hours=24
)
```

**Step 4:** AWS Client calls CloudWatch:
```python
cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')

response = cloudwatch.get_metric_statistics(
    Namespace='AWS/EC2',
    MetricName='CPUUtilization',
    Dimensions=[{'Name': 'InstanceId', 'Value': 'i-12345'}],
    StartTime=datetime.utcnow() - timedelta(hours=24),
    EndTime=datetime.utcnow(),
    Period=3600,
    Statistics=['Average', 'Maximum']
)
```

**Step 5:** AWS returns 24 data points (one per hour)

**Step 6:** Flask sends to browser:
```json
{
    "success": true,
    "data": {
        "i-12345": {
            "cpu": [
                {"Timestamp": "2025-01-21T00:00:00Z", "Average": 45.5},
                {"Timestamp": "2025-01-21T01:00:00Z", "Average": 52.1},
                ...
            ]
        }
    }
}
```

**Step 7:** Browser draws chart with Chart.js

---

## Key Concepts

### 1. Region-Specific Services
- **EC2, RDS, Lambda** → Must specify region
- **S3, IAM, Cost Explorer** → Global (or use us-east-1)

### 2. Pagination
Some APIs return lots of data:
```python
# Without pagination (simple)
response = ec2.describe_instances()

# With pagination (for 1000+ instances)
paginator = ec2.get_paginator('describe_instances')
for page in paginator.paginate():
    process(page)
```

### 3. Rate Limits
AWS limits API calls:
- EC2: 100 requests/second
- CloudWatch: 1,000 requests/second
- Cost Explorer: 5 requests/second

Our app handles this automatically.

### 4. Costs
- Most "describe" calls are FREE
- CloudWatch metrics: First 1 million requests free/month
- Cost Explorer: $0.01 per request (first request/day is free)

---

## Summary

### The application does 4 main things:

1. **Resource Discovery**
   - Calls `describe_*()` APIs
   - Gets lists of EC2, RDS, S3, Lambda, etc.
   - Displays in tables

2. **Performance Monitoring**
   - Calls CloudWatch `get_metric_statistics()`
   - Gets CPU, connections, invocations
   - Displays in charts

3. **Cost Analysis**
   - Calls Cost Explorer `get_cost_and_usage()`
   - Gets spending by service and day
   - Displays totals and breakdowns

4. **Bottleneck Detection**
   - Combines #1 and #2
   - Analyzes metrics vs. thresholds
   - Flags problems

### All using:
- **Boto3** (AWS SDK)
- **AWS API** (REST endpoints)
- **Your credentials** (for authentication)
- **JSON** (for data format)

That's it! The complexity is in AWS's side - we just ask questions and get answers.
