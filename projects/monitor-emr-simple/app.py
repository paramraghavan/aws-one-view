from flask import Flask, render_template, jsonify, request
import yaml
import requests
from datetime import datetime, timedelta
import json
import logging
import threading
import time
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class EnhancedEMRMonitor:
    def __init__(self, config_file='emr_config.yaml'):
        self.config_file = config_file
        self.clusters = self.load_config()
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 30  # Cache for 30 seconds

    def load_config(self):
        """Load and validate configuration"""
        try:
            with open(self.config_file, 'r') as file:
                config = yaml.safe_load(file)
                return self.validate_config(config)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    def validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration structure"""
        required_fields = ['name', 'spark_url', 'yarn_url']

        for cluster_id, cluster_config in config.items():
            for field in required_fields:
                if field not in cluster_config:
                    logger.warning(f"Missing required field '{field}' in cluster '{cluster_id}'")

            # Set default values
            cluster_config.setdefault('auth', {'type': 'none'})
            cluster_config.setdefault('thresholds', {
                'max_long_running_hours': 2,
                'max_memory_gb': 100,
                'max_failed_apps': 5,
                'min_healthy_nodes_percent': 80
            })
            cluster_config.setdefault('tags', {})

        return config

    def get_cached_data(self, key: str) -> Optional[Any]:
        """Get cached data if not expired"""
        if key in self.cache and key in self.cache_expiry:
            if datetime.now() < self.cache_expiry[key]:
                return self.cache[key]
        return None

    def set_cached_data(self, key: str, data: Any):
        """Set cached data with expiry"""
        self.cache[key] = data
        self.cache_expiry[key] = datetime.now() + timedelta(seconds=self.cache_duration)

    def make_request(self, url: str, cluster_config: Dict[str, Any], timeout: int = 10) -> Optional[requests.Response]:
        """Make HTTP request with authentication if configured"""
        try:
            auth = cluster_config.get('auth', {})
            headers = {'Accept': 'application/json'}

            if auth.get('type') == 'basic':
                username = auth.get('username')
                password = auth.get('password')
                if username and password:
                    credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
                    headers['Authorization'] = f'Basic {credentials}'

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            return None

    def get_spark_applications(self, cluster_id: str) -> List[Dict[str, Any]]:
        """Get Spark applications with caching"""
        cache_key = f"spark_apps_{cluster_id}"
        cached_data = self.get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return []

        spark_url = cluster['spark_url']
        try:
            # Get all applications
            response = self.make_request(f"{spark_url}/api/v1/applications", cluster)
            if not response:
                return []

            applications = response.json()

            # Get detailed info for recent applications
            detailed_apps = []
            for app in applications[:20]:  # Limit for performance
                app_id = app['id']
                try:
                    detail_response = self.make_request(f"{spark_url}/api/v1/applications/{app_id}", cluster, timeout=5)
                    if detail_response:
                        detail = detail_response.json()

                        # Get executors info
                        exec_response = self.make_request(f"{spark_url}/api/v1/applications/{app_id}/executors",
                                                          cluster, timeout=5)
                        if exec_response:
                            detail['executors'] = exec_response.json()

                        # Get stages info
                        stages_response = self.make_request(f"{spark_url}/api/v1/applications/{app_id}/stages", cluster,
                                                            timeout=5)
                        if stages_response:
                            detail['stages'] = stages_response.json()

                        detailed_apps.append(detail)
                    else:
                        detailed_apps.append(app)
                except Exception as e:
                    logger.error(f"Error getting details for app {app_id}: {e}")
                    detailed_apps.append(app)

            self.set_cached_data(cache_key, detailed_apps)
            return detailed_apps

        except Exception as e:
            logger.error(f"Error fetching Spark applications: {e}")
            return []

    def get_yarn_applications(self, cluster_id: str) -> List[Dict[str, Any]]:
        """Get YARN applications with caching"""
        cache_key = f"yarn_apps_{cluster_id}"
        cached_data = self.get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return []

        yarn_url = cluster['yarn_url']
        try:
            response = self.make_request(f"{yarn_url}/ws/v1/cluster/apps", cluster)
            if not response:
                return []

            data = response.json()
            apps = data.get('apps', {}).get('app', [])

            # Ensure apps is a list
            if isinstance(apps, dict):
                apps = [apps]

            self.set_cached_data(cache_key, apps)
            return apps

        except Exception as e:
            logger.error(f"Error fetching YARN applications: {e}")
            return []

    def get_yarn_nodes(self, cluster_id: str) -> List[Dict[str, Any]]:
        """Get YARN nodes with caching"""
        cache_key = f"yarn_nodes_{cluster_id}"
        cached_data = self.get_cached_data(cache_key)
        if cached_data is not None:
            return cached_data

        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return []

        yarn_url = cluster['yarn_url']
        try:
            response = self.make_request(f"{yarn_url}/ws/v1/cluster/nodes", cluster)
            if not response:
                return []

            data = response.json()
            nodes = data.get('nodes', {}).get('node', [])

            # Ensure nodes is a list
            if isinstance(nodes, dict):
                nodes = [nodes]

            self.set_cached_data(cache_key, nodes)
            return nodes

        except Exception as e:
            logger.error(f"Error fetching YARN nodes: {e}")
            return []

    def get_cluster_metrics(self, cluster_id: str) -> Dict[str, Any]:
        """Get cluster-level metrics"""
        cluster = self.clusters.get(cluster_id)
        if not cluster:
            return {}

        yarn_url = cluster['yarn_url']
        try:
            response = self.make_request(f"{yarn_url}/ws/v1/cluster/metrics", cluster)
            if response:
                return response.json().get('clusterMetrics', {})
        except Exception as e:
            logger.error(f"Error fetching cluster metrics: {e}")

        return {}

    def analyze_resource_usage(self, cluster_id: str) -> Dict[str, Any]:
        """Enhanced resource analysis"""
        spark_apps = self.get_spark_applications(cluster_id)
        yarn_apps = self.get_yarn_applications(cluster_id)
        nodes = self.get_yarn_nodes(cluster_id)
        cluster_metrics = self.get_cluster_metrics(cluster_id)

        cluster_config = self.clusters.get(cluster_id, {})
        thresholds = cluster_config.get('thresholds', {})

        analysis = {
            'cluster_id': cluster_id,
            'cluster_name': cluster_config.get('name', cluster_id),
            'timestamp': datetime.now().isoformat(),
            'spark_apps': spark_apps,
            'yarn_apps': yarn_apps,
            'nodes': nodes,
            'cluster_metrics': cluster_metrics,
            'summary': self._generate_enhanced_summary(spark_apps, yarn_apps, nodes, cluster_metrics, thresholds),
            'recommendations': self._generate_recommendations(spark_apps, yarn_apps, nodes, thresholds),
            'alerts': self._generate_alerts(spark_apps, yarn_apps, nodes, thresholds)
        }

        return analysis

    def _generate_enhanced_summary(self, spark_apps, yarn_apps, nodes, cluster_metrics, thresholds):
        """Generate enhanced summary with more metrics"""
        summary = {
            'total_spark_apps': len(spark_apps) if spark_apps else 0,
            'total_yarn_apps': len(yarn_apps) if yarn_apps else 0,
            'running_apps': 0,
            'failed_apps': 0,
            'completed_apps': 0,
            'pending_apps': 0,
            'long_running_apps': [],
            'resource_heavy_apps': [],
            'failed_apps_list': [],
            'node_status': {'RUNNING': 0, 'LOST': 0, 'UNHEALTHY': 0, 'DECOMMISSIONED': 0, 'NEW': 0},
            'total_memory_used': 0,
            'total_memory_available': cluster_metrics.get('totalMB', 0),
            'total_vcores_used': 0,
            'total_vcores_available': cluster_metrics.get('totalVirtualCores', 0),
            'memory_utilization': 0,
            'vcores_utilization': 0,
            'active_nodes': cluster_metrics.get('activeNodes', 0),
            'total_nodes': cluster_metrics.get('totalNodes', 0)
        }

        # Analyze YARN applications
        if yarn_apps:
            for app in yarn_apps:
                state = app.get('state', '')
                final_status = app.get('finalStatus', '')

                if state == 'RUNNING':
                    summary['running_apps'] += 1
                elif state in ['FAILED', 'KILLED']:
                    summary['failed_apps'] += 1
                    summary['failed_apps_list'].append({
                        'name': app.get('name', 'Unknown'),
                        'id': app.get('id'),
                        'finalStatus': final_status,
                        'user': app.get('user', 'Unknown'),
                        'startedTime': app.get('startedTime', 0)
                    })
                elif state == 'FINISHED':
                    summary['completed_apps'] += 1
                elif state in ['NEW', 'SUBMITTED', 'ACCEPTED']:
                    summary['pending_apps'] += 1

                # Check for long running apps
                elapsed_time = app.get('elapsedTime', 0)
                if elapsed_time > thresholds.get('max_long_running_hours', 2) * 3600 * 1000:  # Convert hours to ms
                    summary['long_running_apps'].append({
                        'name': app.get('name', 'Unknown'),
                        'id': app.get('id'),
                        'duration_hours': elapsed_time / (3600 * 1000),
                        'user': app.get('user', 'Unknown'),
                        'state': state
                    })

                # Sum up resource usage
                allocated_mb = app.get('allocatedMB', 0)
                allocated_vcores = app.get('allocatedVCores', 0)

                summary['total_memory_used'] += allocated_mb
                summary['total_vcores_used'] += allocated_vcores

                # Check for resource heavy apps
                max_memory_mb = thresholds.get('max_memory_gb', 100) * 1024
                if allocated_mb > max_memory_mb or allocated_vcores > 50:
                    summary['resource_heavy_apps'].append({
                        'name': app.get('name', 'Unknown'),
                        'id': app.get('id'),
                        'memory_mb': allocated_mb,
                        'memory_gb': allocated_mb / 1024,
                        'vcores': allocated_vcores,
                        'user': app.get('user', 'Unknown')
                    })

        # Analyze nodes
        if nodes:
            for node in nodes:
                state = node.get('state', 'UNKNOWN')
                if state in summary['node_status']:
                    summary['node_status'][state] += 1
                else:
                    summary['node_status']['UNKNOWN'] = summary['node_status'].get('UNKNOWN', 0) + 1

        # Calculate utilization percentages
        if summary['total_memory_available'] > 0:
            summary['memory_utilization'] = (summary['total_memory_used'] / summary['total_memory_available']) * 100

        if summary['total_vcores_available'] > 0:
            summary['vcores_utilization'] = (summary['total_vcores_used'] / summary['total_vcores_available']) * 100

        return summary

    def _generate_recommendations(self, spark_apps, yarn_apps, nodes, thresholds):
        """Generate actionable recommendations"""
        recommendations = []

        # Memory usage recommendations
        total_memory_used = sum(app.get('allocatedMB', 0) for app in yarn_apps or [])
        if total_memory_used > thresholds.get('max_memory_gb', 100) * 1024:
            recommendations.append({
                'type': 'resource',
                'severity': 'high',
                'message': f"High memory usage: {total_memory_used / 1024:.1f}GB. Consider optimizing applications or scaling cluster.",
                'action': 'Review application memory configurations and consider cluster scaling'
            })

        # Long running applications
        long_running = [app for app in yarn_apps or []
                        if app.get('elapsedTime', 0) > thresholds.get('max_long_running_hours', 2) * 3600 * 1000]
        if long_running:
            recommendations.append({
                'type': 'performance',
                'severity': 'medium',
                'message': f"{len(long_running)} long-running applications detected.",
                'action': 'Review applications for potential Spark session leaks or optimization opportunities'
            })

        # Failed applications
        failed_count = len([app for app in yarn_apps or [] if app.get('state') in ['FAILED', 'KILLED']])
        if failed_count > thresholds.get('max_failed_apps', 5):
            recommendations.append({
                'type': 'reliability',
                'severity': 'high',
                'message': f"{failed_count} failed applications detected.",
                'action': 'Check application logs and cluster health'
            })

        # Node health
        unhealthy_nodes = sum(1 for node in nodes or []
                              if node.get('state') in ['UNHEALTHY', 'LOST', 'DECOMMISSIONED'])
        if unhealthy_nodes > 0:
            recommendations.append({
                'type': 'infrastructure',
                'severity': 'high',
                'message': f"{unhealthy_nodes} unhealthy nodes detected.",
                'action': 'Check cluster infrastructure and node health'
            })

        if not recommendations:
            recommendations.append({
                'type': 'status',
                'severity': 'info',
                'message': "Cluster appears to be running optimally.",
                'action': 'Continue monitoring'
            })

        return recommendations

    def _generate_alerts(self, spark_apps, yarn_apps, nodes, thresholds):
        """Generate alerts for critical issues"""
        alerts = []

        # Critical resource usage
        total_memory_used = sum(app.get('allocatedMB', 0) for app in yarn_apps or [])
        if total_memory_used > thresholds.get('max_memory_gb', 100) * 1024 * 1.5:  # 150% of threshold
            alerts.append({
                'level': 'critical',
                'message': f"Critical memory usage: {total_memory_used / 1024:.1f}GB",
                'timestamp': datetime.now().isoformat()
            })

        # Multiple node failures
        failed_nodes = sum(1 for node in nodes or [] if node.get('state') in ['LOST', 'DECOMMISSIONED'])
        if failed_nodes > 2:
            alerts.append({
                'level': 'critical',
                'message': f"Multiple node failures: {failed_nodes} nodes",
                'timestamp': datetime.now().isoformat()
            })

        return alerts


# Initialize monitor
monitor = EnhancedEMRMonitor()


@app.route('/')
def index():
    """Main dashboard page"""
    clusters = monitor.clusters
    return render_template('dashboard.html', clusters=clusters)


@app.route('/api/clusters')
def get_clusters():
    """API endpoint to get available clusters"""
    return jsonify(monitor.clusters)


@app.route('/api/monitor/<cluster_id>')
def monitor_cluster(cluster_id):
    """API endpoint to get monitoring data for a specific cluster"""
    try:
        analysis = monitor.analyze_resource_usage(cluster_id)
        return jsonify(analysis)
    except Exception as e:
        logger.error(f"Error monitoring cluster {cluster_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/spark/<cluster_id>')
def get_spark_data(cluster_id):
    """API endpoint to get Spark application data"""
    try:
        apps = monitor.get_spark_applications(cluster_id)
        return jsonify(apps)
    except Exception as e:
        logger.error(f"Error getting Spark data for {cluster_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/yarn/<cluster_id>')
def get_yarn_data(cluster_id):
    """API endpoint to get YARN application data"""
    try:
        apps = monitor.get_yarn_applications(cluster_id)
        return jsonify(apps)
    except Exception as e:
        logger.error(f"Error getting YARN data for {cluster_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/nodes/<cluster_id>')
def get_nodes_data(cluster_id):
    """API endpoint to get YARN nodes data"""
    try:
        nodes = monitor.get_yarn_nodes(cluster_id)
        return jsonify(nodes)
    except Exception as e:
        logger.error(f"Error getting nodes data for {cluster_id}: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'clusters_configured': len(monitor.clusters)
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=6001)