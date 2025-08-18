from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import io
import csv
import os
import logging
from typing import Dict, List, Optional, Tuple

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
                "max_completed_jobs": 200,
                "request_timeout": 10,
                "enable_notifications": True,
                "thresholds": {
                    "high_memory_usage_gb": 100,
                    "long_running_job_hours": 2,
                    "max_failed_jobs_per_hour": 5
                }
            }
        }

    def get_environments(self) -> Dict:
        """Get all available environments"""
        return self.config.get('environments', {})

    def get_environment(self, env_name: str) -> Optional[Dict]:
        """Get specific environment configuration"""
        return self.config.get('environments', {}).get(env_name)

    def get_settings(self) -> Dict:
        """Get application settings"""
        return self.config.get('settings', {})


class AdvancedJobResourceMonitor:
    def __init__(self, spark_history_url: str, yarn_rm_url: str, config_manager: ConfigManager):
        self.spark_history_url = spark_history_url
        self.yarn_rm_url = yarn_rm_url
        self.config_manager = config_manager
        self.settings = config_manager.get_settings()

    def _make_request(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP request with error handling and timeout"""
        try:
            timeout = self.settings.get('request_timeout', 10)
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error for {url}: {e}")
            return None

    def get_cluster_metrics(self) -> Dict:
        """Get cluster-level metrics from YARN"""
        try:
            url = f"{self.yarn_rm_url}/ws/v1/cluster/metrics"
            data = self._make_request(url)

            if not data:
                return {}

            cluster_metrics = data.get('clusterMetrics', {})
            return {
                'total_mb': cluster_metrics.get('totalMB', 0),
                'allocated_mb': cluster_metrics.get('allocatedMB', 0),
                'available_mb': cluster_metrics.get('availableMB', 0),
                'total_vcores': cluster_metrics.get('totalVirtualCores', 0),
                'allocated_vcores': cluster_metrics.get('allocatedVirtualCores', 0),
                'available_vcores': cluster_metrics.get('availableVirtualCores', 0),
                'active_nodes': cluster_metrics.get('activeNodes', 0),
                'decommissioned_nodes': cluster_metrics.get('decommissionedNodes', 0),
                'lost_nodes': cluster_metrics.get('lostNodes', 0),
                'unhealthy_nodes': cluster_metrics.get('unhealthyNodes', 0),
                'total_nodes': cluster_metrics.get('totalNodes', 0)
            }
        except Exception as e:
            logger.error(f"Error fetching cluster metrics: {e}")
            return {}

    def get_running_jobs_detailed(self) -> pd.DataFrame:
        """Get detailed information for currently running jobs"""
        try:
            url = f"{self.yarn_rm_url}/ws/v1/cluster/apps"
            params = {'states': 'RUNNING'}
            data = self._make_request(url, params)

            if not data:
                return pd.DataFrame()

            apps = data.get('apps', {}).get('app', [])
            if not apps:
                return pd.DataFrame()

            running_jobs = []
            for app in apps:
                job_info = self._process_running_job(app)
                if job_info:
                    running_jobs.append(job_info)

            return pd.DataFrame(running_jobs)
        except Exception as e:
            logger.error(f"Error fetching running jobs: {e}")
            return pd.DataFrame()

    def _process_running_job(self, app: Dict) -> Optional[Dict]:
        """Process individual running job data"""
        try:
            started_time = self._safe_int_convert(app.get('startedTime', 0))
            elapsed_time = self._safe_int_convert(app.get('elapsedTime', 0))

            start_time = datetime.fromtimestamp(started_time / 1000) if started_time > 0 else datetime.now()
            elapsed_seconds = elapsed_time / 1000

            allocated_mb = self._safe_float_convert(app.get('allocatedMB', 0))
            allocated_vcores = self._safe_int_convert(app.get('allocatedVCores', 0))
            running_containers = self._safe_int_convert(app.get('runningContainers', 0))
            progress = self._safe_float_convert(app.get('progress', 0))

            # Calculate resource hours
            elapsed_hours = elapsed_seconds / 3600
            memory_gb = allocated_mb / 1024

            # Determine job priority/category
            priority = self._determine_job_priority(memory_gb, allocated_vcores, elapsed_hours)

            return {
                'Job ID': app.get('id'),
                'Job Name': self._truncate_string(app.get('name', 'Unknown'), 50),
                'User': app.get('user'),
                'Queue': app.get('queue'),
                'Priority': priority,
                'App Type': app.get('applicationType'),
                'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                'Elapsed Time (mins)': round(elapsed_seconds / 60, 1),
                'Memory (GB)': round(memory_gb, 2),
                'vCores': allocated_vcores,
                'Containers': running_containers,
                'Progress (%)': round(progress, 1),
                'Status': 'RUNNING',
                'Memory-Hours': round(memory_gb * elapsed_hours, 2),
                'vCore-Hours': round(allocated_vcores * elapsed_hours, 2),
                'Estimated Completion': self._estimate_completion_time(start_time, progress)
            }
        except Exception as e:
            logger.error(f"Error processing running job {app.get('id', 'unknown')}: {e}")
            return None

    def get_completed_jobs_detailed(self, limit: int = None) -> pd.DataFrame:
        """Get detailed information for completed Spark jobs"""
        if limit is None:
            limit = self.settings.get('max_completed_jobs', 200)

        try:
            url = f"{self.spark_history_url}/api/v1/applications"
            params = {'limit': limit}
            data = self._make_request(url, params)

            if not data:
                return pd.DataFrame()

            completed_jobs = []
            for app in data:
                job_info = self._process_completed_job(app)
                if job_info:
                    completed_jobs.append(job_info)

            return pd.DataFrame(completed_jobs)
        except Exception as e:
            logger.error(f"Error fetching completed jobs: {e}")
            return pd.DataFrame()

    def _process_completed_job(self, app: Dict) -> Optional[Dict]:
        """Process individual completed job data"""
        try:
            app_id = app['id']

            # Get executor information
            executors_url = f"{self.spark_history_url}/api/v1/applications/{app_id}/executors"
            executors_data = self._make_request(executors_url)

            total_cores, max_memory_mb = self._calculate_executor_resources(executors_data)

            # Time calculations
            attempts = app.get('attempts', [{}])
            if not attempts:
                attempts = [{}]

            first_attempt = attempts[0]
            start_time_ms = self._safe_int_convert(first_attempt.get('startTime', 0))
            end_time_ms = self._safe_int_convert(first_attempt.get('endTime', 0))
            duration_ms = self._safe_int_convert(first_attempt.get('duration', 0))

            start_time = datetime.fromtimestamp(start_time_ms / 1000) if start_time_ms > 0 else None
            end_time = datetime.fromtimestamp(end_time_ms / 1000) if end_time_ms > 0 else None
            duration_hours = duration_ms / (1000 * 60 * 60) if duration_ms > 0 else 0

            memory_gb = max_memory_mb / 1024
            status = 'COMPLETED' if first_attempt.get('completed', False) else 'FAILED'

            # Calculate efficiency metrics
            efficiency_score = self._calculate_job_efficiency(app_id, duration_hours, memory_gb, total_cores)

            return {
                'Job ID': app_id,
                'Job Name': self._truncate_string(app.get('name', 'Unknown'), 50),
                'User': app.get('sparkUser'),
                'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'Unknown',
                'End Time': end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'Unknown',
                'Duration (mins)': round(duration_ms / (1000 * 60), 1) if duration_ms else 0,
                'Memory (GB)': round(memory_gb, 2),
                'vCores': total_cores,
                'Status': status,
                'Memory-Hours': round(memory_gb * duration_hours, 2),
                'vCore-Hours': round(total_cores * duration_hours, 2),
                'Efficiency Score': efficiency_score,
                'Cost Estimate': self._estimate_job_cost(memory_gb, total_cores, duration_hours)
            }
        except Exception as e:
            logger.error(f"Error processing completed job {app.get('id', 'unknown')}: {e}")
            # Return minimal info for failed requests
            return self._create_minimal_job_info(app)

    def _calculate_executor_resources(self, executors_data: Optional[Dict]) -> Tuple[int, int]:
        """Calculate total cores and memory from executor data"""
        if not executors_data:
            return 0, 0

        total_cores = 0
        max_memory_mb = 0

        for executor in executors_data:
            total_cores += self._safe_int_convert(executor.get('totalCores', 0))
            memory_bytes = self._safe_int_convert(executor.get('maxMemory', 0))
            max_memory_mb += memory_bytes // (1024 * 1024)  # Convert bytes to MB

        return total_cores, max_memory_mb

    def _calculate_job_efficiency(self, app_id: str, duration_hours: float, memory_gb: float, vcores: int) -> float:
        """Calculate job efficiency score based on resource utilization"""
        try:
            # Get job stages information for more detailed analysis
            stages_url = f"{self.spark_history_url}/api/v1/applications/{app_id}/stages"
            stages_data = self._make_request(stages_url)

            if not stages_data or duration_hours == 0:
                return 0.0

            # Basic efficiency calculation
            # This is a simplified version - you can enhance based on your specific metrics
            base_score = min(100, (memory_gb * vcores * duration_hours) / max(1, duration_hours))

            # Adjust based on stages completion ratio
            if stages_data:
                completed_stages = sum(1 for stage in stages_data if stage.get('status') == 'COMPLETE')
                total_stages = len(stages_data)
                completion_ratio = completed_stages / max(1, total_stages)
                base_score *= completion_ratio

            return round(base_score, 1)
        except Exception:
            return 0.0

    def _estimate_job_cost(self, memory_gb: float, vcores: int, duration_hours: float) -> str:
        """Estimate job cost based on resource usage"""
        # These are example rates - adjust based on your actual costs
        memory_cost_per_gb_hour = 0.05  # $0.05 per GB-hour
        vcore_cost_per_hour = 0.10  # $0.10 per vCore-hour

        memory_cost = memory_gb * duration_hours * memory_cost_per_gb_hour
        vcore_cost = vcores * duration_hours * vcore_cost_per_hour
        total_cost = memory_cost + vcore_cost

        return f"${total_cost:.2f}"

    def get_job_failure_analysis(self) -> Dict:
        """Analyze job failures and provide insights"""
        try:
            completed_df = self.get_completed_jobs_detailed(100)
            if completed_df.empty:
                return {}

            # Filter failed jobs from last 24 hours
            now = datetime.now()
            day_ago = now - timedelta(hours=24)

            # Convert submit time to datetime for filtering
            completed_df['Submit DateTime'] = pd.to_datetime(completed_df['Submit Time'], errors='coerce')
            recent_jobs = completed_df[completed_df['Submit DateTime'] >= day_ago]

            failed_jobs = recent_jobs[recent_jobs['Status'] == 'FAILED']

            analysis = {
                'total_jobs_24h': len(recent_jobs),
                'failed_jobs_24h': len(failed_jobs),
                'failure_rate': round((len(failed_jobs) / max(1, len(recent_jobs))) * 100, 1),
                'top_failing_users': failed_jobs['User'].value_counts().head(
                    5).to_dict() if not failed_jobs.empty else {},
                'avg_failed_job_duration': round(failed_jobs['Duration (mins)'].mean(),
                                                 1) if not failed_jobs.empty else 0,
                'memory_usage_failures': len(failed_jobs[failed_jobs['Memory (GB)'] > self.settings['thresholds'][
                    'high_memory_usage_gb']]) if not failed_jobs.empty else 0
            }

            return analysis
        except Exception as e:
            logger.error(f"Error in failure analysis: {e}")
            return {}

    def get_resource_utilization_trends(self) -> Dict:
        """Get resource utilization trends"""
        try:
            cluster_metrics = self.get_cluster_metrics()
            if not cluster_metrics:
                return {}

            memory_utilization = (cluster_metrics['allocated_mb'] / max(1, cluster_metrics['total_mb'])) * 100
            vcores_utilization = (cluster_metrics['allocated_vcores'] / max(1, cluster_metrics['total_vcores'])) * 100

            return {
                'memory_utilization_pct': round(memory_utilization, 1),
                'vcores_utilization_pct': round(vcores_utilization, 1),
                'healthy_nodes_pct': round(
                    (cluster_metrics['active_nodes'] / max(1, cluster_metrics['total_nodes'])) * 100, 1),
                'available_memory_gb': round(cluster_metrics['available_mb'] / 1024, 1),
                'available_vcores': cluster_metrics['available_vcores']
            }
        except Exception as e:
            logger.error(f"Error getting utilization trends: {e}")
            return {}

    # Utility methods
    def _safe_int_convert(self, value) -> int:
        """Safely convert value to int"""
        try:
            return int(value) if value is not None else 0
        except (ValueError, TypeError):
            return 0

    def _safe_float_convert(self, value) -> float:
        """Safely convert value to float"""
        try:
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _truncate_string(self, text: str, max_length: int) -> str:
        """Truncate string to specified length"""
        if not text:
            return 'Unknown'
        return text[:max_length] if len(text) > max_length else text

    def _determine_job_priority(self, memory_gb: float, vcores: int, elapsed_hours: float) -> str:
        """Determine job priority based on resource usage"""
        if memory_gb > 50 or vcores > 20 or elapsed_hours > 1:
            return 'HIGH'
        elif memory_gb > 20 or vcores > 10 or elapsed_hours > 0.5:
            return 'MEDIUM'
        else:
            return 'LOW'

    def _estimate_completion_time(self, start_time: datetime, progress: float) -> str:
        """Estimate job completion time based on progress"""
        if progress <= 0:
            return 'Unknown'

        try:
            elapsed = datetime.now() - start_time
            total_estimated = elapsed / (progress / 100)
            remaining = total_estimated - elapsed
            completion_time = datetime.now() + remaining
            return completion_time.strftime('%H:%M:%S')
        except:
            return 'Unknown'

    def _create_minimal_job_info(self, app: Dict) -> Dict:
        """Create minimal job info for failed requests"""
        start_time_ms = self._safe_int_convert(app.get('attempts', [{}])[0].get('startTime', 0))
        start_time = datetime.fromtimestamp(start_time_ms / 1000) if start_time_ms > 0 else None

        return {
            'Job ID': app.get('id'),
            'Job Name': self._truncate_string(app.get('name', 'Unknown'), 50),
            'User': app.get('sparkUser', 'Unknown'),
            'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'Unknown',
            'End Time': 'Error',
            'Duration (mins)': 0,
            'Memory (GB)': 0,
            'vCores': 0,
            'Status': 'ERROR',
            'Memory-Hours': 0,
            'vCore-Hours': 0,
            'Efficiency Score': 0,
            'Cost Estimate': '$0.00'
        }

    def get_aggregated_by_job_submission(self, df: pd.DataFrame, time_window_hours: int = 24) -> pd.DataFrame:
        """Aggregate jobs by submission time windows"""
        if df.empty:
            return pd.DataFrame()

        try:
            # Safe datetime conversion
            df['Submit DateTime'] = pd.to_datetime(df['Submit Time'], errors='coerce')
            df = df.dropna(subset=['Submit DateTime'])

            if df.empty:
                return pd.DataFrame()

            # Create hourly aggregation
            df['Submit Hour'] = df['Submit DateTime'].dt.floor('H')

            # Enhanced aggregation with more metrics
            hourly_agg = df.groupby('Submit Hour').agg({
                'Job ID': 'count',
                'Memory (GB)': ['sum', 'mean', 'max', 'std'],
                'vCores': ['sum', 'mean', 'max'],
                'Duration (mins)': ['mean', 'max', 'std'],
                'Memory-Hours': 'sum',
                'vCore-Hours': 'sum',
                'User': lambda x: len(x.unique()),
                'Status': lambda x: (x == 'COMPLETED').sum()  # Count successful jobs
            }).round(2)

            # Flatten column names
            hourly_agg.columns = [
                'Job Count', 'Total Memory (GB)', 'Avg Memory (GB)', 'Max Memory (GB)', 'Memory Std Dev',
                'Total vCores', 'Avg vCores', 'Max vCores',
                'Avg Duration (mins)', 'Max Duration (mins)', 'Duration Std Dev',
                'Total Memory-Hours', 'Total vCore-Hours', 'Unique Users', 'Successful Jobs'
            ]

            # Add success rate
            hourly_agg['Success Rate (%)'] = round((hourly_agg['Successful Jobs'] / hourly_agg['Job Count']) * 100, 1)

            # Reset index and format
            hourly_agg = hourly_agg.reset_index()
            hourly_agg['Submit Hour'] = hourly_agg['Submit Hour'].dt.strftime('%Y-%m-%d %H:00')

            return hourly_agg.sort_values('Submit Hour', ascending=False)
        except Exception as e:
            logger.error(f"Error in hourly aggregation: {e}")
            return pd.DataFrame()


# Initialize config manager
config_manager = ConfigManager()


# Routes
@app.route('/')
def index():
    environments = config_manager.get_environments()
    settings = config_manager.get_settings()
    return render_template('index.html', environments=environments, settings=settings)


@app.route('/api/environments')
def get_environments():
    """Get available environments"""
    return jsonify(config_manager.get_environments())


@app.route('/api/cluster-metrics')
def get_cluster_metrics():
    """Get cluster-level metrics"""
    env_name = request.args.get('environment')
    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = AdvancedJobResourceMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )

    cluster_metrics = monitor.get_cluster_metrics()
    utilization_trends = monitor.get_resource_utilization_trends()
    failure_analysis = monitor.get_job_failure_analysis()

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

    monitor = AdvancedJobResourceMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )
    df = monitor.get_running_jobs_detailed()

    if df.empty:
        return jsonify({'data': [], 'summary': {}, 'columns': []})

    # Enhanced summary metrics
    high_priority_jobs = len(df[df['Priority'] == 'HIGH'])
    long_running_jobs = len(
        df[df['Elapsed Time (mins)'] > config_manager.get_settings()['thresholds']['long_running_job_hours'] * 60])

    summary = {
        'total_jobs': len(df),
        'total_memory': round(df['Memory (GB)'].sum(), 1),
        'total_vcores': df['vCores'].sum(),
        'total_containers': df['Containers'].sum(),
        'high_priority_jobs': high_priority_jobs,
        'long_running_jobs': long_running_jobs,
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
    limit = int(request.args.get('limit', config_manager.get_settings().get('max_completed_jobs', 200)))

    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = AdvancedJobResourceMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )
    df = monitor.get_completed_jobs_detailed(limit)

    if df.empty:
        return jsonify({'data': [], 'summary': {}, 'columns': []})

    # Enhanced summary metrics
    total_memory_hours = df['Memory-Hours'].sum()
    total_vcore_hours = df['vCore-Hours'].sum()
    success_rate = (df['Status'] == 'COMPLETED').mean() * 100
    avg_efficiency = df['Efficiency Score'].mean()

    # Calculate total estimated cost
    total_cost = 0
    for cost_str in df['Cost Estimate']:
        try:
            total_cost += float(cost_str.replace('$', ''))
        except:
            continue

    summary = {
        'total_jobs': len(df),
        'total_memory_hours': round(total_memory_hours, 1),
        'total_vcore_hours': round(total_vcore_hours, 1),
        'success_rate': round(success_rate, 1),
        'avg_efficiency': round(avg_efficiency, 1),
        'total_estimated_cost': f"${total_cost:.2f}"
    }

    return jsonify({
        'data': df.to_dict('records'),
        'summary': summary,
        'columns': df.columns.tolist()
    })


@app.route('/api/hourly-aggregation')
def get_hourly_aggregation():
    env_name = request.args.get('environment')
    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = AdvancedJobResourceMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )
    completed_df = monitor.get_completed_jobs_detailed(200)

    if completed_df.empty:
        return jsonify({'data': [], 'summary': {}, 'columns': []})

    hourly_agg = monitor.get_aggregated_by_job_submission(completed_df)

    if hourly_agg.empty:
        return jsonify({'data': [], 'summary': {}, 'columns': []})

    # Enhanced summary statistics
    peak_metrics = {
        'peak_hour_jobs': hourly_agg.loc[hourly_agg['Job Count'].idxmax(), 'Submit Hour'],
        'peak_hour_memory': hourly_agg.loc[hourly_agg['Total Memory (GB)'].idxmax(), 'Submit Hour'],
        'peak_hour_vcores': hourly_agg.loc[hourly_agg['Total vCores'].idxmax(), 'Submit Hour'],
        'avg_jobs_per_hour': round(hourly_agg['Job Count'].mean(), 1),
        'avg_memory_per_hour': round(hourly_agg['Total Memory (GB)'].mean(), 1),
        'avg_vcores_per_hour': round(hourly_agg['Total vCores'].mean(), 1),
        'avg_success_rate': round(hourly_agg['Success Rate (%)'].mean(), 1),
        'busiest_hours': hourly_agg.nlargest(3, 'Job Count')['Submit Hour'].tolist()
    }

    return jsonify({
        'data': hourly_agg.to_dict('records'),
        'summary': peak_metrics,
        'columns': hourly_agg.columns.tolist()
    })


@app.route('/api/job-summary')
def get_job_summary():
    env_name = request.args.get('environment')
    if not env_name:
        return jsonify({'error': 'Environment not specified'}), 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return jsonify({'error': 'Environment not found'}), 404

    monitor = AdvancedJobResourceMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )

    running_df = monitor.get_running_jobs_detailed()
    completed_df = monitor.get_completed_jobs_detailed(200)

    all_jobs = []

    if not running_df.empty:
        running_summary = running_df.copy()
        running_summary['Job Type'] = 'RUNNING'
        if 'End Time' not in running_summary.columns:
            running_summary['End Time'] = 'Still Running'
        if 'Duration (mins)' not in running_summary.columns:
            running_summary['Duration (mins)'] = running_summary.get('Elapsed Time (mins)', 0)
        if 'Efficiency Score' not in running_summary.columns:
            running_summary['Efficiency Score'] = 0
        if 'Cost Estimate' not in running_summary.columns:
            running_summary['Cost Estimate'] = '$0.00'
        all_jobs.append(running_summary)

    if not completed_df.empty:
        completed_summary = completed_df.copy()
        completed_summary['Job Type'] = 'COMPLETED'
        if 'Elapsed Time (mins)' not in completed_summary.columns:
            completed_summary['Elapsed Time (mins)'] = completed_summary.get('Duration (mins)', 0)
        if 'Progress (%)' not in completed_summary.columns:
            completed_summary['Progress (%)'] = 100.0
        if 'Containers' not in completed_summary.columns:
            completed_summary['Containers'] = 0
        if 'Priority' not in completed_summary.columns:
            completed_summary['Priority'] = 'MEDIUM'
        if 'Estimated Completion' not in completed_summary.columns:
            completed_summary['Estimated Completion'] = 'Completed'
        all_jobs.append(completed_summary)

    if not all_jobs:
        return jsonify({'data': [], 'summary': {}, 'columns': []})

    try:
        # Align columns before concatenating
        if len(all_jobs) > 1:
            all_columns = set()
            for df in all_jobs:
                all_columns.update(df.columns)

            for i, df in enumerate(all_jobs):
                for col in all_columns:
                    if col not in df.columns:
                        if col in ['Memory (GB)', 'Memory-Hours', 'vCore-Hours', 'Efficiency Score']:
                            df[col] = 0.0
                        elif col in ['vCores', 'Containers']:
                            df[col] = 0
                        elif col in ['Progress (%)', 'Duration (mins)', 'Elapsed Time (mins)']:
                            df[col] = 0.0
                        elif col == 'Priority':
                            df[col] = 'MEDIUM'
                        elif col == 'Cost Estimate':
                            df[col] = '$0.00'
                        else:
                            df[col] = 'N/A'
                all_jobs[i] = df

        combined_df = pd.concat(all_jobs, ignore_index=True, sort=False)

        # Clean and ensure proper data types
        numeric_columns = ['Memory (GB)', 'vCores', 'Memory-Hours', 'vCore-Hours', 'Efficiency Score']
        for col in numeric_columns:
            if col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0)

        # Handle Duration columns
        if 'Duration (mins)' in combined_df.columns and 'Elapsed Time (mins)' in combined_df.columns:
            combined_df['Effective Duration (mins)'] = combined_df.apply(
                lambda row: row['Elapsed Time (mins)'] if row['Job Type'] == 'RUNNING' else row['Duration (mins)'],
                axis=1
            )
        elif 'Duration (mins)' in combined_df.columns:
            combined_df['Effective Duration (mins)'] = combined_df['Duration (mins)']
        elif 'Elapsed Time (mins)' in combined_df.columns:
            combined_df['Effective Duration (mins)'] = combined_df['Elapsed Time (mins)']
        else:
            combined_df['Effective Duration (mins)'] = 0

        combined_df['Effective Duration (mins)'] = pd.to_numeric(
            combined_df['Effective Duration (mins)'], errors='coerce'
        ).fillna(0)

        # Remove invalid job names
        combined_df = combined_df.dropna(subset=['Job Name'])
        combined_df = combined_df[combined_df['Job Name'].str.strip() != '']
        combined_df = combined_df[combined_df['Job Name'] != 'Unknown']

        if combined_df.empty:
            return jsonify({'data': [], 'summary': {}, 'columns': []})

        # Enhanced job aggregation with efficiency metrics
        agg_dict = {
            'Job ID': 'count',
            'User': lambda x: ', '.join(x.dropna().unique()[:3]),
            'Memory (GB)': ['sum', 'mean', 'max'],
            'vCores': ['sum', 'mean', 'max'],
            'Memory-Hours': 'sum',
            'vCore-Hours': 'sum',
            'Effective Duration (mins)': ['mean', 'max'],
            'Efficiency Score': 'mean'
        }

        # Add cost aggregation if available
        if 'Cost Estimate' in combined_df.columns:
            # Convert cost estimates to numeric for aggregation
            """
                errors='raise' (default) - Raises exception on conversion failure
                errors='coerce' - Sets invalid values to NaN
            """
            combined_df['Cost_Numeric'] = combined_df['Cost Estimate'].str.replace('$', '').astype(float, errors='coerce')
            agg_dict['Cost_Numeric'] = 'sum'

            job_summary = combined_df.groupby('Job Name').agg(agg_dict).round(2)

            # Flatten column names
            new_columns = []
            for col in job_summary.columns:
                if isinstance(col, tuple):
                    if col[1] == 'sum' and col[0] == 'Memory (GB)':
                        new_columns.append('Total Memory (GB)')
                    elif col[1] == 'mean' and col[0] == 'Memory (GB)':
                        new_columns.append('Avg Memory (GB)')
                    elif col[1] == 'max' and col[0] == 'Memory (GB)':
                        new_columns.append('Max Memory (GB)')
                    elif col[1] == 'sum' and col[0] == 'vCores':
                        new_columns.append('Total vCores')
                    elif col[1] == 'mean' and col[0] == 'vCores':
                        new_columns.append('Avg vCores')
                    elif col[1] == 'max' and col[0] == 'vCores':
                        new_columns.append('Max vCores')
                    elif col[1] == 'sum' and col[0] == 'Memory-Hours':
                        new_columns.append('Total Memory-Hours')
                    elif col[1] == 'sum' and col[0] == 'vCore-Hours':
                        new_columns.append('Total vCore-Hours')
                    elif col[1] == 'mean' and col[0] == 'Effective Duration (mins)':
                        new_columns.append('Avg Duration (mins)')
                    elif col[1] == 'max' and col[0] == 'Effective Duration (mins)':
                        new_columns.append('Max Duration (mins)')
                    elif col[1] == 'mean' and col[0] == 'Efficiency Score':
                        new_columns.append('Avg Efficiency Score')
                    elif col[1] == 'sum' and col[0] == 'Cost_Numeric':
                        new_columns.append('Total Cost')
                    else:
                        new_columns.append(f"{col[0]} {col[1]}")
            else:
                if col == 'Job ID':
                    new_columns.append('Total Runs')
                else:
                    new_columns.append(col)

            job_summary.columns = new_columns

            # Format cost column if it exists
            if 'Total Cost' in job_summary.columns:
                job_summary['Total Cost'] = job_summary['Total Cost'].apply(lambda x: f"${x:.2f}")

                # Add job type breakdown
        try:
            job_types = combined_df.groupby(['Job Name', 'Job Type']).size().unstack(fill_value=0)
            job_summary = job_summary.join(job_types, how='left').fillna(0)
        except Exception as e:
            logger.warning(f"Could not add job type breakdown: {e}")

        # Sort by total resource usage (Memory-Hours preferred)
        sort_column = 'Total Memory-Hours'
        if sort_column not in job_summary.columns:
            if 'Total Memory (GB)' in job_summary.columns:
                sort_column = 'Total Memory (GB)'
            elif 'Total Runs' in job_summary.columns:
                sort_column = 'Total Runs'
            else:
                sort_column = job_summary.columns[0]

        job_summary = job_summary.sort_values(sort_column, ascending=False)

        return jsonify({
            'data': job_summary.reset_index().to_dict('records'),
            'columns': job_summary.reset_index().columns.tolist()
        })

    except Exception as e:
        logger.error(f"Error in job summary: {e}")
        return jsonify({'data': [], 'summary': {}, 'columns': []})


@app.route('/download/<data_type>')
def download_csv(data_type):
    env_name = request.args.get('environment')
    if not env_name:
        return "Environment not specified", 400

    env_config = config_manager.get_environment(env_name)
    if not env_config:
        return "Environment not found", 404

    monitor = AdvancedJobResourceMonitor(
        env_config['spark_url'],
        env_config['yarn_url'],
        config_manager
    )

    if data_type == 'running':
        df = monitor.get_running_jobs_detailed()
        filename = f'running_jobs_{env_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    elif data_type == 'completed':
        df = monitor.get_completed_jobs_detailed(200)
        filename = f'completed_jobs_{env_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    elif data_type == 'hourly':
        completed_df = monitor.get_completed_jobs_detailed(200)
        df = monitor.get_aggregated_by_job_submission(completed_df)
        filename = f'hourly_aggregation_{env_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
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