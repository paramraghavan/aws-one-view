from flask import Flask, render_template, jsonify, request, session
from flask_cors import CORS
from flask_session import Session
import requests
import json
import yaml
import os
from datetime import datetime, timedelta

# Create Flask app
app = Flask(__name__)
app.secret_key = 'emr-monitor-secret-key'
CORS(app)


class EMRMonitor:
    def __init__(self, config_path='config.yaml'):
        self.config_path = config_path
        self.clusters = {}
        self.load_config()

    def load_config(self):
        """Load EMR cluster configurations from YAML or JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    if self.config_path.endswith('.yaml') or self.config_path.endswith('.yml'):
                        self.clusters = yaml.safe_load(f)
                    else:
                        self.clusters = json.load(f)
            else:
                # Default configuration if file doesn't exist
                self.clusters = {
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
                print("⚠️  Using default cluster configuration. Create config.yaml for custom clusters.")
        except Exception as e:
            print(f"Error loading config: {e}")
            self.clusters = {}

    def get_spark_applications(self, cluster_id):
        """Get Spark applications from Spark History Server"""
        try:
            cluster = self.clusters.get(cluster_id)
            if not cluster:
                return {"error": "Cluster not found"}

            spark_url = cluster['spark_url']

            # Get running applications
            running_url = f"{spark_url}/api/v1/applications"
            response = requests.get(running_url, timeout=10)
            applications = response.json() if response.status_code == 200 else []

            # Enhance with additional details
            enhanced_apps = []
            for app in applications:
                try:
                    app_id = app['id']
                    # Get detailed application info
                    detail_url = f"{spark_url}/api/v1/applications/{app_id}"
                    detail_response = requests.get(detail_url, timeout=5)

                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        app.update(detail_data)

                    # Get executors info
                    exec_url = f"{spark_url}/api/v1/applications/{app_id}/executors"
                    exec_response = requests.get(exec_url, timeout=5)

                    if exec_response.status_code == 200:
                        executors = exec_response.json()
                        app['executors'] = executors
                        app['total_cores'] = sum(exec.get('totalCores', 0) for exec in executors)
                        app['total_memory'] = sum(exec.get('maxMemory', 0) for exec in executors)

                    enhanced_apps.append(app)

                except Exception as e:
                    print(f"Error getting details for app {app.get('id', 'unknown')}: {e}")
                    enhanced_apps.append(app)

            return enhanced_apps

        except Exception as e:
            return {"error": str(e)}

    def get_yarn_applications(self, cluster_id):
        """Get YARN applications"""
        try:
            cluster = self.clusters.get(cluster_id)
            if not cluster:
                return {"error": "Cluster not found"}

            yarn_url = cluster['yarn_url']

            # Get YARN applications
            apps_url = f"{yarn_url}/ws/v1/cluster/apps"
            response = requests.get(apps_url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                return data.get('apps', {}).get('app', [])

            return []

        except Exception as e:
            return {"error": str(e)}

    def get_cluster_metrics(self, cluster_id):
        """Get cluster resource metrics from YARN"""
        try:
            cluster = self.clusters.get(cluster_id)
            if not cluster:
                return {"error": "Cluster not found"}

            yarn_url = cluster['yarn_url']

            # Get cluster metrics
            metrics_url = f"{yarn_url}/ws/v1/cluster/metrics"
            response = requests.get(metrics_url, timeout=10)

            if response.status_code == 200:
                return response.json().get('clusterMetrics', {})

            return {}

        except Exception as e:
            return {"error": str(e)}

    def identify_problematic_jobs(self, cluster_id):
        """Identify jobs that might be hogging resources"""
        try:
            spark_apps = self.get_spark_applications(cluster_id)
            yarn_apps = self.get_yarn_applications(cluster_id)

            if isinstance(spark_apps, dict) and "error" in spark_apps:
                return spark_apps

            problematic_jobs = []

            for app in spark_apps:
                issues = []

                # Check for long-running jobs
                if app.get('attempts'):
                    start_time = app['attempts'][0].get('startTime')
                    if start_time:
                        start_dt = datetime.fromtimestamp(start_time / 1000)
                        duration = datetime.now() - start_dt
                        if duration.total_seconds() > 3600:  # More than 1 hour
                            issues.append(f"Long running: {duration}")

                # Check for high resource usage with low utilization
                if app.get('executors'):
                    total_cores = app.get('total_cores', 0)
                    active_tasks = sum(exec.get('activeTasks', 0) for exec in app['executors'])

                    if total_cores > 10 and active_tasks == 0:
                        issues.append("High resource allocation with no active tasks")

                    # Check for zombie executors
                    failed_executors = sum(1 for exec in app['executors'] if exec.get('isBlacklisted', False))
                    if failed_executors > 0:
                        issues.append(f"Failed/blacklisted executors: {failed_executors}")

                if issues:
                    problematic_jobs.append({
                        'app': app,
                        'issues': issues
                    })

            return problematic_jobs

        except Exception as e:
            return {"error": str(e)}


# Initialize EMR Monitor at module level (global scope)
monitor = EMRMonitor()


def add_session_persistence(app):
    """Add persistent session storage to EMR monitor"""
    sessions_dir = os.path.join(os.path.dirname(__file__), 'flask_sessions')
    os.makedirs(sessions_dir, exist_ok=True)

    app.config.update(
        SESSION_TYPE='filesystem',
        SESSION_FILE_DIR=sessions_dir,
        SESSION_PERMANENT=True,
        SESSION_USE_SIGNER=True,
        SESSION_KEY_PREFIX='emr_monitor:',
        PERMANENT_SESSION_LIFETIME=86400 * 30  # 30 days
    )

    Session(app)
    print(f"✅ Session persistence enabled: {sessions_dir}")
    return app


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', clusters=monitor.clusters)


@app.route('/api/clusters')
def get_clusters():
    """Get list of available clusters"""
    return jsonify(monitor.clusters)


@app.route('/api/cluster/<cluster_id>/spark-apps')
def get_spark_apps(cluster_id):
    """Get Spark applications for a cluster"""
    apps = monitor.get_spark_applications(cluster_id)
    return jsonify(apps)


@app.route('/api/cluster/<cluster_id>/yarn-apps')
def get_yarn_apps(cluster_id):
    """Get YARN applications for a cluster"""
    apps = monitor.get_yarn_applications(cluster_id)
    return jsonify(apps)


@app.route('/api/cluster/<cluster_id>/metrics')
def get_cluster_metrics(cluster_id):
    """Get cluster metrics"""
    metrics = monitor.get_cluster_metrics(cluster_id)
    return jsonify(metrics)


@app.route('/api/cluster/<cluster_id>/problematic-jobs')
def get_problematic_jobs(cluster_id):
    """Get jobs that might be causing issues"""
    jobs = monitor.identify_problematic_jobs(cluster_id)
    return jsonify(jobs)


@app.route('/api/pin-cluster', methods=['POST'])
def pin_cluster():
    """Pin a cluster as favorite"""
    data = request.get_json()
    cluster_id = data.get('cluster_id')

    if 'pinned_clusters' not in session:
        session['pinned_clusters'] = []

    if cluster_id not in session['pinned_clusters']:
        session['pinned_clusters'].append(cluster_id)

    return jsonify({"status": "success", "pinned_clusters": session['pinned_clusters']})


@app.route('/api/unpin-cluster', methods=['POST'])
def unpin_cluster():
    """Unpin a cluster"""
    data = request.get_json()
    cluster_id = data.get('cluster_id')

    if 'pinned_clusters' in session and cluster_id in session['pinned_clusters']:
        session['pinned_clusters'].remove(cluster_id)

    return jsonify({"status": "success", "pinned_clusters": session.get('pinned_clusters', [])})


@app.route('/api/pinned-clusters')
def get_pinned_clusters():
    """Get user's pinned clusters"""
    return jsonify(session.get('pinned_clusters', []))


@app.route('/api/reload-config')
def reload_config():
    """Reload cluster configuration from file"""
    monitor.load_config()
    return jsonify({
        "status": "success",
        "message": "Configuration reloaded",
        "clusters": monitor.clusters
    })

"""
# pip install flask flask-cors flask-session requests pyyaml
"""
if __name__ == '__main__':
    print("🚀 EMR Monitor Starting...")
    print(f"📡 Monitoring {len(monitor.clusters)} EMR clusters:")

    for cluster_id, cluster_info in monitor.clusters.items():
        print(f"  • {cluster_info['name']} ({cluster_id})")

    # Add session persistence
    app = add_session_persistence(app)

    print("✅ EMR Monitor ready with persistent sessions")
    print("🌐 Visit: http://localhost:5000")

    app.run(debug=True, host='0.0.0.0', port=5000)