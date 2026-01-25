"""
AWS Monitor - Simplified
Multi-region resource monitoring with script generation
"""
from flask import Flask, render_template, jsonify, request, send_file
from app.resources import ResourceMonitor
from app.script_generator import ScriptGenerator
import logging
import io

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Default regions (auto-selected when UI starts)
DEFAULT_REGIONS = ['us-east-1', 'us-west-2']


@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')


@app.route('/api/discover', methods=['POST'])
def discover_resources():
    """
    Discover all resources across regions
    POST body: {
        "regions": ["us-east-1", "us-west-2"],
        "filters": {
            "tags": {"Environment": "production"},
            "names": ["web-server"],
            "ids": ["i-1234567"]
        }
    }
    """
    data = request.get_json()
    regions = data.get('regions', DEFAULT_REGIONS)
    filters = data.get('filters', {})
    
    try:
        monitor = ResourceMonitor()
        resources = monitor.discover_all(regions, filters)
        return jsonify(resources)
    except Exception as e:
        logger.error(f"Discovery error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/metrics', methods=['POST'])
def get_metrics():
    """
    Get performance metrics for resources
    POST body: {
        "resources": [{"type": "ec2", "id": "i-123", "region": "us-east-1"}],
        "period": 300
    }
    """
    data = request.get_json()
    resources = data.get('resources', [])
    period = data.get('period', 300)
    
    try:
        monitor = ResourceMonitor()
        metrics = monitor.get_metrics(resources, period)
        return jsonify(metrics)
    except Exception as e:
        logger.error(f"Metrics error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/costs', methods=['POST'])
def analyze_costs():
    """
    Analyze costs
    POST body: {
        "regions": ["us-east-1"],
        "days": 30
    }
    """
    data = request.get_json()
    regions = data.get('regions', DEFAULT_REGIONS)
    days = data.get('days', 7)
    
    try:
        monitor = ResourceMonitor()
        costs = monitor.analyze_costs(regions, days)
        return jsonify(costs)
    except Exception as e:
        logger.error(f"Cost error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts', methods=['POST'])
def check_alerts():
    """
    Check alerts and failures
    POST body: {
        "resources": [...],
        "thresholds": {"cpu": 80, "memory": 85}
    }
    """
    data = request.get_json()
    resources = data.get('resources', [])
    thresholds = data.get('thresholds', {})
    
    try:
        monitor = ResourceMonitor()
        alerts = monitor.check_alerts(resources, thresholds)
        return jsonify(alerts)
    except Exception as e:
        logger.error(f"Alert error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate-script', methods=['POST'])
def generate_script():
    """
    Generate Python monitoring script for cron/scheduler
    POST body: {
        "regions": ["us-east-1"],
        "resources": {
            "types": ["ec2", "rds"],
            "filters": {"tags": {}, "names": [], "ids": []}
        },
        "checks": ["performance", "cost", "alerts"],
        "thresholds": {"cpu": 80},
        "notification": {"email": "user@example.com"}
    }
    """
    data = request.get_json()
    
    try:
        generator = ScriptGenerator()
        script_content = generator.generate(data)
        
        # Return as downloadable file
        buffer = io.BytesIO(script_content.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='text/x-python',
            as_attachment=True,
            download_name='aws_monitor_job.py'
        )
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/regions')
def list_regions():
    """Get available AWS regions"""
    try:
        monitor = ResourceMonitor()
        regions = monitor.get_regions()
        return jsonify({'regions': regions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
