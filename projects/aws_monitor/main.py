"""
AWS Monitor - Simplified
Multi-region resource monitoring with script generation
"""
from flask import Flask, render_template, jsonify, request, send_file, make_response
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


@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring and load balancers
    Returns 200 if healthy, 503 if unhealthy
    """
    try:
        from datetime import datetime
        health_status = {
            'status': 'healthy',
            'service': 'aws-monitor',
            'version': '1.3.0',
            'timestamp': datetime.utcnow().isoformat()
        }
        return jsonify(health_status), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503


@app.route('/api/status')
def api_status():
    """
    Detailed status endpoint for admins
    Returns application status and statistics
    """
    from datetime import datetime
    import time
    
    try:
        status = {
            'service': 'aws-monitor',
            'version': '1.3.0',
            'status': 'running',
            'aws_profile': 'monitor',
            'role_arn': ROLE_ARN or 'none',
            'default_regions': DEFAULT_REGIONS,
            'timestamp': datetime.utcnow().isoformat(),
            'directories': {
                'logs': os.path.exists('logs'),
                'output': os.path.exists('output'),
                'configs': os.path.exists('configs')
            }
        }
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/discover', methods=['POST'])
def discover_resources():
    """
    Discover all resources across regions
    POST body: {
        "regions": ["us-east-1", "us-west-2"],
        "resource_types": ["ec2", "rds", "s3"],  # Optional
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
    resource_types = data.get('resource_types', None)  # None = discover all
    
    try:
        monitor = ResourceMonitor(role_arn=ROLE_ARN, session_name=SESSION_NAME)
        resources = monitor.discover_all(regions, filters, resource_types)
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
        
        # Return as JSON with script content
        # This avoids browser security issues with file downloads over HTTP
        return jsonify({
            'success': True,
            'script': script_content,
            'filename': 'aws_monitor_job.py'
        })
    except Exception as e:
        logger.error(f"Script generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download-script', methods=['POST'])
def download_script():
    """
    Alternative endpoint that forces file download
    For use when browser allows it
    """
    data = request.get_json()
    
    try:
        generator = ScriptGenerator()
        script_content = generator.generate(data, role_arn=ROLE_ARN, session_name=SESSION_NAME)
        
        # Create response with proper headers for download
        response = make_response(script_content)
        response.headers['Content-Type'] = 'text/plain; charset=utf-8'
        response.headers['Content-Disposition'] = 'attachment; filename=aws_monitor_job.py'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        return response
    except Exception as e:
        logger.error(f"Script download error: {e}")
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
    
    parser.add_argument(
        '--ssl',
        action='store_true',
        help='Run with HTTPS using self-signed certificate (for development)'
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
    
    # Setup SSL if requested
    ssl_context = None
    if args.ssl:
        import ssl
        import os
        
        cert_file = 'certs/cert.pem'
        key_file = 'certs/key.pem'
        
        if os.path.exists(cert_file) and os.path.exists(key_file):
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(cert_file, key_file)
            logger.info(f"✅ Running with HTTPS (self-signed certificate)")
            logger.info(f"Server: https://{args.host}:{args.port}")
            logger.info(f"⚠️  Browser will show security warning - click 'Advanced' and 'Proceed to localhost'")
        else:
            logger.error(f"❌ SSL certificate files not found!")
            logger.error(f"Expected: {cert_file} and {key_file}")
            logger.error(f"Run './generate_cert.sh' to create certificates")
            sys.exit(1)
    else:
        logger.info(f"Server: http://{args.host}:{args.port}")
        logger.info(f"⚠️  Running with HTTP - file downloads may be blocked by browser")
        logger.info(f"💡 Use --ssl flag for HTTPS: python main.py --ssl")
    
    # Run Flask app
    app.run(host=args.host, port=args.port, debug=args.debug, ssl_context=ssl_context)
