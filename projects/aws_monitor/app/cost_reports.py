"""
Cost Report Generator - Create scheduled cost reports for specific resources.
Generates daily, weekly, or monthly cost reports and sends via email.
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional
import logging

from app.aws_client import AWSClient
from app.alerts import AlertManager
from app.config import Config

logger = logging.getLogger(__name__)


class CostReportGenerator:
    """
    Generate cost reports for specific resources.
    Supports daily, weekly, and monthly reports.
    """
    
    def __init__(self):
        """Initialize the cost report generator."""
        self.aws_client = AWSClient()
        self.alert_manager = AlertManager()
    
    def generate_report(
        self,
        resources: List[Dict[str, Any]],
        period: str = 'daily',
        send_email: bool = True
    ) -> Dict[str, Any]:
        """
        Generate cost report for selected resources.
        
        Args:
            resources: List of resources to include in report
                      Each resource: {'id': str, 'type': str, 'region': str, 'name': str}
            period: Report period - 'daily', 'weekly', or 'monthly'
            send_email: Whether to send report via email
        
        Returns:
            Dictionary with report data and status
        """
        logger.info(f"Generating {period} cost report for {len(resources)} resources")
        
        # Determine date range based on period
        end_date = date.today()
        
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
            report_title = f"Daily Cost Report - {end_date.strftime('%Y-%m-%d')}"
        elif period == 'weekly':
            start_date = end_date - timedelta(days=7)
            report_title = f"Weekly Cost Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        elif period == 'monthly':
            # Start of current month to today
            start_date = date(end_date.year, end_date.month, 1)
            report_title = f"Monthly Cost Report - {end_date.strftime('%B %Y')}"
        else:
            raise ValueError(f"Invalid period: {period}. Must be 'daily', 'weekly', or 'monthly'")
        
        # Get costs for each resource
        resource_costs = []
        total_cost = 0.0
        
        for resource in resources:
            try:
                cost_data = self._get_resource_cost(
                    resource_id=resource['id'],
                    resource_type=resource['type'],
                    region=resource['region'],
                    start_date=start_date,
                    end_date=end_date
                )
                
                resource_costs.append({
                    'id': resource['id'],
                    'name': resource.get('name', resource['id']),
                    'type': resource['type'],
                    'region': resource['region'],
                    'cost': cost_data['cost'],
                    'estimated': cost_data['estimated']
                })
                
                total_cost += cost_data['cost']
                
            except Exception as e:
                logger.error(f"Error getting cost for {resource['id']}: {e}")
                resource_costs.append({
                    'id': resource['id'],
                    'name': resource.get('name', resource['id']),
                    'type': resource['type'],
                    'region': resource['region'],
                    'cost': 0.0,
                    'error': str(e)
                })
        
        # Create report
        report = {
            'title': report_title,
            'period': period,
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'total_cost': round(total_cost, 2),
            'resource_count': len(resources),
            'resources': sorted(resource_costs, key=lambda x: x['cost'], reverse=True),
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Report generated: ${total_cost:.2f} for {len(resources)} resources")
        
        # Send email if requested
        if send_email:
            self._send_report_email(report)
        
        return report
    
    def _get_resource_cost(
        self,
        resource_id: str,
        resource_type: str,
        region: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get cost for a specific resource.
        
        Uses cost allocation tags if available, otherwise estimates based on usage.
        
        Returns:
            Dictionary with 'cost' and 'estimated' flag
        """
        # Try to get actual costs using tags
        actual_cost = self._get_tagged_cost(resource_id, start_date, end_date)
        
        if actual_cost is not None:
            return {'cost': actual_cost, 'estimated': False}
        
        # Fall back to estimation based on resource type
        estimated_cost = self._estimate_resource_cost(
            resource_id, resource_type, region, start_date, end_date
        )
        
        return {'cost': estimated_cost, 'estimated': True}
    
    def _get_tagged_cost(
        self,
        resource_id: str,
        start_date: date,
        end_date: date
    ) -> Optional[float]:
        """
        Get actual cost for resource using cost allocation tags.
        Returns None if tags are not configured.
        """
        try:
            ce = self.aws_client.session.client('ce', region_name='us-east-1')
            
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                Filter={
                    'Tags': {
                        'Key': 'ResourceId',
                        'Values': [resource_id]
                    }
                }
            )
            
            total = 0.0
            for result in response['ResultsByTime']:
                if result['Total']:
                    cost = float(result['Total']['UnblendedCost']['Amount'])
                    total += cost
            
            return total if total > 0 else None
            
        except Exception as e:
            # Tags probably not configured
            logger.debug(f"Could not get tagged cost for {resource_id}: {e}")
            return None
    
    def _estimate_resource_cost(
        self,
        resource_id: str,
        resource_type: str,
        region: str,
        start_date: date,
        end_date: date
    ) -> float:
        """
        Estimate resource cost based on usage metrics and pricing.
        This is an approximation when cost allocation tags aren't available.
        """
        days = (end_date - start_date).days
        
        if resource_type == 'ec2':
            return self._estimate_ec2_cost(resource_id, region, days)
        elif resource_type == 'rds':
            return self._estimate_rds_cost(resource_id, region, days)
        elif resource_type == 'lambda':
            return self._estimate_lambda_cost(resource_id, region, days)
        else:
            logger.warning(f"Cannot estimate cost for resource type: {resource_type}")
            return 0.0
    
    def _estimate_ec2_cost(self, instance_id: str, region: str, days: int) -> float:
        """Estimate EC2 instance cost based on instance type and hours."""
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            response = ec2.describe_instances(InstanceIds=[instance_id])
            
            instance = response['Reservations'][0]['Instances'][0]
            instance_type = instance['InstanceType']
            
            # Simplified pricing (should use AWS Pricing API for accuracy)
            # These are approximate on-demand prices for us-east-1
            pricing_estimates = {
                't2.micro': 0.0116,
                't2.small': 0.023,
                't2.medium': 0.0464,
                't3.micro': 0.0104,
                't3.small': 0.0208,
                't3.medium': 0.0416,
                't3.large': 0.0832,
                'm5.large': 0.096,
                'm5.xlarge': 0.192,
                'c5.large': 0.085,
            }
            
            hourly_rate = pricing_estimates.get(instance_type, 0.10)  # Default $0.10/hour
            hours = days * 24
            
            estimated_cost = hourly_rate * hours
            logger.info(f"Estimated EC2 cost for {instance_id}: ${estimated_cost:.2f}")
            
            return estimated_cost
            
        except Exception as e:
            logger.error(f"Error estimating EC2 cost for {instance_id}: {e}")
            return 0.0
    
    def _estimate_rds_cost(self, db_id: str, region: str, days: int) -> float:
        """Estimate RDS database cost."""
        try:
            rds = self.aws_client.session.client('rds', region_name=region)
            response = rds.describe_db_instances(DBInstanceIdentifier=db_id)
            
            db = response['DBInstances'][0]
            db_class = db['DBInstanceClass']
            storage_gb = db['AllocatedStorage']
            
            # Simplified RDS pricing estimates
            instance_pricing = {
                'db.t3.micro': 0.017,
                'db.t3.small': 0.034,
                'db.t3.medium': 0.068,
                'db.m5.large': 0.192,
            }
            
            hourly_rate = instance_pricing.get(db_class, 0.10)
            storage_cost_per_gb_month = 0.115  # GP2 storage
            
            compute_cost = hourly_rate * days * 24
            storage_cost = storage_gb * storage_cost_per_gb_month * (days / 30)
            
            total_cost = compute_cost + storage_cost
            logger.info(f"Estimated RDS cost for {db_id}: ${total_cost:.2f}")
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Error estimating RDS cost for {db_id}: {e}")
            return 0.0
    
    def _estimate_lambda_cost(self, function_name: str, region: str, days: int) -> float:
        """Estimate Lambda function cost based on invocations."""
        try:
            # Get invocation count from CloudWatch
            cloudwatch = self.aws_client.session.client('cloudwatch', region_name=region)
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=days)
            
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=86400 * days,  # Total for period
                Statistics=['Sum']
            )
            
            total_invocations = 0
            if response['Datapoints']:
                total_invocations = response['Datapoints'][0]['Sum']
            
            # Lambda pricing: $0.20 per 1M requests + $0.0000166667 per GB-second
            # Simplified: just count invocations (compute cost varies by memory/duration)
            request_cost = (total_invocations / 1_000_000) * 0.20
            
            # Assume average of $0.000001 per invocation for compute (rough estimate)
            compute_cost = total_invocations * 0.000001
            
            total_cost = request_cost + compute_cost
            logger.info(f"Estimated Lambda cost for {function_name}: ${total_cost:.4f}")
            
            return total_cost
            
        except Exception as e:
            logger.error(f"Error estimating Lambda cost for {function_name}: {e}")
            return 0.0
    
    def _send_report_email(self, report: Dict[str, Any]):
        """Send cost report via email."""
        try:
            subject = f"AWS Cost Report: {report['title']}"
            body = self._format_report_email(report)
            
            # Use existing alert manager to send email
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            import smtplib
            
            msg = MIMEMultipart()
            msg['From'] = Config.SMTP_FROM_EMAIL
            msg['To'] = ', '.join(Config.ALERT_RECIPIENTS)
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            if Config.ALERT_METHOD == 'smtp':
                with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                    if Config.SMTP_USE_TLS:
                        server.starttls()
                    if Config.SMTP_USERNAME and Config.SMTP_PASSWORD:
                        server.login(Config.SMTP_USERNAME, Config.SMTP_PASSWORD)
                    server.send_message(msg)
            elif Config.ALERT_METHOD == 'ses':
                import boto3
                ses = boto3.client('ses', region_name=Config.AWS_SES_REGION)
                ses.send_email(
                    Source=Config.SMTP_FROM_EMAIL,
                    Destination={'ToAddresses': Config.ALERT_RECIPIENTS},
                    Message={
                        'Subject': {'Data': subject},
                        'Body': {'Text': {'Data': body}}
                    }
                )
            
            logger.info("Cost report email sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending cost report email: {e}")
    
    def _format_report_email(self, report: Dict[str, Any]) -> str:
        """Format cost report as email body."""
        body = f"""
AWS COST REPORT
{'=' * 70}

{report['title']}
Period: {report['start_date']} to {report['end_date']}
Generated: {datetime.fromisoformat(report['generated_at']).strftime('%Y-%m-%d %H:%M:%S UTC')}

{'=' * 70}

SUMMARY
-------
Total Cost: ${report['total_cost']:.2f}
Resources Monitored: {report['resource_count']}

{'=' * 70}

COST BREAKDOWN BY RESOURCE
---------------------------
"""
        
        for resource in report['resources']:
            status = " (estimated)" if resource.get('estimated', False) else ""
            error = f" - ERROR: {resource['error']}" if 'error' in resource else ""
            
            body += f"""
Resource: {resource['name']}
  ID: {resource['id']}
  Type: {resource['type']}
  Region: {resource['region']}
  Cost: ${resource['cost']:.2f}{status}{error}
"""
        
        body += f"""
{'=' * 70}

NOTES
-----
"""
        
        # Count estimated vs actual
        estimated_count = sum(1 for r in report['resources'] if r.get('estimated', False))
        actual_count = len(report['resources']) - estimated_count
        
        if estimated_count > 0:
            body += f"""
* {estimated_count} resource(s) have estimated costs (cost allocation tags not configured)
* {actual_count} resource(s) have actual costs from AWS Cost Explorer

To get actual costs for all resources:
1. Enable Cost Allocation Tags in AWS Console → Billing → Cost Allocation Tags
2. Tag resources with 'ResourceId' tag
3. Wait 24 hours for tags to appear in Cost Explorer
"""
        else:
            body += "* All costs are actual values from AWS Cost Explorer\n"
        
        body += """
{'=' * 70}

This is an automated cost report from AWS Resource Monitor.
To modify report settings, visit your dashboard.
"""
        
        return body


# Global report generator instance
report_generator = CostReportGenerator()
