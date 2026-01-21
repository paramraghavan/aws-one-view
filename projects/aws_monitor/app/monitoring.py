"""
Background Monitoring - Scheduled resource checks and alerting.
Runs periodic scans and sends alerts when thresholds are exceeded.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
from typing import List, Dict, Any
import logging

from app.aws_client import AWSClient
from app.alerts import AlertManager
from app.config import Config

logger = logging.getLogger(__name__)


class ResourceMonitor:
    """
    Background monitor for AWS resources.
    Periodically checks resources and sends alerts.
    """
    
    def __init__(self):
        """Initialize the monitor with AWS client and alert manager."""
        self.aws_client = AWSClient()
        self.alert_manager = AlertManager()
        self.scheduler = BackgroundScheduler()
        self.monitoring_enabled = False
        
        # Store monitored resources
        self.monitored_resources = []
    
    def start(self):
        """Start background monitoring."""
        if self.monitoring_enabled:
            logger.warning("Monitoring already started")
            return
        
        # Schedule periodic checks
        self.scheduler.add_job(
            func=self.check_resources,
            trigger='interval',
            minutes=Config.MONITORING_INTERVAL_MINUTES,
            id='resource_check',
            name='Check monitored resources',
            replace_existing=True
        )
        
        self.scheduler.start()
        self.monitoring_enabled = True
        logger.info(f"Background monitoring started (every {Config.MONITORING_INTERVAL_MINUTES} minutes)")
    
    def stop(self):
        """Stop background monitoring."""
        if not self.monitoring_enabled:
            return
        
        self.scheduler.shutdown()
        self.monitoring_enabled = False
        logger.info("Background monitoring stopped")
    
    def add_resource(self, resource: Dict[str, Any]):
        """
        Add a resource to monitor.
        
        Args:
            resource: Dict with keys: id, type, region, thresholds
        """
        # Check if already monitoring
        if any(r['id'] == resource['id'] for r in self.monitored_resources):
            logger.warning(f"Already monitoring {resource['id']}")
            return
        
        self.monitored_resources.append(resource)
        logger.info(f"Added {resource['id']} to monitoring")
    
    def remove_resource(self, resource_id: str):
        """Remove a resource from monitoring."""
        self.monitored_resources = [
            r for r in self.monitored_resources if r['id'] != resource_id
        ]
        logger.info(f"Removed {resource_id} from monitoring")
    
    def get_monitored_resources(self) -> List[Dict[str, Any]]:
        """Get list of currently monitored resources."""
        return self.monitored_resources
    
    def check_resources(self):
        """
        Check all monitored resources (runs periodically).
        This is the main monitoring loop.
        """
        if not self.monitored_resources:
            logger.debug("No resources to monitor")
            return
        
        logger.info(f"Checking {len(self.monitored_resources)} monitored resources...")
        alerts = []
        
        for resource in self.monitored_resources:
            try:
                # Check the resource
                issues = self._check_resource(resource)
                
                if issues:
                    alerts.extend(issues)
            
            except Exception as e:
                logger.error(f"Error checking {resource['id']}: {e}")
        
        # Send alerts if any issues found
        if alerts:
            self.alert_manager.send_alert(alerts)
            logger.info(f"Sent {len(alerts)} alerts")
        else:
            logger.info("All resources OK")
    
    def _check_resource(self, resource: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check a single resource for issues.
        
        Args:
            resource: Resource configuration
        
        Returns:
            List of issues found (empty if OK)
        """
        issues = []
        resource_type = resource['type']
        resource_id = resource['id']
        region = resource['region']
        
        # Get metrics for the resource
        try:
            metrics = self.aws_client.get_metrics(
                resource_type=resource_type,
                resource_ids=[resource_id],
                region=region,
                hours=1  # Check last hour
            )
            
            if resource_id not in metrics:
                return issues
            
            resource_metrics = metrics[resource_id]
            
            # Check CPU threshold
            if 'cpu' in resource_metrics and resource_metrics['cpu']:
                avg_cpu = sum(d['Average'] for d in resource_metrics['cpu']) / len(resource_metrics['cpu'])
                max_cpu = max(d['Maximum'] for d in resource_metrics['cpu'])
                
                # Get custom threshold or use default
                cpu_threshold = resource.get('cpu_threshold', Config.CPU_HIGH_THRESHOLD)
                
                if max_cpu > cpu_threshold:
                    issues.append({
                        'resource_id': resource_id,
                        'resource_type': resource_type,
                        'region': region,
                        'metric': 'CPU',
                        'value': round(max_cpu, 2),
                        'threshold': cpu_threshold,
                        'severity': 'critical' if max_cpu > 90 else 'high',
                        'message': f'CPU at {max_cpu:.1f}% (threshold: {cpu_threshold}%)',
                        'timestamp': datetime.utcnow().isoformat()
                    })
            
            # Check connections for RDS
            if resource_type == 'rds' and 'connections' in resource_metrics:
                if resource_metrics['connections']:
                    avg_conn = sum(d['Average'] for d in resource_metrics['connections']) / len(resource_metrics['connections'])
                    conn_threshold = resource.get('connection_threshold', 100)
                    
                    if avg_conn > conn_threshold:
                        issues.append({
                            'resource_id': resource_id,
                            'resource_type': resource_type,
                            'region': region,
                            'metric': 'Connections',
                            'value': round(avg_conn, 0),
                            'threshold': conn_threshold,
                            'severity': 'high',
                            'message': f'Connections at {avg_conn:.0f} (threshold: {conn_threshold})',
                            'timestamp': datetime.utcnow().isoformat()
                        })
        
        except Exception as e:
            logger.error(f"Error getting metrics for {resource_id}: {e}")
        
        return issues


# Global monitor instance
monitor = ResourceMonitor()
