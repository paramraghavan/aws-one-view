from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import io
import csv
import os
import logging
from typing import Dict, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class ConfigManager:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Config file {self.config_file} not found. Using default config.")
                return self.get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self.get_default_config()

    def get_default_config(self) -> Dict:
        """Return default configuration if file is missing"""
        return {
            "environments": {
                "local": {
                    "name": "Local EMR",
                    "spark_url": "http://localhost:18080",
                    "yarn_url": "http://localhost:8088",
                    "description": "Local development cluster"
                }
            },
            "settings": {
                "default_environment": "local",
                "auto_refresh_interval": 30,
                "max_completed_jobs": 100,
                "request_timeout": 10,
                "thresholds": {
                    "high_memory_usage_gb": 50,
                    "long_running_job_hours": 2
                }
            }
        }

    def get_environments(self) -> Dict:
        return self.config.get('environments', {})

    def get_environment(self, env_name: str) -> Optional[Dict]:
        return self.config.get('environments', {}).get(env_name)

    def get_settings(self) -> Dict:
        return self.config.get('settings', {})


class SimplifiedJobMonitor:
    def __init__(self, spark_history_url: str, yarn_rm_url: str, config_manager: ConfigManager):
        self.spark_history_url = spark_history_url
        self.yarn_rm_url = yarn_rm_url
        self.config_manager = config_manager
        self.settings = config_manager.get_settings()

    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request with error handling"""
        try:
            timeout = self.settings.get('request_timeout', 10)
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def _safe_convert(self, value, convert_type=float, default=0):
        """Safely convert values with fallback"""
        try:
            return convert_type(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def get_cluster_metrics(self) -> Dict:
        """Get simplified cluster metrics"""
        try:
            url = f"{self.yarn_rm_url}/ws/v1/cluster/metrics"
            data = self._make_request(url)

            if not data:
                return {}

            cluster_metrics = data.get('clusterMetrics', {})
            return {
                'total_mb': cluster_metrics.get('totalMB', 0),
                'allocated_mb': cluster_metrics.get('allocatedMB', 0),
                'total_vcores': cluster_metrics.get('totalVirtualCores', 0),
                'allocated_vcores': cluster_metrics.get('allocatedVirtualCores', 0),
                'active_nodes': cluster_metrics.get('activeNodes', 0),
                'total_nodes': cluster_metrics.get('totalNodes', 0)
            }
        except Exception as e:
            logger.error(f"Error fetching cluster metrics: {e}")
            return {}

    def get_running_jobs(self) -> pd.DataFrame:
        """Get simplified running jobs data"""
        try:
            url = f"{self.yarn_rm_url}/ws/v1/cluster/apps"
            # All active states
            params = {'states': 'RUNNING,ACCEPTED,SUBMITTED'}
            data = self._make_request(url, params)

            if not data:
                return pd.DataFrame()

            apps = data.get('apps', {}).get('app', [])
            if not apps:
                return pd.DataFrame()

            running_jobs = []
            for app in apps:
                # Basic job info with safe conversions
                started_time = self._safe_convert(app.get('startedTime', 0), int)
                elapsed_time = self._safe_convert(app.get('elapsedTime', 0), int)
                allocated_mb = self._safe_convert(app.get('allocatedMB', 0), float)
                allocated_vcores = self._safe_convert(app.get('allocatedVCores', 0), int)
                progress = self._safe_convert(app.get('progress', 0), float)

                start_time = datetime.fromtimestamp(started_time / 1000) if started_time > 0 else datetime.now()
                elapsed_minutes = elapsed_time / (1000 * 60)
                memory_gb = allocated_mb / 1024

                # Simple priority calculation
                if memory_gb > 50 or allocated_vcores > 20:
                    priority = 'HIGH'
                elif memory_gb > 20 or allocated_vcores > 10:
                    priority = 'MEDIUM'
                else:
                    priority = 'LOW'

                job_info = {
                    'Job ID': app.get('id', 'Unknown'),
                    'Job Name': (app.get('name', 'Unknown') or 'Unknown')[:40],
                    'User': app.get('user', 'Unknown'),
                    'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Elapsed Time (mins)': round(elapsed_minutes, 1),
                    'Memory (GB)': round(memory_gb, 1),
                    'vCores': allocated_vcores,
                    'Progress (%)': round(progress, 1),
                    'Priority': priority,
                    'Status': 'RUNNING'
                }
                running_jobs.append(job_info)

            return pd.DataFrame(running_jobs)
        except Exception as e:
            logger.error(f"Error fetching running jobs: {e}")
            return pd.DataFrame()

    def get_completed_jobs(self, limit: int = None) -> pd.DataFrame:
        """Get simplified completed jobs data"""
        if limit is None:
            limit = self.settings.get('max_completed_jobs', 100)

        try:
            url = f"{self.spark_history_url}/api/v1/applications"
            params = {'limit': limit}
            data = self._make_request(url, params)

            if not data:
                return pd.DataFrame()

            completed_jobs = []
            for app in data:
                try:
                    app_id = app['id']

                    # Get basic executor info
                    executors_url = f"{self.spark_history_url}/api/v1/applications/{app_id}/executors"
                    executors_data = self._make_request(executors_url)

                    total_cores = 0
                    max_memory_mb = 0

                    if executors_data:
                        for executor in executors_data:
                            total_cores += self._safe_convert(executor.get('totalCores', 0), int)
                            memory_bytes = self._safe_convert(executor.get('maxMemory', 0), int)
                            max_memory_mb += memory_bytes // (1024 * 1024)

                    # Time calculations
                    attempts = app.get('attempts', [{}])
                    if attempts:
                        first_attempt = attempts[0]
                        start_time_ms = self._safe_convert(first_attempt.get('startTime', 0), int)
                        end_time_ms = self._safe_convert(first_attempt.get('endTime', 0), int)
                        duration_ms = self._safe_convert(first_attempt.get('duration', 0), int)

                        start_time = datetime.fromtimestamp(start_time_ms / 1000) if start_time_ms > 0 else None
                        end_time = datetime.fromtimestamp(end_time_ms / 1000) if end_time_ms > 0 else None
                        duration_minutes = duration_ms / (1000 * 60) if duration_ms > 0 else 0
                        duration_hours = duration_ms / (1000 * 60 * 60) if duration_ms > 0 else 0

                        memory_gb = max_memory_mb / 1024
                        status = 'COMPLETED' if first_attempt.get('completed', False) else 'FAILED'

                        # Simple cost calculation ($0.05 per GB-hour + $0.10 per vCore-hour)
                        cost = (memory_gb * 0.05 + total_cores * 0.10) * duration_hours

                        job_info = {
                            'Job ID': app_id,
                            'Job Name': (app.get('name', 'Unknown') or 'Unknown')[:40],
                            'User': app.get('sparkUser', 'Unknown'),
                            'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'Unknown',
                            'End Time': end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'Unknown',
                            'Duration (mins)': round(duration_minutes, 1),
                            'Memory (GB)': round(memory_gb, 1),
                            'vCores': total_cores,
                            'Status': status,
                            'Cost Estimate': f"${cost:.2f}" if cost > 0 else '$0.00'
                        }
                        completed_jobs.append(job_info)

                except Exception as e:
                    logger.warning(f"Error processing job {app.get('id', 'unknown')}: {e}")
                    continue

            return pd.DataFrame(completed_jobs)
        except Exception as e:
            logger.error(f"Error fetching completed jobs: {e}")
            return pd.DataFrame()

    def get_job_summary(self) -> pd.DataFrame:
        """Get simplified job summary"""
        try:
            # Get both running and completed jobs
            running_df = self.get_running_jobs()
            completed_df = self.get_completed_jobs()

            all_jobs = []

            # Add running jobs
            if not running_df.empty:
                running_summary = running_df.copy()
                running_summary['Job Type'] = 'RUNNING'
                if 'Duration (mins)' not in running_summary.columns:
                    running_summary['Duration (mins)'] = running_summary.get('Elapsed Time (mins)', 0)
                if 'Cost Estimate' not in running_summary.columns:
                    running_summary['Cost Estimate'] = '$0.00'
                all_jobs.append(running_summary)

            # Add completed jobs
            if not completed_df.empty:
                completed_summary = completed_df.copy()
                completed_summary['Job Type'] = 'COMPLETED'
                if 'Elapsed Time (mins)' not in completed_summary.columns:
                    completed_summary['Elapsed Time (mins)'] = completed_summary.get('Duration (mins)', 0)
                if 'Progress (%)' not in completed_summary.columns:
                    completed_summary['Progress (%)'] = 100.0
                if 'Priority' not in completed_summary.columns:
                    completed_summary['Priority'] = 'MEDIUM'
                all_jobs.append(completed_summary)

            if not all_jobs:
                return pd.DataFrame()

            # Combine data
            combined_df = pd.concat(all_jobs, ignore_index=True, sort=False)

            # Clean job names
            combined_df = combined_df[combined_df['Job Name'].notna()]
            combined_df = combined_df[combined_df['Job Name'] != 'Unknown']

            if combined_df.empty:
                return pd.DataFrame()

            # Convert cost to numeric for aggregation
            combined_df['Cost_Numeric'] = (
                combined_df['Cost Estimate']
                .str.replace('$', '', regex=False)
                .astype(float, errors='coerce')
                .fillna(0)
            )

            # Simple aggregation
            job_summary = combined_df.groupby('Job Name').agg({
                'Job ID': 'count',
                'User': lambda x: ', '.join(x.dropna().unique()[:3]),
                'Memory (GB)': ['sum', 'mean'],
                'vCores': ['sum', 'mean'],
                'Duration (mins)': 'mean',
                'Cost_Numeric': 'sum'
            }).round(2)

            # Flatten column names
            new_columns = []
            for col in job_summary.columns:
                if isinstance(col, tuple):
                    if col == ('Job ID', 'count'):
                        new_columns.append('Total Runs')
                    elif col == ('Memory (GB)', 'sum'):
                        new_columns.append('Total Memory (GB)')
                    elif col == ('Memory (GB)', 'mean'):
                        new_columns.append('Avg Memory (GB)')
                    elif col == ('vCores', 'sum'):
                        new_columns.append('Total vCores')
                    elif col == ('vCores', 'mean'):
                        new_columns.append('Avg vCores')
                    elif col == ('Duration (mins)', 'mean'):
                        new_columns.append('Avg Duration (mins)')
                    elif col == ('Cost_Numeric', 'sum'):
                        new_columns.append('Total Cost')
                    else:
                        new_columns.append(f"{col[0]} {col[1]}")
                else:
                    new_columns.append(col)

            job_summary.columns = new_columns

            # Format cost column
            if 'Total Cost' in job_summary.columns:
                job_summary['Total Cost'] = job_summary['Total Cost'].apply(lambda x: f"${x:.2f}")

            # Sort by total runs
            sort_column = 'Total Runs'
            if sort_column in job_summary.columns:
                job_summary = job_summary.sort_values(sort_column, ascending=False)

            return job_summary.reset_index()

        except Exception as e:
            logger.error(f"Error creating job summary: {e}")
            return pd.DataFrame()


# Initialize config manager
config_manager = ConfigManager()


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/environments')
def get_environments():
    """Get available environments"""
    return jsonify(config_manager.get_environments())


@app.route('/api/cluster-metrics')
def get_cluster_metrics():
    """Get simplified cluster metrics"""
    env_name = request.args.get('environment')
    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = SimplifiedJobMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )

    cluster_metrics = monitor.get_cluster_metrics()

    # Calculate utilization
    memory_util = 0
    vcores_util = 0
    if cluster_metrics.get('total_mb', 0) > 0:
        memory_util = (cluster_metrics['allocated_mb'] / cluster_metrics['total_mb']) * 100
    if cluster_metrics.get('total_vcores', 0) > 0:
        vcores_util = (cluster_metrics['allocated_vcores'] / cluster_metrics['total_vcores']) * 100

    utilization_trends = {
        'memory_utilization_pct': round(memory_util, 1),
        'vcores_utilization_pct': round(vcores_util, 1)
    }

    # Simple failure analysis (placeholder)
    failure_analysis = {
        'failed_jobs_24h': 0,
        'failure_rate': 0
    }

    return jsonify({
        'cluster_metrics': cluster_metrics,
        'utilization_trends': utilization_trends,
        'failure_analysis': failure_analysis
    })


@app.route('/api/running-jobs')
def get_running_jobs():
    env_name = request.args.get('environment')
    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = SimplifiedJobMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )
    df = monitor.get_running_jobs()

    if df.empty:
        return jsonify({'data': [], 'summary': {}, 'columns': []})

    # Calculate summary
    high_priority_jobs = len(df[df['Priority'] == 'HIGH'])

    summary = {
        'total_jobs': len(df),
        'total_memory': round(df['Memory (GB)'].sum(), 1),
        'total_vcores': int(df['vCores'].sum()),
        'high_priority_jobs': high_priority_jobs,
        'avg_progress': round(df['Progress (%)'].mean(), 1)
    }

    return jsonify({
        'data': df.to_dict('records'),
        'summary': summary,
        'columns': df.columns.tolist()
    })


@app.route('/api/completed-jobs')
def get_completed_jobs():
    env_name = request.args.get('environment')
    limit = int(request.args.get('limit', config_manager.get_settings().get('max_completed_jobs', 100)))

    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = SimplifiedJobMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )
    df = monitor.get_completed_jobs(limit)

    if df.empty:
        return jsonify({'data': [], 'summary': {}, 'columns': []})

    # Calculate summary
    success_rate = (df['Status'] == 'COMPLETED').mean() * 100 if len(df) > 0 else 0

    # Calculate total cost
    total_cost = 0
    for cost_str in df['Cost Estimate']:
        try:
            total_cost += float(cost_str.replace('$', ''))
        except:
            continue

    summary = {
        'total_jobs': len(df),
        'success_rate': round(success_rate, 1),
        'total_estimated_cost': f"${total_cost:.2f}"
    }

    return jsonify({
        'data': df.to_dict('records'),
        'summary': summary,
        'columns': df.columns.tolist()
    })


@app.route('/api/job-summary')
def get_job_summary():
    env_name = request.args.get('environment')
    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = SimplifiedJobMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )

    df = monitor.get_job_summary()

    if df.empty:
        return jsonify({'data': [], 'columns': []})

    return jsonify({
        'data': df.to_dict('records'),
        'columns': df.columns.tolist()
    })


@app.route('/download/<data_type>')
def download_csv(data_type):
    env_name = request.args.get('environment')
    if not env_name:
        return "Environment not specified", 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return "Environment not found", 404

    monitor = SimplifiedJobMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )

    if data_type == 'running':
        df = monitor.get_running_jobs()
        filename = f'running_jobs_{env_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    elif data_type == 'completed':
        df = monitor.get_completed_jobs()
        filename = f'completed_jobs_{env_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    elif data_type == 'summary':
        df = monitor.get_job_summary()
        filename = f'job_summary_{env_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    else:
        return "Invalid data type", 400

    if df.empty:
        return "No data available", 404

    # Create CSV in memory
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    # Convert to BytesIO for send_file
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)

    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'environments': list(config_manager.get_environments().keys())
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)