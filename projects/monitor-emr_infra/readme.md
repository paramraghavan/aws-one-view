# EMR Cluster Monitor

A Flask-based web application for monitoring AWS EMR (Elastic MapReduce) clusters in real-time. This tool provides
infrastructure teams with a simple, unified dashboard to monitor cluster health, resource usage, and job status across
multiple EMR environments.

## Features

- **Real-time Monitoring**: Auto-refreshes every 30 seconds
- **Multi-Cluster Support**: Monitor multiple EMR clusters from a single dashboard
- **Spark History Server Integration**: Track completed and failed Spark jobs
- **YARN ResourceManager Integration**: Monitor running applications and resource utilization
- **Node Health Tracking**: Monitor node status (RUNNING, LOST, UNHEALTHY, DECOMMISSIONED)
- **Threshold-based Alerting**: Configurable warning and critical thresholds for:
    - Memory usage
    - CPU usage (vCores)
    - Unhealthy nodes
- **Alert History**: Persistent storage of critical alerts using pickle files
- **Clean UI**: Color-coded status indicators for quick health assessment
- **Easy Reset**: Clear all alerts and start fresh with one click

## Project Structure

```
emr-monitor/
├── app.py                      # Flask application
├── requirements.txt            # Python dependencies
├── emr_config.yaml            # EMR cluster configuration
├── templates/
│   └── index.html             # Dashboard UI
└── critical_alerts.pkl        # Alert history (auto-generated)
```

## Installation

### 1. Prerequisites

- Python 3.8 or higher
- Access to EMR cluster Spark History Server (port 18080)
- Access to EMR cluster YARN ResourceManager (port 8088)

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Clusters

Edit `emr_config.yaml` to add your EMR clusters:

```yaml
# Threshold Configuration
memory_warning: 80
memory_critical: 90
cpu_warning: 80
cpu_critical: 90
unhealthy_nodes_warning: 1
unhealthy_nodes_critical: 3

# EMR Clusters
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
```

## Usage

### Start the Application

```bash
python app.py
```

The application will start on `http://localhost:5000`

### Access the Dashboard

Open your browser and navigate to:

```
http://localhost:5000
```

### Dashboard Features

**Cluster Cards**: Each cluster is displayed in a card showing:

- Overall status (Healthy, Warning, Critical, Offline)
- Memory usage with visual indicators
- CPU usage (vCore utilization)
- Running applications count
- Node health status
- Spark job statistics
- Critical alert counter

**Alert History Table**: Shows all critical threshold violations with:

- Timestamp
- Cluster name
- Alert type (Memory, CPU, Unhealthy Nodes)
- Actual value vs threshold
- Severity level

**Clear Alerts Button**: Resets all alerts and deletes the pickle file to start fresh

## Configuration

### Threshold Customization

Modify thresholds in `emr_config.yaml`:

```yaml
memory_warning: 80          # 80% memory triggers warning (yellow)
memory_critical: 90         # 90% memory triggers critical (red)
cpu_warning: 80             # 80% CPU triggers warning
cpu_critical: 90            # 90% CPU triggers critical
unhealthy_nodes_warning: 1  # 1 unhealthy node triggers warning
unhealthy_nodes_critical: 3 # 3 unhealthy nodes trigger critical
```

### Adding New Clusters

Add a new cluster section in `emr_config.yaml`:

```yaml
staging:
  name: "Staging EMR"
  spark_url: "http://staging-master:18080"
  yarn_url: "http://staging-master:8088"
  description: "Staging environment cluster"
```

## API Endpoints

- `GET /`: Main dashboard
- `GET /api/clusters`: Returns all cluster metrics (JSON)
- `GET /api/alerts`: Returns alert history (JSON)
- `POST /api/clear_alerts`: Clears all alerts

## Monitoring Details

### Spark History Server Metrics

- Completed jobs count
- Failed jobs count
- Connection status

### YARN ResourceManager Metrics

- Memory usage (total, used, available in GB)
- vCore usage (CPU resources)
- Application states (Running, Accepted, Submitted)
- Node status counts
- Node health status

### Critical Alert Triggers

Alerts are logged when any of these conditions are met:

- Memory usage ≥ critical threshold
- CPU usage ≥ critical threshold
- Unhealthy nodes ≥ critical threshold

## Troubleshooting

### Cluster Shows as Offline

- Verify the Spark URL and YARN URL are accessible
- Check network connectivity to EMR master nodes
- Ensure ports 18080 (Spark) and 8088 (YARN) are open

### No Metrics Displayed

- Check EMR cluster is running
- Verify Spark History Server is enabled
- Ensure YARN ResourceManager API is accessible

### Alerts Not Saving

- Check write permissions in the application directory
- Verify `critical_alerts.pkl` can be created/modified

## Security Considerations

- This application does not include authentication
- For production use, add authentication (e.g., Flask-Login, OAuth)
- Use HTTPS in production environments
- Restrict network access to EMR ports
- Consider using environment variables for sensitive URLs

## Customization

### Auto-refresh Interval

Modify the interval in `templates/index.html`:

```javascript
// Change 30000 (30 seconds) to desired milliseconds
refreshInterval = setInterval(fetchData, 30000);
```

### Status Colors

Modify CSS classes in `templates/index.html`:

```css
.status-healthy { background: #2ecc71; }
.status-warning { background: #f39c12; }
.status-critical { background: #e74c3c; }
```

## Production Deployment

For production use:

1. Use a production WSGI server (Gunicorn, uWSGI):
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 app:app
   ```

2. Set up reverse proxy (Nginx, Apache)

3. Enable SSL/TLS

4. Add authentication and authorization

5. Use environment variables for configuration

6. Set up log rotation and monitoring
