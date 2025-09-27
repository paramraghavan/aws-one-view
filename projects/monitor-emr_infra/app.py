#!/usr/bin/env python3
"""
EMR Health Monitor - Background monitoring service for EMR clusters
Monitors cluster health, logs issues, and sends email alerts
"""

import os
import yaml
import requests
import logging
import pickle
import smtplib
import atexit
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
from threading import Lock
from flask import Flask, jsonify, render_template_string, request
from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('emr_health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Configure requests for corporate proxy (if needed)
def get_requests_session():
    """Get requests session with proxy configuration if needed"""
    session = requests.Session()

    # Check for proxy configuration in environment variables
    http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')

    if http_proxy or https_proxy:
        proxies = {}
        if http_proxy:
            proxies['http'] = http_proxy
        if https_proxy:
            proxies['https'] = https_proxy
        session.proxies.update(proxies)
        logger.info(f"Using proxy configuration: {proxies}")

    # Disable SSL verification if needed for corporate proxies (NOT recommended for production)
    # Uncomment the line below only if absolutely necessary and approved by security team
    # session.verify = False

    return session


# Global session for reuse
requests_session = get_requests_session()


@dataclass
class HealthEvent:
    """Represents a health monitoring event"""
    timestamp: datetime
    cluster_id: str
    cluster_name: str
    event_type: str  # 'resource_alert', 'node_alert', 'connection_error'
    severity: str  # 'warning', 'critical', 'error'
    message: str
    details: Dict[str, Any]
    resolved: bool = False


class EMRHealthConfig:
    """Handle EMR health monitoring configuration"""

    def __init__(self, config_file: str = 'emr_health_config.yaml'):
        self.config_file = config_file
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_file} not found")
            return self._create_default_config()
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            return {}

    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        default_config = {
            'monitoring': {
                'interval_minutes': 5,
                'data_file': 'emr_health_data.pkl',
                'max_history_days': 30
            },
            'alerts': {
                'email_enabled': False,
                'email_smtp_server': 'smtp.gmail.com',
                'email_smtp_port': 587,
                'email_username': '',
                'email_password': '',
                'email_recipients': [],
                'error_threshold': 5,
                'alert_cooldown_hours': 1
            },
            'thresholds': {
                'memory_warning': 80,
                'memory_critical': 90,
                'cpu_warning': 80,
                'cpu_critical': 90,
                'unhealthy_nodes_warning': 1,
                'unhealthy_nodes_critical': 3
            },
            'clusters': {}
        }

        # Save default config
        with open(self.config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)

        logger.info(f"Created default configuration file: {self.config_file}")
        return default_config

    def get_clusters(self) -> Dict[str, Any]:
        """Get cluster configurations"""
        return self.config.get('clusters', {})

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get monitoring configuration"""
        return self.config.get('monitoring', {})

    def get_alert_config(self) -> Dict[str, Any]:
        """Get alert configuration"""
        return self.config.get('alerts', {})

    def get_thresholds(self) -> Dict[str, Any]:
        """Get threshold configurations"""
        return self.config.get('thresholds', {})


class HealthDataManager:
    """Manages health monitoring data storage and retrieval"""

    def __init__(self, data_file: str = 'emr_health_data.pkl'):
        self.data_file = data_file
        self.health_events: List[HealthEvent] = []
        self.alert_history: Dict[str, datetime] = {}  # cluster_id -> last_alert_time
        self.lock = Lock()
        self._load_data()

    def _load_data(self):
        """Load data from pickle file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'rb') as f:
                    data = pickle.load(f)
                    self.health_events = data.get('health_events', [])
                    self.alert_history = data.get('alert_history', {})
                logger.info(f"Loaded {len(self.health_events)} health events from {self.data_file}")
            except Exception as e:
                logger.error(f"Error loading data from {self.data_file}: {e}")
                self.health_events = []
                self.alert_history = {}

    def save_data(self):
        """Save data to pickle file"""
        try:
            data = {
                'health_events': self.health_events,
                'alert_history': self.alert_history
            }
            with open(self.data_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"Saved {len(self.health_events)} health events to {self.data_file}")
        except Exception as e:
            logger.error(f"Error saving data to {self.data_file}: {e}")

    def add_event(self, event: HealthEvent):
        """Add a health event"""
        with self.lock:
            self.health_events.append(event)
            logger.info(f"Added health event: {event.cluster_id} - {event.event_type} - {event.severity}")

    def get_recent_events(self, cluster_id: str = None, hours: int = 24) -> List[HealthEvent]:
        """Get recent health events"""
        cutoff = datetime.now() - timedelta(hours=hours)
        with self.lock:
            events = [e for e in self.health_events if e.timestamp >= cutoff]
            if cluster_id:
                events = [e for e in events if e.cluster_id == cluster_id]
            return sorted(events, key=lambda x: x.timestamp, reverse=True)

    def get_error_count(self, cluster_id: str, hours: int = 24) -> int:
        """Get error count for a cluster in the last X hours"""
        events = self.get_recent_events(cluster_id, hours)
        return len([e for e in events if e.severity in ['critical', 'error']])

    def cleanup_old_events(self, days: int = 30):
        """Remove events older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        with self.lock:
            old_count = len(self.health_events)
            self.health_events = [e for e in self.health_events if e.timestamp >= cutoff]
            removed = old_count - len(self.health_events)
            if removed > 0:
                logger.info(f"Cleaned up {removed} old health events")

    def can_send_alert(self, cluster_id: str, cooldown_hours: int = 1) -> bool:
        """Check if we can send alert (respects cooldown period)"""
        last_alert = self.alert_history.get(cluster_id)
        if last_alert:
            cooldown = timedelta(hours=cooldown_hours)
            return datetime.now() - last_alert >= cooldown
        return True

    def record_alert_sent(self, cluster_id: str):
        """Record that an alert was sent"""
        self.alert_history[cluster_id] = datetime.now()


class ClusterHealthChecker:
    """Checks health of individual EMR clusters"""

    def __init__(self, cluster_config: Dict[str, Any], thresholds: Dict[str, Any]):
        self.cluster_config = cluster_config
        self.thresholds = thresholds
        self.cluster_id = cluster_config.get('id', 'unknown')
        self.cluster_name = cluster_config.get('name', 'Unknown')

    def check_cluster_health(self) -> List[HealthEvent]:
        """Check overall cluster health and return health events"""
        events = []

        try:
            # Check YARN ResourceManager
            yarn_url = self.cluster_config.get('yarn_url')
            if yarn_url:
                events.extend(self._check_yarn_health(yarn_url))
            else:
                logger.warning(f"No YARN URL configured for cluster {self.cluster_id}")

            # Check if Spark History Server is accessible
            spark_url = self.cluster_config.get('spark_url')
            if spark_url:
                events.extend(self._check_spark_health(spark_url))
            else:
                logger.warning(f"No Spark URL configured for cluster {self.cluster_id}")

        except Exception as e:
            logger.error(f"Error checking health for cluster {self.cluster_id}: {e}")
            events.append(HealthEvent(
                timestamp=datetime.now(),
                cluster_id=self.cluster_id,
                cluster_name=self.cluster_name,
                event_type='connection_error',
                severity='error',
                message=f"Failed to check cluster health: {str(e)}",
                details={'error': str(e)}
            ))

        return events

    def _check_yarn_health(self, yarn_url: str) -> List[HealthEvent]:
        """Check YARN ResourceManager health"""
        events = []

        try:
            # Get cluster metrics
            metrics_response = requests_session.get(f"{yarn_url}/ws/v1/cluster/metrics", timeout=30)
            metrics_response.raise_for_status()
            metrics = metrics_response.json().get('clusterMetrics', {})

            # Check resource usage
            events.extend(self._check_resource_usage(metrics))

            # Get node information
            nodes_response = requests_session.get(f"{yarn_url}/ws/v1/cluster/nodes", timeout=30)
            nodes_response.raise_for_status()
            nodes_data = nodes_response.json().get('nodes', {})
            nodes = nodes_data.get('node', []) if nodes_data else []

            # Check node health
            events.extend(self._check_node_health(nodes))

        except requests.RequestException as e:
            logger.error(f"Error accessing YARN API for {self.cluster_id}: {e}")
            events.append(HealthEvent(
                timestamp=datetime.now(),
                cluster_id=self.cluster_id,
                cluster_name=self.cluster_name,
                event_type='connection_error',
                severity='error',
                message=f"Cannot access YARN ResourceManager: {str(e)}",
                details={'yarn_url': yarn_url, 'error': str(e)}
            ))

        return events

    def _check_spark_health(self, spark_url: str) -> List[HealthEvent]:
        """Check Spark History Server health"""
        events = []

        try:
            # Simple connectivity check
            response = requests_session.get(f"{spark_url}/api/v1/applications", timeout=30, params={'limit': 1})
            response.raise_for_status()
            logger.debug(f"Spark History Server accessible for {self.cluster_id}")

        except requests.RequestException as e:
            logger.error(f"Error accessing Spark History Server for {self.cluster_id}: {e}")
            events.append(HealthEvent(
                timestamp=datetime.now(),
                cluster_id=self.cluster_id,
                cluster_name=self.cluster_name,
                event_type='connection_error',
                severity='warning',
                message=f"Cannot access Spark History Server: {str(e)}",
                details={'spark_url': spark_url, 'error': str(e)}
            ))

        return events

    def _check_resource_usage(self, metrics: Dict[str, Any]) -> List[HealthEvent]:
        """Check resource usage against thresholds"""
        events = []

        total_memory = metrics.get('totalMB', 0)
        used_memory = metrics.get('allocatedMB', 0)
        total_cores = metrics.get('totalVirtualCores', 0)
        used_cores = metrics.get('allocatedVirtualCores', 0)

        # ========================================
        # 🚨 MEMORY CRITICAL THRESHOLD CHECK 🚨
        # ========================================
        if total_memory > 0:
            memory_usage = (used_memory / total_memory) * 100

            # CHECK FOR CRITICAL MEMORY USAGE (default: 90%)
            if memory_usage >= self.thresholds.get('memory_critical', 90):
                logger.warning(f"🚨 CRITICAL: {self.cluster_name} memory usage: {memory_usage:.1f}%")
                events.append(HealthEvent(
                    timestamp=datetime.now(),
                    cluster_id=self.cluster_id,
                    cluster_name=self.cluster_name,
                    event_type='resource_alert',
                    severity='critical',  # ← THIS MARKS IT AS CRITICAL!
                    message=f"Critical memory usage: {memory_usage:.1f}%",
                    details={
                        'memory_usage_pct': memory_usage,
                        'used_mb': used_memory,
                        'total_mb': total_memory,
                        'threshold_exceeded': 'memory_critical',
                        'threshold_value': self.thresholds.get('memory_critical', 90)
                    }
                ))
            # CHECK FOR WARNING MEMORY USAGE (default: 80%)
            elif memory_usage >= self.thresholds.get('memory_warning', 80):
                logger.info(f"⚠️ WARNING: {self.cluster_name} memory usage: {memory_usage:.1f}%")
                events.append(HealthEvent(
                    timestamp=datetime.now(),
                    cluster_id=self.cluster_id,
                    cluster_name=self.cluster_name,
                    event_type='resource_alert',
                    severity='warning',  # ← Warning level
                    message=f"High memory usage: {memory_usage:.1f}%",
                    details={
                        'memory_usage_pct': memory_usage,
                        'used_mb': used_memory,
                        'total_mb': total_memory,
                        'threshold_exceeded': 'memory_warning',
                        'threshold_value': self.thresholds.get('memory_warning', 80)
                    }
                ))

        # =====================================
        # 🚨 CPU CRITICAL THRESHOLD CHECK 🚨
        # =====================================
        if total_cores > 0:
            cpu_usage = (used_cores / total_cores) * 100

            # CHECK FOR CRITICAL CPU USAGE (default: 90%)
            if cpu_usage >= self.thresholds.get('cpu_critical', 90):
                logger.warning(f"🚨 CRITICAL: {self.cluster_name} CPU usage: {cpu_usage:.1f}%")
                events.append(HealthEvent(
                    timestamp=datetime.now(),
                    cluster_id=self.cluster_id,
                    cluster_name=self.cluster_name,
                    event_type='resource_alert',
                    severity='critical',  # ← THIS MARKS IT AS CRITICAL!
                    message=f"Critical CPU usage: {cpu_usage:.1f}%",
                    details={
                        'cpu_usage_pct': cpu_usage,
                        'used_cores': used_cores,
                        'total_cores': total_cores,
                        'threshold_exceeded': 'cpu_critical',
                        'threshold_value': self.thresholds.get('cpu_critical', 90)
                    }
                ))
            # CHECK FOR WARNING CPU USAGE (default: 80%)
            elif cpu_usage >= self.thresholds.get('cpu_warning', 80):
                logger.info(f"⚠️ WARNING: {self.cluster_name} CPU usage: {cpu_usage:.1f}%")
                events.append(HealthEvent(
                    timestamp=datetime.now(),
                    cluster_id=self.cluster_id,
                    cluster_name=self.cluster_name,
                    event_type='resource_alert',
                    severity='warning',  # ← Warning level
                    message=f"High CPU usage: {cpu_usage:.1f}%",
                    details={
                        'cpu_usage_pct': cpu_usage,
                        'used_cores': used_cores,
                        'total_cores': total_cores,
                        'threshold_exceeded': 'cpu_warning',
                        'threshold_value': self.thresholds.get('cpu_warning', 80)
                    }
                ))

        return events

    def _check_node_health(self, nodes: List[Dict[str, Any]]) -> List[HealthEvent]:
        """Check node health status"""
        events = []

        unhealthy_states = ['LOST', 'UNHEALTHY', 'DECOMMISSIONED']
        unhealthy_nodes = [node for node in nodes if node.get('state') in unhealthy_states]

        if len(unhealthy_nodes) >= self.thresholds.get('unhealthy_nodes_critical', 3):
            events.append(HealthEvent(
                timestamp=datetime.now(),
                cluster_id=self.cluster_id,
                cluster_name=self.cluster_name,
                event_type='node_alert',
                severity='critical',
                message=f"Critical: {len(unhealthy_nodes)} unhealthy nodes detected",
                details={
                    'unhealthy_count': len(unhealthy_nodes),
                    'total_nodes': len(nodes),
                    'unhealthy_nodes': [{'id': n.get('id'), 'state': n.get('state')} for n in unhealthy_nodes]
                }
            ))
        elif len(unhealthy_nodes) >= self.thresholds.get('unhealthy_nodes_warning', 1):
            events.append(HealthEvent(
                timestamp=datetime.now(),
                cluster_id=self.cluster_id,
                cluster_name=self.cluster_name,
                event_type='node_alert',
                severity='warning',
                message=f"Warning: {len(unhealthy_nodes)} unhealthy nodes detected",
                details={
                    'unhealthy_count': len(unhealthy_nodes),
                    'total_nodes': len(nodes),
                    'unhealthy_nodes': [{'id': n.get('id'), 'state': n.get('state')} for n in unhealthy_nodes]
                }
            ))

        return events


class EmailAlertManager:
    """Manages email alerts for health events"""

    def __init__(self, alert_config: Dict[str, Any]):
        self.config = alert_config
        self.enabled = alert_config.get('email_enabled', False)

        if self.enabled and not alert_config.get('email_recipients'):
            logger.warning("Email alerts enabled but no recipients configured")
            self.enabled = False

    def send_alert(self, cluster_id: str, cluster_name: str, recent_events: List[HealthEvent], error_count: int):
        """Send email alert for cluster issues"""
        if not self.enabled:
            return

        try:
            subject = f"EMR Health Alert: {cluster_name} ({cluster_id}) - {error_count} errors"
            body = self._create_alert_body(cluster_name, recent_events, error_count)

            msg = MimeMultipart()
            msg['From'] = self.config.get('email_username')
            msg['Subject'] = subject
            msg.attach(MimeText(body, 'html'))

            # Send to all recipients
            recipients = self.config.get('email_recipients', [])
            sent_to = []
            failed_recipients = []

            for recipient in recipients:
                try:
                    msg_copy = MimeMultipart()
                    msg_copy['From'] = self.config.get('email_username')
                    msg_copy['To'] = recipient
                    msg_copy['Subject'] = subject
                    msg_copy.attach(MimeText(body, 'html'))

                    self._send_email(msg_copy)
                    sent_to.append(recipient)
                    logger.info(f"Alert email sent to {recipient} for cluster {cluster_id}")
                except Exception as e:
                    failed_recipients.append({'email': recipient, 'error': str(e)})
                    logger.error(f"Failed to send email to {recipient}: {e}")

            # Determine severity based on success/failure ratio
            total_recipients = len(recipients)
            successful_sends = len(sent_to)
            failed_sends = len(failed_recipients)

            if successful_sends == 0:
                # Complete failure - no emails sent
                severity = 'error'
                message = f"Failed to send email alert to any recipients ({failed_sends} failures)"
            elif failed_sends == 0:
                # Complete success - all emails sent
                severity = 'info'
                message = f"Email alert sent to {successful_sends} recipients - {error_count} errors detected"
            else:
                # Partial failure - some emails sent, some failed
                severity = 'warning'
                message = f"Email alert partially sent: {successful_sends} successful, {failed_sends} failed - {error_count} errors detected"

            # Return email alert event to be logged
            return HealthEvent(
                timestamp=datetime.now(),
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                event_type='email_alert',
                severity=severity,
                message=message,
                details={
                    'recipients_successful': sent_to,
                    'recipients_failed': failed_recipients,
                    'total_recipients': total_recipients,
                    'success_count': successful_sends,
                    'failure_count': failed_sends,
                    'error_count': error_count,
                    'recent_events_count': len(recent_events),
                    'alert_subject': subject
                }
            )

        except Exception as e:
            logger.error(f"Failed to send email alert for cluster {cluster_id}: {e}")
            # Return error event for complete system failure
            return HealthEvent(
                timestamp=datetime.now(),
                cluster_id=cluster_id,
                cluster_name=cluster_name,
                event_type='email_alert',
                severity='error',
                message=f"Email alert system failure: {str(e)}",
                details={'error': str(e), 'error_count': error_count, 'failure_type': 'system_failure'}
            )

    def _create_alert_body(self, cluster_name: str, events: List[HealthEvent], error_count: int) -> str:
        """Create HTML email body"""
        html = f"""
        <html>
        <body>
            <h2>EMR Cluster Health Alert</h2>
            <p><strong>Cluster:</strong> {cluster_name}</p>
            <p><strong>Error Count (last 24h):</strong> {error_count}</p>
            <p><strong>Alert Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

            <h3>Recent Issues:</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f0f0f0;">
                    <th>Time</th>
                    <th>Severity</th>
                    <th>Type</th>
                    <th>Message</th>
                </tr>
        """

        for event in events[:10]:  # Show last 10 events
            severity_color = {
                'critical': '#ff4444',
                'warning': '#ffaa00',
                'error': '#ff6666'
            }.get(event.severity, '#000000')

            html += f"""
                <tr>
                    <td>{event.timestamp.strftime('%H:%M:%S')}</td>
                    <td style="color: {severity_color}; font-weight: bold;">{event.severity.upper()}</td>
                    <td>{event.event_type}</td>
                    <td>{event.message}</td>
                </tr>
            """

        html += """
            </table>
            <p><em>This is an automated alert from EMR Health Monitor.</em></p>
        </body>
        </html>
        """

        return html

    def _send_email(self, msg: MimeMultipart):
        """Send email via SMTP"""
        smtp_server = self.config.get('email_smtp_server', 'smtp.gmail.com')
        smtp_port = self.config.get('email_smtp_port', 587)
        username = self.config.get('email_username')
        password = self.config.get('email_password')

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
        server.quit()


class EMRHealthMonitor:
    """Main EMR Health Monitor service"""

    def __init__(self):
        self.config = EMRHealthConfig()
        self.data_manager = HealthDataManager(
            self.config.get_monitoring_config().get('data_file', 'emr_health_data.pkl')
        )
        self.email_manager = EmailAlertManager(self.config.get_alert_config())
        self.scheduler = BackgroundScheduler()
        self.running = False

    def start_monitoring(self):
        """Start background monitoring"""
        interval_minutes = self.config.get_monitoring_config().get('interval_minutes', 5)

        self.scheduler.add_job(
            func=self._check_all_clusters,
            trigger="interval",
            minutes=interval_minutes,
            id='health_check'
        )

        # Add cleanup job (daily)
        self.scheduler.add_job(
            func=self._cleanup_old_data,
            trigger="interval",
            hours=24,
            id='cleanup'
        )

        self.scheduler.start()
        self.running = True
        logger.info(f"Started EMR health monitoring (interval: {interval_minutes} minutes)")

        # Run initial check
        self._check_all_clusters()

    def stop_monitoring(self):
        """Stop monitoring and save data"""
        if self.scheduler.running:
            self.scheduler.shutdown()

        self.data_manager.save_data()
        self.running = False
        logger.info("Stopped EMR health monitoring")

    def _check_all_clusters(self):
        """Check health of all configured clusters"""
        clusters = self.config.get_clusters()
        thresholds = self.config.get_thresholds()
        alert_config = self.config.get_alert_config()

        logger.info(f"Starting health check for {len(clusters)} clusters")

        for cluster_id, cluster_config in clusters.items():
            cluster_config['id'] = cluster_id
            checker = ClusterHealthChecker(cluster_config, thresholds)
            events = checker.check_cluster_health()

            # Store events
            for event in events:
                self.data_manager.add_event(event)

            # Check if we need to send alerts
            if events and alert_config.get('email_enabled'):
                error_count = self.data_manager.get_error_count(cluster_id, 24)
                threshold = alert_config.get('error_threshold', 5)
                cooldown = alert_config.get('alert_cooldown_hours', 1)

                if (error_count >= threshold and
                        self.data_manager.can_send_alert(cluster_id, cooldown)):

                    recent_events = self.data_manager.get_recent_events(cluster_id, 24)
                    email_event = self.email_manager.send_alert(
                        cluster_id,
                        cluster_config.get('name', cluster_id),
                        recent_events,
                        error_count
                    )

                    # Log the email alert event
                    if email_event:
                        self.data_manager.add_event(email_event)

                    self.data_manager.record_alert_sent(cluster_id)

        logger.info("Completed health check cycle")

    def _cleanup_old_data(self):
        """Clean up old monitoring data"""
        max_days = self.config.get_monitoring_config().get('max_history_days', 30)
        self.data_manager.cleanup_old_events(max_days)
        self.data_manager.save_data()

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for web dashboard"""
        clusters = self.config.get_clusters()
        recent_events_24h = self.data_manager.get_recent_events(hours=24)
        email_alerts_24h = len([e for e in recent_events_24h if e.event_type == 'email_alert'])

        # Get critical alerts for dashboard table
        critical_alerts = []
        email_errors = []

        for event in recent_events_24h:
            # Collect critical resource/node alerts
            if event.severity == 'critical' and event.event_type in ['resource_alert', 'node_alert']:
                critical_alerts.append(event)

            # Collect email alert errors/warnings
            if event.event_type == 'email_alert' and event.severity in ['error', 'warning']:
                email_errors.append(event)

        # Sort by timestamp (most recent first)
        critical_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        email_errors.sort(key=lambda x: x.timestamp, reverse=True)

        dashboard_data = {
            'clusters': {},
            'critical_alerts': critical_alerts[:10],  # Show last 10 critical alerts
            'email_errors': email_errors[:5],  # Show last 5 email issues
            'summary': {
                'total_clusters': len(clusters),
                'monitoring_status': 'running' if self.running else 'stopped',
                'last_check': datetime.now().isoformat(),
                'total_events_24h': len(recent_events_24h),
                'email_alerts_24h': email_alerts_24h,
                'critical_alerts_count': len(critical_alerts),
                'has_critical_issues': len(critical_alerts) > 0 or len(email_errors) > 0
            }
        }

        for cluster_id, cluster_config in clusters.items():
            recent_events = self.data_manager.get_recent_events(cluster_id, 24)
            error_count = len([e for e in recent_events if e.severity in ['critical', 'error']])
            warning_count = len([e for e in recent_events if e.severity == 'warning'])
            email_alert_count = len([e for e in recent_events if e.event_type == 'email_alert'])
            critical_count = len([e for e in recent_events if e.severity == 'critical'])

            dashboard_data['clusters'][cluster_id] = {
                'name': cluster_config.get('name', cluster_id),
                'error_count_24h': error_count,
                'warning_count_24h': warning_count,
                'email_alert_count_24h': email_alert_count,
                'critical_count_24h': critical_count,
                'last_event': recent_events[0].timestamp.isoformat() if recent_events else None,
                'status': 'critical' if critical_count > 0 else 'error' if error_count > 0 else 'warning' if warning_count > 0 else 'healthy'
            }

        return dashboard_data


# Initialize monitoring service
health_monitor = EMRHealthMonitor()

# Flask app for basic web interface
app = Flask(__name__)


@app.route('/')
def dashboard():
    """Simple web dashboard"""
    data = health_monitor.get_dashboard_data()

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{% if data.summary.has_critical_issues %}🚨 CRITICAL ISSUES - {% endif %}EMR Health Monitor</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1000px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .cluster-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
            .cluster-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .status-healthy { border-left: 5px solid #28a745; }
            .status-warning { border-left: 5px solid #ffc107; }
            .status-critical { border-left: 5px solid #dc3545; background: #f8d7da !important; }
            .status-error { border-left: 5px solid #fd7e14; background: #fff3cd !important; }
            .metric { display: flex; justify-content: space-between; margin: 10px 0; }
            .metric-value { font-weight: bold; }
            .critical-section { background: linear-gradient(135deg, #dc3545, #c82333); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(220,53,69,0.3); }
            .warning-section { background: linear-gradient(135deg, #ffc107, #e0a800); color: #212529; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(255,193,7,0.3); }
            .alert-table { width: 100%; border-collapse: collapse; margin-top: 15px; background: rgba(255,255,255,0.95); border-radius: 8px; overflow: hidden; }
            .alert-table th { background: rgba(0,0,0,0.1); padding: 12px; text-align: left; font-weight: bold; }
            .alert-table td { padding: 12px; border-bottom: 1px solid rgba(255,255,255,0.2); }
            .alert-table tr:hover { background: rgba(255,255,255,0.1); }
            .critical-badge { background: #dc3545; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
            .warning-badge { background: #ffc107; color: #212529; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
            .error-badge { background: #fd7e14; color: white; padding: 4px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; }
            .pulse { animation: pulse 2s infinite; }
            @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
            .blink { animation: blink 1.5s infinite; }
            @keyframes blink { 0%, 50% { opacity: 1; } 51%, 100% { opacity: 0.3; } }
            .no-issues { background: linear-gradient(135deg, #28a745, #20c997); color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
            h1, h2 { color: #333; }
            .btn { display: inline-block; padding: 10px 20px; border-radius: 5px; text-decoration: none; font-weight: bold; transition: all 0.3s ease; }
            .btn:hover { transform: translateY(-2px); opacity: 0.9; }
            .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
            .summary-item { background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"{% if data.summary.has_critical_issues %} style="border: 3px solid #dc3545; background: linear-gradient(135deg, #f8d7da, #ffffff);"{% endif %}>
                <h1>🏥 EMR Health Monitor
                    {% if data.summary.has_critical_issues %}
                        <span style="color: #dc3545; animation: blink 1s infinite;">🚨 CRITICAL ISSUES DETECTED!</span>
                    {% endif %}
                </h1>
                <p>Background monitoring service for EMR clusters
                    {% if data.summary.has_critical_issues %}
                        <strong style="color: #dc3545;"> - {{ data.summary.critical_alerts_count }} critical alerts require immediate attention!</strong>
                    {% endif %}
                </p>

                <div style="margin-top: 15px;">
                    <a href="/data" class="btn" style="background: #28a745; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px; margin-right: 10px;">📊 View Historical Data</a>
                    <a href="/api/data/export" class="btn" style="background: #17a2b8; color: white; text-decoration: none; padding: 10px 20px; border-radius: 5px;">📥 Export Data</a>
                </div>

                <div class="summary">
                    <div class="summary-item">
                        <strong>{{ data.summary.total_clusters }}</strong><br>
                        Clusters Monitored
                    </div>
                    <div class="summary-item">
                        <strong>{{ data.summary.monitoring_status|title }}</strong><br>
                        Monitoring Status
                    </div>
                    <div class="summary-item">
                        <strong>{{ data.summary.total_events_24h }}</strong><br>
                        Events (24h)
                    </div>
                    <div class="summary-item">
                        <strong>{{ data.summary.email_alerts_24h }}</strong><br>
                        📧 Alerts Sent (24h)
                    </div>
                </div>
            </div>

            <div class="cluster-grid">
                {% for cluster_id, cluster in data.clusters.items() %}
                <div class="cluster-card status-{{ cluster.status }}{% if cluster.critical_count_24h > 0 %} pulse{% endif %}">
                    <h3>{{ cluster.name }}
                        {% if cluster.critical_count_24h > 0 %}
                            <span class="critical-badge blink">🚨 {{ cluster.critical_count_24h }} CRITICAL</span>
                        {% endif %}
                    </h3>

                    <div class="metric">
                        <span>Status:</span>
                        <span class="metric-value" style="color: {% if cluster.status == 'critical' %}#dc3545{% elif cluster.status == 'error' %}#fd7e14{% elif cluster.status == 'warning' %}#ffc107{% else %}#28a745{% endif %};">
                            {{ cluster.status|title }}
                            {% if cluster.status == 'critical' %}🚨{% elif cluster.status == 'error' %}⚠️{% elif cluster.status == 'warning' %}⚠️{% else %}✅{% endif %}
                        </span>
                    </div>

                    {% if cluster.critical_count_24h > 0 %}
                    <div class="metric" style="background: #f8d7da; padding: 8px; border-radius: 4px; border: 1px solid #dc3545;">
                        <span style="color: #721c24; font-weight: bold;">🚨 Critical Issues:</span>
                        <span class="metric-value" style="color: #dc3545; font-size: 1.2em;">{{ cluster.critical_count_24h }}</span>
                    </div>
                    {% endif %}

                    <div class="metric">
                        <span>Errors (24h):</span>
                        <span class="metric-value" style="color: {% if cluster.error_count_24h > 0 %}#dc3545{% else %}#333{% endif %};">{{ cluster.error_count_24h }}</span>
                    </div>

                    <div class="metric">
                        <span>Warnings (24h):</span>
                        <span class="metric-value" style="color: {% if cluster.warning_count_24h > 0 %}#ffc107{% else %}#333{% endif %};">{{ cluster.warning_count_24h }}</span>
                    </div>

                    <div class="metric">
                        <span>📧 Email Alerts (24h):</span>
                        <span class="metric-value" style="color: #17a2b8;">{{ cluster.email_alert_count_24h }}</span>
                    </div>

                    <div class="metric">
                        <span>Last Event:</span>
                        <span class="metric-value">
                            {% if cluster.last_event %}
                                {{ cluster.last_event[:19]|replace('T', ' ') }}
                            {% else %}
                                No events
                            {% endif %}
                        </span>
                    </div>
                </div>
                {% endfor %}
            </div>

            <div style="margin-top: 30px; text-align: center; color: #666;">
                <p>Last updated: {{ data.summary.last_check[:19]|replace('T', ' ') }} | Auto-refresh: 30s</p>
            </div>
        </div>
    </body>
    </html>
    """

    return render_template_string(html_template, data=data)


@app.route('/api/status')
def api_status():
    """API endpoint for status"""
    return jsonify(health_monitor.get_dashboard_data())


@app.route('/api/events/<cluster_id>')
def api_events(cluster_id):
    """API endpoint for cluster events"""
    hours = request.args.get('hours', 24, type=int)
    events = health_monitor.data_manager.get_recent_events(cluster_id, hours)
    return jsonify([asdict(event) for event in events])


@app.route('/data')
def data_viewer():
    """View stored health monitoring data"""
    # Get filter parameters
    cluster_filter = request.args.get('cluster', 'all')
    hours = request.args.get('hours', 24, type=int)
    severity_filter = request.args.get('severity', 'all')
    event_type_filter = request.args.get('event_type', 'all')

    # Get events
    if cluster_filter == 'all':
        events = health_monitor.data_manager.get_recent_events(hours=hours)
    else:
        events = health_monitor.data_manager.get_recent_events(cluster_filter, hours)

    # Filter by severity
    if severity_filter != 'all':
        events = [e for e in events if e.severity == severity_filter]

    # Filter by event type
    if event_type_filter != 'all':
        events = [e for e in events if e.event_type == event_type_filter]

    # Get available clusters for filter dropdown
    clusters = health_monitor.config.get_clusters()

    # Prepare data for template
    data = {
        'events': events,
        'clusters': clusters,
        'total_events': len(health_monitor.data_manager.health_events),
        'email_alerts_count': len([e for e in events if e.event_type == 'email_alert']),
        'current_filters': {
            'cluster': cluster_filter,
            'hours': hours,
            'severity': severity_filter,
            'event_type': event_type_filter
        },
        'alert_history': health_monitor.data_manager.alert_history
    }

    html_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>EMR Health Data Viewer</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .container { max-width: 1400px; margin: 0 auto; }
            .header { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .filters { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .filter-group { display: inline-block; margin-right: 20px; margin-bottom: 10px; }
            .filter-group label { display: block; margin-bottom: 5px; font-weight: bold; }
            .filter-group select, .filter-group input { padding: 8px; border: 1px solid #ddd; border-radius: 4px; }
            .btn { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
            .btn:hover { background: #0056b3; }
            .btn-secondary { background: #6c757d; }
            .btn-secondary:hover { background: #545b62; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 15px; border-radius: 8px; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .stat-value { font-size: 2em; font-weight: bold; color: #007bff; }
            .events-table { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); overflow-x: auto; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f8f9fa; font-weight: bold; position: sticky; top: 0; }
            tr:hover { background: #f8f9fa; }
            .severity-critical { color: #dc3545; font-weight: bold; }
            .severity-warning { color: #ffc107; font-weight: bold; }
            .severity-error { color: #fd7e14; font-weight: bold; }
            .severity-info { color: #17a2b8; font-weight: bold; }
            .event-type { background: #e9ecef; padding: 4px 8px; border-radius: 4px; font-size: 0.9em; }
            .event-type-email_alert { background: #d1ecf1; color: #0c5460; font-weight: bold; }
            .email-alert-row { background-color: #fff3cd !important; border-left: 4px solid #ffc107; }
            .email-alert-success { background-color: #d4edda !important; border-left: 4px solid #28a745; }
            .email-alert-error { background-color: #f8d7da !important; border-left: 4px solid #dc3545; }
            .details-toggle { cursor: pointer; color: #007bff; text-decoration: underline; }
            .details { display: none; background: #f8f9fa; padding: 10px; margin-top: 10px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
            .no-events { text-align: center; padding: 40px; color: #666; }
            .back-link { margin-bottom: 20px; }
            .alert-history { background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="back-link">
                <a href="/" class="btn btn-secondary">← Back to Dashboard</a>
            </div>

            <div class="header">
                <h1>📊 EMR Health Data Viewer</h1>
                <p>View and analyze stored health monitoring events from pickle file</p>
            </div>

            <div class="stats">
                <div class="stat-card">
                    <div class="stat-value">{{ data.total_events }}</div>
                    <div>Total Events Stored</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ events|length }}</div>
                    <div>Events Shown</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{{ data.clusters|length }}</div>
                    <div>Clusters Monitored</div>
                </div>
                <div class="stat-card" style="background: #d1ecf1;">
                    <div class="stat-value" style="color: #0c5460;">📧 {{ data.email_alerts_count }}</div>
                    <div>Email Alerts (filtered)</div>
                </div>
            </div>

            <div class="filters">
                <form method="GET" action="/data">
                    <div class="filter-group">
                        <label>Cluster:</label>
                        <select name="cluster">
                            <option value="all" {% if data.current_filters.cluster == 'all' %}selected{% endif %}>All Clusters</option>
                            {% for cluster_id, cluster_config in data.clusters.items() %}
                            <option value="{{ cluster_id }}" {% if data.current_filters.cluster == cluster_id %}selected{% endif %}>
                                {{ cluster_config.name }}
                            </option>
                            {% endfor %}
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Time Period:</label>
                        <select name="hours">
                            <option value="1" {% if data.current_filters.hours == 1 %}selected{% endif %}>Last 1 hour</option>
                            <option value="6" {% if data.current_filters.hours == 6 %}selected{% endif %}>Last 6 hours</option>
                            <option value="24" {% if data.current_filters.hours == 24 %}selected{% endif %}>Last 24 hours</option>
                            <option value="168" {% if data.current_filters.hours == 168 %}selected{% endif %}>Last 7 days</option>
                            <option value="720" {% if data.current_filters.hours == 720 %}selected{% endif %}>Last 30 days</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Severity:</label>
                        <select name="severity">
                            <option value="all" {% if data.current_filters.severity == 'all' %}selected{% endif %}>All Severities</option>
                            <option value="critical" {% if data.current_filters.severity == 'critical' %}selected{% endif %}>Critical</option>
                            <option value="warning" {% if data.current_filters.severity == 'warning' %}selected{% endif %}>Warning</option>
                            <option value="error" {% if data.current_filters.severity == 'error' %}selected{% endif %}>Error</option>
                            <option value="info" {% if data.current_filters.severity == 'info' %}selected{% endif %}>Info</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>Event Type:</label>
                        <select name="event_type">
                            <option value="all" {% if data.current_filters.event_type == 'all' %}selected{% endif %}>All Types</option>
                            <option value="resource_alert" {% if data.current_filters.event_type == 'resource_alert' %}selected{% endif %}>Resource Alerts</option>
                            <option value="node_alert" {% if data.current_filters.event_type == 'node_alert' %}selected{% endif %}>Node Alerts</option>
                            <option value="connection_error" {% if data.current_filters.event_type == 'connection_error' %}selected{% endif %}>Connection Errors</option>
                            <option value="email_alert" {% if data.current_filters.event_type == 'email_alert' %}selected{% endif %}>📧 Email Alerts</option>
                        </select>
                    </div>

                    <div class="filter-group">
                        <label>&nbsp;</label>
                        <button type="submit" class="btn">Apply Filters</button>
                    </div>
                </form>
            </div>

            {% if data.alert_history %}
            <div class="alert-history">
                <h3>📧 Recent Alert History</h3>
                <table style="margin-top: 10px;">
                    <thead>
                        <tr>
                            <th>Cluster</th>
                            <th>Last Alert Sent</th>
                            <th>Time Ago</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for cluster_id, alert_time in data.alert_history.items() %}
                        <tr>
                            <td>{{ data.clusters.get(cluster_id, {}).get('name', cluster_id) }}</td>
                            <td>{{ alert_time.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                            <td>{{ ((data.events[0].timestamp - alert_time).total_seconds() / 3600) | round(1) if data.events else 'N/A' }}h ago</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% endif %}

            <div class="events-table">
                <h3>🔍 Health Events</h3>
                {% if events %}
                <table>
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Cluster</th>
                            <th>Severity</th>
                            <th>Event Type</th>
                            <th>Message</th>
                            <th>Details</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for event in events %}
                        {% set row_class = '' %}
                        {% if event.event_type == 'email_alert' %}
                            {% if event.severity == 'info' %}
                                {% set row_class = 'email-alert-success' %}
                            {% elif event.severity == 'error' %}
                                {% set row_class = 'email-alert-error' %}
                            {% elif event.severity == 'warning' %}
                                {% set row_class = 'email-alert-row' %}
                            {% else %}
                                {% set row_class = 'email-alert-row' %}
                            {% endif %}
                        {% endif %}

                        <tr class="{{ row_class }}">
                            <td>{{ event.timestamp.strftime('%Y-%m-%d %H:%M:%S') }}</td>
                            <td>{{ event.cluster_name }}</td>
                            <td><span class="severity-{{ event.severity }}">{{ event.severity.upper() }}</span></td>
                            <td>
                                <span class="event-type{% if event.event_type == 'email_alert' %} event-type-email_alert{% endif %}">
                                    {% if event.event_type == 'email_alert' %}
                                        📧 {{ event.event_type }}
                                    {% else %}
                                        {{ event.event_type }}
                                    {% endif %}
                                </span>
                            </td>
                            <td>{{ event.message }}</td>
                            <td>
                                <span class="details-toggle" onclick="toggleDetails({{ loop.index }})">View Details</span>
                                <div id="details-{{ loop.index }}" class="details">
                                    <pre>{{ event.details | tojson(indent=2) }}</pre>
                                </div>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
                {% else %}
                <div class="no-events">
                    <h3>No events found</h3>
                    <p>No health events match the current filters.</p>
                </div>
                {% endif %}
            </div>

            <div style="margin-top: 30px; text-align: center; color: #666;">
                <p>Data loaded from: {{ health_monitor.data_manager.data_file }}</p>
                <p>Total events in pickle file: {{ data.total_events }}</p>
            </div>
        </div>

        <script>
            function toggleDetails(index) {
                const details = document.getElementById('details-' + index);
                if (details.style.display === 'none' || details.style.display === '') {
                    details.style.display = 'block';
                } else {
                    details.style.display = 'none';
                }
            }

            // Auto-refresh every 60 seconds
            setTimeout(function() {
                location.reload();
            }, 60000);
        </script>
    </body>
    </html>
    """

    return render_template_string(html_template, data=data, events=events, health_monitor=health_monitor)


@app.route('/api/data/export')
def export_data():
    """Export health data as JSON"""
    hours = request.args.get('hours', 24, type=int)
    events = health_monitor.data_manager.get_recent_events(hours=hours)

    export_data = {
        'export_time': datetime.now().isoformat(),
        'events': [asdict(event) for event in events],
        'alert_history': {k: v.isoformat() for k, v in health_monitor.data_manager.alert_history.items()},
        'total_events': len(health_monitor.data_manager.health_events)
    }

    response = jsonify(export_data)
    response.headers[
        'Content-Disposition'] = f'attachment; filename=emr_health_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    return response


def cleanup_handler(signum=None, frame=None):
    """Handle cleanup on shutdown"""
    logger.info("Shutting down EMR Health Monitor...")
    health_monitor.stop_monitoring()
    sys.exit(0)


# Register cleanup handlers
atexit.register(health_monitor.stop_monitoring)
signal.signal(signal.SIGINT, cleanup_handler)
signal.signal(signal.SIGTERM, cleanup_handler)

if __name__ == '__main__':
    # Start monitoring in background
    health_monitor.start_monitoring()

    # Start Flask web interface
    logger.info("Starting web interface on http://localhost:7501")
    app.run(debug=False, host='0.0.0.0', port=7501, use_reloader=False)