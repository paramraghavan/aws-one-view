#!/usr/bin/env python3
"""
Enhanced EMR Monitoring Tool
A Flask-based web application for monitoring EMR clusters, jobs, and resources.
Incorporates improvements from Streamlit version + task node monitoring.
"""

import json
import yaml
import requests
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
import os
from typing import Dict, List, Optional
import logging
import time
import pytz

app = Flask(__name__)
app.secret_key = 'emr-monitoring-secret-key'

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def convert_gmt_to_est(gmt_timestamp_str):
    """Convert GMT timestamp to EST timezone"""
    if not gmt_timestamp_str or '1969-12-31' in str(gmt_timestamp_str):
        return 'N/A'

    try:
        gmt_timezone = pytz.timezone('GMT')
        est_timezone = pytz.timezone('US/Eastern')

        # Handle different timestamp formats
        if isinstance(gmt_timestamp_str, (int, float)):
            # Handle milliseconds timestamp
            timestamp_ms = int(gmt_timestamp_str)
            gmt_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=gmt_timezone)
        elif 'T' in str(gmt_timestamp_str) and 'Z' in str(gmt_timestamp_str):
            # Handle ISO format with Z timezone
            gmt_dt = gmt_timezone.localize(datetime.strptime(str(gmt_timestamp_str), '%Y-%m-%dT%H:%M:%S.%fZ'))
        else:
            # Try to parse as milliseconds timestamp
            timestamp_ms = int(gmt_timestamp_str)
            gmt_dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=gmt_timezone)

        est_dt = gmt_dt.astimezone(est_timezone)
        return est_dt.strftime('%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.warning(f"Error converting timestamp {gmt_timestamp_str}: {e}")
        return str(gmt_timestamp_str)


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

    def safe_float_convert(self, value, default=0.0):
        """Safely convert value to float"""
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def safe_int_convert(self, value, default=0):
        """Safely convert value to int"""
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def detect_instance_type(self, node_id: str, node_rack: str = None) -> str:
        """Detect if instance is spot, on-demand, or reserved"""
        try:
            if node_id:
                node_lower = node_id.lower()

                # Check for common spot instance patterns
                spot_patterns = ['spot', 'spt', '-s-', 'task-spot', 'spot-task']
                for pattern in spot_patterns:
                    if pattern in node_lower:
                        return 'spot'

                # Check for core/master patterns (usually on-demand/reserved)
                if 'master' in node_lower or 'core' in node_lower:
                    return 'on-demand'

                # Task nodes could be spot
                if 'task' in node_lower:
                    return 'spot'

            return 'unknown'
        except Exception as e:
            logger.warning(f"Error detecting instance type for {node_id}: {e}")
            return 'unknown'

    def get_task_nodes_details(self, cluster_id: str) -> List[Dict]:
        """Get detailed task node information including instance types and health"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return []

        try:
            yarn_url = cluster.get('yarn_url')
            if not yarn_url:
                logger.error(f"No yarn_url configured for cluster {cluster_id}")
                return []

            response = requests.get(f"{yarn_url}/ws/v1/cluster/nodes", timeout=10)
            response.raise_for_status()

            data = response.json()
            nodes = data.get('nodes', {}).get('node', [])

            if isinstance(nodes, dict):
                nodes = [nodes]

            task_nodes = []
            for node in nodes:
                node_id = node.get('id', '')
                node_state = node.get('state', 'UNKNOWN')
                node_rack = node.get('rack', '')
                node_host = node.get('nodeHostName', '')

                # Detect instance type
                instance_type = self.detect_instance_type(node_id, node_rack)

                # Calculate health metrics
                last_health_update = node.get('lastHealthUpdate', 0)
                if last_health_update > 0:
                    last_update_time = datetime.fromtimestamp(last_health_update / 1000)
                    time_since_update = datetime.now() - last_update_time
                    health_status = 'healthy' if time_since_update.total_seconds() < 300 else 'stale'
                else:
                    health_status = 'unknown'
                    last_update_time = None

                # Detect potential spot termination
                spot_termination_risk = 'low'
                if instance_type == 'spot':
                    if node_state in ['LOST', 'UNHEALTHY', 'DECOMMISSIONED']:
                        spot_termination_risk = 'high'
                    elif health_status == 'stale':
                        spot_termination_risk = 'medium'

                node_info = {
                    'node_id': node_id,
                    'hostname': node_host,
                    'state': node_state,
                    'rack': node_rack,
                    'instance_type': instance_type,
                    'health_status': health_status,
                    'last_health_update': last_update_time.strftime(
                        '%Y-%m-%d %H:%M:%S') if last_update_time else 'Unknown',
                    'spot_termination_risk': spot_termination_risk,
                    'memory_mb': self.safe_int_convert(node.get('availMemoryMB', 0)),
                    'vcores': self.safe_int_convert(node.get('availableVirtualCores', 0)),
                    'used_memory_mb': self.safe_int_convert(node.get('usedMemoryMB', 0)),
                    'used_vcores': self.safe_int_convert(node.get('usedVirtualCores', 0)),
                    'num_containers': self.safe_int_convert(node.get('numContainers', 0))
                }

                task_nodes.append(node_info)

            return task_nodes

        except Exception as e:
            logger.error(f"Error fetching task nodes for {cluster_id}: {e}")
            return []

    def get_spark_applications_enhanced(self, cluster_id: str, status_filter: str = None, limit: int = 200) -> List[
        Dict]:
        """Enhanced Spark applications with better error handling and resource calculations"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return []

        try:
            spark_url = cluster.get('spark_url')
            if not spark_url:
                logger.error(f"No spark_url configured for cluster {cluster_id}")
                return []

            # Build API URL with parameters
            api_url = f"{spark_url}/api/v1/applications"
            params = {'limit': limit}

            # Add status filter if provided
            status_mapping = {
                'completed': ['SUCCEEDED'],
                'running': ['RUNNING'],
                'failed': ['FAILED'],
                'killed': ['KILLED'],
                'all': None
            }

            if status_filter and status_filter in status_mapping:
                spark_statuses = status_mapping[status_filter]
                if spark_statuses:
                    params['status'] = ','.join(spark_statuses)

            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()

            applications = response.json()

            # Enhanced processing with better error handling
            enhanced_apps = []
            for app in applications:
                try:
                    app_id = app['id']
                    app['cluster_id'] = cluster_id
                    app['cluster_name'] = cluster.get('name', 'Unknown')

                    # Get detailed metrics for completed applications
                    last_attempt = app.get('attempts', [{}])[-1]
                    is_completed = last_attempt.get('completed', True)

                    if is_completed:
                        # Get executor details
                        executor_details = self.get_application_details(cluster_id, app_id)
                        app.update(executor_details)

                        # Calculate resource hours
                        start_time_str = last_attempt.get('startTime', '')
                        end_time_str = last_attempt.get('endTime', '')
                        duration_ms = last_attempt.get('duration', 0)

                        # Convert timestamps
                        app['start_time_est'] = convert_gmt_to_est(start_time_str)
                        app['end_time_est'] = convert_gmt_to_est(end_time_str)

                        duration_hours = self.safe_float_convert(duration_ms) / (1000 * 60 * 60)
                        app['duration_hours'] = duration_hours
                        app['duration_minutes'] = duration_hours * 60

                        # Calculate resource usage
                        memory_gb = self.safe_float_convert(app.get('total_memory_mb', 0)) / 1024
                        vcores = self.safe_int_convert(app.get('total_cores', 0))

                        app['memory_gb'] = memory_gb
                        app['memory_hours'] = memory_gb * duration_hours
                        app['vcore_hours'] = vcores * duration_hours

                        app['standardized_status'] = 'SUCCEEDED' if last_attempt.get('completed') else 'FAILED'
                    else:
                        # Running application - limited data
                        app['standardized_status'] = 'RUNNING'
                        app['start_time_est'] = convert_gmt_to_est(last_attempt.get('startTime', ''))
                        app['status_note'] = 'Running - detailed metrics not available'

                    enhanced_apps.append(app)

                except Exception as e:
                    logger.warning(f"Error processing Spark application {app.get('id', 'unknown')}: {e}")
                    # Add minimal info for failed processing
                    app['standardized_status'] = 'ERROR'
                    app['status_note'] = f'Processing error: {str(e)[:100]}'
                    enhanced_apps.append(app)

            return enhanced_apps

        except Exception as e:
            logger.error(f"Error fetching enhanced Spark applications for {cluster_id}: {e}")
            return []

    def get_yarn_applications_enhanced(self, cluster_id: str, status_filter: str = None) -> List[Dict]:
        """Enhanced YARN applications with resource efficiency calculations"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return []

        try:
            yarn_url = cluster.get('yarn_url')
            if not yarn_url:
                logger.error(f"No yarn_url configured for cluster {cluster_id}")
                return []

            api_url = f"{yarn_url}/ws/v1/cluster/apps"
            params = {}

            # Add status filter
            yarn_state_mapping = {
                'running': ['RUNNING'],
                'completed': ['FINISHED'],
                'failed': ['FAILED'],
                'killed': ['KILLED'],
                'accepted': ['ACCEPTED'],
                'waiting': ['SUBMITTED', 'ACCEPTED'],
                'all': None
            }

            if status_filter and status_filter in yarn_state_mapping:
                yarn_states = yarn_state_mapping[status_filter]
                if yarn_states:
                    params['states'] = ','.join(yarn_states)

            response = requests.get(api_url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            applications = data.get('apps', {}).get('app', [])

            if isinstance(applications, dict):
                applications = [applications]

            enhanced_apps = []
            for app in applications:
                try:
                    app['cluster_id'] = cluster_id
                    app['cluster_name'] = cluster.get('name', 'Unknown')

                    # Safe type conversions
                    started_time = self.safe_int_convert(app.get('startedTime', 0))
                    finished_time = self.safe_int_convert(app.get('finishedTime', 0))
                    elapsed_time = self.safe_int_convert(app.get('elapsedTime', 0))

                    # Convert timestamps
                    if started_time > 0:
                        app['startedTimeFormatted'] = datetime.fromtimestamp(started_time / 1000).strftime(
                            '%Y-%m-%d %H:%M:%S')
                        app['start_time_est'] = convert_gmt_to_est(started_time)

                    if finished_time > 0:
                        app['finishedTimeFormatted'] = datetime.fromtimestamp(finished_time / 1000).strftime(
                            '%Y-%m-%d %H:%M:%S')
                        app['end_time_est'] = convert_gmt_to_est(finished_time)

                    # Duration calculations
                    duration_seconds = elapsed_time / 1000 if elapsed_time > 0 else 0
                    duration_hours = duration_seconds / 3600
                    app['duration_minutes'] = duration_seconds / 60
                    app['duration_hours'] = duration_hours
                    app['durationFormatted'] = self.format_duration(elapsed_time)

                    # Resource calculations
                    allocated_mb = self.safe_float_convert(app.get('allocatedMB', 0))
                    allocated_vcores = self.safe_int_convert(app.get('allocatedVCores', 0))
                    memory_seconds = self.safe_float_convert(app.get('memorySeconds', 0))
                    vcore_seconds = self.safe_float_convert(app.get('vcoreSeconds', 0))

                    app['memory_gb'] = allocated_mb / 1024
                    app['memory_hours'] = (allocated_mb / 1024) * duration_hours
                    app['vcore_hours'] = allocated_vcores * duration_hours

                    # Resource efficiency calculations
                    if duration_seconds > 0 and allocated_mb > 0:
                        expected_memory_seconds = allocated_mb * duration_seconds
                        memory_efficiency = (
                                    memory_seconds / expected_memory_seconds * 100) if expected_memory_seconds > 0 else 0
                        app['memory_efficiency_percent'] = round(memory_efficiency, 2)

                    if duration_seconds > 0 and allocated_vcores > 0:
                        expected_vcore_seconds = allocated_vcores * duration_seconds
                        vcore_efficiency = (
                                    vcore_seconds / expected_vcore_seconds * 100) if expected_vcore_seconds > 0 else 0
                        app['vcore_efficiency_percent'] = round(vcore_efficiency, 2)

                    # Standardized status
                    yarn_state = app.get('state', 'UNKNOWN')
                    final_status = app.get('finalStatus', 'UNDEFINED')

                    if yarn_state == 'RUNNING':
                        app['standardized_status'] = 'RUNNING'
                    elif yarn_state == 'FINISHED' and final_status == 'SUCCEEDED':
                        app['standardized_status'] = 'SUCCEEDED'
                    elif yarn_state in ['FAILED', 'KILLED'] or final_status in ['FAILED', 'KILLED']:
                        app['standardized_status'] = 'FAILED'
                    elif yarn_state in ['ACCEPTED', 'SUBMITTED']:
                        app['standardized_status'] = 'ACCEPTED'
                    else:
                        app['standardized_status'] = yarn_state

                    enhanced_apps.append(app)

                except Exception as e:
                    logger.warning(f"Error processing YARN application {app.get('id', 'unknown')}: {e}")
                    app['standardized_status'] = 'ERROR'
                    enhanced_apps.append(app)

            return enhanced_apps

        except Exception as e:
            logger.error(f"Error fetching enhanced YARN applications for {cluster_id}: {e}")
            return []

    def get_application_summary_by_name(self, cluster_id: str, hours_back: int = 24) -> List[Dict]:
        """Get aggregated job summary by application name"""
        try:
            # Get both running and completed applications
            running_apps = self.get_yarn_applications_enhanced(cluster_id, 'running')
            completed_apps = self.get_spark_applications_enhanced(cluster_id, 'completed', limit=500)

            all_apps = running_apps + completed_apps

            if not all_apps:
                return []

            # Filter by time window
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            filtered_apps = []

            for app in all_apps:
                start_time_str = app.get('start_time_est') or app.get('startedTimeFormatted', '')
                if start_time_str and start_time_str != 'N/A':
                    try:
                        start_time = datetime.strptime(
                            start_time_str.split(' ')[0] + ' ' + start_time_str.split(' ')[1], '%Y-%m-%d %H:%M:%S')
                        if start_time >= cutoff_time:
                            filtered_apps.append(app)
                    except:
                        filtered_apps.append(app)  # Include if can't parse time
                else:
                    filtered_apps.append(app)

            # Group by application name
            app_groups = {}
            for app in filtered_apps:
                app_name = app.get('name', 'Unknown')
                if app_name not in app_groups:
                    app_groups[app_name] = []
                app_groups[app_name].append(app)

            # Calculate summary statistics
            summary_list = []
            for app_name, apps in app_groups.items():
                total_runs = len(apps)
                running_count = sum(1 for app in apps if app.get('standardized_status') == 'RUNNING')
                succeeded_count = sum(1 for app in apps if app.get('standardized_status') == 'SUCCEEDED')
                failed_count = sum(1 for app in apps if app.get('standardized_status') in ['FAILED', 'KILLED'])

                total_memory_hours = sum(self.safe_float_convert(app.get('memory_hours', 0)) for app in apps)
                total_vcore_hours = sum(self.safe_float_convert(app.get('vcore_hours', 0)) for app in apps)
                avg_duration_minutes = sum(self.safe_float_convert(app.get('duration_minutes', 0)) for app in
                                           apps) / total_runs if total_runs > 0 else 0

                users = list(set(app.get('user', app.get('sparkUser', 'Unknown')) for app in apps))

                summary = {
                    'app_name': app_name,
                    'total_runs': total_runs,
                    'running': running_count,
                    'succeeded': succeeded_count,
                    'failed': failed_count,
                    'success_rate': (succeeded_count / total_runs * 100) if total_runs > 0 else 0,
                    'total_memory_hours': total_memory_hours,
                    'total_vcore_hours': total_vcore_hours,
                    'avg_duration_minutes': avg_duration_minutes,
                    'users': ', '.join(users[:3])  # Limit to first 3 users
                }
                summary_list.append(summary)

            # Sort by total resource usage
            summary_list.sort(key=lambda x: x['total_memory_hours'], reverse=True)
            return summary_list

        except Exception as e:
            logger.error(f"Error generating application summary for {cluster_id}: {e}")
            return []

    def get_application_details(self, cluster_id: str, app_id: str) -> Dict:
        """Get detailed application information from Spark History Server"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return {}

        try:
            spark_url = cluster.get('spark_url')
            if not spark_url:
                logger.error(f"No spark_url configured for cluster {cluster_id}")
                return {}

            # Get executors info
            exec_response = requests.get(f"{spark_url}/api/v1/applications/{app_id}/executors", timeout=10)
            executors = exec_response.json() if exec_response.status_code == 200 else []

            # Get stages info
            stages_response = requests.get(f"{spark_url}/api/v1/applications/{app_id}/stages", timeout=10)
            stages = stages_response.json() if stages_response.status_code == 200 else []

            # Calculate resource usage with safe conversions
            total_cores = 0
            total_memory = 0

            for executor in executors:
                total_cores += self.safe_int_convert(executor.get('totalCores', 0))
                total_memory += self.safe_int_convert(executor.get('maxMemory', 0))

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

    def get_cluster_info(self, cluster_id: str) -> Dict:
        """Enhanced cluster information with task node details"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return {}

        try:
            yarn_url = cluster.get('yarn_url')
            if not yarn_url:
                logger.error(f"No yarn_url configured for cluster {cluster_id}")
                return {}

            response = requests.get(f"{yarn_url}/ws/v1/cluster/info", timeout=10)
            response.raise_for_status()

            cluster_info = response.json().get('clusterInfo', {})

            # Get enhanced node information
            task_nodes = self.get_task_nodes_details(cluster_id)

            # Categorize nodes
            node_types = {'master': 0, 'core': 0, 'task': 0}
            node_states = {}
            instance_types = {'spot': 0, 'on-demand': 0, 'unknown': 0}
            spot_risk_summary = {'high': 0, 'medium': 0, 'low': 0}

            for node in task_nodes:
                # Categorize by role
                node_id = node['node_id'].lower()
                if 'master' in node_id:
                    node_types['master'] += 1
                elif 'core' in node_id:
                    node_types['core'] += 1
                else:
                    node_types['task'] += 1

                # Count states
                state = node['state']
                node_states[state] = node_states.get(state, 0) + 1

                # Count instance types
                instance_type = node['instance_type']
                instance_types[instance_type] = instance_types.get(instance_type, 0) + 1

                # Count spot termination risk
                risk = node['spot_termination_risk']
                spot_risk_summary[risk] = spot_risk_summary.get(risk, 0) + 1

            cluster_info['nodeTypes'] = node_types
            cluster_info['nodeStates'] = node_states
            cluster_info['instanceTypes'] = instance_types
            cluster_info['spotTerminationRisk'] = spot_risk_summary
            cluster_info['totalNodes'] = len(task_nodes)
            cluster_info['taskNodes'] = task_nodes

            # Add AWS cluster ID
            cluster_info['awsClusterId'] = self.get_aws_cluster_id(cluster_id)

            return cluster_info
        except Exception as e:
            logger.error(f"Error fetching enhanced cluster info for {cluster_id}: {e}")
            return {}

    def format_duration(self, milliseconds: int) -> str:
        """Format duration from milliseconds to human readable format"""
        try:
            seconds = self.safe_int_convert(milliseconds) // 1000
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60

            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                return f"{minutes}m {seconds}s"
            else:
                return f"{seconds}s"
        except:
            return "0s"

    def get_aws_cluster_id(self, cluster_id: str) -> str:
        """Get AWS EMR cluster ID from the master node"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        if not cluster:
            return "Unknown"

        try:
            # Try to get cluster ID from config first
            if 'aws_cluster_id' in cluster:
                return cluster['aws_cluster_id']

            # Try to get from YARN cluster info
            yarn_url = cluster.get('yarn_url')
            if not yarn_url:
                return "No YARN URL configured"

            response = requests.get(f"{yarn_url}/ws/v1/cluster/info", timeout=5)
            if response.status_code == 200:
                cluster_info = response.json().get('clusterInfo', {})
                cluster_name = cluster_info.get('clusterName', '')
                if cluster_name:
                    return f"From YARN: {cluster_name}"

            return "Not Available"

        except Exception as e:
            logger.error(f"Error fetching AWS cluster ID for {cluster_id}: {e}")
            return "Error fetching"

    def get_application_logs(self, cluster_id: str, app_id: str) -> str:
        """Get application logs (enhanced placeholder)"""
        cluster = self.config['emr_clusters'].get(cluster_id)
        cluster_name = cluster.get('name', 'Unknown') if cluster else 'Unknown'

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return f"""
=== EMR Application Logs ===
Cluster: {cluster_name}
Application ID: {app_id}
Retrieved: {timestamp}

=== Log Retrieval Information ===
This is a placeholder for log retrieval functionality.

To implement actual log retrieval, you can:
1. Access logs from S3 (if configured for log aggregation)
2. Access logs from HDFS on the cluster
3. Access logs from local filesystem on nodes
4. Use AWS EMR APIs to fetch step logs

=== Sample Implementation ===
For S3 logs: s3://your-emr-logs-bucket/{app_id}/
For HDFS logs: hdfs://cluster/var/log/spark/
For local logs: /var/log/spark/

=== Next Steps ===
Update the get_application_logs() method in app.py to:
- Connect to your actual log storage location
- Parse and format log entries
- Handle different log types (stdout, stderr, spark logs)
- Implement log filtering and searching

Current timestamp: {timestamp}
"""


# Initialize monitor - SINGLE INSTANCE
monitor = EMRMonitor()


# Flask Routes
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
    """Get enhanced cluster information with task nodes"""
    info = monitor.get_cluster_info(cluster_id)
    return jsonify(info)


@app.route('/api/cluster/<cluster_id>/task-nodes')
def api_task_nodes(cluster_id):
    """Get detailed task node information"""
    task_nodes = monitor.get_task_nodes_details(cluster_id)
    return jsonify(task_nodes)


@app.route('/api/cluster/<cluster_id>/applications')
def api_applications(cluster_id):
    """Get enhanced applications for a cluster with filtering"""
    source = request.args.get('source', 'both')
    status_filter = request.args.get('status', 'all')
    limit = int(request.args.get('limit', 200))

    applications = []

    if source in ['spark', 'both']:
        spark_apps = monitor.get_spark_applications_enhanced(cluster_id, status_filter, limit)
        for app in spark_apps:
            app['source'] = 'spark'
        applications.extend(spark_apps)

    if source in ['yarn', 'both']:
        yarn_apps = monitor.get_yarn_applications_enhanced(cluster_id, status_filter)
        for app in yarn_apps:
            app['source'] = 'yarn'
        applications.extend(yarn_apps)

    return jsonify(applications)


@app.route('/api/cluster/<cluster_id>/application-summary')
def api_application_summary(cluster_id):
    """Get application summary grouped by name"""
    hours_back = int(request.args.get('hours', 24))
    summary = monitor.get_application_summary_by_name(cluster_id, hours_back)
    return jsonify(summary)


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


@app.route('/api/cluster/<cluster_id>/spot-analysis')
def api_spot_analysis(cluster_id):
    """Get spot instance analysis and termination risks"""
    task_nodes = monitor.get_task_nodes_details(cluster_id)

    spot_nodes = [node for node in task_nodes if node['instance_type'] == 'spot']

    analysis = {
        'total_spot_nodes': len(spot_nodes),
        'high_risk_nodes': len([n for n in spot_nodes if n['spot_termination_risk'] == 'high']),
        'medium_risk_nodes': len([n for n in spot_nodes if n['spot_termination_risk'] == 'medium']),
        'low_risk_nodes': len([n for n in spot_nodes if n['spot_termination_risk'] == 'low']),
        'unhealthy_nodes': len([n for n in spot_nodes if n['state'] in ['LOST', 'UNHEALTHY', 'DECOMMISSIONED']]),
        'spot_nodes_detail': spot_nodes
    }

    return jsonify(analysis)


if __name__ == '__main__':
    try:
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
                        'description': 'Staging EMR cluster',
                        'aws_cluster_id': 'j-EXAMPLE123456'
                    },
                    'production': {
                        'name': 'Production EMR',
                        'spark_url': 'http://production-master:18080',
                        'yarn_url': 'http://production-master:8088',
                        'description': 'Production EMR cluster',
                        'aws_cluster_id': 'j-EXAMPLE789012'
                    }
                }
            }

            try:
                with open('config.yaml', 'w') as f:
                    yaml.dump(default_config, f, default_flow_style=False)
                print("✅ Created default config.yaml file. Please update with your EMR cluster details.")
            except Exception as e:
                print(f"❌ Error creating config.yaml: {e}")

        print("\n" + "=" * 60)
        print("🚀 Starting Enhanced EMR Monitoring Tool")
        print("=" * 60)
        print("Features:")
        print("  ✅ Task node monitoring")
        print("  ✅ Resource efficiency tracking")
        print("  ✅ Spot instance analysis")
        print("  ✅ Enhanced data processing")
        print("  ✅ Real-time monitoring")
        print("=" * 60)
        print(f"🌐 Access the dashboard at: http://localhost:6001")
        print(f"📋 Note: Run 'python create_static_files.py' first to generate template files")
        print(f"🔍 Run 'python validate_config.py' to test your configuration")
        print("=" * 60)

        # Start the Flask application
        app.run(host='0.0.0.0', port=6001, debug=True)

    except KeyboardInterrupt:
        print("\n👋 EMR Monitoring Tool stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting EMR Monitoring Tool: {e}")
        print("💡 Try running 'python validate_config.py' to check your configuration")
        exit(1)