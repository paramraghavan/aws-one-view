#!/usr/bin/env python3
"""
EMR Monitoring Tool
A Flask-based web application for monitoring EMR clusters, jobs, and resources.
"""

import json
import yaml
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_file
import os
from typing import Dict, List, Optional
import logging
from urllib.parse import urljoin
import time

app = Flask(__name__)
app.secret_key = 'emr-monitoring-secret-key'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EMRMonitor:
    def __init__(self, config_file: str = 'config.yaml'):
        self.config = self.load_config(config_file)

    def load_config(self, config_file: str) -> Dict:
        """Load EMR cluster configuration"""
        try:
            if config_file.endswith('.json'):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
        except FileNotFoundError:
            # Default config if file doesn't exist
            return {
                "emr_clusters": {
                    "staging": {
                        "name": "Staging EMR",
                        "spark_url": "http://staging-master:18080",
                        "yarn_url": "http://staging-master:8088",
                        "description": "Staging EMR cluster"
                    }
                }
            }

    def get_spark_applications(self, cluster_id: str) -> List[Dict]:
        """Get applications from Spark History Server"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return []

        try:
            spark_url = cluster['spark_url']
            response = requests.get(f"{spark_url}/api/v1/applications", timeout=10)
            response.raise_for_status()

            applications = response.json()

            # Enrich with additional details ONLY for completed applications
            for app in applications:
                app['cluster_id'] = cluster_id
                app['cluster_name'] = cluster['name']

                # Get detailed info ONLY for completed applications
                # Spark History Server has complete data for finished apps
                last_attempt = app.get('attempts', [{}])[-1]
                is_completed = last_attempt.get('completed', True)

                if is_completed:  # Only get details for completed apps
                    detailed_info = self.get_application_details(cluster_id, app['id'])
                    if detailed_info:
                        app.update(detailed_info)
                else:
                    # For running applications, we can only get basic info
                    # The detailed metrics aren't available in History Server yet
                    app['status_note'] = 'Running - detailed metrics not available in History Server'

            return applications
        except Exception as e:
            logger.error(f"Error fetching Spark applications for {cluster_id}: {e}")
            return []

    def get_application_details(self, cluster_id: str, app_id: str) -> Dict:
        """
        Get detailed application information from Spark History Server
        Note: This works best for COMPLETED applications.
        Running applications may have limited data available.
        """
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return {}

    def get_running_application_details_from_yarn(self, cluster_id: str, app_id: str) -> Dict:
        """
        Get running application details from YARN ResourceManager
        This is better for monitoring currently running applications
        """
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return {}

        try:
            yarn_url = cluster['yarn_url']

            # Get application details from YARN
            response = requests.get(f"{yarn_url}/ws/v1/cluster/apps/{app_id}", timeout=10)
            if response.status_code != 200:
                return {}

            app_info = response.json().get('app', {})

            # Get resource usage details
            allocated_mb = app_info.get('allocatedMB', 0)
            allocated_vcores = app_info.get('allocatedVCores', 0)
            running_containers = app_info.get('runningContainers', 0)

            return {
                'allocated_memory_mb': allocated_mb,
                'allocated_vcores': allocated_vcores,
                'running_containers': running_containers,
                'progress': app_info.get('progress', 0),
                'elapsed_time': app_info.get('elapsedTime', 0),
                'memory_seconds': app_info.get('memorySeconds', 0),
                'vcore_seconds': app_info.get('vcoreSeconds', 0),
                'source': 'yarn_live'
            }
        except Exception as e:
            logger.error(f"Error fetching YARN application details for {app_id}: {e}")
            return {}

        try:
            spark_url = cluster['spark_url']

            # Get executors info - may be empty for running applications
            exec_response = requests.get(f"{spark_url}/api/v1/applications/{app_id}/executors", timeout=10)
            executors = exec_response.json() if exec_response.status_code == 200 else []

            # Get stages info - may be incomplete for running applications
            stages_response = requests.get(f"{spark_url}/api/v1/applications/{app_id}/stages", timeout=10)
            stages = stages_response.json() if stages_response.status_code == 200 else []

            # Calculate resource usage from available data
            total_cores = sum(exec.get('totalCores', 0) for exec in executors)
            total_memory = sum(exec.get('maxMemory', 0) for exec in executors)

            return {
                'executors': executors,
                'stages': stages,
                'total_cores': total_cores,
                'total_memory_mb': total_memory // (1024 * 1024) if total_memory else 0,
                'executor_count': len(executors)
            }
        except Exception as e:
            logger.error(f"Error fetching application details for {app_id}: {e}")
            return {}

    def get_yarn_applications(self, cluster_id: str) -> List[Dict]:
        """
        Get applications from YARN ResourceManager
        This is the primary source for monitoring running applications
        """
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return []

        try:
            yarn_url = cluster['yarn_url']
            response = requests.get(f"{yarn_url}/ws/v1/cluster/apps", timeout=10)
            response.raise_for_status()

            data = response.json()
            applications = data.get('apps', {}).get('app', [])

            if isinstance(applications, dict):
                applications = [applications]

            for app in applications:
                app['cluster_id'] = cluster_id
                app['cluster_name'] = cluster['name']

                # Convert timestamps
                if 'startedTime' in app:
                    app['startedTimeFormatted'] = datetime.fromtimestamp(
                        app['startedTime'] / 1000).strftime('%Y-%m-%d %H:%M:%S')

                if 'finishedTime' in app and app['finishedTime'] > 0:
                    app['finishedTimeFormatted'] = datetime.fromtimestamp(
                        app['finishedTime'] / 1000).strftime('%Y-%m-%d %H:%M:%S')

                # Calculate duration
                if 'elapsedTime' in app:
                    app['durationFormatted'] = self.format_duration(app['elapsedTime'])

                # Add resource efficiency metrics for better monitoring
                allocated_mb = app.get('allocatedMB', 0)
                allocated_vcores = app.get('allocatedVCores', 0)
                memory_seconds = app.get('memorySeconds', 0)
                vcore_seconds = app.get('vcoreSeconds', 0)
                elapsed_time_seconds = app.get('elapsedTime', 0) / 1000

                # Calculate resource utilization efficiency
                if elapsed_time_seconds > 0 and allocated_mb > 0:
                    expected_memory_seconds = allocated_mb * elapsed_time_seconds
                    memory_efficiency = (
                                memory_seconds / expected_memory_seconds * 100) if expected_memory_seconds > 0 else 0
                    app['memory_efficiency_percent'] = round(memory_efficiency, 2)

                if elapsed_time_seconds > 0 and allocated_vcores > 0:
                    expected_vcore_seconds = allocated_vcores * elapsed_time_seconds
                    vcore_efficiency = (
                                vcore_seconds / expected_vcore_seconds * 100) if expected_vcore_seconds > 0 else 0
                    app['vcore_efficiency_percent'] = round(vcore_efficiency, 2)

            return applications
        except Exception as e:
            logger.error(f"Error fetching YARN applications for {cluster_id}: {e}")
            return []

    def get_cluster_info(self, cluster_id: str) -> Dict:
        """Get cluster information from YARN"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return {}

        try:
            yarn_url = cluster['yarn_url']
            response = requests.get(f"{yarn_url}/ws/v1/cluster/info", timeout=10)
            response.raise_for_status()

            cluster_info = response.json().get('clusterInfo', {})

            # Get node information
            nodes_response = requests.get(f"{yarn_url}/ws/v1/cluster/nodes", timeout=10)
            nodes_data = nodes_response.json() if nodes_response.status_code == 200 else {}
            nodes = nodes_data.get('nodes', {}).get('node', [])

            if isinstance(nodes, dict):
                nodes = [nodes]

            # Categorize nodes
            node_types = {'master': 0, 'core': 0, 'task': 0}
            node_states = {}

            for node in nodes:
                # Simple heuristic to categorize nodes
                if 'master' in node.get('id', '').lower():
                    node_types['master'] += 1
                elif 'core' in node.get('id', '').lower():
                    node_types['core'] += 1
                else:
                    node_types['task'] += 1

                state = node.get('state', 'UNKNOWN')
                node_states[state] = node_states.get(state, 0) + 1

            cluster_info['nodeTypes'] = node_types
            cluster_info['nodeStates'] = node_states
            cluster_info['totalNodes'] = len(nodes)

            # Add AWS cluster ID
            cluster_info['awsClusterId'] = self.get_aws_cluster_id(cluster_id)

            return cluster_info
        except Exception as e:
            logger.error(f"Error fetching cluster info for {cluster_id}: {e}")
            return {}

    def format_duration(self, milliseconds: int) -> str:
        """Format duration from milliseconds to human readable format"""
        seconds = milliseconds // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def get_aws_cluster_id(self, cluster_id: str) -> str:
        """Get AWS EMR cluster ID from the master node"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return "Unknown"

        try:
            # Try to get cluster ID from master node's metadata
            master_host = cluster['spark_url'].replace('http://', '').replace(':18080', '')

            # Method 1: Try to get from job-flow.json (requires SSH access)
            # This is a placeholder - in reality you'd need SSH access

            # Method 2: Try to extract from YARN cluster info
            yarn_url = cluster['yarn_url']
            response = requests.get(f"{yarn_url}/ws/v1/cluster/info", timeout=5)
            if response.status_code == 200:
                cluster_info = response.json().get('clusterInfo', {})
                # Sometimes cluster info contains additional metadata
                cluster_name = cluster_info.get('clusterName', '')
                if cluster_name:
                    return f"From YARN: {cluster_name}"

            # Method 3: Return from config if available
            if 'aws_cluster_id' in cluster:
                return cluster['aws_cluster_id']

            return "Not Available"

        except Exception as e:
            logger.error(f"Error fetching AWS cluster ID for {cluster_id}: {e}")
            return "Error fetching"

    def get_application_logs(self, cluster_id: str, app_id: str) -> str:
        """Get application logs (placeholder for actual implementation)"""
        # In a real implementation, you would fetch logs from the appropriate location
        # This could be from S3, HDFS, or local file system depending on your setup
        return f"Logs for application {app_id} on cluster {cluster_id}\n\nLog retrieval not implemented yet."


# Initialize monitor
monitor = EMRMonitor()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', clusters=monitor.config.get('emr_clusters', {}))


@app.route('/api/clusters')
def api_clusters():
    """Get available EMR clusters"""
    return jsonify(monitor.config.get('emr_clusters', {}))


@app.route('/api/cluster/<cluster_id>/info')
def api_cluster_info(cluster_id):
    """Get cluster information"""
    info = monitor.get_cluster_info(cluster_id)
    return jsonify(info)


@app.route('/api/cluster/<cluster_id>/applications')
def api_applications(cluster_id):
    """Get applications for a cluster"""
    source = request.args.get('source', 'both')

    applications = []

    if source in ['spark', 'both']:
        spark_apps = monitor.get_spark_applications(cluster_id)
        for app in spark_apps:
            app['source'] = 'spark'
        applications.extend(spark_apps)

    if source in ['yarn', 'both']:
        yarn_apps = monitor.get_yarn_applications(cluster_id)
        for app in yarn_apps:
            app['source'] = 'yarn'
        applications.extend(yarn_apps)

    return jsonify(applications)


@app.route('/api/cluster/<cluster_id>/application/<app_id>/details')
def api_application_details(cluster_id, app_id):
    """Get detailed application information"""
    details = monitor.get_application_details(cluster_id, app_id)
    return jsonify(details)


@app.route('/api/cluster/<cluster_id>/application/<app_id>/logs')
def api_application_logs(cluster_id, app_id):
    """Get application logs"""
    logs = monitor.get_application_logs(cluster_id, app_id)
    return jsonify({'logs': logs})


if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)

    # Create a basic config file if it doesn't exist
    if not os.path.exists('config.yaml'):
        default_config = {
            'emr_clusters': {
                'staging': {
                    'name': 'Staging EMR',
                    'spark_url': 'http://staging-master:18080',
                    'yarn_url': 'http://staging-master:8088',
                    'description': 'Staging EMR cluster'
                },
                'production': {
                    'name': 'Production EMR',
                    'spark_url': 'http://production-master:18080',
                    'yarn_url': 'http://production-master:8088',
                    'description': 'Production EMR cluster'
                }
            }
        }

        with open('config.yaml', 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

        print("Created default config.yaml file. Please update with your EMR cluster details.")

    print("Starting EMR Monitoring Tool...")
    print("Access the dashboard at: http://localhost:6001")
    print("Note: Run create_static_files.py first to generate template and static files.")
    app.run(host='0.0.0.0', port=6001, debug=True)