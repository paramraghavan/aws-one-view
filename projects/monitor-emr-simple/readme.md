# EMR Monitor - Setup and Usage Guide

## Requirements

### Python Dependencies (requirements.txt)
```
Flask==2.3.3
PyYAML==6.0.1
requests==2.31.0
```

## File Structure
```
emr_monitor/
├── app.py                 # Main Flask application
├── emr_config.yaml        # EMR cluster configuration
├── templates/
│   └── index.html        # Web interface template
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Installation and Setup

### 1. Create Project Directory
```bash
mkdir emr_monitor
cd emr_monitor
```

### 2. Create Virtual Environment (Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Create Configuration File
Create `emr_config.yaml` with your EMR clusters:

```yaml
production:
  name: "Production EMR"
  spark_url: "http://production-master:18080"
  yarn_url: "http://production-master:8088"
  description: "Production EMR cluster"

dev-cluster:
  name: "Development EMR"
  spark_url: "http://dev-master:18080"
  yarn_url: "http://dev-master:8088"
  description: "Development EMR cluster for testing"

staging:
  name: "Staging EMR"
  spark_url: "http://staging-master:18080"
  yarn_url: "http://staging-master:8088"
  description: "Staging environment for testing"
```

### 5. Create Templates Directory
```bash
mkdir templates
```
Place the `index.html` file in the `templates/` directory.

### 6. Run the Application
```bash
python app.py
```

The application will start on `http://localhost:5000`

## Features

### 🔍 **Real-time Monitoring**
- **Cluster Overview**: View cluster state, Resource Manager version, and start time
- **Resource Usage**: Monitor memory and CPU utilization with visual progress bars
- **Node Status**: Track running, lost, unhealthy, and decommissioned nodes

### 🚀 **Application Monitoring**
- **Active Applications**: View currently running YARN applications
- **Long Running Jobs**: Identify Spark jobs running longer than 2 hours
- **Recent Spark Applications**: Monitor recently completed and failed Spark jobs

### 📊 **Key Metrics**
- Memory usage percentage and absolute values
- CPU core utilization
- Application counts by state
- Node health summary

### 🔄 **Auto-refresh**
- Automatic data refresh every 30 seconds
- Manual refresh button for immediate updates
- Real-time timestamp display

## API Endpoints

### Get Cluster List
```
GET /api/clusters
```

### Get Cluster Status
```
GET /api/cluster/<cluster_id>/status
```

### Refresh Cluster Data
```
GET /api/cluster/<cluster_id>/refresh
```

## Configuration Options

### EMR Config File Format
```yaml
<cluster_id>:
  name: "<Display Name>"
  spark_url: "<Spark History Server URL>"
  yarn_url: "<YARN ResourceManager URL>"
  description: "<Optional Description>"
```

### URL Format Examples
- Spark History Server: `http://master-node:18080`
- YARN ResourceManager: `http://master-node:8088`

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Ensure EMR cluster URLs are accessible from the monitoring server
   - Check firewall rules and security groups
   - Verify Spark History Server and YARN ResourceManager are running

2. **Configuration Errors**
   - Validate YAML syntax in `emr_config.yaml`
   - Check cluster IDs match exactly
   - Ensure URLs don't have trailing slashes

3. **Performance Issues**
   - Reduce refresh interval if monitoring multiple large clusters
   - Limit application history depth in Spark configuration
   - Monitor network bandwidth usage

### Logs and Debugging
The application logs to console. To enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Considerations

- **Network Access**: Ensure monitoring server has network access to EMR clusters
- **Authentication**: Consider implementing authentication for production use
- **HTTPS**: Use HTTPS in production environments
- **Firewall**: Configure appropriate firewall rules

## Customization

### Adding New Metrics
Extend the `get_cluster_status` method in `EMRMonitor` class to include additional metrics from Spark or YARN APIs.

### UI Customization
Modify the HTML template and CSS styles in `templates/index.html` to customize the appearance.

### Alert Integration
Add webhook or email notifications for critical thresholds:

```python
def check_alerts(self, status):
    if status['resources']['memory']['usage_percent'] > 90:
        self.send_alert("High memory usage detected")
```

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

### Environment Variables
Set environment variables for production:
```bash
export FLASK_ENV=production
export EMR_CONFIG_PATH=/path/to/emr_config.yaml
```

## Monitoring Best Practices

1. **Set Up Alerts**: Configure alerts for high resource usage (>80%)
2. **Regular Maintenance**: Clean up old Spark application logs periodically
3. **Capacity Planning**: Monitor trends to predict capacity needs
4. **Job Optimization**: Use long-running job reports to identify optimization opportunities

## Contributing

To extend functionality:
1. Fork the project
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

This project is open source and available under the MIT License.