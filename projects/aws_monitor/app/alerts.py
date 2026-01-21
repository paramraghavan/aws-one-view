"""
Alert Manager - Email notifications for resource issues.
Supports both SMTP and AWS SES for sending alerts.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any
import logging

from app.config import Config

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Manages alert notifications via email.
    Supports SMTP and AWS SES.
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self.enabled = Config.ALERTS_ENABLED
        self.method = Config.ALERT_METHOD  # 'smtp' or 'ses'
    
    def send_alert(self, issues: List[Dict[str, Any]]):
        """
        Send alert email with list of issues.
        
        Args:
            issues: List of issue dictionaries
        """
        if not self.enabled:
            logger.debug("Alerts disabled, skipping")
            return
        
        if not issues:
            return
        
        try:
            # Format the alert message
            subject = f"AWS Alert: {len(issues)} issue(s) detected"
            body = self._format_alert_email(issues)
            
            # Send based on configured method
            if self.method == 'smtp':
                self._send_via_smtp(subject, body)
            elif self.method == 'ses':
                self._send_via_ses(subject, body)
            else:
                logger.error(f"Unknown alert method: {self.method}")
            
            logger.info(f"Alert sent successfully ({self.method})")
        
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def _format_alert_email(self, issues: List[Dict[str, Any]]) -> str:
        """
        Format issues into a readable email.
        
        Args:
            issues: List of issues
        
        Returns:
            Formatted email body
        """
        # Group by severity
        critical = [i for i in issues if i.get('severity') == 'critical']
        high = [i for i in issues if i.get('severity') == 'high']
        
        body = "AWS Resource Monitor Alert\n"
        body += "=" * 60 + "\n\n"
        body += f"Detected {len(issues)} issue(s) with your AWS resources.\n\n"
        
        if critical:
            body += "🔴 CRITICAL ISSUES:\n"
            body += "-" * 60 + "\n"
            for issue in critical:
                body += self._format_issue(issue)
            body += "\n"
        
        if high:
            body += "⚠️  HIGH PRIORITY:\n"
            body += "-" * 60 + "\n"
            for issue in high:
                body += self._format_issue(issue)
            body += "\n"
        
        body += "\n"
        body += "View details: http://localhost:5000\n"
        body += "\n"
        body += "This is an automated alert from AWS Resource Monitor.\n"
        
        return body
    
    def _format_issue(self, issue: Dict[str, Any]) -> str:
        """Format a single issue."""
        return (
            f"Resource: {issue['resource_id']} ({issue['resource_type']})\n"
            f"Region: {issue['region']}\n"
            f"Issue: {issue['message']}\n"
            f"Time: {issue['timestamp']}\n"
            f"\n"
        )
    
    def _send_via_smtp(self, subject: str, body: str):
        """
        Send email via SMTP.
        
        Args:
            subject: Email subject
            body: Email body
        """
        # Create message
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_FROM_EMAIL
        msg['To'] = ', '.join(Config.ALERT_RECIPIENTS)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))
        
        # Connect and send
        with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
            if Config.SMTP_USE_TLS:
                server.starttls()
            
            if Config.SMTP_USERNAME and Config.SMTP_PASSWORD:
                server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
            
            server.send_message(msg)
    
    def _send_via_ses(self, subject: str, body: str):
        """
        Send email via AWS SES.
        
        Args:
            subject: Email subject
            body: Email body
        """
        import boto3
        
        ses = boto3.client('ses', region_name=Config.AWS_SES_REGION)
        
        response = ses.send_email(
            Source=Config.SMTP_FROM_EMAIL,
            Destination={
                'ToAddresses': Config.ALERT_RECIPIENTS
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )
        
        logger.debug(f"SES MessageId: {response['MessageId']}")
    
    def test_alert(self):
        """Send a test alert to verify configuration."""
        test_issue = {
            'resource_id': 'test-instance',
            'resource_type': 'ec2',
            'region': 'us-east-1',
            'metric': 'CPU',
            'value': 95.5,
            'threshold': 80,
            'severity': 'high',
            'message': 'This is a test alert',
            'timestamp': '2025-01-01T12:00:00Z'
        }
        
        self.send_alert([test_issue])
        logger.info("Test alert sent")
