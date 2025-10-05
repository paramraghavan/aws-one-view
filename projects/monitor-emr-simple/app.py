#!/usr/bin/env python3
"""
EMR Monitor - Flask application to monitor EMR clusters
Monitors Spark jobs via History Server and YARN ResourceManager
Enhanced with resource usage tracking for Spark jobs
"""

import os
import yaml
import requests
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from typing import Dict, List, Any, Optional
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class EMRConfig:
    """Handle EMR configuration from YAML file"""

    def __init__(self, config_file: str = 'emr_config.yaml'):
        self.config_file = config_file
        self.clusters = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load EMR configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_file} not found")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            return {}

    def get_clusters(self) -> Dict[str, Any]:
        """Get all configured clusters"""
        return self.clusters

    def get_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        """Get specific cluster configuration"""
        return self.clusters.get(cluster_id)


class SparkMonitor:
    """Monitor Spark applications via History Server API with resource tracking"""

    def __init__(self, spark_url: str):
        self.spark_url = spark_url.rstrip('/')
        self.api_base = f"{self.spark_url}/api/v1/applications"

    def get_applications(self, limit: int = 50, include_resources: bool = False) -> List[Dict[str, Any]]:
        """
        Get Spark applications from History Server

        Args:
            limit: Maximum number of applications to retrieve
            include_resources: If True, fetch detailed resource usage for each app

        Returns:
            List of application dictionaries with optional resource usage info
        """
        try:
            response = requests.get(f"{self.api_base}?limit={limit}", timeout=10)
            response.raise_for_status()
            apps = response.json()

            if include_resources:
                # Enrich each application with resource usage
                for app in apps:
                    app_id = app.get('id')
                    if app_id:
                        resources = self.get_application_resources(app_id)
                        app['resources'] = resources

            return apps
        except requests.RequestException as e:
            logger.error(f"Error fetching Spark applications: {e}")
            return []

    def get_application_details(self, app_id: str) -> Dict[str, Any]:
        """Get detailed information about a specific application"""
        try:
            response = requests.get(f"{self.api_base}/{app_id}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching application {app_id}: {e}")
            return {}

    def get_application_executors(self, app_id: str) -> List[Dict[str, Any]]:
        """Get executor information for an application"""
        try:
            # Get all attempts for the application
            app_details = self.get_application_details(app_id)
            attempts = app_details.get('attempts', [])

            if not attempts:
                return []

            # Use the first (most recent) attempt
            attempt_id = attempts[0].get('attemptId')

            # Fetch executors for this attempt
            if attempt_id:
                url = f"{self.api_base}/{app_id}/{attempt_id}/executors"
            else:
                url = f"{self.api_base}/{app_id}/executors"

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching executors for {app_id}: {e}")
            return []

    def get_application_resources(self, app_id: str) -> Dict[str, Any]:
        """
        Calculate total memory and cores used by a Spark application

        Returns:
            Dictionary with resource usage details
        """
        try:
            executors = self.get_application_executors(app_id)

            if not executors:
                return {
                    'total_memory_mb': 0,
                    'total_cores': 0,
                    'executor_count': 0,
                    'driver_memory_mb': 0,
                    'driver_cores': 0,
                    'error': 'No executor data available'
                }

            total_memory_mb = 0
            total_cores = 0
            executor_count = 0
            driver_memory_mb = 0
            driver_cores = 0

            for executor in executors:
                executor_id = executor.get('id', '')

                # Driver is typically executor with id "driver"
                is_driver = executor_id.lower() == 'driver'

                # Get memory (in bytes, convert to MB)
                max_memory = executor.get('maxMemory', 0)
                memory_mb = max_memory / (1024 * 1024) if max_memory > 0 else 0

                # Get cores
                cores = executor.get('totalCores', 0)

                if is_driver:
                    driver_memory_mb = memory_mb
                    driver_cores = cores
                else:
                    executor_count += 1

                total_memory_mb += memory_mb
                total_cores += cores

            return {
                'total_memory_mb': round(total_memory_mb, 2),
                'total_memory_gb': round(total_memory_mb / 1024, 2),
                'total_cores': total_cores,
                'executor_count': executor_count,
                'driver_memory_mb': round(driver_memory_mb, 2),
                'driver_cores': driver_cores,
                'executor_memory_mb': round((total_memory_mb - driver_memory_mb) / executor_count,
                                            2) if executor_count > 0 else 0,
                'executor_cores': round((total_cores - driver_cores) / executor_count, 2) if executor_count > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error calculating resources for {app_id}: {e}")
            return {
                'total_memory_mb': 0,
                'total_cores': 0,
                'executor_count': 0,
                'error': str(e)
            }

    def get_completed_jobs_summary(self, limit: int = 50) -> Dict[str, Any]:
        """
        Get summary of completed jobs with aggregated resource usage
        """
        apps = self.get_applications(limit=limit, include_resources=True)

        total_jobs = 0
        failed_jobs = 0
        total_memory_gb = 0
        total_core_hours = 0

        for app in apps:
            try:
                attempts = app.get('attempts', [])
                if not attempts:
                    continue

                attempt = attempts[0]

                # Check if completed
                if not attempt.get('completed', False):
                    continue

                total_jobs += 1

                # Check if failed
                if not attempt.get('completed') or attempt.get('lastUpdated') == attempt.get('endTime'):
                    failed_jobs += 1

                # Get resource usage
                resources = app.get('resources', {})
                memory_gb = resources.get('total_memory_gb', 0)
                cores = resources.get('total_cores', 0)

                # Calculate duration in hours
                start_time_str = attempt.get('startTime')
                end_time_str = attempt.get('endTime')

                if start_time_str and end_time_str:
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                    duration_hours = (end_time - start_time).total_seconds() / 3600

                    total_memory_gb += memory_gb
                    total_core_hours += (cores * duration_hours)

            except Exception as e:
                logger.warning(f"Error processing app {app.get('id', 'unknown')}: {e}")
                continue

        return {
            'total_jobs': total_jobs,
            'failed_jobs': failed_jobs,
            'success_rate': round((total_jobs - failed_jobs) / total_jobs * 100, 1) if total_jobs > 0 else 0,
            'total_memory_gb': round(total_memory_gb, 2),
            'total_core_hours': round(total_core_hours, 2),
            'avg_memory_gb': round(total_memory_gb / total_jobs, 2) if total_jobs > 0 else 0,
            'avg_core_hours': round(total_core_hours / total_jobs, 2) if total_jobs > 0 else 0
        }

    def get_long_running_jobs(self, hours_threshold: float = 2.0, limit: int = 100) -> List[Dict[str, Any]]:
        """Find long-running applications that might be consuming resources"""
        apps = self.get_applications(limit, include_resources=True)
        long_running = []

        for app in apps:
            try:
                attempt = app['attempts'][0]
                start_time_str = attempt['startTime']
                end_time_str = attempt.get('endTime')

                # Parse start time
                start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')

                # Calculate duration based on whether job is completed or still running
                if end_time_str:
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                    duration_hours = (end_time - start_time).total_seconds() / 3600
                    app['is_running'] = False
                else:
                    duration_hours = (datetime.utcnow() - start_time).total_seconds() / 3600
                    app['is_running'] = True

                # Only include if duration exceeds threshold
                if duration_hours > hours_threshold:
                    app['duration_hours'] = round(duration_hours, 2)
                    app['start_time_parsed'] = start_time
                    app['end_time_parsed'] = end_time if end_time_str else None

                    # Add resource efficiency metrics
                    resources = app.get('resources', {})
                    if resources and resources.get('total_cores', 0) > 0:
                        app['memory_core_ratio'] = round(
                            resources.get('total_memory_gb', 0) / resources.get('total_cores', 1),
                            2
                        )

                    long_running.append(app)

            except (KeyError, ValueError, IndexError) as e:
                logger.warning(f"Error processing application timing for app {app.get('id', 'unknown')}: {e}")
                continue

        return sorted(long_running, key=lambda x: x.get('duration_hours', 0), reverse=True)


class YARNMonitor:
    """Monitor YARN ResourceManager"""

    def __init__(self, yarn_url: str):
        self.yarn_url = yarn_url.rstrip('/')
        self.api_base = f"{self.yarn_url}/ws/v1/cluster"

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get general cluster information"""
        try:
            response = requests.get(f"{self.api_base}/info", timeout=10)
            response.raise_for_status()
            return response.json().get('clusterInfo', {})
        except requests.RequestException as e:
            logger.error(f"Error fetching cluster info: {e}")
            return {}

    def get_cluster_metrics(self) -> Dict[str, Any]:
        """Get cluster resource metrics"""
        try:
            response = requests.get(f"{self.api_base}/metrics", timeout=10)
            response.raise_for_status()
            return response.json().get('clusterMetrics', {})
        except requests.RequestException as e:
            logger.error(f"Error fetching cluster metrics: {e}")
            return {}

    def get_applications(self, states: List[str] = None) -> List[Dict[str, Any]]:
        """Get YARN applications with optional state filtering"""
        try:
            url = f"{self.api_base}/apps"
            if states:
                state_params = '&'.join([f"states={state}" for state in states])
                url += f"?{state_params}"

            response = requests.get(url, timeout=10)
            response.raise_for_status()
            apps_data = response.json().get('apps', {})
            return apps_data.get('app', []) if apps_data else []
        except requests.RequestException as e:
            logger.error(f"Error fetching YARN applications: {e}")
            return []

    def get_nodes(self) -> List[Dict[str, Any]]:
        """Get cluster nodes information"""
        try:
            response = requests.get(f"{self.api_base}/nodes", timeout=10)
            response.raise_for_status()
            nodes_data = response.json().get('nodes', {})
            return nodes_data.get('node', []) if nodes_data else []
        except requests.RequestException as e:
            logger.error(f"Error fetching cluster nodes: {e}")
            return []

    def get_node_summary(self) -> Dict[str, int]:
        """Get summary of node states"""
        nodes = self.get_nodes()
        summary = {
            'RUNNING': 0,
            'LOST': 0,
            'UNHEALTHY': 0,
            'DECOMMISSIONED': 0,
            'TOTAL': len(nodes)
        }

        for node in nodes:
            state = node.get('state', 'UNKNOWN')
            if state in summary:
                summary[state] += 1

        return summary


class EMRMonitor:
    """Main EMR monitoring class"""

    def __init__(self, config: EMRConfig):
        self.config = config
        self.monitors = {}

    def get_monitor(self, cluster_id: str) -> tuple:
        """Get or create monitors for a cluster"""
        if cluster_id not in self.monitors:
            cluster_config = self.config.get_cluster(cluster_id)
            if not cluster_config:
                return None, None

            spark_monitor = SparkMonitor(cluster_config['spark_url'])
            yarn_monitor = YARNMonitor(cluster_config['yarn_url'])
            self.monitors[cluster_id] = (spark_monitor, yarn_monitor)

        return self.monitors[cluster_id]

    def get_cluster_status(self, cluster_id: str, threshold_hours: float = 2.0, limit: int = 50) -> Dict[str, Any]:
        """Get comprehensive cluster status"""
        spark_monitor, yarn_monitor = self.get_monitor(cluster_id)
        if not spark_monitor or not yarn_monitor:
            return {'error': 'Cluster not found'}

        # Get data from both monitors
        cluster_info = yarn_monitor.get_cluster_info()
        cluster_metrics = yarn_monitor.get_cluster_metrics()
        node_summary = yarn_monitor.get_node_summary()

        running_apps = yarn_monitor.get_applications(['RUNNING', 'ACCEPTED', 'SUBMITTED'])

        # Get Spark applications WITHOUT resource details for basic listing (faster)
        # Use the limit parameter from UI
        spark_apps = spark_monitor.get_applications(min(limit, 20), include_resources=False)

        # Get completed jobs summary WITH resource details
        # Use the limit parameter from UI
        completed_summary = spark_monitor.get_completed_jobs_summary(limit)

        # Get long-running jobs WITH resource details
        # Use the limit parameter from UI
        long_running = spark_monitor.get_long_running_jobs(threshold_hours, limit)

        # Calculate resource usage
        total_memory = cluster_metrics.get('totalMB', 0)
        used_memory = cluster_metrics.get('allocatedMB', 0)
        total_cores = cluster_metrics.get('totalVirtualCores', 0)
        used_cores = cluster_metrics.get('allocatedVirtualCores', 0)

        memory_usage_pct = (used_memory / total_memory * 100) if total_memory > 0 else 0
        cpu_usage_pct = (used_cores / total_cores * 100) if total_cores > 0 else 0

        return {
            'cluster_info': cluster_info,
            'resources': {
                'memory': {
                    'total_mb': total_memory,
                    'used_mb': used_memory,
                    'free_mb': total_memory - used_memory,
                    'usage_percent': round(memory_usage_pct, 1)
                },
                'cpu': {
                    'total_cores': total_cores,
                    'used_cores': used_cores,
                    'free_cores': total_cores - used_cores,
                    'usage_percent': round(cpu_usage_pct, 1)
                }
            },
            'nodes': node_summary,
            'applications': {
                'running_count': len(running_apps),
                'running_apps': running_apps[:10],
                'spark_apps': spark_apps[:10],
                'long_running_count': len(long_running),
                'long_running': long_running[:5]
            },
            'completed_jobs': completed_summary,
            'threshold': threshold_hours,
            'timestamp': datetime.now().isoformat()
        }


# Initialize
config = EMRConfig()
emr_monitor = EMRMonitor(config)


@app.route('/')
def index():
    """Main dashboard page"""
    clusters = config.get_clusters()
    return render_template('index.html', clusters=clusters)


@app.route('/api/clusters')
def api_clusters():
    """API endpoint to get cluster list"""
    return jsonify(config.get_clusters())


@app.route('/api/cluster/<cluster_id>/status')
def api_cluster_status(cluster_id):
    """API endpoint to get cluster status"""
    threshold = request.args.get('threshold', 2.0, type=float)
    limit = request.args.get('limit', 50, type=int)
    status = emr_monitor.get_cluster_status(cluster_id, threshold, limit)
    return jsonify(status)


@app.route('/api/cluster/<cluster_id>/spark/resources')
def api_cluster_spark_resources(cluster_id):
    """API endpoint to get detailed Spark resource usage"""
    spark_monitor, _ = emr_monitor.get_monitor(cluster_id)
    if not spark_monitor:
        return jsonify({'error': 'Cluster not found'}), 404

    limit = request.args.get('limit', 20, type=int)
    summary = spark_monitor.get_completed_jobs_summary(limit)

    return jsonify(summary)


@app.route('/api/cluster/<cluster_id>/spark/applications')
def api_cluster_spark_applications(cluster_id):
    """API endpoint to get Spark applications with resource details"""
    spark_monitor, _ = emr_monitor.get_monitor(cluster_id)
    if not spark_monitor:
        return jsonify({'error': 'Cluster not found'}), 404

    limit = request.args.get('limit', 20, type=int)
    include_resources = request.args.get('resources', 'true').lower() == 'true'

    apps = spark_monitor.get_applications(limit, include_resources)

    return jsonify({
        'count': len(apps),
        'applications': apps
    })


@app.route('/api/cluster/<cluster_id>/refresh')
def api_cluster_refresh(cluster_id):
    """API endpoint to refresh cluster data"""
    threshold = request.args.get('threshold', 2.0, type=float)
    limit = request.args.get('limit', 50, type=int)

    # Clear cached monitors to force refresh
    if cluster_id in emr_monitor.monitors:
        del emr_monitor.monitors[cluster_id]

    status = emr_monitor.get_cluster_status(cluster_id, threshold, limit)
    return jsonify(status)


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    logger.info("=" * 60)
    logger.info("Starting EMR Monitor with Enhanced Resource Tracking")
    logger.info("=" * 60)

    app.run(debug=True, host='0.0.0.0', port=7501)