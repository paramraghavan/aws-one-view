# Maintenance Guide

This guide helps you maintain and extend the AWS Resource Monitor.

## Code Organization

### File Structure
```
aws_monitor/
├── main.py                 # Flask app and API endpoints
├── app/
│   ├── aws_client.py       # AWS API operations
│   └── config.py           # Configuration settings
├── templates/
│   └── index.html          # Web interface
├── static/
│   ├── css/style.css       # Styles
│   └── js/app.js           # Frontend logic
├── tests/
│   └── test_connection.py  # Connection testing
└── docs/                   # Documentation
```

### Key Components

1. **main.py**: Flask routes - add new endpoints here
2. **aws_client.py**: AWS operations - add new resource types here
3. **config.py**: Settings - modify thresholds here
4. **index.html**: UI structure - add new sections here
5. **app.js**: Frontend logic - add new interactions here

## Common Tasks

### Adding a New Resource Type

**Example: Adding DynamoDB support**

#### 1. Update Backend (`app/aws_client.py`)

```python
# Add to get_all_resources()
resources['dynamodb'] = []

for region in regions:
    resources['dynamodb'].extend(self._get_dynamodb_tables(region))

# Add discovery method
def _get_dynamodb_tables(self, region: str) -> List[Dict[str, Any]]:
    """Get all DynamoDB tables in a region."""
    try:
        dynamodb = self.session.client('dynamodb', region_name=region)
        response = dynamodb.list_tables()
        
        tables = []
        for table_name in response['TableNames']:
            table_info = dynamodb.describe_table(TableName=table_name)
            tables.append({
                'id': table_name,
                'status': table_info['Table']['TableStatus'],
                'region': region
            })
        
        return tables
    except Exception as e:
        logger.error(f"Error getting DynamoDB tables in {region}: {e}")
        return []
```

#### 2. Update Frontend (`templates/index.html`)

```html
<!-- Add tab -->
<button class="tab-btn" data-type="dynamodb">DynamoDB</button>
```

#### 3. Update Frontend Logic (`static/js/app.js`)

```javascript
// Add to getColumnsForResourceType()
case 'dynamodb':
    return ['Table Name', 'Status', 'Region'];

// Add to getRowContentForResource()
case 'dynamodb':
    html += '<td>' + resource.id + '</td>';
    html += '<td>' + resource.status + '</td>';
    html += '<td>' + resource.region + '</td>';
    break;
```

### Modifying Thresholds

Edit `app/config.py`:

```python
class Config:
    CPU_HIGH_THRESHOLD = 80.0      # Change to 70.0 for stricter
    CPU_CRITICAL_THRESHOLD = 90.0  # Change to 85.0 for stricter
    CPU_LOW_THRESHOLD = 10.0       # Change to 15.0 for stricter
```

### Adding New Metrics

Add to `app/aws_client.py`:

```python
def _get_ec2_metrics(self, cloudwatch, instance_id, start_time, end_time):
    # Existing CPU metrics...
    
    # Add network metrics
    network = cloudwatch.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='NetworkIn',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=start_time,
        EndTime=end_time,
        Period=Config.METRICS_PERIOD_SECONDS,
        Statistics=['Sum']
    )
    
    return {
        'cpu': ...,
        'network': sorted(network['Datapoints'], key=lambda x: x['Timestamp'])
    }
```

### Customizing the UI

Edit `static/css/style.css`:

```css
/* Change color scheme */
.btn-primary {
    background: #4285f4;  /* Change primary color */
}

body {
    background: linear-gradient(135deg, #4285f4 0%, #34a853 100%);
}
```

## Testing

### Run Connection Test

```bash
python tests/test_connection.py
```

### Manual Testing Checklist

- [ ] Load regions successfully
- [ ] Load resources from multiple regions
- [ ] View each resource type tab
- [ ] Select resources and load metrics
- [ ] Load cost data
- [ ] Detect bottlenecks
- [ ] Check for errors in browser console (F12)

### Adding Unit Tests

Create `tests/test_aws_client.py`:

```python
import unittest
from unittest.mock import Mock, patch
from app.aws_client import AWSClient

class TestAWSClient(unittest.TestCase):
    
    @patch('boto3.Session')
    def test_get_regions(self, mock_session):
        # Test implementation
        pass
```

## Debugging

### Enable Debug Mode

```bash
export DEBUG=true
python main.py
```

### Check Logs

Logs are printed to console. Look for:
- `ERROR` - Problems that need fixing
- `WARNING` - Things to be aware of
- `INFO` - Normal operation

### Common Issues

**"No resources found"**
- Check AWS credentials
- Verify IAM permissions
- Ensure resources exist in selected regions

**"Cost data not loading"**
- Enable Cost Explorer in AWS Console
- Add `ce:GetCostAndUsage` permission
- Wait 24 hours for data to appear

**"High CPU not detected"**
- Check CloudWatch has data for instances
- Verify instances have been running >1 hour
- Check thresholds in config.py

## Performance Optimization

### For Large Accounts (1000+ resources)

1. **Add Caching**:
```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_all_resources(self, regions_tuple):
    # Convert tuple back to list
    regions = list(regions_tuple)
    # ... existing code
```

2. **Add Pagination**: Limit results per page

3. **Async Loading**: Use JavaScript to load resources asynchronously

### Reducing API Calls

```python
# In config.py
class Config:
    METRICS_PERIOD_SECONDS = 7200  # 2 hours instead of 1
```

## Upgrading Dependencies

```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade flask

# Update all
pip install --upgrade -r requirements.txt

# Test after upgrading
python tests/test_connection.py
```

## Security Maintenance

### Regular Tasks

1. **Rotate credentials** every 90 days
2. **Review IAM permissions** quarterly
3. **Update dependencies** monthly
4. **Check security advisories** weekly

### Security Checklist

- [ ] No credentials in code
- [ ] Environment variables used
- [ ] Secret key set in production
- [ ] HTTPS enabled (via reverse proxy)
- [ ] IAM least privilege applied
- [ ] MFA enabled for AWS accounts

## Code Quality

### Best Practices

1. **Follow PEP 8** for Python code
2. **Use type hints** for functions
3. **Add docstrings** to new methods
4. **Comment complex logic**
5. **Keep functions small** (<50 lines)
6. **Use meaningful names** for variables

### Code Review Checklist

- [ ] Code is readable and clear
- [ ] Functions have docstrings
- [ ] Error handling is present
- [ ] No hardcoded values
- [ ] Logging statements added
- [ ] No credentials in code

## Deployment

### Update Production

```bash
# 1. Test locally first
./run.sh

# 2. Update server
git pull
pip install -r requirements.txt

# 3. Restart service
sudo systemctl restart aws-monitor
```

### Rollback Plan

```bash
# Keep previous version
git tag v1.0.0

# Rollback if needed
git checkout v1.0.0
pip install -r requirements.txt
sudo systemctl restart aws-monitor
```

## Backup

### What to Backup

1. Configuration files (`.env`, custom configs)
2. Custom modifications to code
3. Documentation updates

### What NOT to Backup

- Virtual environment (`venv/`)
- Cache files (`__pycache__/`)
- AWS credentials (store securely elsewhere)

## Getting Help

### Resources

- AWS Documentation: https://docs.aws.amazon.com/
- Boto3 Docs: https://boto3.amazonaws.com/v1/documentation/api/latest/index.html
- Flask Docs: https://flask.palletsprojects.com/

### Contact

- Check application logs first
- Review this guide
- Check GitHub issues (if applicable)
