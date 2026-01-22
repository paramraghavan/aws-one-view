"""
AWS Resource Monitor - Main Application
A Flask web application for monitoring AWS resources, costs, and performance.
"""

from flask import Flask, render_template, request, jsonify
from typing import Dict, List, Any
import logging

from app.aws_client import AWSClient
from app.config import Config
from app.monitoring import monitor

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize AWS client
aws_client = AWSClient()

# Start background monitoring if enabled
if Config.MONITORING_ENABLED:
    monitor.start()
    logger.info("Background monitoring enabled")


@app.route('/')
def index() -> str:
    """Render the main dashboard page."""
    return render_template('index.html')


@app.route('/api/regions', methods=['GET'])
def get_regions() -> Dict[str, Any]:
    """
    Get list of all available AWS regions.
    
    Returns:
        JSON response with list of regions
    """
    try:
        regions = aws_client.get_regions()
        return jsonify({
            'success': True,
            'data': regions
        })
    except Exception as e:
        logger.error(f"Error getting regions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/resources', methods=['GET'])
def get_resources() -> Dict[str, Any]:
    """
    Get all AWS resources from selected regions.
    
    Query Parameters:
        regions: List of region names (e.g., ?regions=us-east-1&regions=us-west-2)
    
    Returns:
        JSON response with categorized resources
    """
    try:
        regions = request.args.getlist('regions')
        if not regions:
            regions = [Config.DEFAULT_REGION]
        
        logger.info(f"Loading resources from regions: {regions}")
        resources = aws_client.get_all_resources(regions)
        
        return jsonify({
            'success': True,
            'data': resources
        })
    except Exception as e:
        logger.error(f"Error getting resources: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/metrics', methods=['GET'])
def get_metrics() -> Dict[str, Any]:
    """
    Get CloudWatch metrics for selected resources.
    
    Query Parameters:
        resource_ids: List of resource IDs
        resource_type: Type of resource (ec2, rds, lambda)
        region: AWS region
        hours: Number of hours of data (default: 24)
    
    Returns:
        JSON response with metrics data
    """
    try:
        resource_ids = request.args.getlist('resource_ids')
        resource_type = request.args.get('resource_type', 'ec2')
        region = request.args.get('region', Config.DEFAULT_REGION)
        hours = int(request.args.get('hours', 24))
        
        metrics = aws_client.get_metrics(
            resource_type=resource_type,
            resource_ids=resource_ids,
            region=region,
            hours=hours
        )
        
        return jsonify({
            'success': True,
            'data': metrics
        })
    except Exception as e:
        logger.error(f"Error getting metrics: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/costs', methods=['GET'])
def get_costs() -> Dict[str, Any]:
    """
    Get AWS cost data from Cost Explorer.
    
    Query Parameters:
        days: Number of days to retrieve (default: 30)
    
    Returns:
        JSON response with cost data
    """
    try:
        days = int(request.args.get('days', 30))
        costs = aws_client.get_costs(days=days)
        
        return jsonify({
            'success': True,
            'data': costs
        })
    except Exception as e:
        logger.error(f"Error getting costs: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/resource/details', methods=['GET'])
def get_resource_details() -> Dict[str, Any]:
    """
    Get detailed information about a specific resource.
    
    Query Parameters:
        resource_id: Resource identifier
        resource_type: Type of resource (ec2, rds, lambda, s3, ebs)
        region: AWS region
    
    Returns:
        JSON response with detailed resource information
    """
    try:
        resource_id = request.args.get('resource_id')
        resource_type = request.args.get('resource_type')
        region = request.args.get('region', Config.DEFAULT_REGION)
        
        if not resource_id or not resource_type:
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: resource_id, resource_type'
            }), 400
        
        details = aws_client.get_resource_details(resource_id, resource_type, region)
        
        return jsonify({
            'success': True,
            'data': details
        })
    except Exception as e:
        logger.error(f"Error getting resource details: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bottlenecks', methods=['GET'])
def detect_bottlenecks() -> Dict[str, Any]:
    """
    Detect resource bottlenecks and optimization opportunities.
    
    Query Parameters:
        region: AWS region to scan (default: us-east-1)
    
    Returns:
        JSON response with bottleneck information
    """
    try:
        region = request.args.get('region', Config.DEFAULT_REGION)
        bottlenecks = aws_client.detect_bottlenecks(region)
        
        return jsonify({
            'success': True,
            'data': bottlenecks
        })
    except Exception as e:
        logger.error(f"Error detecting bottlenecks: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# MONITORING ENDPOINTS
# ============================================================================

@app.route('/api/monitoring/status', methods=['GET'])
def get_monitoring_status() -> Dict[str, Any]:
    """
    Get current monitoring status.
    
    Returns:
        JSON with monitoring enabled status and monitored resources
    """
    return jsonify({
        'success': True,
        'data': {
            'enabled': monitor.monitoring_enabled,
            'interval_minutes': Config.MONITORING_INTERVAL_MINUTES,
            'monitored_resources': monitor.get_monitored_resources()
        }
    })


@app.route('/api/monitoring/start', methods=['POST'])
def start_monitoring() -> Dict[str, Any]:
    """Start background monitoring."""
    try:
        monitor.start()
        return jsonify({
            'success': True,
            'message': 'Monitoring started'
        })
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/monitoring/stop', methods=['POST'])
def stop_monitoring() -> Dict[str, Any]:
    """Stop background monitoring."""
    try:
        monitor.stop()
        return jsonify({
            'success': True,
            'message': 'Monitoring stopped'
        })
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/monitoring/add', methods=['POST'])
def add_monitored_resource() -> Dict[str, Any]:
    """
    Add a resource to monitor.
    
    Request Body:
        {
            "id": "i-1234567890",
            "type": "ec2",
            "region": "us-east-1",
            "cpu_threshold": 80  // optional
        }
    """
    try:
        resource = request.get_json()
        
        # Validate required fields
        required = ['id', 'type', 'region']
        if not all(k in resource for k in required):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: id, type, region'
            }), 400
        
        monitor.add_resource(resource)
        
        return jsonify({
            'success': True,
            'message': f'Added {resource["id"]} to monitoring'
        })
    except Exception as e:
        logger.error(f"Error adding monitored resource: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/monitoring/remove/<resource_id>', methods=['DELETE'])
def remove_monitored_resource(resource_id: str) -> Dict[str, Any]:
    """Remove a resource from monitoring."""
    try:
        monitor.remove_resource(resource_id)
        return jsonify({
            'success': True,
            'message': f'Removed {resource_id} from monitoring'
        })
    except Exception as e:
        logger.error(f"Error removing monitored resource: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/alerts/test', methods=['POST'])
def test_alert() -> Dict[str, Any]:
    """Send a test alert email."""
    try:
        from app.alerts import AlertManager
        alert_manager = AlertManager()
        alert_manager.test_alert()
        
        return jsonify({
            'success': True,
            'message': 'Test alert sent'
        })
    except Exception as e:
        logger.error(f"Error sending test alert: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )
