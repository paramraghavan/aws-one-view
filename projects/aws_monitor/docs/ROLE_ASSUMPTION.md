# IAM Role Assumption Guide

## Overview

AWS Monitor supports **optional IAM role assumption** for elevated permissions. This is a security best practice that allows you to:

1. Use a base AWS profile with minimal permissions
2. Assume a role with monitoring permissions only when needed
3. Use temporary credentials that expire automatically
4. Support cross-account monitoring
5. Implement least-privilege security

## Why Use Role Assumption?

### Security Benefits

1. **Least Privilege**: Base profile has minimal permissions
2. **Temporary Credentials**: Assumed role credentials expire (1 hour default)
3. **Audit Trail**: All actions are logged under the assumed role
4. **Cross-Account Access**: Monitor resources in different AWS accounts
5. **No Hardcoded Credentials**: Use temporary STS tokens instead

### Common Use Cases

- **Enterprise Environments**: Central monitoring account assumes roles in other accounts
- **Elevated Permissions**: Base user assumes monitoring role with read-only access
- **Compliance**: Separate authentication from authorization
- **Multi-Account**: Monitor resources across multiple AWS accounts

## How It Works

```
┌─────────────────┐
│  Base Profile   │
│   'monitor'     │
│ (Minimal perms) │
└────────┬────────┘
         │
         │ AWS STS AssumeRole
         │
         ▼
┌─────────────────┐
│  Assumed Role   │
│ MonitoringRole  │
│ (Full perms)    │
└────────┬────────┘
         │
         │ Temporary Credentials
         │ (Valid for 1 hour)
         ▼
┌─────────────────┐
│ AWS API Calls   │
│ EC2, RDS, EKS   │
└─────────────────┘
```

## Setup Instructions

### Step 1: Create Monitoring IAM Role

In the **target account** (where resources are located), create a role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::YOUR_BASE_ACCOUNT:user/monitor-user"
      },
      "Action": "sts:AssumeRole",
      "Condition": {}
    }
  ]
}
```

**Attach monitoring permissions policy**:

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
        "ce:GetCostAndUsage",
        "iam:GetUser"
      ],
      "Resource": "*"
    }
  ]
}
```

### Step 2: Configure Base Profile

The base profile only needs permission to assume the role:

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

Configure the profile:

```bash
aws configure --profile monitor
# Enter minimal credentials
```

### Step 3: Run with Role Assumption

**Basic usage (no role)**:
```bash
python main.py
```

**With role assumption**:
```bash
python main.py --role-arn arn:aws:iam::123456789012:role/MonitoringRole
```

**With custom session name**:
```bash
python main.py \
  --role-arn arn:aws:iam::123456789012:role/MonitoringRole \
  --session-name MyMonitoringSession
```

**Full options**:
```bash
python main.py \
  --role-arn arn:aws:iam::123456789012:role/MonitoringRole \
  --session-name MySession \
  --port 8080 \
  --host 0.0.0.0 \
  --debug
```

## Command Line Options

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--role-arn` | No | None | ARN of IAM role to assume |
| `--session-name` | No | AWSMonitorSession | Session name for role assumption |
| `--port` | No | 5000 | Port to run Flask on |
| `--host` | No | 0.0.0.0 | Host to bind to |
| `--debug` | No | False | Enable debug mode |

## Examples

### Example 1: Single Account Monitoring

**Scenario**: Monitor resources in your own account with elevated role

**Setup**:
1. Base profile: `monitor` (minimal permissions)
2. Role: `MonitoringRole` (full read permissions)

**Command**:
```bash
python main.py --role-arn arn:aws:iam::123456789012:role/MonitoringRole
```

### Example 2: Cross-Account Monitoring

**Scenario**: Monitor resources in a different AWS account

**Setup**:
1. Base account: 111111111111 (monitoring account)
2. Target account: 222222222222 (production resources)
3. Role in target: `CrossAccountMonitoringRole`

**Trust policy in target account**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:root"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

**Command**:
```bash
python main.py --role-arn arn:aws:iam::222222222222:role/CrossAccountMonitoringRole
```

### Example 3: Multiple Accounts (Generated Script)

For monitoring multiple accounts, generate a script for each:

```bash
# Account 1 (Production)
python main.py --role-arn arn:aws:iam::222222222222:role/MonitoringRole
# Generate script in UI, save as prod_monitor.py

# Account 2 (Development)  
python main.py --role-arn arn:aws:iam::333333333333:role/MonitoringRole
# Generate script in UI, save as dev_monitor.py

# Schedule both
crontab -e
*/15 * * * * python3 /path/to/prod_monitor.py
*/15 * * * * python3 /path/to/dev_monitor.py
```

## Generated Scripts

When you generate a monitoring script in the UI, the role ARN is automatically included:

```python
# Generated script includes
AWS_PROFILE = 'monitor'
ROLE_ARN = 'arn:aws:iam::123456789012:role/MonitoringRole'
SESSION_NAME = 'AWSMonitorSession'

# Role assumption logic
base_session = boto3.Session(profile_name=AWS_PROFILE)

if ROLE_ARN:
    sts = base_session.client('sts')
    response = sts.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName=SESSION_NAME,
        DurationSeconds=3600
    )
    # Use temporary credentials...
```

## Troubleshooting

### Error: "User is not authorized to perform: sts:AssumeRole"

**Problem**: Base profile doesn't have permission to assume the role

**Solution**: Add policy to base user/role:
```json
{
  "Effect": "Allow",
  "Action": "sts:AssumeRole",
  "Resource": "arn:aws:iam::TARGET_ACCOUNT:role/MonitoringRole"
}
```

### Error: "Access Denied" when assuming role

**Problem**: Trust policy doesn't allow your user/account

**Solution**: Update trust policy in the target role:
```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::YOUR_ACCOUNT:user/YOUR_USER"
  },
  "Action": "sts:AssumeRole"
}
```

### Error: "The security token included in the request is expired"

**Problem**: Temporary credentials expired (default 1 hour)

**Solution**: 
- Restart the application (web UI)
- Re-run the script (generated scripts)
- Credentials automatically refresh on restart

### Verify Role Assumption

Test if role assumption works:

```bash
# Using AWS CLI
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/MonitoringRole \
  --role-session-name test \
  --profile monitor

# Should return temporary credentials
```

Test in Python:

```python
import boto3

session = boto3.Session(profile_name='monitor')
sts = session.client('sts')

response = sts.assume_role(
    RoleArn='arn:aws:iam::123456789012:role/MonitoringRole',
    RoleSessionName='test'
)

print("Success! Credentials:")
print(response['Credentials'])
```

## Security Best Practices

### 1. Use Minimal Base Permissions

Base profile should only have `sts:AssumeRole`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::*:role/MonitoringRole*"
    }
  ]
}
```

### 2. Limit Role Trust Policy

Only allow specific principals:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::111111111111:user/admin",
          "arn:aws:iam::111111111111:role/MonitoringBastion"
        ]
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "sts:ExternalId": "unique-external-id-12345"
        }
      }
    }
  ]
}
```

### 3. Use External ID for Cross-Account

Add external ID requirement:

```bash
python main.py \
  --role-arn arn:aws:iam::222222222222:role/MonitoringRole \
  --external-id unique-external-id-12345
```

(Note: External ID support would need to be added to the code)

### 4. Monitor Role Usage

Enable CloudTrail to track role assumptions:
- Who assumed the role
- When it was assumed
- What actions were performed

### 5. Short Session Duration

Use shortest duration needed:
- Default: 3600 seconds (1 hour)
- Minimum: 900 seconds (15 minutes)
- Maximum: 43200 seconds (12 hours)

### 6. Read-Only Permissions

Only grant read permissions in monitoring role:
- Never include `ec2:*`, `rds:*`
- Only use `Describe*`, `List*`, `Get*` actions
- Follow principle of least privilege

## Architecture Patterns

### Pattern 1: Hub and Spoke

```
┌─────────────────┐
│ Monitoring Hub  │
│   (Account A)   │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ Prod   │ │  Dev   │
│Account │ │Account │
└────────┘ └────────┘
```

Central monitoring account assumes roles in spoke accounts.

### Pattern 2: Delegated Admin

```
┌─────────────────┐
│ Security Acct   │ (Manages all roles)
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│  User  │ │ Monitor│
│ Acct   │ │  Acct  │
└────────┘ └────────┘
```

Security account controls access to monitoring roles.

### Pattern 3: Per-Service Roles

```
┌─────────────────┐
│ Base User       │
└────────┬────────┘
         │
    ┌────┴────┬────────┐
    │         │        │
    ▼         ▼        ▼
┌────────┐ ┌────────┐ ┌────────┐
│ EC2    │ │ RDS    │ │ EKS    │
│ Role   │ │ Role   │ │ Role   │
└────────┘ └────────┘ └────────┘
```

Separate roles for different services (more granular control).

## Comparison: With vs Without Role Assumption

| Feature | Without Role | With Role Assumption |
|---------|-------------|---------------------|
| **Security** | Long-lived credentials | Temporary credentials |
| **Permissions** | Always active | Only when assumed |
| **Audit** | Under user identity | Under role identity |
| **Cross-Account** | Requires separate profiles | Single profile, multiple roles |
| **Complexity** | Simple | Moderate |
| **Expiration** | Never | 1 hour default |
| **Best For** | Single account, dev/test | Production, multi-account |

## FAQ

**Q: Do I need role assumption?**  
A: Optional. Use it for better security or cross-account monitoring.

**Q: Can I use role assumption with generated scripts?**  
A: Yes, the role ARN is automatically included in generated scripts.

**Q: How long do credentials last?**  
A: 1 hour by default. The application/script will use them until they expire.

**Q: What happens when credentials expire?**  
A: Web UI: Restart the application. Scripts: Re-run the script.

**Q: Can I monitor multiple accounts?**  
A: Yes, generate separate scripts with different role ARNs.

**Q: Do I need different AWS profiles for different accounts?**  
A: No! Use one profile, multiple roles. That's the benefit of role assumption.

**Q: Is role assumption slower?**  
A: Initial setup takes ~1 second for AssumeRole call. After that, no difference.

**Q: Can I use MFA with role assumption?**  
A: Yes, add MFA requirement in the role's trust policy.

## Summary

Role assumption is **optional but recommended** for:
- ✅ Production environments
- ✅ Multi-account setups
- ✅ Enhanced security
- ✅ Compliance requirements
- ✅ Cross-account monitoring

Use **without role assumption** for:
- ✅ Development/testing
- ✅ Single account
- ✅ Simple setups
- ✅ Quick start

**The choice is yours!** The application works perfectly either way.
