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
from app.cost_reports import CostReportGenerator
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
        self.cost_report_generator = CostReportGenerator()
        self.scheduler = BackgroundScheduler()
        self.monitoring_enabled = False
        
        # Store monitored resources
        self.monitored_resources = []
        
        # Store scheduled cost reports
        self.scheduled_reports = []
    
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
    
    # ============================================================================
    # COST REPORT SCHEDULING
    # ============================================================================
    
    def add_scheduled_report(
        self,
        name: str,
        resources: List[Dict[str, Any]],
        period: str,
        schedule: str
    ):
        """
        Add a scheduled cost report.
        
        Args:
            name: Report name/identifier
            resources: List of resources to include in report
            period: Report period - 'daily', 'weekly', or 'monthly'
            schedule: Schedule string - 'daily', 'weekly_monday', 'monthly_1st', etc.
        """
        if not self.monitoring_enabled:
            logger.warning("Start monitoring before scheduling reports")
            return
        
        # Parse schedule
        trigger_config = self._parse_schedule(schedule)
        
        # Create job
        job_id = f'cost_report_{name}'
        
        self.scheduler.add_job(
            func=self._run_cost_report,
            args=[name, resources, period],
            id=job_id,
            name=f'Cost Report: {name}',
            replace_existing=True,
            **trigger_config
        )
        
        # Store report config
        report_config = {
            'name': name,
            'resources': resources,
            'period': period,
            'schedule': schedule,
            'job_id': job_id,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Remove existing report with same name
        self.scheduled_reports = [r for r in self.scheduled_reports if r['name'] != name]
        self.scheduled_reports.append(report_config)
        
        logger.info(f"Scheduled cost report '{name}' ({period}, {schedule})")
    
    def remove_scheduled_report(self, name: str):
        """Remove a scheduled cost report."""
        self.scheduled_reports = [r for r in self.scheduled_reports if r['name'] != name]
        
        job_id = f'cost_report_{name}'
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed scheduled report: {name}")
        except Exception as e:
            logger.error(f"Error removing report job: {e}")
    
    def get_scheduled_reports(self) -> List[Dict[str, Any]]:
        """Get list of scheduled cost reports."""
        return self.scheduled_reports
    
    def _parse_schedule(self, schedule: str) -> Dict[str, Any]:
        """
        Parse schedule string into APScheduler trigger config.
        
        Supported formats:
        - 'daily' - Every day at 9 AM
        - 'weekly_monday' - Every Monday at 9 AM
        - 'monthly_1st' - 1st of every month at 9 AM
        - 'custom_06:00' - Custom time daily
        """
        if schedule == 'daily':
            return {
                'trigger': 'cron',
                'hour': 9,
                'minute': 0
            }
        elif schedule.startswith('weekly_'):
            day = schedule.split('_')[1].lower()
            day_map = {
                'monday': 0, 'tuesday': 1, 'wednesday': 2,
                'thursday': 3, 'friday': 4, 'saturday': 5, 'sunday': 6
            }
            return {
                'trigger': 'cron',
                'day_of_week': day_map.get(day, 0),
                'hour': 9,
                'minute': 0
            }
        elif schedule == 'monthly_1st':
            return {
                'trigger': 'cron',
                'day': 1,
                'hour': 9,
                'minute': 0
            }
        elif schedule.startswith('custom_'):
            time_str = schedule.split('_')[1]
            hour, minute = map(int, time_str.split(':'))
            return {
                'trigger': 'cron',
                'hour': hour,
                'minute': minute
            }
        else:
            # Default to daily
            return {
                'trigger': 'cron',
                'hour': 9,
                'minute': 0
            }
    
    def _run_cost_report(self, name: str, resources: List[Dict], period: str):
        """Execute a scheduled cost report."""
        logger.info(f"Running scheduled cost report: {name}")
        
        try:
            report = self.cost_report_generator.generate_report(
                resources=resources,
                period=period,
                send_email=True
            )
            logger.info(f"Cost report '{name}' completed: ${report['total_cost']:.2f}")
        except Exception as e:
            logger.error(f"Error running cost report '{name}': {e}")
    
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
