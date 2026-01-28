# Quick Start: IAM Role Assumption

## What You Need

1. **Base AWS Profile** (`monitor`) - Minimal permissions
2. **IAM Role** - Full monitoring permissions  
3. **Trust Relationship** - Allow base profile to assume role

## 5-Minute Setup

### Step 1: Create the Monitoring Role

In AWS Console → IAM → Roles → Create Role:

**Trust Policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::YOUR_ACCOUNT:user/YOUR_USER"
    },
    "Action": "sts:AssumeRole"
  }]
}
```

**Attach Policy:** ReadOnlyAccess (or create custom monitoring policy)

**Role Name:** `MonitoringRole`

**Copy Role ARN:** `arn:aws:iam::123456789012:role/MonitoringRole`

### Step 2: Give Base Profile Permission to Assume Role

Create/attach this policy to your `monitor` user:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "sts:AssumeRole",
    "Resource": "arn:aws:iam::123456789012:role/MonitoringRole"
  }]
}
```

### Step 3: Run with Role Assumption

```bash
python main.py --role-arn arn:aws:iam::123456789012:role/MonitoringRole
```

Done! The application now uses temporary credentials with full monitoring permissions.

## Verification

Check the console output:
```
INFO - Starting AWS Monitor with role assumption
INFO - Profile: monitor
INFO - Role ARN: arn:aws:iam::123456789012:role/MonitoringRole
INFO - Session Name: AWSMonitorSession
INFO - Assuming role: arn:aws:iam::123456789012:role/MonitoringRole
INFO - Successfully assumed role
INFO - Session expires at: 2024-01-28T13:53:00Z
```

## Cross-Account Setup

To monitor resources in **another AWS account**:

**In Target Account (222222222222):**
1. Create role with trust policy allowing your base account
2. Attach monitoring permissions

```json
{
  "Effect": "Allow",
  "Principal": {
    "AWS": "arn:aws:iam::111111111111:root"
  },
  "Action": "sts:AssumeRole"
}
```

**In Base Account (111111111111):**
Allow assuming the cross-account role:
```json
{
  "Effect": "Allow",
  "Action": "sts:AssumeRole",
  "Resource": "arn:aws:iam::222222222222:role/MonitoringRole"
}
```

**Run:**
```bash
python main.py --role-arn arn:aws:iam::222222222222:role/MonitoringRole
```

## Common Issues

### Issue: "User is not authorized to perform: sts:AssumeRole"

**Fix:** Add policy to base user allowing AssumeRole on the target role.

### Issue: "Access Denied" 

**Fix:** Check role's trust policy allows your user/account.

### Issue: "Credentials expired"

**Fix:** Restart the application (credentials last 1 hour).

## Test It

```bash
# Test assuming role with AWS CLI
aws sts assume-role \
  --role-arn arn:aws:iam::123456789012:role/MonitoringRole \
  --role-session-name test \
  --profile monitor
```

If this works, the application will work too!

## Why Use This?

✅ **Security**: Temporary credentials that expire  
✅ **Least Privilege**: Base profile has minimal permissions  
✅ **Cross-Account**: Monitor resources in any AWS account  
✅ **Audit**: All actions tracked under assumed role  
✅ **Compliance**: Separate authentication from authorization  

## Full Documentation

See `docs/ROLE_ASSUMPTION.md` for complete guide with examples, architectures, and troubleshooting.
