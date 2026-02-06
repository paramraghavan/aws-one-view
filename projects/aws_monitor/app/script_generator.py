"""
Script Generator - Creates standalone monitoring scripts
Users can schedule generated scripts with cron or task scheduler
"""
from datetime import datetime
import json


class ScriptGenerator:
    """Generate Python monitoring scripts for scheduling"""
    
    def generate(self, config, role_arn=None, session_name='AWSMonitorSession'):
        """
        Generate monitoring script based on configuration
        
        Args:
            config: dict with regions, resources, checks, thresholds, notification
            role_arn: Optional ARN of IAM role to assume
            session_name: Session name for role assumption
        
        Returns:
            str: Complete Python script content
        """
        regions = config.get('regions', ['us-east-1'])
        resources = config.get('resources', {})
        checks = config.get('checks', ['performance'])
        thresholds = config.get('thresholds', {})
        notification = config.get('notification', {})
        
        script = self._generate_header()
        script += self._generate_imports()
        script += self._generate_config(regions, resources, thresholds, notification, role_arn, session_name)
        script += self._generate_monitor_class()
        
        # Add check functions based on requested checks
        if 'performance' in checks:
            script += self._generate_performance_check()
        if 'cost' in checks:
            script += self._generate_cost_check()
        if 'alerts' in checks:
            script += self._generate_alert_check()
        
        script += self._generate_notification_functions(notification)
        script += self._generate_main()
        
        return script
    
    def _generate_header(self):
        """Generate script header with usage instructions"""
        return '''#!/usr/bin/env python3
"""
AWS Monitor - Generated Monitoring Script
Generated: {timestamp}

Usage:
    python aws_monitor_job.py

Schedule with cron:
    # Run every 5 minutes
    */5 * * * * /usr/bin/python3 /path/to/aws_monitor_job.py >> /var/log/aws_monitor.log 2>&1
    
    # Run every hour
    0 * * * * /usr/bin/python3 /path/to/aws_monitor_job.py
    
    # Run daily at 8 AM
    0 8 * * * /usr/bin/python3 /path/to/aws_monitor_job.py

Schedule with Python APScheduler:
    from apscheduler.schedulers.blocking import BlockingScheduler
    scheduler = BlockingScheduler()
    scheduler.add_job(main, 'interval', minutes=5)
    scheduler.start()

Requirements:
    pip install boto3
    
    Optional (for email notifications):
    pip install sendgrid  # or use SMTP

AWS Configuration:
    Ensure AWS profile 'monitor' is configured:
    aws configure --profile monitor
    
    Or set environment variables:
    export AWS_ACCESS_KEY_ID=your_key
    export AWS_SECRET_ACCESS_KEY=your_secret
    export AWS_DEFAULT_REGION=us-east-1
"""

'''.format(timestamp=datetime.utcnow().isoformat())
    
    def _generate_imports(self):
        """Generate import statements"""
        return '''import boto3
import json
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('aws_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

'''
    
    def _generate_config(self, regions, resources, thresholds, notification, role_arn, session_name):
        """Generate configuration section"""
        role_config = f"ROLE_ARN = '{role_arn}'\nSESSION_NAME = '{session_name}'" if role_arn else "ROLE_ARN = None\nSESSION_NAME = None"
        
        config_str = f'''
# ===== CONFIGURATION =====
AWS_PROFILE = 'monitor'
{role_config}
REGIONS = {regions}

# Resource filters
RESOURCE_FILTERS = {json.dumps(resources, indent=4)}

# Alert thresholds
THRESHOLDS = {json.dumps(thresholds, indent=4)}

# Notification settings
NOTIFICATION_CONFIG = {json.dumps(notification, indent=4)}

'''
        return config_str
    
    def _generate_monitor_class(self):
        """Generate main monitor class"""
        return '''
class AWSMonitor:
    """AWS Resource Monitor"""
    
    def __init__(self):
        # Create base session with profile
        base_session = boto3.Session(profile_name=AWS_PROFILE)
        
        # If role ARN provided, assume the role
        if ROLE_ARN:
            logger.info(f"Assuming role: {ROLE_ARN}")
            try:
                sts = base_session.client('sts')
                response = sts.assume_role(
                    RoleArn=ROLE_ARN,
                    RoleSessionName=SESSION_NAME,
                    DurationSeconds=3600
                )
                
                credentials = response['Credentials']
                
                # Create new session with assumed role credentials
                self.session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
                
                logger.info(f"Successfully assumed role: {ROLE_ARN}")
                logger.info(f"Session expires at: {credentials['Expiration']}")
                
            except Exception as e:
                logger.error(f"Failed to assume role {ROLE_ARN}: {e}")
                raise
        else:
            # Use base session with profile
            self.session = base_session
            logger.info(f"Using base profile: {AWS_PROFILE}")
        
        self.results = {
            'timestamp': datetime.utcnow().isoformat(),
            'resources': {},
            'alerts': [],
            'costs': {}
        }
    
    def discover_resources(self):
        """Discover resources based on filters"""
        logger.info("Discovering resources...")
        
        resource_types = RESOURCE_FILTERS.get('types', [])
        filters = RESOURCE_FILTERS.get('filters', {})
        
        for region in REGIONS:
            self.results['resources'][region] = {}
            
            if 'ec2' in resource_types:
                self.results['resources'][region]['ec2'] = self._discover_ec2(region, filters)
            
            if 'rds' in resource_types:
                self.results['resources'][region]['rds'] = self._discover_rds(region, filters)
            
            if 'lambda' in resource_types:
                self.results['resources'][region]['lambda'] = self._discover_lambda(region, filters)
            
            if 'eks' in resource_types:
                self.results['resources'][region]['eks'] = self._discover_eks(region, filters)
            
            if 'emr' in resource_types:
                self.results['resources'][region]['emr'] = self._discover_emr(region, filters)
        
        total = sum(len(resources) for region_data in self.results['resources'].values() 
                   for resources in region_data.values())
        logger.info(f"Discovered {total} resources")
    
    def _discover_ec2(self, region, filters):
        """Discover EC2 instances"""
        try:
            ec2 = self.session.client('ec2', region_name=region)
            
            api_filters = []
            if filters.get('tags'):
                for k, v in filters['tags'].items():
                    api_filters.append({'Name': f'tag:{k}', 'Values': [v]})
            if filters.get('ids'):
                api_filters.append({'Name': 'instance-id', 'Values': filters['ids']})
            
            response = ec2.describe_instances(Filters=api_filters)
            
            instances = []
            for reservation in response['Reservations']:
                for inst in reservation['Instances']:
                    name = self._get_tag(inst.get('Tags', []), 'Name')
                    
                    if filters.get('names') and name not in filters['names']:
                        continue
                    
                    instances.append({
                        'id': inst['InstanceId'],
                        'name': name,
                        'type': inst['InstanceType'],
                        'state': inst['State']['Name'],
                        'region': region
                    })
            
            return instances
        except Exception as e:
            logger.error(f"EC2 discovery error in {region}: {e}")
            return []
    
    def _discover_rds(self, region, filters):
        """Discover RDS instances"""
        try:
            rds = self.session.client('rds', region_name=region)
            response = rds.describe_db_instances()
            
            instances = []
            for db in response['DBInstances']:
                name = db['DBInstanceIdentifier']
                
                if filters.get('names') and name not in filters['names']:
                    continue
                
                instances.append({
                    'id': db['DbiResourceId'],
                    'name': name,
                    'class': db['DBInstanceClass'],
                    'status': db['DBInstanceStatus'],
                    'region': region
                })
            
            return instances
        except Exception as e:
            logger.error(f"RDS discovery error in {region}: {e}")
            return []
    
    def _discover_lambda(self, region, filters):
        """Discover Lambda functions"""
        try:
            lambda_client = self.session.client('lambda', region_name=region)
            response = lambda_client.list_functions()
            
            functions = []
            for func in response['Functions']:
                name = func['FunctionName']
                
                if filters.get('names') and name not in filters['names']:
                    continue
                
                functions.append({
                    'name': name,
                    'runtime': func['Runtime'],
                    'region': region
                })
            
            return functions
        except Exception as e:
            logger.error(f"Lambda discovery error in {region}: {e}")
            return []
    
    def _discover_eks(self, region, filters):
        """Discover EKS clusters"""
        try:
            eks = self.session.client('eks', region_name=region)
            response = eks.list_clusters()
            
            clusters = []
            for cluster_name in response['clusters']:
                if filters.get('names') and cluster_name not in filters['names']:
                    continue
                
                cluster = eks.describe_cluster(name=cluster_name)['cluster']
                clusters.append({
                    'name': cluster_name,
                    'status': cluster['status'],
                    'version': cluster['version'],
                    'region': region
                })
            
            return clusters
        except Exception as e:
            logger.error(f"EKS discovery error in {region}: {e}")
            return []
    
    def _discover_emr(self, region, filters):
        """Discover EMR clusters"""
        try:
            emr = self.session.client('emr', region_name=region)
            response = emr.list_clusters(ClusterStates=['RUNNING', 'WAITING'])
            
            clusters = []
            for cluster in response['Clusters']:
                name = cluster['Name']
                
                if filters.get('names') and name not in filters['names']:
                    continue
                
                clusters.append({
                    'id': cluster['Id'],
                    'name': name,
                    'status': cluster['Status']['State'],
                    'region': region
                })
            
            return clusters
        except Exception as e:
            logger.error(f"EMR discovery error in {region}: {e}")
            return []
    
    def _get_tag(self, tags, key):
        """Get tag value"""
        for tag in tags:
            if tag['Key'] == key:
                return tag['Value']
        return ''

'''
    
    def _generate_performance_check(self):
        """Generate performance monitoring code"""
        return '''
    def check_performance(self):
        """Check performance metrics"""
        logger.info("Checking performance metrics...")
        
        for region, resource_types in self.results['resources'].items():
            for resource_type, resources in resource_types.items():
                for resource in resources:
                    try:
                        if resource_type == 'ec2':
                            metrics = self._get_ec2_metrics(resource['id'], region)
                            self._check_thresholds(resource, metrics, 'ec2')
                        
                        elif resource_type == 'rds':
                            metrics = self._get_rds_metrics(resource['name'], region)
                            self._check_thresholds(resource, metrics, 'rds')
                        
                        elif resource_type == 'lambda':
                            metrics = self._get_lambda_metrics(resource['name'], region)
                            self._check_thresholds(resource, metrics, 'lambda')
                    
                    except Exception as e:
                        logger.error(f"Error checking {resource_type} {resource.get('id', resource.get('name'))}: {e}")
    
    def _get_ec2_metrics(self, instance_id, region):
        """Get EC2 CloudWatch metrics"""
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=15)
        
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Average', 'Maximum']
        )
        
        if response['Datapoints']:
            latest = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
            return {
                'cpu': latest['Average'],
                'cpu_max': latest['Maximum']
            }
        return {}
    
    def _get_rds_metrics(self, db_identifier, region):
        """Get RDS CloudWatch metrics"""
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=15)
        
        metrics = {}
        for metric_name in ['CPUUtilization', 'DatabaseConnections']:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName=metric_name,
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_identifier}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=['Average']
            )
            
            if response['Datapoints']:
                latest = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                metrics[metric_name.lower()] = latest['Average']
        
        return metrics
    
    def _get_lambda_metrics(self, function_name, region):
        """Get Lambda CloudWatch metrics"""
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=15)
        
        metrics = {}
        for metric_name in ['Invocations', 'Errors', 'Duration']:
            stat = 'Sum' if metric_name in ['Invocations', 'Errors'] else 'Average'
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName=metric_name,
                Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                StartTime=start_time,
                EndTime=end_time,
                Period=300,
                Statistics=[stat]
            )
            
            if response['Datapoints']:
                latest = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])[-1]
                metrics[metric_name.lower()] = latest[stat]
        
        return metrics
    
    def _check_thresholds(self, resource, metrics, resource_type):
        """Check metrics against thresholds"""
        if not metrics:
            return
        
        # Check CPU threshold
        if 'cpu' in metrics or 'cpuutilization' in metrics:
            cpu = metrics.get('cpu') or metrics.get('cpuutilization')
            threshold = THRESHOLDS.get('cpu', 80)
            
            if cpu > threshold:
                alert = {
                    'severity': 'CRITICAL',
                    'resource_type': resource_type,
                    'resource_id': resource.get('id', resource.get('name')),
                    'resource_name': resource.get('name', ''),
                    'metric': 'CPU',
                    'value': cpu,
                    'threshold': threshold,
                    'message': f"CPU {cpu:.1f}% exceeds threshold {threshold}%"
                }
                self.results['alerts'].append(alert)
                logger.warning(f"ALERT: {alert['message']} for {alert['resource_id']}")
        
        # Check Lambda errors
        if resource_type == 'lambda' and 'errors' in metrics:
            if metrics['errors'] > 0:
                alert = {
                    'severity': 'WARNING',
                    'resource_type': resource_type,
                    'resource_id': resource['name'],
                    'metric': 'Errors',
                    'value': metrics['errors'],
                    'message': f"Lambda function has {metrics['errors']} errors"
                }
                self.results['alerts'].append(alert)
                logger.warning(f"ALERT: {alert['message']}")
        
        # Check RDS connections
        if resource_type == 'rds' and 'databaseconnections' in metrics:
            connections = metrics['databaseconnections']
            max_conn = THRESHOLDS.get('max_db_connections', 100)
            
            if connections > max_conn * 0.9:
                alert = {
                    'severity': 'CRITICAL',
                    'resource_type': resource_type,
                    'resource_id': resource['name'],
                    'metric': 'Connections',
                    'value': connections,
                    'threshold': max_conn,
                    'message': f"Database connections {connections} near limit {max_conn}"
                }
                self.results['alerts'].append(alert)
                logger.warning(f"ALERT: {alert['message']}")

'''
    
    def _generate_cost_check(self):
        """Generate cost analysis code"""
        return '''
    def check_costs(self):
        """Analyze costs"""
        logger.info("Analyzing costs...")
        
        try:
            ce = self.session.client('ce', region_name='us-east-1')
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=7)
            
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.isoformat(),
                    'End': end_date.isoformat()
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            costs_by_service = {}
            total_cost = 0
            
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    service = group['Keys'][0]
                    amount = float(group['Metrics']['UnblendedCost']['Amount'])
                    costs_by_service[service] = costs_by_service.get(service, 0) + amount
                    total_cost += amount
            
            self.results['costs'] = {
                'period': f"{start_date} to {end_date}",
                'total': round(total_cost, 2),
                'by_service': {k: round(v, 2) for k, v in sorted(costs_by_service.items(), key=lambda x: x[1], reverse=True)[:5]}
            }
            
            logger.info(f"Total cost for last 7 days: ${total_cost:.2f}")
            
        except Exception as e:
            logger.error(f"Cost analysis error: {e}")
            self.results['costs'] = {'error': str(e)}

'''
    
    def _generate_alert_check(self):
        """Generate alert checking code"""
        return '''
    def check_failover(self):
        """Check for failover issues and health"""
        logger.info("Checking failover and health...")
        
        for region, resource_types in self.results['resources'].items():
            # Check RDS Multi-AZ
            if 'rds' in resource_types:
                for db in resource_types['rds']:
                    try:
                        rds = self.session.client('rds', region_name=region)
                        details = rds.describe_db_instances(DBInstanceIdentifier=db['name'])
                        instance = details['DBInstances'][0]
                        
                        if not instance['MultiAZ']:
                            alert = {
                                'severity': 'INFO',
                                'resource_type': 'rds',
                                'resource_id': db['name'],
                                'message': f"RDS instance {db['name']} is not configured for Multi-AZ"
                            }
                            self.results['alerts'].append(alert)
                    except Exception as e:
                        logger.error(f"Error checking RDS Multi-AZ: {e}")
            
            # Check EKS node health
            if 'eks' in resource_types:
                for cluster in resource_types['eks']:
                    try:
                        eks = self.session.client('eks', region_name=region)
                        ng_response = eks.list_nodegroups(clusterName=cluster['name'])
                        
                        for ng_name in ng_response['nodegroups']:
                            ng = eks.describe_nodegroup(
                                clusterName=cluster['name'],
                                nodegroupName=ng_name
                            )['nodegroup']
                            
                            if ng['status'] != 'ACTIVE':
                                alert = {
                                    'severity': 'CRITICAL',
                                    'resource_type': 'eks',
                                    'resource_id': cluster['name'],
                                    'message': f"EKS node group {ng_name} status: {ng['status']}"
                                }
                                self.results['alerts'].append(alert)
                    except Exception as e:
                        logger.error(f"Error checking EKS health: {e}")

'''
    
    def _generate_notification_functions(self, notification):
        """Generate notification functions"""
        email = notification.get('email', '')
        
        return f'''
    def send_notifications(self):
        """Send notifications if there are alerts"""
        if not self.results['alerts']:
            logger.info("No alerts to notify")
            return
        
        critical_count = len([a for a in self.results['alerts'] if a.get('severity') == 'CRITICAL'])
        warning_count = len([a for a in self.results['alerts'] if a.get('severity') == 'WARNING'])
        
        logger.info(f"Alerts: {{critical_count}} critical, {{warning_count}} warnings")
        
        # Send email if configured
        if NOTIFICATION_CONFIG.get('email'):
            self._send_email_notification(critical_count, warning_count)
        
        # Save to file
        self._save_results()
    
    def _send_email_notification(self, critical_count, warning_count):
        """Send email notification"""
        email = NOTIFICATION_CONFIG['email']
        
        subject = f"AWS Monitor Alert: {{critical_count}} critical, {{warning_count}} warnings"
        
        body = f"""
AWS Monitor Alert Report
Generated: {{datetime.utcnow().isoformat()}}

Summary:
- Critical Alerts: {{critical_count}}
- Warning Alerts: {{warning_count}}
- Total Resources Monitored: {{sum(len(r) for region in self.results['resources'].values() for r in region.values())}}

Alerts:
"""
        for alert in self.results['alerts']:
            body += f"\\n[{{alert['severity']}}] {{alert.get('resource_type')}} {{alert.get('resource_id')}}: {{alert['message']}}"
        
        logger.info(f"Would send email to {{email}}")
        # TODO: Implement actual email sending using SMTP or SendGrid
        # Example with SMTP:
        # import smtplib
        # from email.mime.text import MIMEText
        # msg = MIMEText(body)
        # msg['Subject'] = subject
        # msg['From'] = 'aws-monitor@example.com'
        # msg['To'] = email
        # s = smtplib.SMTP('localhost')
        # s.send_message(msg)
        # s.quit()
    
    def _save_results(self):
        """Save results to JSON file"""
        filename = f"aws_monitor_{{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}}.json"
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {{filename}}")

'''
    
    def _generate_main(self):
        """Generate main execution function"""
        return '''
def main():
    """Main execution function"""
    logger.info("=" * 60)
    logger.info("AWS Monitor Job Started")
    logger.info("=" * 60)
    
    try:
        monitor = AWSMonitor()
        
        # Discover resources
        monitor.discover_resources()
        
        # Run checks based on configuration
        checks_to_run = ['performance', 'cost', 'alerts']  # Customize as needed
        
        if 'performance' in checks_to_run:
            monitor.check_performance()
        
        if 'cost' in checks_to_run:
            monitor.check_costs()
        
        if 'alerts' in checks_to_run:
            monitor.check_failover()
        
        # Send notifications
        monitor.send_notifications()
        
        logger.info("=" * 60)
        logger.info("AWS Monitor Job Completed Successfully")
        logger.info("=" * 60)
        
        return 0
    
    except Exception as e:
        logger.error(f"Job failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit(main())
'''


# Example usage for testing
if __name__ == '__main__':
    generator = ScriptGenerator()
    config = {
        'regions': ['us-east-1', 'us-west-2'],
        'resources': {
            'types': ['ec2', 'rds', 'lambda'],
            'filters': {
                'tags': {'Environment': 'production'},
                'names': [],
                'ids': []
            }
        },
        'checks': ['performance', 'cost', 'alerts'],
        'thresholds': {
            'cpu': 80,
            'memory': 85,
            'max_db_connections': 100
        },
        'notification': {
            'email': 'admin@example.com'
        }
    }
    
    script = generator.generate(config)
    print(script)
