"""
AWS Client - Handles all AWS API interactions.
This module provides a clean interface to AWS services.
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from app.config import Config

logger = logging.getLogger(__name__)


class AWSClient:
    """
    Unified client for AWS API operations.
    
    This class handles:
    - Resource discovery across services
    - CloudWatch metrics collection
    - Cost analysis via Cost Explorer
    - Bottleneck detection
    """
    
    def __init__(self):
        """Initialize AWS session using default credentials."""
        self.session = boto3.Session()
        logger.info("AWS client initialized")
    
    # ============================================================================
    # REGION OPERATIONS
    # ============================================================================
    
    def get_regions(self) -> List[str]:
        """
        Get list of all available AWS regions.
        
        Returns:
            List of region names (e.g., ['us-east-1', 'us-west-2'])
        """
        ec2 = self.session.client('ec2', region_name='us-east-1')
        response = ec2.describe_regions()
        return [r['RegionName'] for r in response['Regions']]
    
    # ============================================================================
    # RESOURCE DISCOVERY
    # ============================================================================
    
    def get_all_resources(self, regions: List[str]) -> Dict[str, List[Dict]]:
        """
        Discover all resources across specified regions.
        Continues gracefully if individual resource types fail.
        
        Args:
            regions: List of AWS regions to scan
        
        Returns:
            Dictionary with resource types as keys and lists of resources as values
            Example: {'ec2': [...], 'rds': [...], 's3': [...]}
        """
        resources = {
            'ec2': [],
            'rds': [],
            's3': [],
            'lambda': [],
            'ebs': []
        }
        
        for region in regions:
            logger.info(f"Scanning region: {region}")
            
            # Get EC2 instances (with error handling)
            try:
                ec2_list = self._get_ec2_instances(region)
                resources['ec2'].extend(ec2_list)
                logger.info(f"Found {len(ec2_list)} EC2 instances in {region}")
            except Exception as e:
                logger.warning(f"Cannot access EC2 in {region}: {e}. Continuing with other resources...")
            
            # Get RDS instances (with error handling)
            try:
                rds_list = self._get_rds_instances(region)
                resources['rds'].extend(rds_list)
                logger.info(f"Found {len(rds_list)} RDS instances in {region}")
            except Exception as e:
                logger.warning(f"Cannot access RDS in {region}: {e}. Continuing with other resources...")
            
            # Get Lambda functions (with error handling)
            try:
                lambda_list = self._get_lambda_functions(region)
                resources['lambda'].extend(lambda_list)
                logger.info(f"Found {len(lambda_list)} Lambda functions in {region}")
            except Exception as e:
                logger.warning(f"Cannot access Lambda in {region}: {e}. Continuing with other resources...")
            
            # Get EBS volumes (with error handling)
            try:
                ebs_list = self._get_ebs_volumes(region)
                resources['ebs'].extend(ebs_list)
                logger.info(f"Found {len(ebs_list)} EBS volumes in {region}")
            except Exception as e:
                logger.warning(f"Cannot access EBS in {region}: {e}. Continuing with other resources...")
        
        # Get S3 buckets (global service, with error handling)
        try:
            s3_list = self._get_s3_buckets()
            resources['s3'] = s3_list
            logger.info(f"Found {len(s3_list)} S3 buckets")
        except Exception as e:
            logger.warning(f"Cannot access S3: {e}. Continuing with other resources...")
            resources['s3'] = []
        
        # Log summary
        total_resources = sum(len(v) for v in resources.values())
        logger.info(f"Successfully retrieved {total_resources} total resources")
        
        return resources
    
    def _get_ec2_instances(self, region: str) -> List[Dict[str, Any]]:
        """Get all EC2 instances in a region."""
        try:
            ec2 = self.session.client('ec2', region_name=region)
            response = ec2.describe_instances()
            
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'id': instance['InstanceId'],
                        'type': instance['InstanceType'],
                        'state': instance['State']['Name'],
                        'region': region,
                        'launch_time': instance['LaunchTime'].isoformat(),
                        'tags': self._extract_tags(instance.get('Tags', []))
                    })
            
            return instances
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UnauthorizedOperation':
                logger.warning(f"No permission to access EC2 in {region}")
            elif error_code == 'OptInRequired':
                logger.info(f"Region {region} is not enabled in your account")
            else:
                logger.error(f"AWS error getting EC2 instances in {region}: {error_code} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting EC2 instances in {region}: {type(e).__name__} - {e}")
            raise
    
    def _get_rds_instances(self, region: str) -> List[Dict[str, Any]]:
        """Get all RDS instances in a region."""
        try:
            rds = self.session.client('rds', region_name=region)
            response = rds.describe_db_instances()
            
            instances = []
            for db in response['DBInstances']:
                instances.append({
                    'id': db['DBInstanceIdentifier'],
                    'class': db['DBInstanceClass'],
                    'engine': db['Engine'],
                    'status': db['DBInstanceStatus'],
                    'region': region,
                    'storage_gb': db['AllocatedStorage']
                })
            
            return instances
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                logger.warning(f"No permission to access RDS in {region}")
            else:
                logger.error(f"AWS error getting RDS instances in {region}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting RDS instances in {region}: {type(e).__name__} - {e}")
            raise
    
    def _get_s3_buckets(self) -> List[Dict[str, Any]]:
        """Get all S3 buckets (global service)."""
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            
            buckets = []
            for bucket in response['Buckets']:
                # Get bucket region (handle errors for individual buckets)
                try:
                    location = s3.get_bucket_location(Bucket=bucket['Name'])
                    region = location['LocationConstraint'] or 'us-east-1'
                except Exception as e:
                    logger.debug(f"Could not get location for bucket {bucket['Name']}: {e}")
                    region = 'unknown'
                
                buckets.append({
                    'id': bucket['Name'],
                    'region': region,
                    'created': bucket['CreationDate'].isoformat()
                })
            
            return buckets
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                logger.warning("No permission to list S3 buckets")
            else:
                logger.error(f"AWS error getting S3 buckets: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting S3 buckets: {type(e).__name__} - {e}")
            raise
    
    def _get_lambda_functions(self, region: str) -> List[Dict[str, Any]]:
        """Get all Lambda functions in a region."""
        try:
            lambda_client = self.session.client('lambda', region_name=region)
            response = lambda_client.list_functions()
            
            functions = []
            for func in response['Functions']:
                functions.append({
                    'id': func['FunctionName'],
                    'runtime': func['Runtime'],
                    'memory_mb': func['MemorySize'],
                    'timeout_sec': func['Timeout'],
                    'region': region
                })
            
            return functions
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                logger.warning(f"No permission to access Lambda in {region}")
            else:
                logger.error(f"AWS error getting Lambda functions in {region}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting Lambda functions in {region}: {type(e).__name__} - {e}")
            raise
    
    def _get_ebs_volumes(self, region: str) -> List[Dict[str, Any]]:
        """Get all EBS volumes in a region."""
        try:
            ec2 = self.session.client('ec2', region_name=region)
            response = ec2.describe_volumes()
            
            volumes = []
            for volume in response['Volumes']:
                volumes.append({
                    'id': volume['VolumeId'],
                    'size_gb': volume['Size'],
                    'type': volume['VolumeType'],
                    'state': volume['State'],
                    'region': region,
                    'attached': len(volume['Attachments']) > 0
                })
            
            return volumes
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UnauthorizedOperation':
                logger.warning(f"No permission to access EBS volumes in {region}")
            else:
                logger.error(f"AWS error getting EBS volumes in {region}: {error_code}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting EBS volumes in {region}: {type(e).__name__} - {e}")
            raise
    
    # ============================================================================
    # CLOUDWATCH METRICS
    # ============================================================================
    
    def get_metrics(
        self,
        resource_type: str,
        resource_ids: List[str],
        region: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get CloudWatch metrics for resources.
        Continues gracefully if individual resources fail.
        
        Args:
            resource_type: Type of resource ('ec2', 'rds', 'lambda')
            resource_ids: List of resource IDs to get metrics for
            region: AWS region
            hours: Number of hours of historical data
        
        Returns:
            Dictionary mapping resource IDs to their metrics
        """
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        metrics = {}
        
        for resource_id in resource_ids:
            try:
                if resource_type == 'ec2':
                    metrics[resource_id] = self._get_ec2_metrics(
                        cloudwatch, resource_id, start_time, end_time
                    )
                elif resource_type == 'rds':
                    metrics[resource_id] = self._get_rds_metrics(
                        cloudwatch, resource_id, start_time, end_time
                    )
                elif resource_type == 'lambda':
                    metrics[resource_id] = self._get_lambda_metrics(
                        cloudwatch, resource_id, start_time, end_time
                    )
                
                logger.info(f"Successfully retrieved metrics for {resource_id}")
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'AccessDenied':
                    logger.warning(f"No permission to get metrics for {resource_id}")
                else:
                    logger.error(f"AWS error getting metrics for {resource_id}: {error_code}")
                metrics[resource_id] = {'error': f'Access denied or resource not found'}
            except Exception as e:
                logger.error(f"Error getting metrics for {resource_id}: {type(e).__name__} - {e}")
                metrics[resource_id] = {'error': str(e)}
        
        return metrics
    
    def _get_ec2_metrics(
        self,
        cloudwatch,
        instance_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List]:
        """Get CPU and network metrics for EC2 instance."""
        cpu = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=Config.METRICS_PERIOD_SECONDS,
            Statistics=['Average', 'Maximum']
        )
        
        return {
            'cpu': sorted(cpu['Datapoints'], key=lambda x: x['Timestamp'])
        }
    
    def _get_rds_metrics(
        self,
        cloudwatch,
        db_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List]:
        """Get CPU and connection metrics for RDS instance."""
        cpu = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=Config.METRICS_PERIOD_SECONDS,
            Statistics=['Average', 'Maximum']
        )
        
        connections = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='DatabaseConnections',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=Config.METRICS_PERIOD_SECONDS,
            Statistics=['Average']
        )
        
        return {
            'cpu': sorted(cpu['Datapoints'], key=lambda x: x['Timestamp']),
            'connections': sorted(connections['Datapoints'], key=lambda x: x['Timestamp'])
        }
    
    def _get_lambda_metrics(
        self,
        cloudwatch,
        function_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List]:
        """Get invocation and duration metrics for Lambda function."""
        invocations = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Invocations',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=Config.METRICS_PERIOD_SECONDS,
            Statistics=['Sum']
        )
        
        return {
            'invocations': sorted(invocations['Datapoints'], key=lambda x: x['Timestamp'])
        }
    
    # ============================================================================
    # COST ANALYSIS
    # ============================================================================
    
    def get_costs(self, days: int = 30) -> Dict[str, Any]:
        """
        Get AWS cost data from Cost Explorer.
        
        Args:
            days: Number of days of cost data to retrieve
        
        Returns:
            Dictionary with total cost and breakdown by service
        """
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
            
            # Calculate total and organize by service
            total_cost = 0.0
            by_service = defaultdict(list)
            
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    total_cost += cost
                    by_service[service].append({'date': date, 'cost': cost})
            
            logger.info(f"Successfully retrieved cost data: ${total_cost:.2f} over {days} days")
            
            return {
                'total': round(total_cost, 2),
                'by_service': dict(by_service),
                'period_days': days
            }
        
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDeniedException':
                logger.warning("No permission to access Cost Explorer. Check IAM permissions.")
                return {'error': 'Access denied to Cost Explorer. Ensure ce:GetCostAndUsage permission is granted.'}
            elif error_code == 'OptInRequired':
                logger.warning("Cost Explorer not enabled. Enable it in AWS Console.")
                return {'error': 'Cost Explorer not enabled. Enable it in AWS Console → Billing → Cost Explorer.'}
            else:
                logger.error(f"AWS error getting costs: {error_code}")
                return {'error': f'AWS error: {error_code}'}
        
        except Exception as e:
            logger.error(f"Unexpected error getting costs: {type(e).__name__} - {e}")
            return {'error': f'Error retrieving cost data: {str(e)}'}
    
    # ============================================================================
    # BOTTLENECK DETECTION
    # ============================================================================
    
    def detect_bottlenecks(self, region: str) -> Dict[str, List[Dict]]:
        """
        Detect resource bottlenecks and optimization opportunities.
        
        Args:
            region: AWS region to scan
        
        Returns:
            Dictionary with lists of bottlenecks by category:
            - high_cpu: Resources with high CPU utilization
            - underutilized: Resources that could be downsized
        """
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        ec2 = self.session.client('ec2', region_name=region)
        
        bottlenecks = {
            'high_cpu': [],
            'underutilized': []
        }
        
        # Get running EC2 instances
        response = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                
                try:
                    # Get CPU metrics
                    cpu_data = cloudwatch.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=3600,
                        Statistics=['Average', 'Maximum']
                    )
                    
                    if not cpu_data['Datapoints']:
                        continue
                    
                    avg_cpu = sum(d['Average'] for d in cpu_data['Datapoints']) / len(cpu_data['Datapoints'])
                    max_cpu = max(d['Maximum'] for d in cpu_data['Datapoints'])
                    
                    # Check for high CPU
                    if max_cpu > Config.CPU_HIGH_THRESHOLD:
                        severity = 'critical' if max_cpu > Config.CPU_CRITICAL_THRESHOLD else 'high'
                        bottlenecks['high_cpu'].append({
                            'resource_id': instance_id,
                            'type': instance['InstanceType'],
                            'avg_cpu': round(avg_cpu, 2),
                            'max_cpu': round(max_cpu, 2),
                            'severity': severity
                        })
                    
                    # Check for underutilization
                    elif avg_cpu < Config.CPU_LOW_THRESHOLD:
                        bottlenecks['underutilized'].append({
                            'resource_id': instance_id,
                            'type': instance['InstanceType'],
                            'avg_cpu': round(avg_cpu, 2),
                            'recommendation': 'Consider downsizing or terminating'
                        })
                
                except Exception as e:
                    logger.error(f"Error checking {instance_id}: {e}")
                    continue
        
        return bottlenecks
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    @staticmethod
    def _extract_tags(tags: List[Dict]) -> Dict[str, str]:
        """Convert AWS tag list to dictionary."""
        return {tag['Key']: tag['Value'] for tag in tags}
