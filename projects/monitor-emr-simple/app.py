#!/usr/bin/env python3
"""
EMR Monitor - Flask application to monitor EMR clusters
Monitors Spark jobs via History Server and YARN ResourceManager
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
    """Monitor Spark applications via History Server API"""

    def __init__(self, spark_url: str):
        self.spark_url = spark_url.rstrip('/')
        self.api_base = f"{self.spark_url}/api/v1/applications"

    def get_applications(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get Spark applications from History Server"""
        try:
            response = requests.get(f"{self.api_base}?limit={limit}", timeout=10)
            response.raise_for_status()
            return response.json()
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

    def get_long_running_jobs(self, hours_threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Find long-running applications that might be consuming resources"""
        apps = self.get_applications(100)
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
                    # Job is completed - use end time
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                    duration_hours = (end_time - start_time).total_seconds() / 3600
                    app['is_running'] = False
                else:
                    # Job is still running - use current time
                    duration_hours = (datetime.utcnow() - start_time).total_seconds() / 3600
                    app['is_running'] = True

                # Only include if duration exceeds threshold
                if duration_hours > hours_threshold:
                    app['duration_hours'] = round(duration_hours, 2)
                    app['start_time_parsed'] = start_time
                    app['end_time_parsed'] = end_time if end_time_str else None
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

    def get_cluster_status(self, cluster_id: str, threshold_hours: float = 2.0) -> Dict[str, Any]:
        """Get comprehensive cluster status"""
        spark_monitor, yarn_monitor = self.get_monitor(cluster_id)
        if not spark_monitor or not yarn_monitor:
            return {'error': 'Cluster not found'}

        # Get data from both monitors
        cluster_info = yarn_monitor.get_cluster_info()
        cluster_metrics = yarn_monitor.get_cluster_metrics()
        node_summary = yarn_monitor.get_node_summary()

        running_apps = yarn_monitor.get_applications(['RUNNING', 'ACCEPTED', 'SUBMITTED'])
        spark_apps = spark_monitor.get_applications(20)
        long_running = spark_monitor.get_long_running_jobs(threshold_hours)

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
                'running_apps': running_apps[:10],  # Limit to top 10
                'spark_apps': spark_apps[:10],
                'long_running_count': len(long_running),
                'long_running': long_running[:5]  # Top 5 long running
            },
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
    status = emr_monitor.get_cluster_status(cluster_id, threshold)
    return jsonify(status)


@app.route('/api/cluster/<cluster_id>/refresh')
def api_cluster_refresh(cluster_id):
    """API endpoint to refresh cluster data"""
    threshold = request.args.get('threshold', 2.0, type=float)

    # Clear cached monitors to force refresh
    if cluster_id in emr_monitor.monitors:
        del emr_monitor.monitors[cluster_id]

    status = emr_monitor.get_cluster_status(cluster_id, threshold)
    return jsonify(status)


if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)

    app.run(debug=True, host='0.0.0.0', port=7501)