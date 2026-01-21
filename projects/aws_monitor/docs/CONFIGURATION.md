# Configuration Guide

## Environment Variables

Configure the application using environment variables:

### AWS Credentials

```bash
# Required
export AWS_ACCESS_KEY_ID="your-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-secret-access-key"

# Optional (default: us-east-1)
export AWS_DEFAULT_REGION="us-east-1"
```

### Application Settings

```bash
# Enable debug mode (default: false)
export DEBUG=true

# Secret key for Flask (required in production)
export SECRET_KEY="your-secret-key-here"

# Flask environment (development or production)
export FLASK_ENV=production
```

## Configuration File

Edit `app/config.py` to customize thresholds and settings:

```python
class Config:
    # CloudWatch Metrics
    METRICS_PERIOD_SECONDS = 3600    # 1 hour intervals
    DEFAULT_METRIC_HOURS = 24         # 24 hours of data
    
    # Cost Analysis
    DEFAULT_COST_DAYS = 30            # 30 days of cost data
    
    # Bottleneck Detection
    CPU_HIGH_THRESHOLD = 80.0         # Alert when CPU > 80%
    CPU_CRITICAL_THRESHOLD = 90.0     # Critical when CPU > 90%
    CPU_LOW_THRESHOLD = 10.0          # Underutilized when CPU < 10%
```

## IAM Permissions

Create an IAM user with the policy in `docs/iam-policy.json`:

### Using AWS CLI

```bash
# Create policy
aws iam create-policy \
  --policy-name AWSResourceMonitorPolicy \
  --policy-document file://docs/iam-policy.json

# Attach to user
aws iam attach-user-policy \
  --user-name your-username \
  --policy-arn arn:aws:iam::ACCOUNT-ID:policy/AWSResourceMonitorPolicy
```

### Using AWS Console

1. Go to IAM → Policies → Create Policy
2. Select JSON tab
3. Paste contents from `docs/iam-policy.json`
4. Name it "AWSResourceMonitorPolicy"
5. Attach to your IAM user

## Credentials Configuration Methods

### Method 1: AWS CLI (Recommended)

```bash
aws configure
```

This creates `~/.aws/credentials` and `~/.aws/config`.

### Method 2: Environment Variables

```bash
export AWS_ACCESS_KEY_ID="xxx"
export AWS_SECRET_ACCESS_KEY="yyy"
export AWS_DEFAULT_REGION="us-east-1"
```

### Method 3: IAM Role (For EC2/ECS)

When running on AWS infrastructure, attach an IAM role with the required permissions. No credentials needed.

### Method 4: Credentials File

Create `~/.aws/credentials`:

```ini
[default]
aws_access_key_id = YOUR_ACCESS_KEY
aws_secret_access_key = YOUR_SECRET_KEY
```

And `~/.aws/config`:

```ini
[default]
region = us-east-1
```

## Production Deployment

### Using Gunicorn

```bash
pip install gunicorn
export FLASK_ENV=production
export SECRET_KEY="change-this-to-a-random-string"
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

### Using Docker

```bash
docker build -t aws-monitor .
docker run -d -p 5000:5000 \
  -e AWS_ACCESS_KEY_ID="xxx" \
  -e AWS_SECRET_ACCESS_KEY="yyy" \
  -e SECRET_KEY="xxx" \
  aws-monitor
```

## Security Best Practices

1. **Never commit credentials** to version control
2. **Use IAM roles** when running on AWS
3. **Rotate keys regularly** (90 days)
4. **Use least privilege** - only grant required permissions
5. **Enable MFA** for IAM users
6. **Use environment variables** instead of hardcoding
7. **Set SECRET_KEY** in production
8. **Use HTTPS** with a reverse proxy (nginx/Apache)

## Troubleshooting

### Credentials Not Found

```bash
# Check if credentials are configured
aws sts get-caller-identity

# Test with Python
python3 -c "import boto3; print(boto3.client('sts').get_caller_identity())"
```

### Permission Denied

Check that your IAM user/role has all required permissions from `docs/iam-policy.json`.

### Cost Explorer Access

Cost Explorer must be enabled in AWS Console and requires explicit permissions.
