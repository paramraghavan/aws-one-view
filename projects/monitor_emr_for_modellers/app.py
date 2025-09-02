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
        """Get all Spark applications from the cluster"""
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

            # Enrich with additional details
            for app in all_apps:
                try:
                    app_id = app['id']
                    detail_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}"
                    detail_response = self.session.get(detail_url)
                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        app.update(detail_data)

                    # Get executor information
                    executor_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/executors"
                    executor_response = self.session.get(executor_url)
                    if executor_response.status_code == 200:
                        app['executors'] = executor_response.json()

                except Exception as e:
                    logging.warning(f"Failed to get details for app {app.get('id', 'unknown')}: {e}")

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
        """Get application logs"""
        cluster = self.config.get(cluster_key)
        if not cluster:
            return None

        try:
            # Try to get Spark application logs
            logs_url = f"{cluster['spark_url']}/api/v1/applications/{app_id}/logs"
            response = self.session.get(logs_url)
            if response.status_code == 200:
                return response.text

            # Fallback to YARN logs
            yarn_logs_url = f"{cluster['yarn_url']}/ws/v1/cluster/apps/{app_id}/logs"
            yarn_response = self.session.get(yarn_logs_url)
            if yarn_response.status_code == 200:
                return yarn_response.text

            return None
        except Exception as e:
            logging.error(f"Failed to get application logs: {e}")
            return None


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
    """Get applications for a specific cluster"""
    spark_apps = monitor.get_spark_applications(cluster_key)
    yarn_apps = monitor.get_yarn_applications(cluster_key)

    # Combine and enrich data
    apps_data = {
        'spark_applications': spark_apps,
        'yarn_applications': yarn_apps,
        'cluster_info': monitor.get_cluster_info(cluster_key),
        'cluster_metrics': monitor.get_cluster_metrics(cluster_key)
    }

    return jsonify(apps_data)


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
    logs = monitor.get_application_logs(cluster_key, app_id)

    if logs:
        return jsonify({
            'logs': logs,
            'app_id': app_id,
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({'error': 'Logs not found'}), 404


@app.route('/api/cluster/<cluster_key>/application/<app_id>/download_logs')
def download_application_logs(cluster_key, app_id):
    """Download logs for a specific application"""
    logs = monitor.get_application_logs(cluster_key, app_id)

    if logs:
        # Create a zip file with logs
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f'{app_id}_logs.txt', logs)

        memory_file.seek(0)

        return send_file(
            memory_file,
            as_attachment=True,
            download_name=f'{app_id}_logs.zip',
            mimetype='application/zip'
        )
    else:
        return jsonify({'error': 'Logs not found'}), 404


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