# EMR Cluster Monitor

A comprehensive Flask-based web application for monitoring Amazon EMR clusters through Spark History Server and YARN ResourceManager APIs.

## Features

- **Real-time Monitoring**: Monitor multiple EMR clusters simultaneously
- **Resource Tracking**: Track memory, CPU, and application usage
- **Application Analysis**: Identify long-running, failed, and resource-heavy applications
- **Node Health**: Monitor cluster node status and health
- **Smart Alerts**: Get recommendations and alerts for optimization
- **Responsive UI**: Modern, mobile-friendly dashboard
- **Caching**: Efficient data caching to reduce API calls
- **Authentication**: Support for basic authentication to EMR endpoints

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   Flask App      │    │   EMR Cluster   │
│                 │◄──►│                  │◄──►│                 │
│ - Dashboard     │    │ - REST APIs      │    │ - Spark History │
│ - Auto-refresh  │    │ - Data Caching   │    │ - YARN RM       │
│ - Cluster Select│    │ - Authentication │    │ - Node Status   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Prerequisites

- Python 3.7 or higher
- Network access to EMR cluster endpoints
- EMR clusters with accessible Spark History Server (port 18080) and YARN ResourceManager (port 8088)

## Installation

### 1. Clone or Download the Project

```bash
mkdir emr-monitor
cd emr-monitor
```

### 2. Create Project Structure

```
emr-monitor/
├── app.py                 # Main Flask application
├── emr_config.yaml       # EMR cluster configuration
├── requirements.txt      # Python dependencies
├── templates/
│   └── dashboard.html    # HTML template
├── static/              # Optional static files
└── README.md           # This file
```

### 3. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 4. Configure EMR Clusters

Create `emr_config.yaml` with your cluster details:

```yaml
production:
  name: "Production EMR"
  spark_url: "http://your-production-master:18080"
  yarn_url: "http://your-production-master:8088"
  description: "Production EMR cluster"
  auth:
    type: "none"  # or "basic"
  thresholds:
    max_long_running_hours: 4
    max_memory_gb: 500
    max_failed_apps: 10
    min_healthy_nodes_percent: 90
  tags:
    environment: "production"
    team: "data-engineering"

dev-cluster:
  name: "Development EMR"
  spark_url: "http://your-dev-master:18080"
  yarn_url: "http://your-dev-master:8088"
  description: "Development EMR cluster"
  auth:
    type: "basic"
    username: "admin"
    password: "password"
  thresholds:
    max_long_running_hours: 2
    max_memory_gb: 100
    max_failed_apps: 5
    min_healthy_nodes_percent: 80
  tags:
    environment: "development"
```

### 5. Create Templates Directory

```bash
mkdir templates
# Save dashboard.html in the templates directory
```

## Usage

### Running the Application

```bash
# Start the Flask development server
python app.py
```

The application will be available at `http://localhost:5000`

### Using the Dashboard

1. **Select Cluster**: Choose an EMR cluster from the dropdown
2. **Monitor Resources**: View real-time resource usage and application status
3. **Review Alerts**: Check recommendations and alerts for optimization
4. **Auto-refresh**: Enable automatic data refresh every 30 seconds
5. **Application Details**: Click on applications to view detailed information

### API Endpoints

The application provides REST API endpoints for programmatic access:

| Endpoint | Description |
|----------|-------------|
| `GET /api/clusters` | List all configured clusters |
| `GET /api/monitor/{cluster_id}` | Get complete monitoring data |
| `GET /api/spark/{cluster_id}` | Get Spark applications |
| `GET /api/yarn/{cluster_id}` | Get YARN applications |
| `GET /api/nodes/{cluster_id}` | Get cluster nodes |
| `GET /api/health` | Application health check |

### Example API Usage

```bash
# Get all clusters
curl http://localhost:5000/api/clusters

# Monitor specific cluster
curl http://localhost:5000/api/monitor/production

# Get YARN applications
curl http://localhost:5000/api/yarn/dev-cluster
```

## Configuration Options

### Authentication

Support for different authentication methods:

```yaml
auth:
  type: "none"        # No authentication
  # OR
  type: "basic"       # Basic authentication
  username: "admin"
  password: "password"
```

### Thresholds

Configure alert thresholds:

```yaml
thresholds:
  max_long_running_hours: 4      # Alert for apps running > 4 hours
  max_memory_gb: 500             # Alert for memory usage > 500GB
  max_failed_apps: 10            # Alert for > 10 failed apps
  min_healthy_nodes_percent: 90  # Alert if < 90% nodes healthy
```

### Tags

Organize clusters with tags:

```yaml
tags:
  environment: "production"
  team: "data-engineering"
  cost_center: "engineering"
```

## Monitoring Capabilities

### Application Monitoring

- **Running Applications**: Track active Spark and YARN applications
- **Resource Usage**: Monitor memory and CPU allocation
- **Duration Tracking**: Identify long-running applications
- **Failure Analysis**: Track failed applications and reasons

### Cluster Health

- **Node Status**: Monitor RUNNING, LOST, UNHEALTHY, DECOMMISSIONED nodes
- **Resource Utilization**: Track cluster-wide memory and CPU usage
- **Capacity Planning**: Monitor available vs. used resources

### Alerts and Recommendations

- **Performance Alerts**: Long-running applications, resource bottlenecks
- **Health Alerts**: Node failures, cluster issues
- **Optimization Recommendations**: Resource optimization suggestions

## Production Deployment

### Using Gunicorn

```bash
# Install Gunicorn
pip install gunicorn

# Run with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# With additional options
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --keep-alive 2 app:app
```

### Using Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

Build and run:

```bash
docker build -t emr-monitor .
docker run -p 5000:5000 -v $(pwd)/emr_config.yaml:/app/emr_config.yaml emr-monitor
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   - Ensure EMR cluster endpoints are accessible
   - Check security groups and network ACLs
   - Verify ports 18080 and 8088 are open

2. **Authentication Errors**
   - Verify username/password in configuration
   - Check EMR cluster authentication settings

3. **Data Not Loading**
   - Check EMR cluster status
   - Verify Spark History Server and YARN RM are running
   - Check application logs for errors

4. **Performance Issues**
   - Increase cache duration for less frequent updates
   - Limit number of applications fetched
   - Use pagination for large datasets

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check logs:

```bash
tail -f /var/log/emr-monitor.log
```

### Network Connectivity

Test connectivity to EMR endpoints:

```bash
# Test Spark History Server
curl http://your-emr-master:18080/api/v1/applications

# Test YARN ResourceManager
curl http://your-emr-master:8088/ws/v1/cluster/apps
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

1. Check the troubleshooting section
2. Review the logs for error messages
3. Ensure EMR clusters are accessible
4. Verify configuration file syntax

## Roadmap

- [ ] Email/Slack alerts for critical issues
- [ ] Historical data storage and trending
- [ ] Custom dashboard widgets
- [ ] Export data to CSV/JSON
- [ ] Integration with monitoring systems (Prometheus, Grafana)
- [ ] Support for Kerberos authentication
- [ ] Mobile app companion