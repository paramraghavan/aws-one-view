# Resource Metrics Guide - All Types

## 📊 Overview

Different AWS resources have different metric behaviors. This guide explains what metrics are available for each resource type and why you might not see metrics.

---

## 🎯 Quick Reference

| Resource | Metrics Always Available? | Common Issue |
|----------|--------------------------|--------------|
| **EC2** | ✅ Yes (CPU, Network, Disk) | Memory requires agent |
| **RDS** | ✅ Yes (CPU, Connections, Memory) | None |
| **Lambda** | ⚠️ Only when invoked | No recent invocations |
| **S3** | ⚠️ Updates once per day | Storage metrics delayed |
| **EBS** | ✅ Yes (if attached) | Detached volumes have no metrics |
| **EKS** | ❌ Requires Container Insights | Not enabled by default |
| **EMR** | ⚠️ Only when running jobs | Idle clusters show limited data |

---

## 1. EC2 Instances ✅

### Always Available Metrics

- **CPUUtilization** - CPU usage percentage
- **NetworkIn** - Incoming network traffic (bytes)
- **NetworkOut** - Outgoing network traffic (bytes)
- **DiskReadBytes** - Disk read activity
- **DiskWriteBytes** - Disk write activity

### Special Case: Memory ⚠️

**Memory is NOT available by default!**

**Why?** EC2 instances are customer-managed. AWS doesn't have access to OS-level metrics.

**How to get memory metrics**:
1. Install CloudWatch agent on the instance
2. Configure agent to collect memory metrics
3. Metrics appear in `CWAgent` namespace

**See**: docs/BOTO3_REFERENCE.md for setup instructions

### When You Won't See Metrics

- ❌ Instance is stopped (no metrics when stopped)
- ⚠️ Just started (wait 1-2 minutes for first datapoints)

---

## 2. RDS Databases ✅

### Always Available Metrics

- **CPUUtilization** - CPU usage percentage
- **DatabaseConnections** - Number of active connections
- **FreeStorageSpace** - Available disk space (bytes)
- **ReadLatency** - Read operation latency (seconds)
- **WriteLatency** - Write operation latency (seconds)
- **FreeableMemory** - Available memory (bytes) ✅

### Why RDS Has Memory But EC2 Doesn't

**RDS is a managed service** - AWS controls the underlying instances, so memory metrics are built-in.

**EC2 is unmanaged** - You control the instances, so AWS needs your permission (agent) to see memory.

### When You Won't See Metrics

- ❌ Database is stopped
- ⚠️ Just created (wait 2-3 minutes)

---

## 3. Lambda Functions ⏱️

### Available Metrics (When Invoked)

- **Invocations** - Number of times function was called
- **Errors** - Number of failed invocations
- **Duration** - Execution time (milliseconds)
- **Throttles** - Number of throttled invocations

### ⚠️ Key Difference: Activity-Based Metrics

**Lambda metrics ONLY appear when the function is invoked!**

### When You Won't See Metrics

- ❌ Function never invoked
- ❌ No invocations in selected time period
- ❌ Function runs daily, but you selected "5 minutes" period

### Solutions

1. **Invoke the function**:
   ```bash
   aws lambda invoke --function-name my-function \
     --payload '{}' response.json
   ```

2. **Wait 2-3 minutes** for CloudWatch delay

3. **Select appropriate time period**:
   - Runs every minute → 5 minutes
   - Runs hourly → 1 hour
   - Runs daily → Check after it runs

4. **Check function is actually being used**

### You'll See This Message

```
⏱️ No recent invocations - Lambda metrics only 
   appear when function is called

Try: Invoke the function or select "1 hour" period
```

**See**: docs/LAMBDA_METRICS.md for complete Lambda guide

---

## 4. S3 Buckets 🪣

### Available Metrics

#### Storage Metrics (Daily Update)
- **BucketSizeBytes** - Total bucket size (converted to GB)
- **NumberOfObjects** - Count of objects in bucket

#### Request Metrics (Optional)
- **AllRequests** - Total API requests
- Requires enabling CloudWatch request metrics on bucket

### ⚠️ Key Difference: Daily Updates

**S3 storage metrics update only once per day!**

### When You Won't See Metrics

- ❌ Bucket created less than 24 hours ago
- ❌ Empty bucket (0 bytes, 0 objects)
- ⚠️ Request metrics not enabled (normal)

### Why This Happens

**Storage metrics are calculated daily** because:
- S3 can have billions of objects
- Real-time calculation would be too expensive
- Most users only need daily snapshots

**Request metrics cost extra** and must be explicitly enabled.

### You'll See This Message

```
🪣 S3 storage metrics update once per day

Storage metrics may take 24 hours to appear.
Request metrics require enabling CloudWatch
request metrics on the bucket.
```

### How to Enable Request Metrics

1. Go to S3 Console → Bucket → Metrics tab
2. Enable "Request metrics"
3. Costs: $0.01 per 1,000 metrics requests

### What You'll See (With Data)

```
┌────────────────────────────────────┐
│ s3:my-data-bucket                  │
├────────────────────────────────────┤
│  Bucket Size        Object Count   │
│    45.67 GB            12,543      │
│                                    │
│  Requests (optional)               │
│    1,234 requests                  │
└────────────────────────────────────┘
```

---

## 5. EBS Volumes 💾

### Available Metrics (When Attached)

- **VolumeReadBytes** - Data read from volume (MB)
- **VolumeWriteBytes** - Data written to volume (MB)
- **VolumeReadOps** - Number of read operations
- **VolumeWriteOps** - Number of write operations
- **VolumeIdleTime** - Time with no read/write activity (seconds)

### When You Won't See Metrics

- ❌ Volume is detached (not attached to instance)
- ❌ Attached to stopped instance
- ⚠️ Just attached (wait 2-3 minutes)
- ❌ Volume never used (no I/O operations)

### You'll See This Message

```
💾 No EBS metrics available

EBS metrics require the volume to be attached
to a running instance
```

### What You'll See (With Data)

```
┌────────────────────────────────────┐
│ ebs:vol-abc123                     │
├────────────────────────────────────┤
│  Read Bytes         Write Bytes    │
│    123.45 MB          234.56 MB    │
│                                    │
│  Read Ops           Write Ops      │
│    1,234 ops          2,345 ops    │
│                                    │
│  Idle Time                         │
│    45 sec                          │
└────────────────────────────────────┘
```

---

## 6. EKS Clusters ☸️

### Metrics Require Container Insights

**EKS does NOT provide metrics by default!**

You must enable **Container Insights** on your cluster.

### Available Metrics (With Container Insights)

- cluster_failed_node_count
- cluster_node_count
- namespace_number_of_running_pods
- node_cpu_utilization
- node_memory_utilization
- pod_cpu_utilization
- pod_memory_utilization

### When You Won't See Metrics

- ❌ Container Insights not enabled (default)
- ⚠️ Just enabled (wait 5-10 minutes for first data)

### You'll See This Message

```
☸️ EKS metrics require Container Insights

Enable Container Insights on your EKS cluster
to see metrics

How to enable: [AWS Documentation link]
```

### How to Enable Container Insights

**Using eksctl**:
```bash
eksctl utils update-cluster-logging \
  --enable-types all \
  --region us-east-1 \
  --cluster my-cluster \
  --approve
```

**Using AWS Console**:
1. Go to EKS → Clusters → Your Cluster
2. Click "Observability" tab
3. Enable "Container Insights"

**Cost**: ~$1-5 per cluster per month (depends on pod count)

---

## 7. EMR Clusters 📊

### Available Metrics (When Running Jobs)

- **IsIdle** - Whether cluster is idle (0 or 1)
- **ContainerPending** - Containers waiting to start
- **AppsRunning** - Number of running applications

### When You Won't See Metrics

- ❌ Cluster terminated
- ⚠️ Cluster idle (no jobs running)
- ❌ Just started (wait 5 minutes)

### You'll See This Message

```
📊 No EMR metrics available for this time period

EMR metrics may not be available if cluster is
terminated or not running jobs
```

### What You'll See (With Data)

```
┌────────────────────────────────────┐
│ emr:j-ABC123                       │
├────────────────────────────────────┤
│  Is Idle            Apps Running   │
│    0 (running)          3          │
│                                    │
│  Container Pending                 │
│    5                               │
└────────────────────────────────────┘
```

---

## 🎯 Comparison Table

### Metrics Availability

| Resource | Always On? | Update Frequency | Special Requirements |
|----------|-----------|------------------|---------------------|
| **EC2** | ✅ Yes | 1-5 minutes | Memory requires agent |
| **RDS** | ✅ Yes | 1-5 minutes | None |
| **Lambda** | ❌ No | When invoked | Must be invoked |
| **S3** | ⚠️ Partial | Once per day | Request metrics cost extra |
| **EBS** | ✅ Yes* | 1-5 minutes | *Must be attached |
| **EKS** | ❌ No | N/A | Requires Container Insights |
| **EMR** | ⚠️ Partial | 5 minutes | Only when running jobs |

---

## 📝 Best Practices

### 1. Choose Appropriate Time Period

**For each resource type**:
- **EC2/RDS/EBS**: Any period works (5 min to 1 hour)
- **Lambda**: Match to invocation frequency
  - Runs every minute → 5 minutes
  - Runs hourly → 1 hour
  - Runs daily → Check after scheduled time
- **S3**: Use 1 hour or longer (daily updates)
- **EMR**: Use 15 minutes to 1 hour

---

### 2. Wait for Initial Metrics

**After creating/starting a resource**:
- EC2/RDS/EBS: Wait 2-3 minutes
- Lambda: Invoke once, wait 2 minutes
- S3: Wait 24 hours for first storage metrics
- EKS: Wait 5-10 minutes after enabling Container Insights
- EMR: Wait 5 minutes after starting cluster

---

### 3. Understand Update Frequency

**Real-time (1-5 min delay)**:
- EC2, RDS, EBS, Lambda (when active), EMR

**Daily (24 hour delay)**:
- S3 storage metrics

**On-demand (requires enablement)**:
- EC2 memory (CloudWatch agent)
- S3 request metrics (CloudWatch request metrics)
- EKS metrics (Container Insights)

---

### 4. Cost Considerations

**Free metrics**:
- EC2 basic metrics (CPU, Network, Disk)
- RDS all metrics
- Lambda all metrics
- S3 storage metrics
- EBS all metrics
- EMR basic metrics

**Costs money**:
- EC2 detailed monitoring ($2.10/month per instance)
- EC2 memory metrics (CloudWatch agent + log ingestion)
- S3 request metrics ($0.01 per 1,000 requests)
- EKS Container Insights ($1-5/month per cluster)

---

## 🔍 Troubleshooting

### "I don't see any metrics for my resource"

**Checklist by resource type**:

**EC2**:
- [ ] Instance is running?
- [ ] Waited 2-3 minutes?
- [ ] For memory: CloudWatch agent installed?

**RDS**:
- [ ] Database is available?
- [ ] Waited 2-3 minutes?

**Lambda**:
- [ ] Function invoked recently?
- [ ] Selected appropriate time period?
- [ ] Waited 2 minutes after invocation?

**S3**:
- [ ] Bucket exists for 24+ hours?
- [ ] Bucket has objects?
- [ ] For requests: CloudWatch request metrics enabled?

**EBS**:
- [ ] Volume is attached?
- [ ] Attached to running instance?
- [ ] Instance is performing I/O?

**EKS**:
- [ ] Container Insights enabled?
- [ ] Waited 10 minutes after enabling?

**EMR**:
- [ ] Cluster is running?
- [ ] Cluster has active jobs?
- [ ] Not just in WAITING state?

---

### "Metrics were working, now they're gone"

**Common causes**:
- Resource was stopped/terminated
- Selected time period doesn't include recent data
- Lambda function stopped being invoked
- EBS volume was detached
- EMR cluster finished jobs and is idle

**Solution**: Check resource state in AWS Console

---

### "Some metrics show but not others"

**Common scenarios**:
- **EC2 without memory**: CloudWatch agent not installed
- **S3 with size but no requests**: Request metrics not enabled
- **Lambda with invocations but 0 errors**: This is good! No errors.

---

## 📚 Additional Resources

### Documentation

- **BOTO3_REFERENCE.md**: Complete API reference including metrics
- **LAMBDA_METRICS.md**: Detailed Lambda metrics guide
- **HOW_TO_USE_METRICS.md**: General metrics usage guide

### AWS Documentation

- [CloudWatch Metrics Reference](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/aws-services-cloudwatch-metrics.html)
- [CloudWatch Agent Setup](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html)
- [Container Insights Setup](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-setup-EKS-quickstart.html)
- [S3 Request Metrics](https://docs.aws.amazon.com/AmazonS3/latest/userguide/metrics-configurations.html)

---

## ✅ Summary

### Key Takeaways

1. **Different resources have different metric behaviors**
2. **Not all resources have always-on metrics**:
   - Lambda: Only when invoked
   - S3: Daily updates
   - EKS: Requires Container Insights
   - EBS: Requires attachment

3. **Common issues are normal**:
   - Lambda with no recent invocations → Expected
   - S3 with no metrics on day 1 → Expected
   - EKS with no metrics → Container Insights not enabled

4. **Most issues are fixable**:
   - Lambda: Invoke the function
   - S3: Wait 24 hours or enable request metrics
   - EKS: Enable Container Insights
   - EBS: Attach to running instance

5. **Choose appropriate time periods**:
   - Frequent activity: 5-15 minutes
   - Hourly activity: 1 hour
   - Daily activity: Check after scheduled time

---

**Now you understand why metrics might not appear for any resource type!** 📊✅
