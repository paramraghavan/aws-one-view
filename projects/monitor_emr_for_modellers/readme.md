# EMR Monitoring Tool - Setup Guide

## Overview
This EMR monitoring tool helps data scientists and modellers monitor their Spark jobs running on EMR clusters. It identifies resource-hogging jobs, tracks running applications, and provides insights into cluster utilization.

## Features
- **Multi-cluster monitoring** - Monitor multiple EMR clusters from a single dashboard
- **Real-time job tracking** - View running, completed, and failed Spark applications
- **Resource utilization** - Track memory, CPU cores, and cluster metrics
- **Problematic job detection** - Automatically identify jobs that may be hogging resources
- **Job duration tracking** - Monitor long-running jobs that might need attention
- **User preferences** - Pin favorite clusters for quick access
- **Auto-refresh** - Optional automatic data refresh every 30 seconds

## Installation

### Prerequisites
- Python 3.7+
- Access to EMR cluster Spark History Server and YARN Resource Manager endpoints
- Network connectivity to EMR master nodes

### Setup Steps

1. **Clone or create the project structure:**
```bash
mkdir emr-monitor
cd emr-monitor
```

2. **Install Python dependencies:**
```bash
pip install flask flask-cors requests pyyaml
```

3. **Create the Flask application file:**
Save the Flask backend code as `app.py`

4. **Create the HTML template directory:**
```bash
mkdir templates
```
Save the HTML frontend code as `templates/index.html`

5. **Create configuration file:**
Create `config.yaml` with your EMR cluster details:
```yaml
staging:
  name: "Staging EMR"
  spark_url: "http://your-staging-master:18080"
  yarn_url: "http://your-staging-master:8088"
  description: "Staging EMR cluster"
```

6. **Run the application:**
```bash
python app.py
```

7. **Access the dashboard:**
Open your browser to `http://localhost:5000`

## Configuration

### Cluster Configuration
Edit `config.yaml` to add your EMR clusters:

```yaml
cluster_name:
  name: "Display Name"
  spark_url: "http://master-node:18080"
  yarn_url: "http://master-node:8088"
  description: "Cluster description"
```

### Required EMR Endpoints
The tool requires access to these EMR services:
- **Spark History Server**: Usually port 18080
- **YARN Resource Manager**: Usually port 8088

### Network Access
Ensure the server running this tool can access:
- EMR master nodes on ports 18080 and 8088
- Internet access for CDN resources (Font Awesome, etc.)

## Usage

### Monitoring Jobs
1. **Select a cluster** - Click on a cluster card to start monitoring
2. **View running jobs** - See currently active Spark applications
3. **Check problematic jobs** - Review jobs that might be causing issues
4. **Monitor resources** - Track cluster memory and CPU utilization

### Identifying Problem Jobs
The tool automatically identifies jobs with these issues:
- **Long-running jobs** - Applications running for more than 1 hour
- **Resource hogging** - High resource allocation with no active tasks
- **Failed executors** - Jobs with blacklisted or failed executors
- **Zombie contexts** - Completed jobs that haven't released Spark contexts

### User Features
- **Pin clusters** - Click the pin icon to mark frequently used clusters
- **Auto-refresh** - Toggle automatic data refresh
- **Real-time updates** - Manual refresh button for immediate updates

## API Endpoints

### Cluster Management
- `GET /api/clusters` - List all configured clusters
- `GET /api/pinned-clusters` - Get user's pinned clusters
- `POST /api/pin-cluster` - Pin a cluster
- `POST /api/unpin-cluster` - Unpin a cluster

### Monitoring Data
- `GET /api/cluster/<id>/spark-apps` - Get Spark applications
- `GET /api/cluster/<id>/yarn-apps` - Get YARN applications
- `GET /api/cluster/<id>/metrics` - Get cluster metrics
- `GET /api/cluster/<id>/problematic-jobs` - Get problematic jobs

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Verify EMR master node addresses
   - Check network connectivity
   - Ensure ports 18080 and 8088 are accessible

2. **No Data Displayed**
   - Check EMR cluster is running
   - Verify Spark History Server is enabled
   - Confirm YARN Resource Manager is accessible

3. **Incorrect Metrics**
   - EMR clusters may take time to update metrics
   - Try refreshing data manually
   - Check if applications are actually running

### Security Considerations
- The tool makes HTTP requests to EMR endpoints
- Consider running behind a VPN for production use
- Implement authentication if needed for sensitive environments

## Customization

### Adding New Metrics
Extend the `get_cluster_metrics()` method to include additional YARN or Spark metrics.

### Custom Job Detection Rules
Modify the `identify_problematic_jobs()` method to add custom logic for detecting issues.

### UI Customization
Edit the HTML template to customize colors, layout, or add new features.

## Production Deployment

### Using Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Using Docker
Create a `Dockerfile`:
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
Consider using environment variables for sensitive configuration:
```python
import os
spark_url = os.getenv('SPARK_URL', 'http://localhost:18080')
```
