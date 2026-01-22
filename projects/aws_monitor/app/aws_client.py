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
            by_service = defaultdict(lambda: {'daily': [], 'total': 0.0})
            
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                for group in result['Groups']:
                    service = group['Keys'][0]
                    cost = float(group['Metrics']['UnblendedCost']['Amount'])
                    total_cost += cost
                    
                    # Store daily cost
                    by_service[service]['daily'].append({'date': date, 'cost': cost})
                    # Accumulate total
                    by_service[service]['total'] += cost
            
            # Convert to regular dict and sort by total cost
            services_dict = {}
            for service, data in by_service.items():
                services_dict[service] = {
                    'total': round(data['total'], 2),
                    'daily': data['daily'],
                    'percentage': round((data['total'] / total_cost * 100) if total_cost > 0 else 0, 2)
                }
            
            # Sort by total cost (highest first)
            sorted_services = dict(sorted(services_dict.items(), key=lambda x: x[1]['total'], reverse=True))
            
            logger.info(f"Successfully retrieved cost data: ${total_cost:.2f} over {days} days")
            logger.info(f"Cost breakdown: {len(sorted_services)} services")
            
            # Log services with costs (even small ones)
            for service, data in sorted_services.items():
                if data['total'] > 0:
                    logger.info(f"  {service}: ${data['total']:.2f} ({data['percentage']}%)")
            
            return {
                'total': round(total_cost, 2),
                'by_service': sorted_services,
                'period_days': days,
                'service_count': len(sorted_services)
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
    # RESOURCE DETAILS
    # ============================================================================
    
    def get_resource_details(self, resource_id: str, resource_type: str, region: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific resource.
        
        Args:
            resource_id: Resource identifier
            resource_type: Type of resource (ec2, rds, lambda, etc.)
            region: AWS region
        
        Returns:
            Dictionary with detailed resource information
        """
        try:
            if resource_type == 'ec2':
                return self._get_ec2_details(resource_id, region)
            elif resource_type == 'rds':
                return self._get_rds_details(resource_id, region)
            elif resource_type == 'lambda':
                return self._get_lambda_details(resource_id, region)
            elif resource_type == 's3':
                return self._get_s3_details(resource_id)
            elif resource_type == 'ebs':
                return self._get_ebs_details(resource_id, region)
            else:
                return {'error': f'Unsupported resource type: {resource_type}'}
        except Exception as e:
            logger.error(f"Error getting details for {resource_id}: {e}")
            return {'error': str(e)}
    
    def _get_ec2_details(self, instance_id: str, region: str) -> Dict[str, Any]:
        """Get detailed EC2 instance information."""
        ec2 = self.session.client('ec2', region_name=region)
        
        # Get instance details
        response = ec2.describe_instances(InstanceIds=[instance_id])
        instance = response['Reservations'][0]['Instances'][0]
        
        # Get recent CPU metrics (last 6 hours)
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=6)
        
        cpu_data = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=900,  # 15 minutes
            Statistics=['Average', 'Maximum']
        )
        
        # Calculate current CPU
        current_cpu = None
        if cpu_data['Datapoints']:
            sorted_points = sorted(cpu_data['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
            current_cpu = sorted_points[0]['Average']
        
        return {
            'id': instance_id,
            'type': instance['InstanceType'],
            'state': instance['State']['Name'],
            'az': instance['Placement']['AvailabilityZone'],
            'launch_time': instance['LaunchTime'].isoformat(),
            'private_ip': instance.get('PrivateIpAddress', 'N/A'),
            'public_ip': instance.get('PublicIpAddress', 'N/A'),
            'vpc_id': instance.get('VpcId', 'N/A'),
            'subnet_id': instance.get('SubnetId', 'N/A'),
            'security_groups': [sg['GroupName'] for sg in instance.get('SecurityGroups', [])],
            'tags': self._extract_tags(instance.get('Tags', [])),
            'monitoring': instance['Monitoring']['State'],
            'current_cpu': round(current_cpu, 2) if current_cpu else 'N/A',
            'platform': instance.get('Platform', 'Linux'),
            'architecture': instance.get('Architecture', 'x86_64')
        }
    
    def _get_rds_details(self, db_id: str, region: str) -> Dict[str, Any]:
        """Get detailed RDS instance information."""
        rds = self.session.client('rds', region_name=region)
        
        response = rds.describe_db_instances(DBInstanceIdentifier=db_id)
        db = response['DBInstances'][0]
        
        # Get recent CPU metrics
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=6)
        
        cpu_data = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=900,
            Statistics=['Average']
        )
        
        current_cpu = None
        if cpu_data['Datapoints']:
            sorted_points = sorted(cpu_data['Datapoints'], key=lambda x: x['Timestamp'], reverse=True)
            current_cpu = sorted_points[0]['Average']
        
        return {
            'id': db_id,
            'class': db['DBInstanceClass'],
            'engine': db['Engine'],
            'engine_version': db['EngineVersion'],
            'status': db['DBInstanceStatus'],
            'az': db.get('AvailabilityZone', 'N/A'),
            'multi_az': db['MultiAZ'],
            'storage_gb': db['AllocatedStorage'],
            'storage_type': db['StorageType'],
            'iops': db.get('Iops', 'N/A'),
            'endpoint': db['Endpoint']['Address'] if 'Endpoint' in db else 'N/A',
            'port': db['Endpoint']['Port'] if 'Endpoint' in db else 'N/A',
            'vpc_id': db.get('DBSubnetGroup', {}).get('VpcId', 'N/A'),
            'backup_retention': db['BackupRetentionPeriod'],
            'current_cpu': round(current_cpu, 2) if current_cpu else 'N/A',
            'publicly_accessible': db['PubliclyAccessible']
        }
    
    def _get_lambda_details(self, function_name: str, region: str) -> Dict[str, Any]:
        """Get detailed Lambda function information."""
        lambda_client = self.session.client('lambda', region_name=region)
        
        response = lambda_client.get_function(FunctionName=function_name)
        config = response['Configuration']
        
        # Get recent invocation count
        cloudwatch = self.session.client('cloudwatch', region_name=region)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=24)
        
        invocations = cloudwatch.get_metric_statistics(
            Namespace='AWS/Lambda',
            MetricName='Invocations',
            Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # 1 day
            Statistics=['Sum']
        )
        
        total_invocations = 0
        if invocations['Datapoints']:
            total_invocations = invocations['Datapoints'][0]['Sum']
        
        return {
            'id': function_name,
            'runtime': config['Runtime'],
            'handler': config['Handler'],
            'memory_mb': config['MemorySize'],
            'timeout_sec': config['Timeout'],
            'code_size_bytes': config['CodeSize'],
            'last_modified': config['LastModified'],
            'role': config['Role'].split('/')[-1],
            'vpc_id': config.get('VpcConfig', {}).get('VpcId', 'N/A'),
            'environment': list(config.get('Environment', {}).get('Variables', {}).keys()),
            'invocations_24h': int(total_invocations),
            'layers': len(config.get('Layers', []))
        }
    
    def _get_s3_details(self, bucket_name: str) -> Dict[str, Any]:
        """Get detailed S3 bucket information."""
        s3 = self.session.client('s3')
        
        # Get bucket location
        try:
            location = s3.get_bucket_location(Bucket=bucket_name)
            region = location['LocationConstraint'] or 'us-east-1'
        except:
            region = 'unknown'
        
        # Get bucket size (this requires CloudWatch metrics or S3 API calls)
        # For now, we'll return basic info
        try:
            versioning = s3.get_bucket_versioning(Bucket=bucket_name)
            versioning_status = versioning.get('Status', 'Disabled')
        except:
            versioning_status = 'Unknown'
        
        try:
            encryption = s3.get_bucket_encryption(Bucket=bucket_name)
            encrypted = True
        except:
            encrypted = False
        
        return {
            'id': bucket_name,
            'region': region,
            'versioning': versioning_status,
            'encrypted': encrypted,
            'public_access': 'Check AWS Console'  # Requires additional API calls
        }
    
    def _get_ebs_details(self, volume_id: str, region: str) -> Dict[str, Any]:
        """Get detailed EBS volume information."""
        ec2 = self.session.client('ec2', region_name=region)
        
        response = ec2.describe_volumes(VolumeIds=[volume_id])
        volume = response['Volumes'][0]
        
        attachment = volume['Attachments'][0] if volume['Attachments'] else None
        
        return {
            'id': volume_id,
            'size_gb': volume['Size'],
            'type': volume['VolumeType'],
            'iops': volume.get('Iops', 'N/A'),
            'throughput': volume.get('Throughput', 'N/A'),
            'state': volume['State'],
            'az': volume['AvailabilityZone'],
            'encrypted': volume['Encrypted'],
            'created': volume['CreateTime'].isoformat(),
            'attached_to': attachment['InstanceId'] if attachment else 'Not attached',
            'device': attachment['Device'] if attachment else 'N/A',
            'snapshot_id': volume.get('SnapshotId', 'N/A')
        }
    
    # ============================================================================
    # UTILITY METHODS
    # ============================================================================
    
    @staticmethod
    def _extract_tags(tags: List[Dict]) -> Dict[str, str]:
        """Convert AWS tag list to dictionary."""
        return {tag['Key']: tag['Value'] for tag in tags}
