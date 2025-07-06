from flask import Flask, render_template, request, jsonify
import requests
import json
import yaml
import os
from datetime import datetime

app = Flask(__name__)


def load_apps_config():
    """Load Flask apps configuration from YAML file"""
    config_file = 'config/apps.yaml'

    if not os.path.exists(config_file):
        # Create default config if it doesn't exist
        os.makedirs('config', exist_ok=True)
        default_config = {
            'flask_apps': [
                {
                    'name': 'User Management App',
                    'url': 'http://localhost:5001',
                    'description': 'Handles user registration and authentication',
                    'status': 'active',
                    'icon': '👤',
                    'category': 'backend'
                },
                {
                    'name': 'Data Analytics Dashboard',
                    'url': 'http://localhost:5002',
                    'description': 'Analytics and reporting dashboard',
                    'status': 'active',
                    'icon': '📊',
                    'category': 'frontend'
                },
                {
                    'name': 'File Manager',
                    'url': 'http://localhost:5003',
                    'description': 'File upload and management system',
                    'status': 'active',
                    'icon': '📁',
                    'category': 'utility'
                },
                {
                    'name': 'API Gateway',
                    'url': 'http://localhost:5004',
                    'description': 'Central API management service',
                    'status': 'active',
                    'icon': '🌐',
                    'category': 'backend'
                },
                {
                    'name': 'Task Scheduler',
                    'url': 'http://localhost:5005',
                    'description': 'Background task management',
                    'status': 'maintenance',
                    'icon': '⏰',
                    'category': 'service'
                }
            ]
        }

        with open(config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False, indent=2)

        print(f"Created default config file: {config_file}")
        return default_config['flask_apps']

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
            return config.get('flask_apps', [])
    except Exception as e:
        print(f"Error loading config file: {e}")
        return []


# Load Flask apps configuration
FLASK_APPS = load_apps_config()


def check_app_status(url):
    """Check if a Flask app is running"""
    try:
        response = requests.get(url, timeout=5)
        return 'online' if response.status_code == 200 else 'offline'
    except:
        return 'offline'


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html', apps=FLASK_APPS)


@app.route('/proxy/<path:app_name>')
def proxy_app(app_name):
    """Proxy page for embedding apps"""
    # Find the app by name
    target_app = None
    for app_config in FLASK_APPS:
        if app_config['name'].lower().replace(' ', '-') == app_name.lower():
            target_app = app_config
            break

    if not target_app:
        return "App not found", 404

    return render_template('proxy.html', app=target_app)


@app.route('/api/apps')
def get_apps():
    """API endpoint to get all apps with their current status"""
    apps_with_status = []
    for app_config in FLASK_APPS.copy():
        app_config['current_status'] = check_app_status(app_config['url'])
        apps_with_status.append(app_config)

    return jsonify(apps_with_status)


@app.route('/api/apps/<app_name>/status')
def get_app_status(app_name):
    """Get status of a specific app"""
    for app_config in FLASK_APPS:
        if app_config['name'].lower().replace(' ', '-') == app_name.lower():
            status = check_app_status(app_config['url'])
            return jsonify({
                'name': app_config['name'],
                'url': app_config['url'],
                'status': status,
                'timestamp': datetime.now().isoformat()
            })

    return jsonify({'error': 'App not found'}), 404


@app.route('/reload-config')
def reload_config():
    """Reload configuration from YAML file"""
    global FLASK_APPS
    FLASK_APPS = load_apps_config()
    return jsonify({
        'message': 'Configuration reloaded successfully',
        'apps_count': len(FLASK_APPS),
        'timestamp': datetime.now().isoformat()
    })


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'managed_apps': len(FLASK_APPS)
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)