# EMR Job Resource Monitor

A web-based monitoring solution for Amazon EMR clusters that provides real-time insights into job
performance, resource utilization, and cost analysis.

## Features

### 🚀 Core Capabilities

- **Multi-Environment Support**: Monitor multiple EMR clusters from a single interface
- **Real-Time Monitoring**: Live tracking of running jobs with progress indicators
- **Historical Analysis**: Detailed analysis of completed jobs with efficiency metrics
- **Resource Optimization**: Intelligent insights and recommendations for better resource usage
- **Cost Tracking**: Estimated cost analysis for jobs and clusters
- **Auto-Refresh**: Configurable auto-refresh for real-time updates

### 📊 Enhanced Monitoring

- **Cluster Health**: Real-time cluster status and node health monitoring
- **Job Priority**: Automatic job prioritization based on resource usage
- **Efficiency Scoring**: Performance efficiency metrics for job optimization
- **Hourly Aggregation**: Trend analysis with customizable time windows
- **Failure Analysis**: Detailed failure rate tracking and alerting

### 🎯 Smart Insights

- **Resource Optimization**: Recommendations for memory and CPU optimization
- **Cost Analysis**: Cost trends and high-cost job identification
- **Performance Trends**: Job efficiency and performance pattern analysis
- **Automated Recommendations**: AI-driven suggestions for cluster optimization

## Setup Instructions

### Prerequisites

- Python 3.7+
- Flask
- pandas
- requests
- Access to EMR cluster Spark History Server and YARN Resource Manager

### Installation

1. **Clone or download the application files:**
   ```bash
   # Create project directory
   mkdir emr-monitor
   cd emr-monitor
   
   # Copy the application files
   # - app.py
   # - templates/index.html
   # - config.json
   ```

2. **Install Python dependencies:**
   ```bash
   pip install flask pandas requests
   ```

3. **Configure your EMR environments:**

   Edit `config.json` to add your EMR cluster details:
   ```json
   {
     "environments": {
       "production": {
         "name": "Production EMR",
         "spark_url": "http://your-prod-master:18080",
         "yarn_url": "http://your-prod-master:8088",
         "description": "Production EMR cluster"
       },
       "staging": {
         "name": "Staging EMR", 
         "spark_url": "http://your-staging-master:18080",
         "yarn_url": "http://your-staging-master:8088",
         "description": "Staging EMR cluster"
       }
     },
     "settings": {
       "default_environment": "production",
       "auto_refresh_interval": 30,
       "max_completed_jobs": 200,
       "request_timeout": 10,
       "thresholds": {
         "high_memory_usage_gb": 100,
         "long_running_job_hours": 2,
         "max_failed_jobs_per_hour": 5
       }
     }
   }
   ```

4. **Create the templates directory:**
   ```bash
   mkdir templates
   # Move index.html to templates/index.html
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

6. **Access the monitoring dashboard:**
    - Open your browser to `http://localhost:5000`
    - Select your EMR environment from the dropdown
    - Start monitoring your jobs!

## Configuration Options

### Environment Settings

- **spark_url**: Spark History Server URL (typically port 18080)
- **yarn_url**: YARN Resource Manager URL (typically port 8088)
- **description**: Human-readable description for the environment

### Application Settings

- **default_environment**: Default environment to load on startup
- **auto_refresh_interval**: Auto-refresh interval in seconds
- **max_completed_jobs**: Maximum number of completed jobs to fetch
- **request_timeout**: HTTP request timeout in seconds

### Monitoring Thresholds

- **high_memory_usage_gb**: Threshold for high memory usage alerts
- **long_running_job_hours**: Threshold for long-running job detection
- **max_failed_jobs_per_hour**: Threshold for failure rate alerts

## Usage Guide

### Monitoring Tabs

1. **Running Jobs**:
    - Real-time view of active jobs
    - Progress tracking and resource usage
    - Priority-based filtering and sorting

2. **Completed Jobs**:
    - Historical job analysis
    - Efficiency scoring and cost estimation
    - Success rate and failure analysis

3. **Hourly Analysis**:
    - Resource usage trends over time
    - Peak usage identification
    - Customizable time windows (6-168 hours)

4. **Job Summary**:
    - Aggregated statistics by job name
    - Resource consumption patterns
    - Job type breakdown (running vs completed)

5. **Insights**:
    - Automated optimization recommendations
    - Cost analysis and trends
    - Performance improvement suggestions

### Advanced Features

#### Filtering & Sorting

- Filter by job name, user, status, and resource usage
- Custom sorting with ascending/descending options
- Real-time filter application

#### Data Export

- CSV export for all data views
- Timestamped filenames with environment context
- Full data export including calculated metrics

#### Alerting

- Visual alerts for cluster health issues
- Automatic detection of resource constraints
- Failure rate monitoring and notifications

## Troubleshooting

### Common Issues

1. **Connection Failed**:
    - Verify EMR cluster URLs are accessible
    - Check network connectivity and firewall rules
    - Ensure Spark History Server and YARN RM are running

2. **No Data Displayed**:
    - Confirm jobs are running or have completed recently
    - Check EMR cluster is active and processing jobs
    - Verify API endpoints are responding

3. **Performance Issues**:
    - Reduce `max_completed_jobs` in config for large clusters
    - Increase `request_timeout` for slow networks
    - Disable auto-refresh for resource-constrained environments

### API Endpoints

The application exposes these REST endpoints:

- `GET /api/environments` - List available environments
- `GET /api/cluster-metrics?environment=<env>` - Cluster health metrics
- `GET /api/running-jobs?environment=<env>` - Running jobs data
- `GET /api/completed-jobs?environment=<env>` - Completed jobs data
- `GET /api/hourly-aggregation?environment=<env>` - Hourly trends
- `GET /api/job-summary?environment=<env>` - Job summary statistics
- `GET /download/<type>?environment=<env>` - CSV data export

## Security Considerations

- Run the application behind a reverse proxy (nginx/Apache) in production
- Implement authentication/authorization for sensitive environments
- Use HTTPS for secure data transmission
- Restrict network access to EMR cluster management interfaces
- Regularly update dependencies for security patches

## Performance Optimization

- Cache frequently accessed data for improved response times
- Implement data pagination for large job datasets
- Use database storage for historical data persistence
- Consider horizontal scaling for multiple cluster monitoring

## Contributing

To extend the monitoring capabilities:

1. Add new metrics to the `AdvancedJobResourceMonitor` class
2. Create corresponding API endpoints in the Flask app
3. Update the frontend to display new metrics
4. Add configuration options for new features
