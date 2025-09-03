import json
import yaml
import requests
from flask import Flask, render_template, jsonify, request, send_file
from datetime import datetime, timedelta
import logging
from io import BytesIO
import zipfile
import os
from urllib.parse import urljoin
import time

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


class EMRMonitor:
    def __init__(self, config_file='config.yaml'):
        self.config = self.load_config(config_file)
        self.session = requests.Session()
        self.session.timeout = 30

    def load_config(self, config_file):
        """Load EMR cluster configuration"""
        try:
            if config_file.endswith('.json'):
                with open(config_file, 'r') as f:
                    return json.load(f)
            else:
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f)
        except FileNotFoundError:
            # Default configuration
            return {
                "staging": {
                    "name": "Staging EMR",
                    "spark_url": "http://staging-master:18080",
                    "yarn_url": "http://staging-master:8088",
                    "description": "Staging EMR cluster"
                },
                "production": {
                    "name": "Production EMR",
                    "spark_url": "http://prod-master:18080",
                    "yarn_url": "http://prod-master:8088",
                    "description": "Production EMR cluster"
                }
            }

    def get_spark_applications(self, cluster_key):
        """Get all Spark applications from the cluster with enhanced resource data"""
        cluster = self.config.get(cluster_key)
        if not cluster:
            return []

        try:
            # Get completed applications
            completed_url = f"{cluster['spark_url']}/api/v1/applications"
            completed_response = self.session.get(completed_url)
            completed_apps = completed_response.json() if completed_response.status_code == 200 else []

            # Get running applications
            running_url = f"{cluster['spark_url']}/api/v1/applications?status=running"
            running_response = self.session.get(running_url)
            running_apps = running_response.json() if running_response.status_code == 200 else []

            all_apps = completed_apps + running_apps

            # Enrich with additional details and ensure we get executor info
            for app in all_apps:
                try:
                    app_id = app['id']

                    # Get detailed application info
                    detail_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}"
                    detail_response = self.session.get(detail_url)
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        app.update(detail_data)

                    # Get executor information (crucial for resource data)
                    executor_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/executors"
                    executor_response = self.session.get(executor_url)
                    if executor_response.status_code == 200:
                        executors = executor_response.json()
                        app['executors'] = executors

                        # Calculate summary resource info
                        total_memory_used = sum(exec.get('memoryUsed', 0) for exec in executors)
                        total_cores = sum(exec.get('totalCores', 0) for exec in executors)
                        app['totalMemoryUsed'] = total_memory_used
                        app['totalCores'] = total_cores
                    else:
                        # If no executor data, try to get from application summary
                        app['executors'] = []
                        app['totalMemoryUsed'] = 0
                        app['totalCores'] = 0

                        # Try to get resource info from other sources
                        if 'resourcesPerTask' in app:
                            app['totalCores'] = app.get('resourcesPerTask', {}).get('cores', 0)

                    # Try to get job information for additional context
                    try:
                        jobs_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/jobs"
                        jobs_response = self.session.get(jobs_url)
                        if jobs_response.status_code == 200:
                            app['jobs'] = jobs_response.json()
                    except:
                        pass

                except Exception as e:
                    logging.warning(f"Failed to get details for app {app.get('id', 'unknown')}: {e}")
                    # Ensure we have default values
                    if 'executors' not in app:
                        app['executors'] = []
                    if 'totalMemoryUsed' not in app:
                        app['totalMemoryUsed'] = 0
                    if 'totalCores' not in app:
                        app['totalCores'] = 0

            return all_apps

        except Exception as e:
            logging.error(f"Failed to get Spark applications: {e}")
            return []

    def get_yarn_applications(self, cluster_key):
        """Get YARN applications"""
        cluster = self.config.get(cluster_key)
        if not cluster:
            return []

        try:
            url = f"{cluster['yarn_url']}/ws/v1/cluster/apps"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('apps', {}).get('app', [])
            return []
        except Exception as e:
            logging.error(f"Failed to get YARN applications: {e}")
            return []

    def get_cluster_info(self, cluster_key):
        """Get cluster resource information"""
        cluster = self.config.get(cluster_key)
        if not cluster:
            return {}

        try:
            url = f"{cluster['yarn_url']}/ws/v1/cluster/info"
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logging.error(f"Failed to get cluster info: {e}")
            return {}

    def get_cluster_metrics(self, cluster_key):
        """Get cluster resource metrics"""
        cluster = self.config.get(cluster_key)
        if not cluster:
            return {}

        try:
            url = f"{cluster['yarn_url']}/ws/v1/cluster/metrics"
            response = self.session.get(url)
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception as e:
            logging.error(f"Failed to get cluster metrics: {e}")
            return {}

    def get_application_logs(self, cluster_key, app_id):
        """Get application logs from multiple sources with better error handling"""
        cluster = self.config.get(cluster_key)
        if not cluster:
            return None

        logs_data = {}

        try:
            # 1. Try to get Spark application logs
            try:
                # Check if the application exists in Spark History
                app_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}"
                app_response = self.session.get(app_url)

                if app_response.status_code == 200:
                    # Get executors and their logs
                    executors_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/executors"
                    exec_response = self.session.get(executors_url)

                    if exec_response.status_code == 200:
                        executors = exec_response.json()
                        logs_data['executor_logs'] = {}

                        for executor in executors[:5]:  # Limit to first 5 executors
                            exec_id = executor.get('id')
                            if exec_id:
                                # Try to get logs via different endpoints
                                log_endpoints = [
                                    f"{cluster['spark_url']}/api/v1/applications/{app_id}/executors/{exec_id}/logs",
                                    f"{cluster['spark_url']}/logs/{app_id}/executors/{exec_id}/stdout",
                                    f"{cluster['spark_url']}/logs/{app_id}/executors/{exec_id}/stderr"
                                ]

                                for endpoint in log_endpoints:
                                    try:
                                        log_resp = self.session.get(endpoint)
                                        if log_resp.status_code == 200 and log_resp.text.strip():
                                            log_type = 'stdout' if 'stdout' in endpoint else (
                                                'stderr' if 'stderr' in endpoint else 'combined')
                                            logs_data['executor_logs'][f'executor_{exec_id}_{log_type}'] = log_resp.text
                                    except:
                                        continue

                        # Get driver logs
                        driver_endpoints = [
                            f"{cluster['spark_url']}/api/v1/applications/{app_id}/logs",
                            f"{cluster['spark_url']}/logs/{app_id}/driver/stdout",
                            f"{cluster['spark_url']}/logs/{app_id}/driver/stderr"
                        ]

                        for endpoint in driver_endpoints:
                            try:
                                driver_resp = self.session.get(endpoint)
                                if driver_resp.status_code == 200 and driver_resp.text.strip():
                                    logs_data['driver_logs'] = driver_resp.text
                                    break
                            except:
                                continue

            except Exception as e:
                logging.warning(f"Failed to get Spark logs: {e}")

            # 2. Try YARN application logs
            try:
                yarn_app_url = f"{cluster['yarn_url']}/ws/v1/cluster/apps/{app_id}"
                yarn_response = self.session.get(yarn_app_url)

                if yarn_response.status_code == 200:
                    yarn_data = yarn_response.json()
                    app_info = yarn_data.get('app', {})
                    logs_data['yarn_info'] = {'application_info': app_info}

                    # Try to get container logs
                    attempts_url = f"{cluster['yarn_url']}/ws/v1/cluster/apps/{app_id}/appattempts"
                    attempts_resp = self.session.get(attempts_url)
                    if attempts_resp.status_code == 200:
                        attempts_data = attempts_resp.json()
                        attempts = attempts_data.get('appAttempts', {}).get('appAttempt', [])

                        logs_data['container_logs'] = {}
                        for attempt in attempts[:2]:  # Limit to first 2 attempts
                            attempt_id = attempt.get('appAttemptId')
                            if attempt_id:
                                containers_url = f"{cluster['yarn_url']}/ws/v1/cluster/apps/{app_id}/appattempts/{attempt_id}/containers"
                                containers_resp = self.session.get(containers_url)
                                if containers_resp.status_code == 200:
                                    containers_data = containers_resp.json()
                                    containers = containers_data.get('containers', {}).get('container', [])

                                    for container in containers[:3]:  # Limit to first 3 containers
                                        container_id = container.get('containerId')
                                        node_http_address = container.get('nodeHttpAddress')

                                        if container_id and node_http_address:
                                            # Try to get container logs from node manager
                                            log_endpoints = [
                                                f"http://{node_http_address}/ws/v1/node/containers/{container_id}/logs/stdout",
                                                f"http://{node_http_address}/ws/v1/node/containers/{container_id}/logs/stderr"
                                            ]

                                            for endpoint in log_endpoints:
                                                try:
                                                    log_resp = self.session.get(endpoint, timeout=10)
                                                    if log_resp.status_code == 200 and log_resp.text.strip():
                                                        log_type = 'stdout' if 'stdout' in endpoint else 'stderr'
                                                        logs_data['container_logs'][
                                                            f'{container_id}_{log_type}'] = log_resp.text
                                                except:
                                                    continue

            except Exception as e:
                logging.warning(f"Failed to get YARN logs: {e}")

            # 3. Get Spark job information
            try:
                jobs_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/jobs"
                jobs_resp = self.session.get(jobs_url)
                if jobs_resp.status_code == 200:
                    logs_data['spark_jobs'] = jobs_resp.json()

                # Get stages info
                stages_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/stages"
                stages_resp = self.session.get(stages_url)
                if stages_resp.status_code == 200:
                    logs_data['spark_stages'] = stages_resp.json()

            except Exception as e:
                logging.warning(f"Failed to get Spark job info: {e}")

            # 4. Get application environment
            try:
                env_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/environment"
                env_resp = self.session.get(env_url)
                if env_resp.status_code == 200:
                    logs_data['environment'] = env_resp.json()
            except Exception as e:
                logging.warning(f"Failed to get environment info: {e}")

            # If we still don't have meaningful logs, provide helpful info
            if not any(v for v in logs_data.values() if v):
                container_search = app_id.replace('application_', 'container_')
                logs_data['log_info'] = f"""Application {app_id} Log Information:

                No direct logs were found through the Spark History Server or YARN REST APIs.
                This is common and can happen for several reasons:
                
                1. Application is still starting up
                2. Logs are aggregated to HDFS or S3 storage  
                3. Log retention policies have cleaned up old logs
                4. Application logs are only available on individual nodes
                
                To access logs manually, try these commands on the EMR master node:
                
                Get YARN logs (most reliable method):
                yarn logs -applicationId {app_id}
                
                Check local Spark application directories:
                find /mnt/var/log/spark/apps/{app_id}* -name "*.log" 2>/dev/null
                
                Check HDFS for aggregated logs:
                hdfs dfs -ls /tmp/logs/*/logs/{app_id}
                
                Check container logs on node managers:
                find /mnt/var/log/containers -name "*{container_search}*" 2>/dev/null
                
                If using S3 log aggregation, check your EMR cluster's S3 log location.
                """

        except Exception as e:
            logging.warning(f"Failed to get Spark application logs: {e}")


    def get_spot_instance_info(self, cluster_key):
        """Get spot instance information and interruption details"""
        cluster = self.config.get(cluster_key)
        if not cluster:
            return {}

        try:
            # Get nodes with detailed information
            nodes_url = f"{cluster['yarn_url']}/ws/v1/cluster/nodes"
            nodes_response = self.session.get(nodes_url)

            # Get application history to detect spot interruptions
            apps_url = f"{cluster['yarn_url']}/ws/v1/cluster/apps?states=FAILED,KILLED&limit=50"
            apps_response = self.session.get(apps_url)

            spot_info = {
                'spot_nodes': [],
                'ondemand_nodes': [],
                'interruption_events': [],
                'allocation_failures': [],
                'spot_savings': 0,
                'total_interruptions_24h': 0,
                'current_spot_capacity': 0,
                'current_ondemand_capacity': 0,
                'failed_spot_requests': 0,
                'spot_vs_ondemand': {
                    'spot_count': 0,
                    'ondemand_count': 0,
                    'spot_cores': 0,
                    'ondemand_cores': 0,
                    'spot_memory': 0,
                    'ondemand_memory': 0
                }
            }

            if nodes_response.status_code == 200:
                nodes_data = nodes_response.json()
                nodes = nodes_data.get('nodes', {}).get('node', [])

                current_time = datetime.now()

                for node in nodes:
                    node_hostname = node.get('nodeHostName', '')
                    node_type = self.classify_node_type(node_hostname)

                    # Determine if this is a spot instance
                    is_spot = self.detect_spot_instance(node)

                    memory_mb = (node.get('availMemoryMB', 0) + node.get('usedMemoryMB', 0))
                    cores = (node.get('availVirtualCores', 0) + node.get('usedVirtualCores', 0))

                    node_info = {
                        'hostname': node_hostname,
                        'node_id': node.get('id', ''),
                        'node_type': node_type,
                        'state': node.get('state', 'UNKNOWN'),
                        'last_health_update': node.get('lastHealthUpdate', 0),
                        'memory_mb': memory_mb,
                        'cores': cores,
                        'containers': node.get('numContainers', 0),
                        'uptime_hours': self.calculate_node_uptime(node.get('lastHealthUpdate', 0)),
                        'interruption_risk': self.assess_interruption_risk(node) if is_spot else 'N/A',
                        'estimated_savings': self.estimate_spot_savings(node) if is_spot else 0,
                        'instance_lifecycle': 'spot' if is_spot else 'on-demand'
                    }

                    # Update summary statistics
                    if is_spot:
                        spot_info['spot_nodes'].append(node_info)
                        spot_info['current_spot_capacity'] += cores
                        spot_info['spot_savings'] += node_info['estimated_savings']
                        spot_info['spot_vs_ondemand']['spot_count'] += 1
                        spot_info['spot_vs_ondemand']['spot_cores'] += cores
                        spot_info['spot_vs_ondemand']['spot_memory'] += memory_mb
                    else:
                        spot_info['ondemand_nodes'].append(node_info)
                        spot_info['current_ondemand_capacity'] += cores
                        spot_info['spot_vs_ondemand']['ondemand_count'] += 1
                        spot_info['spot_vs_ondemand']['ondemand_cores'] += cores
                        spot_info['spot_vs_ondemand']['ondemand_memory'] += memory_mb

            if apps_response.status_code == 200:
                apps_data = apps_response.json()
                apps = apps_data.get('apps', {}).get('app', [])

                # Analyze failed/killed applications for spot interruptions
                for app in apps:
                    if self.is_spot_interruption(app):
                        interruption_event = {
                            'app_id': app.get('id', ''),
                            'app_name': app.get('name', ''),
                            'final_status': app.get('finalStatus', ''),
                            'finished_time': app.get('finishedTime', 0),
                            'elapsed_time': app.get('elapsedTime', 0),
                            'allocated_mb': app.get('allocatedMB', 0),
                            'allocated_cores': app.get('allocatedVCores', 0),
                            'interruption_reason': self.get_interruption_reason(app),
                            'affected_node': app.get('amHostHttpAddress', 'Unknown')
                        }
                        spot_info['interruption_events'].append(interruption_event)

                        # Count interruptions in last 24 hours
                        if app.get('finishedTime', 0) > 0:
                            finished_time = datetime.fromtimestamp(app.get('finishedTime', 0) / 1000)
                            if (current_time - finished_time).total_seconds() < 86400:  # 24 hours
                                spot_info['total_interruptions_24h'] += 1

            return spot_info

        except Exception as e:
            logging.error(f"Failed to get spot instance info: {e}")
            return {}

    def detect_spot_instance(self, node):
        """Detect if a node is a spot instance using multiple methods"""

        # Method 1: Check health report or node metadata
        health_report = node.get('healthReport', '').lower()
        if 'spot' in health_report:
            return True

        # Method 2: Check if it's marked in node attributes (custom field from mock server)
        if node.get('spot_instance', False):
            return True

        # Method 3: Check node labels/tags if available
        node_labels = node.get('nodeLabels', [])
        if any('spot' in label.lower() for label in node_labels):
            return True

        # Method 4: Analyze uptime patterns (spot instances typically have shorter uptimes)
        uptime_hours = self.calculate_node_uptime(node.get('lastHealthUpdate', 0))
        if uptime_hours < 24:  # Less than 24 hours might indicate spot
            # Additional checks needed to avoid false positives
            node_hostname = node.get('nodeHostName', '').lower()
            if 'task' in node_hostname or 'compute' in node_hostname:
                return True

        # Method 5: Check for specific hostname patterns that indicate spot
        node_hostname = node.get('nodeHostName', '').lower()
        spot_indicators = ['spot', 'preemptible', 'cheap', 'temp']
        if any(indicator in node_hostname for indicator in spot_indicators):
            return True

        # Method 6: Check instance type patterns (if available)
        instance_type = node.get('instance_type', '')
        # In real AWS, you'd check EC2 instance metadata or tags

        # Method 7: For real EMR clusters, you would use AWS API to check:
        # - EC2 instance lifecycle (spot vs on-demand)
        # - Instance tags
        # - Auto Scaling Group configuration
        # - EMR fleet configuration

        # Default: assume on-demand unless proven otherwise
        # In production, you should integrate with AWS APIs:
        # boto3.client('ec2').describe_instances() to check instance lifecycle
        return False

    def get_instance_lifecycle_from_aws(self, instance_id):
        """
        Real implementation would use AWS APIs to determine instance lifecycle.
        This is a placeholder for the actual implementation.
        """
        # Example implementation (requires boto3 and proper AWS credentials):
        # try:
        #     import boto3
        #     ec2 = boto3.client('ec2')
        #     response = ec2.describe_instances(InstanceIds=[instance_id])
        #     for reservation in response['Reservations']:
        #         for instance in reservation['Instances']:
        #             return instance.get('InstanceLifecycle') == 'spot'
        # except Exception as e:
        #     logging.warning(f"Could not determine instance lifecycle: {e}")
        #     return False
        pass

    def classify_node_type(self, hostname):
        """Classify node type based on hostname"""
        if not hostname:
            return 'Unknown Node'

        hostname_lower = hostname.lower()

        if 'master' in hostname_lower or 'namenode' in hostname_lower:
            return 'Master Node'
        elif 'core' in hostname_lower or 'datanode' in hostname_lower:
            return 'Core Node'
        elif 'task' in hostname_lower or 'compute' in hostname_lower:
            return 'Task Node'
        elif 'ip-172-31-1-50' in hostname or '172.31.1.50' in hostname:
            return 'Master Node'
        elif any(f'ip-172-31-1-5{i}' in hostname for i in [1, 2, 3]) or any(
                f'172.31.1.5{i}' in hostname for i in [1, 2, 3]):
            return 'Core Node'
        else:
            return 'Task Node'  # Usually spot instances

    def calculate_node_uptime(self, last_health_update):
        """Calculate node uptime in hours"""
        if not last_health_update:
            return 0
        current_time = datetime.now().timestamp() * 1000
        uptime_ms = current_time - last_health_update
        return max(0, uptime_ms / (1000 * 3600))  # Convert to hours

    def assess_interruption_risk(self, node):
        """Assess spot interruption risk based on various factors"""
        # In real implementation, you'd use AWS EC2 Spot Instance Advisor API
        # For simulation, use uptime and resource utilization
        uptime_hours = self.calculate_node_uptime(node.get('lastHealthUpdate', 0))

        if uptime_hours < 1:
            return 'High'
        elif uptime_hours < 6:
            return 'Medium'
        else:
            return 'Low'

    def estimate_spot_savings(self, node):
        """Estimate cost savings from using spot instances"""
        # Rough calculation: assume 70% savings vs on-demand
        cores = node.get('availVirtualCores', 0) + node.get('usedVirtualCores', 0)
        memory_gb = ((node.get('availMemoryMB', 0) + node.get('usedMemoryMB', 0)) / 1024)

        # Estimated hourly cost savings (simplified calculation)
        estimated_hourly_savings = (cores * 0.05) + (memory_gb * 0.01)  # USD per hour saved
        return round(estimated_hourly_savings, 2)

    def is_spot_interruption(self, app):
        """Determine if application failure was due to spot interruption"""
        final_status = app.get('finalStatus', '')
        state = app.get('state', '')
        diagnostics = app.get('diagnostics', '').lower()

        # Common patterns indicating spot interruptions
        spot_indicators = [
            final_status == 'FAILED' and 'KILLED' in state,
            app.get('elapsedTime', 0) < 300000,  # Less than 5 minutes (sudden termination)
            'preempted' in diagnostics,
            'spot' in diagnostics,
            'capacity constraints' in diagnostics,
            'price exceeded' in diagnostics,
            app.get('numNonAMContainerPreempted', 0) > 0,
            app.get('numAMContainerPreempted', 0) > 0
        ]

        return any(spot_indicators)

    def get_interruption_reason(self, app):
        """Extract interruption reason from application diagnostics"""
        diagnostics = app.get('diagnostics', '').lower()

        if 'spot' in diagnostics and 'price' in diagnostics:
            return 'Spot price exceeded bid'
        elif 'preempted' in diagnostics:
            return 'Instance preempted'
        elif 'capacity' in diagnostics:
            return 'Insufficient capacity'
        elif app.get('elapsedTime', 0) < 300000:
            return 'Sudden termination (likely spot)'
        elif app.get('numNonAMContainerPreempted', 0) > 0:
            return 'Containers preempted'
        else:
            return 'Unknown interruption'


# Initialize monitor
monitor = EMRMonitor()


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html', clusters=monitor.config)


@app.route('/api/clusters')
def get_clusters():
    """Get available clusters"""
    return jsonify(monitor.config)


@app.route('/api/cluster/<cluster_key>/applications')
def get_applications(cluster_key):
    """Get applications for a specific cluster with spot instance info"""
    spark_apps = monitor.get_spark_applications(cluster_key)
    yarn_apps = monitor.get_yarn_applications(cluster_key)
    spot_info = monitor.get_spot_instance_info(cluster_key)

    # Combine and enrich data
    apps_data = {
        'spark_applications': spark_apps,
        'yarn_applications': yarn_apps,
        'cluster_info': monitor.get_cluster_info(cluster_key),
        'cluster_metrics': monitor.get_cluster_metrics(cluster_key),
        'spot_instance_info': spot_info
    }

    return jsonify(apps_data)


@app.route('/api/cluster/<cluster_key>/spot_status')
def get_spot_status(cluster_key):
    """Get detailed spot instance status"""
    spot_info = monitor.get_spot_instance_info(cluster_key)
    return jsonify({
        'spot_info': spot_info,
        'cluster_key': cluster_key,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/cluster/<cluster_key>/metrics')
def get_cluster_metrics_endpoint(cluster_key):
    """Get cluster metrics"""
    metrics = monitor.get_cluster_metrics(cluster_key)
    info = monitor.get_cluster_info(cluster_key)

    return jsonify({
        'metrics': metrics,
        'info': info,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/cluster/<cluster_key>/application/<app_id>/logs')
def get_application_logs_endpoint(cluster_key, app_id):
    """Get logs for a specific application"""
    logs_data = monitor.get_application_logs(cluster_key, app_id)

    if logs_data:
        return jsonify({
            'logs_data': logs_data,
            'app_id': app_id,
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({'error': 'Logs not found'}), 404


@app.route('/api/cluster/<cluster_key>/application/<app_id>/download_logs')
def download_application_logs(cluster_key, app_id):
    """Download logs for a specific application"""
    logs_data = monitor.get_application_logs(cluster_key, app_id)

    if logs_data:
        # Create a zip file with all available logs
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:

            # Add driver logs
            if 'driver_logs' in logs_data and logs_data['driver_logs']:
                zf.writestr(f'{app_id}_driver.log', logs_data['driver_logs'])

            # Add executor logs
            if 'executor_logs' in logs_data:
                for log_name, log_content in logs_data['executor_logs'].items():
                    if log_content and log_content.strip():
                        zf.writestr(f'{app_id}_{log_name}.log', log_content)

            # Add container logs
            if 'container_logs' in logs_data:
                for container_id, log_content in logs_data['container_logs'].items():
                    if log_content and log_content.strip():
                        zf.writestr(f'{app_id}_container_{container_id}.log', log_content)

            # Add log info message
            if 'log_info' in logs_data:
                zf.writestr(f'{app_id}_log_access_info.txt', logs_data['log_info'])

            # Add YARN application info
            if 'yarn_info' in logs_data:
                yarn_info = json.dumps(logs_data['yarn_info'], indent=2)
                zf.writestr(f'{app_id}_yarn_info.json', yarn_info)

            # Add Spark jobs info
            if 'spark_jobs' in logs_data:
                jobs_info = json.dumps(logs_data['spark_jobs'], indent=2)
                zf.writestr(f'{app_id}_spark_jobs.json', jobs_info)

            # Add Spark stages info
            if 'spark_stages' in logs_data:
                stages_info = json.dumps(logs_data['spark_stages'], indent=2)
                zf.writestr(f'{app_id}_spark_stages.json', stages_info)

            # Add environment info
            if 'environment' in logs_data:
                env_info = json.dumps(logs_data['environment'], indent=2)
                zf.writestr(f'{app_id}_environment.json', env_info)

            # Add a comprehensive README
            readme_content = f"""EMR Application Logs for {app_id}
Generated: {datetime.now().isoformat()}

FILES IN THIS ARCHIVE:
=====================
"""

            file_count = 0
            if 'driver_logs' in logs_data and logs_data['driver_logs']:
                readme_content += f"✓ {app_id}_driver.log - Spark driver logs\n"
                file_count += 1

            if 'executor_logs' in logs_data:
                for log_name in logs_data['executor_logs'].keys():
                    readme_content += f"✓ {app_id}_{log_name}.log - Executor logs\n"
                    file_count += 1

            if 'container_logs' in logs_data:
                for container_id in logs_data['container_logs'].keys():
                    readme_content += f"✓ {app_id}_container_{container_id}.log - YARN container logs\n"
                    file_count += 1

            if file_count == 0:
                readme_content += "\nWARNING: NO LOG FILES FOUND\n"
                readme_content += "See the log_access_info.txt file for manual access instructions.\n"

            readme_content += "\nJSON METADATA FILES:\n"
            readme_content += f"- {app_id}_yarn_info.json - YARN application details\n"
            readme_content += f"- {app_id}_spark_jobs.json - Spark jobs information\n"
            readme_content += f"- {app_id}_spark_stages.json - Spark stages information\n"
            readme_content += f"- {app_id}_environment.json - Application configuration\n"

            if 'log_info' in logs_data:
                readme_content += f"\nSee {app_id}_log_access_info.txt for manual log access instructions.\n"

            zf.writestr(f'{app_id}_README.txt', readme_content)

        memory_file.seek(0)

        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f'{app_id}_logs.zip',
            mimetype='application/zip'
        )
    else:
        return jsonify({'error': 'No logs found. Try: yarn logs -applicationId ' + app_id}), 404


@app.route('/api/cluster/<cluster_key>/application/<app_id>/view_logs')
def view_application_logs(cluster_key, app_id):
    """View logs for a specific application in browser"""
    logs_data = monitor.get_application_logs(cluster_key, app_id)

    if logs_data:
        return render_template('logs.html',
                               app_id=app_id,
                               cluster_key=cluster_key,
                               logs_data=logs_data)
    else:
        return render_template('logs.html',
                               app_id=app_id,
                               cluster_key=cluster_key,
                               logs_data=None,
                               error_message=f'No logs found for {app_id}. Try: yarn logs -applicationId {app_id}')


@app.route('/api/cluster/<cluster_key>/kill_application/<app_id>', methods=['POST'])
def kill_application(cluster_key, app_id):
    """Kill a running application (if supported)"""
    cluster = monitor.config.get(cluster_key)
    if not cluster:
        return jsonify({'error': 'Cluster not found'}), 404

    try:
        # Try to kill via YARN
        url = f"{cluster['yarn_url']}/ws/v1/cluster/apps/{app_id}/state"
        data = {"state": "KILLED"}
        response = monitor.session.put(url, json=data)

        if response.status_code == 200:
            return jsonify({'message': 'Application killed successfully'})
        else:
            return jsonify({'error': 'Failed to kill application'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)