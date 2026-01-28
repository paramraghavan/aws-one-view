"""
AWS Monitor - Simplified
Multi-region resource monitoring with script generation
"""
from flask import Flask, render_template, jsonify, request, send_file
from app.resources import ResourceMonitor
from app.script_generator import ScriptGenerator
import logging
import io
import argparse
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Default regions (auto-selected when UI starts)
DEFAULT_REGIONS = ['us-east-1', 'us-west-2']

# Global configuration for role ARN (set from command line)
ROLE_ARN = None
SESSION_NAME = None


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
        monitor = ResourceMonitor(role_arn=ROLE_ARN, session_name=SESSION_NAME)
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
        monitor = ResourceMonitor(role_arn=ROLE_ARN, session_name=SESSION_NAME)
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
        monitor = ResourceMonitor(role_arn=ROLE_ARN, session_name=SESSION_NAME)
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
        monitor = ResourceMonitor(role_arn=ROLE_ARN, session_name=SESSION_NAME)
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
        script_content = generator.generate(data, role_arn=ROLE_ARN, session_name=SESSION_NAME)
        
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
        monitor = ResourceMonitor(role_arn=ROLE_ARN, session_name=SESSION_NAME)
        regions = monitor.get_regions()
        return jsonify({'regions': regions})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='AWS Monitor - Multi-region resource monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run with base profile only
  python main.py
  
  # Run with elevated role assumption
  python main.py --role-arn arn:aws:iam::123456789012:role/MonitoringRole
  
  # Run with custom session name
  python main.py --role-arn arn:aws:iam::123456789012:role/MonitoringRole --session-name MyMonitorSession
  
  # Run on different port
  python main.py --port 8080
        '''
    )
    
    parser.add_argument(
        '--role-arn',
        type=str,
        help='ARN of IAM role to assume for elevated permissions (optional)'
    )
    
    parser.add_argument(
        '--session-name',
        type=str,
        default='AWSMonitorSession',
        help='Session name for role assumption (default: AWSMonitorSession)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to run Flask app on (default: 5000)'
    )
    
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind Flask app to (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Run Flask in debug mode'
    )
    
    return parser.parse_args()


if __name__ == '__main__':
    # Parse command line arguments
    args = parse_arguments()
    
    # Set global configuration
    ROLE_ARN = args.role_arn
    SESSION_NAME = args.session_name
    
    # Log configuration
    if ROLE_ARN:
        logger.info(f"Starting AWS Monitor with role assumption")
        logger.info(f"Profile: monitor")
        logger.info(f"Role ARN: {ROLE_ARN}")
        logger.info(f"Session Name: {SESSION_NAME}")
    else:
        logger.info("Starting AWS Monitor with base profile: monitor")
    
    logger.info(f"Server: http://{args.host}:{args.port}")
    
    # Run Flask app
    app.run(host=args.host, port=args.port, debug=args.debug)
