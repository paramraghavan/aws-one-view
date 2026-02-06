#!/usr/bin/env python3
"""
AWS Monitor - Config-Driven Monitoring Script
Runs monitoring jobs based on YAML configuration files

Usage:
  python run_monitor.py config1.yaml config2.yaml ...
  python run_monitor.py configs/*.yaml
  python run_monitor.py --all  # Run all configs in configs/ directory

Examples:
  # Run single config
  python run_monitor.py configs/production-monitoring.yaml
  
  # Run multiple configs
  python run_monitor.py configs/production-monitoring.yaml configs/database-monitoring.yaml
  
  # Run all configs
  python run_monitor.py --all
  
  # Schedule with cron (every 15 minutes)
  */15 * * * * /usr/bin/python3 /path/to/run_monitor.py configs/production-monitoring.yaml
"""

import sys
import os
import argparse
import yaml
import json
import boto3
from datetime import datetime, timedelta
from pathlib import Path
import logging
from typing import Dict, List, Any


class ConfigMonitor:
    """Monitor AWS resources based on configuration file"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.config = self._load_config()
        self.setup_logging()
        self.session = None
        self.results = {
            'job_name': self.config['job_name'],
            'timestamp': datetime.utcnow().isoformat(),
            'config_file': config_file,
            'resources': {},
            'metrics': {},
            'costs': {},
            'alerts': [],
            'errors': []
        }
        
    def _load_config(self) -> Dict:
        """Load and validate YAML config file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Set defaults
            config.setdefault('aws_profile', 'monitor')
            config.setdefault('role_arn', None)
            config.setdefault('session_name', 'AWSMonitorSession')
            config.setdefault('regions', ['us-east-1'])
            config.setdefault('resource_types', ['ec2', 'rds'])
            config.setdefault('filters', {})
            config.setdefault('checks', {})
            config.setdefault('notifications', {})
            config.setdefault('output', {'console': True})
            
            return config
            
        except Exception as e:
            print(f"ERROR: Failed to load config {self.config_file}: {e}")
            sys.exit(1)
    
    def setup_logging(self):
        """Setup logging based on config"""
        log_config = self.config.get('output', {})
        log_file = log_config.get('log_file')
        
        handlers = []
        
        # Console handler
        if log_config.get('console', True):
            handlers.append(logging.StreamHandler(sys.stdout))
        
        # File handler
        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            handlers.append(logging.FileHandler(log_file))
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        self.logger = logging.getLogger(self.config['job_name'])
    
    def create_session(self):
        """Create AWS session with optional role assumption"""
        profile = self.config['aws_profile']
        role_arn = self.config.get('role_arn')
        session_name = self.config.get('session_name', 'AWSMonitorSession')
        
        self.logger.info(f"Creating AWS session with profile: {profile}")
        base_session = boto3.Session(profile_name=profile)
        
        if role_arn:
            self.logger.info(f"Assuming role: {role_arn}")
            try:
                sts = base_session.client('sts')
                response = sts.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName=session_name,
                    DurationSeconds=3600
                )
                
                credentials = response['Credentials']
                self.session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
                self.logger.info(f"Role assumed successfully, expires: {credentials['Expiration']}")
            except Exception as e:
                self.logger.error(f"Failed to assume role: {e}")
                raise
        else:
            self.session = base_session
    
    def discover_resources(self):
        """Discover resources based on config"""
        regions = self.config['regions']
        resource_types = self.config['resource_types']
        filters = self.config.get('filters', {})
        
        self.logger.info(f"Discovering resources: {resource_types} in {regions}")
        
        for region in regions:
            self.results['resources'][region] = {}
            
            if 'ec2' in resource_types:
                self.results['resources'][region]['ec2'] = self._discover_ec2(region, filters)
            
            if 'rds' in resource_types:
                self.results['resources'][region]['rds'] = self._discover_rds(region, filters)
            
            if 's3' in resource_types and region == regions[0]:
                self.results['resources'][region]['s3'] = self._discover_s3(filters)
            
            if 'lambda' in resource_types:
                self.results['resources'][region]['lambda'] = self._discover_lambda(region, filters)
            
            if 'eks' in resource_types:
                self.results['resources'][region]['eks'] = self._discover_eks(region, filters)
            
            if 'emr' in resource_types:
                self.results['resources'][region]['emr'] = self._discover_emr(region, filters)
    
    def _discover_ec2(self, region: str, filters: Dict) -> List[Dict]:
        """Discover EC2 instances"""
        try:
            ec2 = self.session.client('ec2', region_name=region)
            
            # Build filters
            aws_filters = []
            if filters.get('tags'):
                for key, value in filters['tags'].items():
                    aws_filters.append({'Name': f'tag:{key}', 'Values': [value]})
            
            response = ec2.describe_instances(Filters=aws_filters)
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'id': instance['InstanceId'],
                        'name': self._get_tag(instance.get('Tags', []), 'Name'),
                        'type': instance['InstanceType'],
                        'state': instance['State']['Name'],
                        'private_ip': instance.get('PrivateIpAddress'),
                        'public_ip': instance.get('PublicIpAddress'),
                        'az': instance['Placement']['AvailabilityZone']
                    })
            
            self.logger.info(f"Found {len(instances)} EC2 instances in {region}")
            return instances
            
        except Exception as e:
            self.logger.error(f"EC2 discovery error in {region}: {e}")
            self.results['errors'].append(f"EC2 discovery in {region}: {str(e)}")
            return []
    
    def _discover_rds(self, region: str, filters: Dict) -> List[Dict]:
        """Discover RDS databases"""
        try:
            rds = self.session.client('rds', region_name=region)
            response = rds.describe_db_instances()
            
            databases = []
            for db in response['DBInstances']:
                db_data = {
                    'id': db['DBInstanceIdentifier'],
                    'name': db['DBInstanceIdentifier'],
                    'engine': db['Engine'],
                    'version': db.get('EngineVersion'),
                    'class': db['DBInstanceClass'],
                    'status': db['DBInstanceStatus'],
                    'multi_az': db.get('MultiAZ', False),
                    'endpoint': db.get('Endpoint', {}).get('Address')
                }
                databases.append(db_data)
            
            self.logger.info(f"Found {len(databases)} RDS instances in {region}")
            return databases
            
        except Exception as e:
            self.logger.error(f"RDS discovery error in {region}: {e}")
            self.results['errors'].append(f"RDS discovery in {region}: {str(e)}")
            return []
    
    def _discover_s3(self, filters: Dict) -> List[Dict]:
        """Discover S3 buckets"""
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            
            buckets = []
            for bucket in response['Buckets']:
                buckets.append({
                    'name': bucket['Name'],
                    'created': bucket['CreationDate'].isoformat()
                })
            
            self.logger.info(f"Found {len(buckets)} S3 buckets")
            return buckets
            
        except Exception as e:
            self.logger.error(f"S3 discovery error: {e}")
            self.results['errors'].append(f"S3 discovery: {str(e)}")
            return []
    
    def _discover_lambda(self, region: str, filters: Dict) -> List[Dict]:
        """Discover Lambda functions"""
        try:
            lambda_client = self.session.client('lambda', region_name=region)
            response = lambda_client.list_functions()
            
            functions = []
            for func in response['Functions']:
                functions.append({
                    'name': func['FunctionName'],
                    'runtime': func.get('Runtime'),
                    'memory': func.get('MemorySize'),
                    'timeout': func.get('Timeout')
                })
            
            self.logger.info(f"Found {len(functions)} Lambda functions in {region}")
            return functions
            
        except Exception as e:
            self.logger.error(f"Lambda discovery error in {region}: {e}")
            self.results['errors'].append(f"Lambda discovery in {region}: {str(e)}")
            return []
    
    def _discover_eks(self, region: str, filters: Dict) -> List[Dict]:
        """Discover EKS clusters"""
        try:
            eks = self.session.client('eks', region_name=region)
            response = eks.list_clusters()
            
            clusters = []
            for cluster_name in response['clusters']:
                cluster = eks.describe_cluster(name=cluster_name)['cluster']
                clusters.append({
                    'name': cluster_name,
                    'version': cluster.get('version'),
                    'status': cluster.get('status'),
                    'endpoint': cluster.get('endpoint')
                })
            
            self.logger.info(f"Found {len(clusters)} EKS clusters in {region}")
            return clusters
            
        except Exception as e:
            self.logger.error(f"EKS discovery error in {region}: {e}")
            self.results['errors'].append(f"EKS discovery in {region}: {str(e)}")
            return []
    
    def _discover_emr(self, region: str, filters: Dict) -> List[Dict]:
        """Discover EMR clusters"""
        try:
            emr = self.session.client('emr', region_name=region)
            response = emr.list_clusters(
                ClusterStates=['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING']
            )
            
            clusters = []
            for cluster in response['Clusters']:
                clusters.append({
                    'id': cluster['Id'],
                    'name': cluster['Name'],
                    'status': cluster['Status']['State']
                })
            
            self.logger.info(f"Found {len(clusters)} EMR clusters in {region}")
            return clusters
            
        except Exception as e:
            self.logger.error(f"EMR discovery error in {region}: {e}")
            self.results['errors'].append(f"EMR discovery in {region}: {str(e)}")
            return []
    
    def collect_metrics(self):
        """Collect performance metrics if enabled"""
        if not self.config.get('checks', {}).get('performance', {}).get('enabled'):
            return
        
        self.logger.info("Collecting performance metrics")
        period = self.config['checks']['performance'].get('period', 300)
        
        # Collect metrics for discovered resources
        for region, resource_types in self.results['resources'].items():
            self.results['metrics'][region] = {}
            
            if 'ec2' in resource_types:
                for instance in resource_types['ec2']:
                    metrics = self._get_ec2_metrics(region, instance['id'], period)
                    if metrics:
                        self.results['metrics'][region][instance['id']] = metrics
    
    def _get_ec2_metrics(self, region: str, instance_id: str, period: int) -> Dict:
        """Get CloudWatch metrics for EC2 instance"""
        try:
            cw = self.session.client('cloudwatch', region_name=region)
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(seconds=period)
            
            # Get CPU utilization
            response = cw.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average', 'Maximum']
            )
            
            if response['Datapoints']:
                datapoint = response['Datapoints'][0]
                return {
                    'cpu_avg': datapoint.get('Average', 0),
                    'cpu_max': datapoint.get('Maximum', 0)
                }
            
            return {}
            
        except Exception as e:
            self.logger.error(f"Metrics error for {instance_id}: {e}")
            return {}
    
    def analyze_costs(self):
        """Analyze costs if enabled"""
        if not self.config.get('checks', {}).get('cost', {}).get('enabled'):
            return
        
        self.logger.info("Analyzing costs")
        days = self.config['checks']['cost'].get('days', 7)
        
        try:
            ce = self.session.client('ce', region_name='us-east-1')
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.strftime('%Y-%m-%d'),
                    'End': end_date.strftime('%Y-%m-%d')
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
            )
            
            total_cost = 0
            for result in response['ResultsByTime']:
                for group in result['Groups']:
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    total_cost += cost
            
            self.results['costs'] = {
                'period_days': days,
                'total_cost': round(total_cost, 2),
                'daily_average': round(total_cost / days, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Cost analysis error: {e}")
            self.results['errors'].append(f"Cost analysis: {str(e)}")
    
    def check_alerts(self):
        """Check for alerts based on thresholds"""
        if not self.config.get('checks', {}).get('alerts', {}).get('enabled'):
            return
        
        self.logger.info("Checking alerts")
        thresholds = self.config['checks']['alerts'].get('thresholds', {})
        
        # Check CPU thresholds
        cpu_threshold = thresholds.get('cpu', 80)
        for region, metrics in self.results.get('metrics', {}).items():
            for resource_id, metric_data in metrics.items():
                cpu = metric_data.get('cpu_avg', 0)
                if cpu > cpu_threshold:
                    self.results['alerts'].append({
                        'severity': 'warning',
                        'resource': resource_id,
                        'region': region,
                        'message': f'High CPU utilization: {cpu:.1f}%',
                        'threshold': cpu_threshold
                    })
    
    def send_notifications(self):
        """Send notifications if configured"""
        if not self.results['alerts'] and not self.results['errors']:
            return
        
        notification_config = self.config.get('notifications', {})
        
        # Email notification
        if notification_config.get('email', {}).get('enabled'):
            self._send_email_notification(notification_config['email'])
        
        # Slack notification
        if notification_config.get('slack', {}).get('enabled'):
            self._send_slack_notification(notification_config['slack'])
        
        # SNS notification
        if notification_config.get('sns', {}).get('enabled'):
            self._send_sns_notification(notification_config['sns'])
    
    def _send_email_notification(self, email_config: Dict):
        """Send email notification"""
        # Placeholder - implement with SES or SMTP
        self.logger.info(f"Would send email to: {email_config.get('to')}")
    
    def _send_slack_notification(self, slack_config: Dict):
        """Send Slack notification"""
        # Placeholder - implement with requests to webhook
        self.logger.info(f"Would send Slack notification")
    
    def _send_sns_notification(self, sns_config: Dict):
        """Send SNS notification"""
        try:
            sns = self.session.client('sns')
            message = json.dumps(self.results, indent=2, default=str)
            
            sns.publish(
                TopicArn=sns_config['topic_arn'],
                Subject=f"AWS Monitor Alert: {self.config['job_name']}",
                Message=message
            )
            self.logger.info("SNS notification sent")
        except Exception as e:
            self.logger.error(f"SNS notification error: {e}")
    
    def save_output(self):
        """Save results to file"""
        output_config = self.config.get('output', {})
        json_file = output_config.get('json_file')
        
        if json_file:
            output_dir = os.path.dirname(json_file)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            with open(json_file, 'w') as f:
                json.dump(self.results, f, indent=2, default=str)
            
            self.logger.info(f"Results saved to: {json_file}")
    
    def print_summary(self):
        """Print summary of results"""
        format_type = self.config.get('output', {}).get('format', 'detailed')
        
        print("\n" + "="*60)
        print(f"AWS Monitor: {self.config['job_name']}")
        print(f"Timestamp: {self.results['timestamp']}")
        print("="*60)
        
        # Resource summary
        total_resources = 0
        for region, types in self.results.get('resources', {}).items():
            for resource_type, resources in types.items():
                count = len(resources)
                if count > 0:
                    print(f"{resource_type.upper()} in {region}: {count}")
                    total_resources += count
        
        print(f"\nTotal Resources: {total_resources}")
        
        # Costs
        if self.results.get('costs'):
            print(f"\nCost ({self.results['costs']['period_days']} days):")
            print(f"  Total: ${self.results['costs']['total_cost']}")
            print(f"  Daily Avg: ${self.results['costs']['daily_average']}")
        
        # Alerts
        if self.results['alerts']:
            print(f"\n⚠️  Alerts: {len(self.results['alerts'])}")
            for alert in self.results['alerts']:
                print(f"  - {alert['resource']}: {alert['message']}")
        
        # Errors
        if self.results['errors']:
            print(f"\n❌ Errors: {len(self.results['errors'])}")
            for error in self.results['errors']:
                print(f"  - {error}")
        
        print("="*60 + "\n")
    
    def _get_tag(self, tags: List, key: str) -> str:
        """Extract tag value from AWS tags list"""
        for tag in tags:
            if tag['Key'] == key:
                return tag['Value']
        return ''
    
    def run(self):
        """Execute the monitoring job"""
        try:
            self.logger.info(f"Starting job: {self.config['job_name']}")
            self.logger.info(f"Config: {self.config_file}")
            
            # Create AWS session
            self.create_session()
            
            # Discover resources
            self.discover_resources()
            
            # Collect metrics
            self.collect_metrics()
            
            # Analyze costs
            self.analyze_costs()
            
            # Check alerts
            self.check_alerts()
            
            # Send notifications
            self.send_notifications()
            
            # Save output
            self.save_output()
            
            # Print summary
            self.print_summary()
            
            self.logger.info(f"Job completed: {self.config['job_name']}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Job failed: {e}")
            self.results['errors'].append(f"Job execution: {str(e)}")
            return False


def main():
    parser = argparse.ArgumentParser(
        description='AWS Monitor - Config-driven monitoring',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run single config
  python run_monitor.py configs/production-monitoring.yaml
  
  # Run multiple configs
  python run_monitor.py configs/prod.yaml configs/dev.yaml
  
  # Run all configs in directory
  python run_monitor.py --all
  python run_monitor.py configs/*.yaml
        """
    )
    
    parser.add_argument(
        'configs',
        nargs='*',
        help='Path to config file(s)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Run all configs in configs/ directory'
    )
    
    parser.add_argument(
        '--config-dir',
        default='configs',
        help='Directory containing config files (default: configs/)'
    )
    
    args = parser.parse_args()
    
    # Determine which configs to run
    config_files = []
    
    if args.all:
        config_dir = Path(args.config_dir)
        if config_dir.exists():
            config_files = list(config_dir.glob('*.yaml')) + list(config_dir.glob('*.yml'))
        else:
            print(f"ERROR: Config directory not found: {args.config_dir}")
            sys.exit(1)
    elif args.configs:
        config_files = args.configs
    else:
        parser.print_help()
        sys.exit(1)
    
    if not config_files:
        print("ERROR: No config files found")
        sys.exit(1)
    
    # Run each config
    print(f"\n{'='*60}")
    print(f"AWS Monitor - Running {len(config_files)} config(s)")
    print(f"{'='*60}\n")
    
    results = []
    for config_file in config_files:
        monitor = ConfigMonitor(config_file)
        success = monitor.run()
        results.append((config_file, success))
    
    # Summary
    print(f"\n{'='*60}")
    print("Final Summary")
    print(f"{'='*60}")
    
    for config_file, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status}: {config_file}")
    
    successful = sum(1 for _, success in results if success)
    print(f"\nTotal: {len(results)} jobs, {successful} successful, {len(results) - successful} failed")
    print(f"{'='*60}\n")
    
    # Exit with error if any job failed
    sys.exit(0 if successful == len(results) else 1)


if __name__ == '__main__':
    main()
