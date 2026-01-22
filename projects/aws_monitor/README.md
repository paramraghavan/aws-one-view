# AWS Resource Monitor

A clean, simple web application to monitor AWS resources, analyze costs, and detect bottlenecks with **automated background monitoring and email alerts**.

## Features

- **Resource Discovery**: View EC2, RDS, S3, Lambda, and EBS resources across multiple regions
- **Performance Monitoring**: Real-time CloudWatch metrics with visual charts
- **Cost Analysis**: Track spending with AWS Cost Explorer integration
- **Bottleneck Detection**: Automatically identify over/under-utilized resources
- **⭐ Background Monitoring**: Continuous monitoring of selected resources
- **⭐ Email Alerts**: Get notified when thresholds are exceeded

## Quick Start

### Prerequisites

- Python 3.8+
- AWS credentials with read permissions
- pip (Python package manager)
- (Optional) Email account for alerts (Gmail, SES, etc.)

### Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set AWS credentials
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-east-1"

# 3. (Optional) Enable monitoring & alerts
export MONITORING_ENABLED=true
export ALERTS_ENABLED=true
export ALERT_RECIPIENTS="your-email@example.com"
export SMTP_SERVER="smtp.gmail.com"
export SMTP_PORT=587
export SMTP_USERNAME="your-email@gmail.com"
export SMTP_PASSWORD="your-app-password"
export SMTP_FROM_EMAIL="your-email@gmail.com"

# 4. Run the application
python main.py
```

### Access

Open your browser to: **http://localhost:5000**

## Usage

1. **Select Regions** → Check the AWS regions you want to monitor
2. **Load Resources** → Click "Load Resources" to scan your infrastructure
3. **Browse** → Use tabs to view different resource types
4. **Analyze** → Select resources to view metrics and details
5. **⭐ Add to Monitoring** → Select resources and click "Add to Background Monitoring"
6. **Optimize** → Use bottleneck detection to find improvement opportunities

## Background Monitoring & Alerts

### Setup

See detailed setup guide: **[docs/ALERTS_SETUP.md](docs/ALERTS_SETUP.md)**

### Quick Setup (Gmail)

```bash
# Enable features
export MONITORING_ENABLED=true
export ALERTS_ENABLED=true

# Configure email
export ALERT_RECIPIENTS="admin@example.com"
export SMTP_USERNAME="your-gmail@gmail.com"
export SMTP_PASSWORD="your-app-password"  # Get from Google
export SMTP_FROM_EMAIL="your-gmail@gmail.com"
```

### How It Works

1. Select resources in the UI
2. Click "Add Selected to Background Monitoring"
3. Set CPU threshold (e.g., 80%)
4. Monitoring checks every 15 minutes
5. Email sent when threshold exceeded

### Example Alert

```
Subject: AWS Alert: 2 issue(s) detected

🔴 CRITICAL ISSUES:
Resource: i-1234567890 (ec2)
Issue: CPU at 95.2% (threshold: 80%)
```

## Configuration

Edit `app/config.py` to customize:

```python
CPU_HIGH_THRESHOLD = 80.0      # Alert when CPU > 80%
CPU_CRITICAL_THRESHOLD = 90.0  # Critical when CPU > 90%
CPU_LOW_THRESHOLD = 10.0       # Underutilized when CPU < 10%
```

## Project Structure

```
aws_monitor/
├── main.py              # Flask application entry point
├── app/
│   ├── aws_client.py    # AWS API integration
│   └── config.py        # Configuration settings
├── templates/
│   └── index.html       # Web interface
├── static/
│   ├── css/style.css    # Styles
│   └── js/app.js        # Frontend logic
└── requirements.txt     # Python dependencies
```

## Required AWS Permissions

The IAM user/role needs these permissions:

- `ec2:DescribeInstances`, `ec2:DescribeVolumes`, `ec2:DescribeRegions`
- `rds:DescribeDBInstances`
- `s3:ListAllMyBuckets`, `s3:GetBucketLocation`
- `lambda:ListFunctions`
- `cloudwatch:GetMetricStatistics`
- `ce:GetCostAndUsage`

See `docs/iam-policy.json` for the complete policy.

## Development

### Running in Debug Mode

```bash
export DEBUG=true
python main.py
```

### Adding New Resource Types

1. Add discovery method in `app/aws_client.py`
2. Update `get_all_resources()` to include new resource
3. Add tab in `templates/index.html`
4. Add display logic in `static/js/app.js`

## Deployment

### Docker

```bash
docker build -t aws-monitor .
docker run -p 5000:5000 \
  -e AWS_ACCESS_KEY_ID=xxx \
  -e AWS_SECRET_ACCESS_KEY=yyy \
  aws-monitor
```

### Production

Use a production WSGI server:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 main:app
```

## Troubleshooting

### No resources found

- Verify AWS credentials are configured
- Check IAM permissions
- Ensure resources exist in selected regions

### Cost data not loading

- Cost Explorer must be enabled in AWS Console
- Requires `ce:GetCostAndUsage` permission
- Data may take 24 hours to appear

### Connection errors

```bash
# Test AWS connectivity
python tests/test_connection.py
```

## Contributing

This project uses:
- **Flask** for the web framework
- **Boto3** for AWS SDK
- **Chart.js** for visualizations
- **jQuery** for DOM manipulation

## License

MIT License - See LICENSE file for details

## Support

For issues or questions:
- Check the documentation in `docs/`
- Review AWS documentation
- Check application logs for errors
