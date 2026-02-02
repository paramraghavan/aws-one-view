"""
Resource Monitor - Core monitoring logic
Handles: EC2, RDS, S3, Lambda, EBS, Kubernetes (EKS), EMR
Uses AWS profile: 'monitor'
Supports optional IAM role assumption for elevated permissions
"""
import boto3
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

AWS_PROFILE = 'monitor'


class ResourceMonitor:
    """Main resource monitoring class"""
    
    def __init__(self, role_arn=None, session_name='AWSMonitorSession'):
        """
        Initialize ResourceMonitor with optional role assumption
        
        Args:
            role_arn: Optional ARN of IAM role to assume
            session_name: Session name for role assumption (default: AWSMonitorSession)
        """
        # Create base session with profile
        base_session = boto3.Session(profile_name=AWS_PROFILE)
        
        # If role ARN provided, assume the role
        if role_arn:
            logger.info(f"Assuming role: {role_arn}")
            try:
                sts = base_session.client('sts')
                response = sts.assume_role(
                    RoleArn=role_arn,
                    RoleSessionName=session_name,
                    DurationSeconds=3600  # 1 hour
                )
                
                credentials = response['Credentials']
                
                # Create new session with assumed role credentials
                self.session = boto3.Session(
                    aws_access_key_id=credentials['AccessKeyId'],
                    aws_secret_access_key=credentials['SecretAccessKey'],
                    aws_session_token=credentials['SessionToken']
                )
                
                logger.info(f"Successfully assumed role: {role_arn}")
                logger.info(f"Session expires at: {credentials['Expiration']}")
                
            except ClientError as e:
                logger.error(f"Failed to assume role {role_arn}: {e}")
                raise Exception(f"Role assumption failed: {e.response['Error']['Message']}")
        else:
            # Use base session with profile
            self.session = base_session
            logger.info(f"Using base profile: {AWS_PROFILE}")
    
    def get_regions(self):
        """Get all available AWS regions"""
        ec2 = self.session.client('ec2', region_name='us-east-1')
        regions = ec2.describe_regions()['Regions']
        return [r['RegionName'] for r in regions]
    
    def discover_all(self, regions, filters=None, resource_types=None):
        """
        Discover resources across regions
        
        Args:
            regions: List of region names
            filters: dict with 'tags', 'names', 'ids'
            resource_types: List of resource types to discover (e.g., ['ec2', 'rds'])
                          If None, discovers all types
        
        Returns:
            dict with all discovered resources
        """
        filters = filters or {}
        resource_types = resource_types or ['ec2', 'rds', 's3', 'lambda', 'ebs', 'eks', 'emr']
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'regions': {}
        }
        
        # Discover S3 once if needed (global service)
        s3_buckets = []
        if 's3' in resource_types:
            s3_buckets = self._discover_s3(filters)
        
        for region in regions:
            logger.info(f"Scanning region: {region} for {', '.join(resource_types)}")
            results['regions'][region] = {}
            
            # Only discover requested resource types
            if 'ec2' in resource_types:
                results['regions'][region]['ec2'] = self._discover_ec2(region, filters)
            
            if 'rds' in resource_types:
                results['regions'][region]['rds'] = self._discover_rds(region, filters)
            
            if 's3' in resource_types:
                # Only include in first region
                results['regions'][region]['s3'] = s3_buckets if region == regions[0] else []
            
            if 'lambda' in resource_types:
                results['regions'][region]['lambda'] = self._discover_lambda(region, filters)
            
            if 'ebs' in resource_types:
                results['regions'][region]['ebs'] = self._discover_ebs(region, filters)
            
            if 'eks' in resource_types:
                results['regions'][region]['eks'] = self._discover_eks(region, filters)
            
            if 'emr' in resource_types:
                results['regions'][region]['emr'] = self._discover_emr(region, filters)
        
        # Add summary
        results['summary'] = self._calculate_summary(results['regions'])
        
        return results
    
    def _discover_ec2(self, region, filters):
        """Discover EC2 instances"""
        try:
            ec2 = self.session.client('ec2', region_name=region)
            
            # Build filters
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
                    
                    # Apply name filter
                    if filters.get('names') and name not in filters['names']:
                        continue
                    
                    instances.append({
                        'id': inst['InstanceId'],
                        'name': name,
                        'type': inst['InstanceType'],
                        'state': inst['State']['Name'],
                        'az': inst['Placement']['AvailabilityZone'],
                        'private_ip': inst.get('PrivateIpAddress'),
                        'public_ip': inst.get('PublicIpAddress'),
                        'launch_time': inst['LaunchTime'].isoformat(),
                        'tags': {t['Key']: t['Value'] for t in inst.get('Tags', [])}
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
                
                # Apply filters
                if filters.get('names') and name not in filters['names']:
                    continue
                if filters.get('ids') and db['DbiResourceId'] not in filters['ids']:
                    continue
                
                # Get tags
                arn = db['DBInstanceArn']
                try:
                    tag_response = rds.list_tags_for_resource(ResourceName=arn)
                    tags = {t['Key']: t['Value'] for t in tag_response['TagList']}
                    
                    # Check tag filter
                    if filters.get('tags'):
                        matches = all(tags.get(k) == v for k, v in filters['tags'].items())
                        if not matches:
                            continue
                except:
                    tags = {}
                
                instances.append({
                    'id': db['DbiResourceId'],
                    'name': name,
                    'engine': db['Engine'],
                    'version': db['EngineVersion'],
                    'class': db['DBInstanceClass'],
                    'status': db['DBInstanceStatus'],
                    'az': db['AvailabilityZone'],
                    'multi_az': db['MultiAZ'],
                    'storage': db['AllocatedStorage'],
                    'endpoint': db['Endpoint']['Address'] if db.get('Endpoint') else None,
                    'tags': tags
                })
            
            return instances
        except Exception as e:
            logger.error(f"RDS discovery error in {region}: {e}")
            return []
    
    def _discover_s3(self, filters):
        """Discover S3 buckets (global service)"""
        try:
            s3 = self.session.client('s3')
            response = s3.list_buckets()
            
            buckets = []
            for bucket in response['Buckets']:
                name = bucket['Name']
                
                # Apply name filter
                if filters.get('names') and name not in filters['names']:
                    continue
                
                # Get tags
                try:
                    tag_response = s3.get_bucket_tagging(Bucket=name)
                    tags = {t['Key']: t['Value'] for t in tag_response['TagSet']}
                    
                    # Check tag filter
                    if filters.get('tags'):
                        matches = all(tags.get(k) == v for k, v in filters['tags'].items())
                        if not matches:
                            continue
                except ClientError:
                    tags = {}
                
                # Get region
                try:
                    location = s3.get_bucket_location(Bucket=name)
                    region = location['LocationConstraint'] or 'us-east-1'
                except:
                    region = 'unknown'
                
                buckets.append({
                    'name': name,
                    'creation_date': bucket['CreationDate'].isoformat(),
                    'region': region,
                    'status': 'Active',  # S3 buckets are always active if they exist
                    'tags': tags
                })
            
            return buckets
        except Exception as e:
            logger.error(f"S3 discovery error: {e}")
            return []
    
    def _discover_lambda(self, region, filters):
        """Discover Lambda functions"""
        try:
            lambda_client = self.session.client('lambda', region_name=region)
            response = lambda_client.list_functions()
            
            functions = []
            for func in response['Functions']:
                name = func['FunctionName']
                
                # Apply name filter
                if filters.get('names') and name not in filters['names']:
                    continue
                
                # Get tags
                try:
                    tag_response = lambda_client.list_tags(Resource=func['FunctionArn'])
                    tags = tag_response['Tags']
                    
                    # Check tag filter
                    if filters.get('tags'):
                        matches = all(tags.get(k) == v for k, v in filters['tags'].items())
                        if not matches:
                            continue
                except:
                    tags = {}
                
                functions.append({
                    'name': name,
                    'arn': func['FunctionArn'],
                    'runtime': func['Runtime'],
                    'memory': func['MemorySize'],
                    'timeout': func['Timeout'],
                    'last_modified': func['LastModified'],
                    'status': 'Active',  # Lambda functions are always active if they exist
                    'tags': tags
                })
            
            return functions
        except Exception as e:
            logger.error(f"Lambda discovery error in {region}: {e}")
            return []
    
    def _discover_ebs(self, region, filters):
        """Discover EBS volumes"""
        try:
            ec2 = self.session.client('ec2', region_name=region)
            
            api_filters = []
            if filters.get('tags'):
                for k, v in filters['tags'].items():
                    api_filters.append({'Name': f'tag:{k}', 'Values': [v]})
            if filters.get('ids'):
                api_filters.append({'Name': 'volume-id', 'Values': filters['ids']})
            
            response = ec2.describe_volumes(Filters=api_filters)
            
            volumes = []
            for vol in response['Volumes']:
                name = self._get_tag(vol.get('Tags', []), 'Name')
                
                # Apply name filter
                if filters.get('names') and name not in filters['names']:
                    continue
                
                volumes.append({
                    'id': vol['VolumeId'],
                    'name': name,
                    'size': vol['Size'],
                    'type': vol['VolumeType'],
                    'state': vol['State'],
                    'az': vol['AvailabilityZone'],
                    'encrypted': vol['Encrypted'],
                    'attached_to': vol['Attachments'][0]['InstanceId'] if vol['Attachments'] else None,
                    'tags': {t['Key']: t['Value'] for t in vol.get('Tags', [])}
                })
            
            return volumes
        except Exception as e:
            logger.error(f"EBS discovery error in {region}: {e}")
            return []
    
    def _discover_eks(self, region, filters):
        """Discover EKS clusters (Kubernetes)"""
        try:
            eks = self.session.client('eks', region_name=region)
            response = eks.list_clusters()
            
            clusters = []
            for cluster_name in response['clusters']:
                # Apply name filter
                if filters.get('names') and cluster_name not in filters['names']:
                    continue
                
                # Get cluster details
                cluster = eks.describe_cluster(name=cluster_name)['cluster']
                
                # Get tags
                tags = cluster.get('tags', {})
                
                # Check tag filter
                if filters.get('tags'):
                    matches = all(tags.get(k) == v for k, v in filters['tags'].items())
                    if not matches:
                        continue
                
                # Get node groups
                node_groups = []
                try:
                    ng_response = eks.list_nodegroups(clusterName=cluster_name)
                    for ng_name in ng_response['nodegroups']:
                        ng = eks.describe_nodegroup(
                            clusterName=cluster_name,
                            nodegroupName=ng_name
                        )['nodegroup']
                        node_groups.append({
                            'name': ng_name,
                            'status': ng['status'],
                            'instance_types': ng.get('instanceTypes', []),
                            'desired_size': ng['scalingConfig']['desiredSize'],
                            'min_size': ng['scalingConfig']['minSize'],
                            'max_size': ng['scalingConfig']['maxSize']
                        })
                except:
                    pass
                
                clusters.append({
                    'name': cluster_name,
                    'arn': cluster['arn'],
                    'version': cluster['version'],
                    'status': cluster['status'],
                    'endpoint': cluster['endpoint'],
                    'created': cluster['createdAt'].isoformat(),
                    'node_groups': node_groups,
                    'tags': tags
                })
            
            return clusters
        except Exception as e:
            logger.error(f"EKS discovery error in {region}: {e}")
            return []
    
    def _discover_emr(self, region, filters):
        """Discover EMR clusters"""
        try:
            emr = self.session.client('emr', region_name=region)
            response = emr.list_clusters(
                ClusterStates=['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING']
            )
            
            clusters = []
            for cluster_summary in response['Clusters']:
                cluster_id = cluster_summary['Id']
                name = cluster_summary['Name']
                
                # Apply filters
                if filters.get('names') and name not in filters['names']:
                    continue
                if filters.get('ids') and cluster_id not in filters['ids']:
                    continue
                
                # Get detailed info
                cluster = emr.describe_cluster(ClusterId=cluster_id)['Cluster']
                
                # Get tags
                tags = {t['Key']: t['Value'] for t in cluster.get('Tags', [])}
                
                # Check tag filter
                if filters.get('tags'):
                    matches = all(tags.get(k) == v for k, v in filters['tags'].items())
                    if not matches:
                        continue
                
                clusters.append({
                    'id': cluster_id,
                    'name': name,
                    'status': cluster['Status']['State'],
                    'release_label': cluster.get('ReleaseLabel'),
                    'master_instance_type': cluster.get('MasterPublicDnsName'),
                    'instance_count': cluster.get('NormalizedInstanceHours', 0),
                    'created': cluster['Status']['Timeline']['CreationDateTime'].isoformat(),
                    'tags': tags
                })
            
            return clusters
        except Exception as e:
            logger.error(f"EMR discovery error in {region}: {e}")
            return []
    
    def _get_tag(self, tags, key):
        """Extract tag value from AWS tags list"""
        for tag in tags:
            if tag['Key'] == key:
                return tag['Value']
        return ''
    
    def _calculate_summary(self, regions_data):
        """Calculate resource summary"""
        summary = {}
        for region, resources in regions_data.items():
            for resource_type, items in resources.items():
                if resource_type == 's3':  # S3 is global, count once
                    if 's3' not in summary:
                        summary['s3'] = len(items)
                else:
                    summary[resource_type] = summary.get(resource_type, 0) + len(items)
        return summary
    
    def get_metrics(self, resources, period=300):
        """
        Get CloudWatch metrics for resources
        
        Args:
            resources: List of dicts with 'type', 'id', 'region'
            period: Metric period in seconds (default 300 = 5 min)
        
        Returns:
            dict with metrics for each resource
        """
        results = {}
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=1)
        
        for resource in resources:
            resource_type = resource['type']
            resource_id = resource['id']
            region = resource['region']
            
            try:
                cloudwatch = self.session.client('cloudwatch', region_name=region)
                
                if resource_type == 'ec2':
                    metrics = self._get_ec2_metrics(cloudwatch, resource_id, start_time, end_time, period)
                elif resource_type == 'rds':
                    metrics = self._get_rds_metrics(cloudwatch, resource_id, start_time, end_time, period)
                elif resource_type == 'lambda':
                    metrics = self._get_lambda_metrics(cloudwatch, resource_id, start_time, end_time, period)
                elif resource_type == 'eks':
                    metrics = self._get_eks_metrics(cloudwatch, resource_id, start_time, end_time, period)
                elif resource_type == 'emr':
                    metrics = self._get_emr_metrics(cloudwatch, resource_id, start_time, end_time, period)
                elif resource_type == 's3':
                    metrics = self._get_s3_metrics(cloudwatch, resource_id, start_time, end_time, period)
                elif resource_type == 'ebs':
                    metrics = self._get_ebs_metrics(cloudwatch, resource_id, start_time, end_time, period)
                else:
                    metrics = {
                        '_note': f'{resource_type.upper()} metrics not yet implemented',
                        '_help': 'Metrics collection for this resource type is coming soon'
                    }
                
                results[f"{resource_type}:{resource_id}"] = metrics
                
            except Exception as e:
                logger.error(f"Metrics error for {resource_type}:{resource_id}: {e}")
                results[f"{resource_type}:{resource_id}"] = {'error': str(e)}
        
        return results
    
    def _get_ec2_metrics(self, cloudwatch, instance_id, start_time, end_time, period):
        """Get EC2 metrics from CloudWatch"""
        metrics = {}
        
        # Standard EC2 metrics (always available)
        standard_metrics = ['CPUUtilization', 'NetworkIn', 'NetworkOut', 'DiskReadBytes', 'DiskWriteBytes']
        
        for metric_name in standard_metrics:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName=metric_name,
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=['Average', 'Maximum']
                )
                
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                if datapoints:
                    metrics[metric_name.lower()] = {
                        'current': datapoints[-1]['Average'],
                        'max': max(d['Maximum'] for d in datapoints),
                        'avg': sum(d['Average'] for d in datapoints) / len(datapoints)
                    }
            except Exception as e:
                logger.warning(f"Could not get {metric_name} for {instance_id}: {e}")
        
        # Try to get memory metrics from CloudWatch agent (if installed)
        # These are in the CWAgent namespace
        try:
            memory_response = cloudwatch.get_metric_statistics(
                Namespace='CWAgent',
                MetricName='mem_used_percent',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average', 'Maximum']
            )
            
            datapoints = sorted(memory_response['Datapoints'], key=lambda x: x['Timestamp'])
            if datapoints:
                metrics['memory_utilization'] = {
                    'current': datapoints[-1]['Average'],
                    'max': max(d['Maximum'] for d in datapoints),
                    'avg': sum(d['Average'] for d in datapoints) / len(datapoints),
                    'note': 'Requires CloudWatch agent'
                }
        except Exception:
            # CloudWatch agent not installed - this is normal
            pass
        
        return metrics
    
    def _get_rds_metrics(self, cloudwatch, db_id, start_time, end_time, period):
        """Get RDS metrics from CloudWatch"""
        metrics = {}
        
        for metric_name in ['CPUUtilization', 'DatabaseConnections', 'FreeStorageSpace', 'ReadLatency', 'WriteLatency']:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/RDS',
                MetricName=metric_name,
                Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Average', 'Maximum']
            )
            
            datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
            if datapoints:
                metrics[metric_name.lower()] = {
                    'current': datapoints[-1]['Average'],
                    'max': max(d['Maximum'] for d in datapoints),
                    'avg': sum(d['Average'] for d in datapoints) / len(datapoints)
                }
        
        return metrics
    
    def _get_lambda_metrics(self, cloudwatch, function_name, start_time, end_time, period):
        """Get Lambda metrics from CloudWatch"""
        metrics = {}
        has_any_data = False
        
        for metric_name in ['Invocations', 'Errors', 'Duration', 'Throttles']:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/Lambda',
                    MetricName=metric_name,
                    Dimensions=[{'Name': 'FunctionName', 'Value': function_name}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=['Sum'] if metric_name in ['Invocations', 'Errors', 'Throttles'] else ['Average', 'Maximum']
                )
                
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                if datapoints:
                    has_any_data = True
                    stat_key = 'Sum' if metric_name in ['Invocations', 'Errors', 'Throttles'] else 'Average'
                    
                    if metric_name in ['Invocations', 'Errors', 'Throttles']:
                        # For count metrics
                        metrics[metric_name.lower()] = {
                            'current': datapoints[-1][stat_key],
                            'total': sum(d[stat_key] for d in datapoints),
                            'max': max(d[stat_key] for d in datapoints),
                            'avg': sum(d[stat_key] for d in datapoints) / len(datapoints)
                        }
                    else:
                        # For duration
                        metrics[metric_name.lower()] = {
                            'current': datapoints[-1]['Average'],
                            'avg': sum(d['Average'] for d in datapoints) / len(datapoints),
                            'max': max(d['Maximum'] for d in datapoints),
                            'min': min(d.get('Average', 0) for d in datapoints)
                        }
            except Exception as e:
                logger.warning(f"Could not get {metric_name} for Lambda {function_name}: {e}")
        
        # If no metrics data at all, provide explanation
        if not has_any_data:
            metrics['_note'] = 'No recent invocations - Lambda metrics only appear when function is called'
            metrics['_help'] = 'Try invoking the function or selecting a longer time period'
        
        return metrics
    
    def _get_eks_metrics(self, cloudwatch, cluster_name, start_time, end_time, period):
        """Get EKS metrics from CloudWatch"""
        # EKS metrics are collected via Container Insights
        # This is a placeholder - actual implementation would query container metrics
        return {
            '_note': 'EKS metrics require Container Insights',
            '_help': 'Enable Container Insights on your EKS cluster to see metrics'
        }
    
    def _get_s3_metrics(self, cloudwatch, bucket_name, start_time, end_time, period):
        """Get S3 metrics from CloudWatch"""
        metrics = {}
        has_any_data = False
        
        # Note: S3 storage metrics are only updated once per day
        # Request metrics require CloudWatch request metrics to be enabled
        
        # Try to get storage metrics (available by default, updated daily)
        storage_metrics = ['BucketSizeBytes', 'NumberOfObjects']
        for metric_name in storage_metrics:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName=metric_name,
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': bucket_name},
                        {'Name': 'StorageType', 'Value': 'StandardStorage'}
                    ],
                    StartTime=start_time - timedelta(days=2),  # Look back 2 days for daily metrics
                    EndTime=end_time,
                    Period=86400,  # 1 day period
                    Statistics=['Average']
                )
                
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                if datapoints:
                    has_any_data = True
                    value = datapoints[-1]['Average']
                    
                    # Format based on metric type
                    if metric_name == 'BucketSizeBytes':
                        # Convert to GB for readability
                        value_gb = value / (1024**3)
                        metrics['bucket_size'] = {
                            'current': value_gb,
                            'unit': 'GB',
                            'raw_bytes': value
                        }
                    else:
                        metrics['object_count'] = {
                            'current': int(value),
                            'unit': 'objects'
                        }
            except Exception as e:
                logger.warning(f"Could not get {metric_name} for S3 bucket {bucket_name}: {e}")
        
        # Try to get request metrics (require CloudWatch request metrics enabled)
        try:
            response = cloudwatch.get_metric_statistics(
                Namespace='AWS/S3',
                MetricName='AllRequests',
                Dimensions=[
                    {'Name': 'BucketName', 'Value': bucket_name}
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=['Sum']
            )
            
            datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
            if datapoints:
                has_any_data = True
                total_requests = sum(d['Sum'] for d in datapoints)
                metrics['requests'] = {
                    'total': int(total_requests),
                    'current': int(datapoints[-1]['Sum'])
                }
        except Exception:
            # Request metrics not enabled - this is normal
            pass
        
        # If no data at all, provide helpful message
        if not has_any_data:
            metrics['_note'] = 'S3 storage metrics update once per day'
            metrics['_help'] = 'Storage metrics may take 24 hours to appear. Request metrics require enabling CloudWatch request metrics on the bucket.'
        
        return metrics
    
    def _get_ebs_metrics(self, cloudwatch, volume_id, start_time, end_time, period):
        """Get EBS volume metrics from CloudWatch"""
        metrics = {}
        has_any_data = False
        
        metric_configs = {
            'VolumeReadBytes': ('read_bytes', 'Bytes', 'Average'),
            'VolumeWriteBytes': ('write_bytes', 'Bytes', 'Average'),
            'VolumeReadOps': ('read_ops', 'Count', 'Average'),
            'VolumeWriteOps': ('write_ops', 'Count', 'Average'),
            'VolumeIdleTime': ('idle_time', 'Seconds', 'Average')
        }
        
        for metric_name, (display_name, unit, stat) in metric_configs.items():
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EBS',
                    MetricName=metric_name,
                    Dimensions=[{'Name': 'VolumeId', 'Value': volume_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=[stat, 'Maximum']
                )
                
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                if datapoints:
                    has_any_data = True
                    
                    # Convert bytes to MB for readability
                    if 'Bytes' in metric_name:
                        current_mb = datapoints[-1][stat] / (1024**2)
                        avg_mb = sum(d[stat] for d in datapoints) / len(datapoints) / (1024**2)
                        max_mb = max(d['Maximum'] for d in datapoints) / (1024**2)
                        
                        metrics[display_name] = {
                            'current': current_mb,
                            'avg': avg_mb,
                            'max': max_mb,
                            'unit': 'MB'
                        }
                    else:
                        metrics[display_name] = {
                            'current': datapoints[-1][stat],
                            'avg': sum(d[stat] for d in datapoints) / len(datapoints),
                            'max': max(d['Maximum'] for d in datapoints),
                            'unit': unit
                        }
            except Exception as e:
                logger.warning(f"Could not get {metric_name} for EBS volume {volume_id}: {e}")
        
        # If no data at all, provide explanation
        if not has_any_data:
            metrics['_note'] = 'No EBS metrics available'
            metrics['_help'] = 'EBS metrics require the volume to be attached and in use'
        
        return metrics
    
    def _get_emr_metrics(self, cloudwatch, cluster_id, start_time, end_time, period):
        """Get EMR metrics from CloudWatch"""
        metrics = {}
        has_any_data = False
        
        for metric_name in ['IsIdle', 'ContainerPending', 'AppsRunning']:
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/ElasticMapReduce',
                    MetricName=metric_name,
                    Dimensions=[{'Name': 'JobFlowId', 'Value': cluster_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=period,
                    Statistics=['Average']
                )
                
                datapoints = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
                if datapoints:
                    has_any_data = True
                    metrics[metric_name.lower()] = {
                        'current': datapoints[-1]['Average'],
                        'avg': sum(d['Average'] for d in datapoints) / len(datapoints)
                    }
            except Exception as e:
                logger.warning(f"Could not get {metric_name} for EMR cluster {cluster_id}: {e}")
        
        # If no data, provide explanation
        if not has_any_data:
            metrics['_note'] = 'No EMR metrics available for this time period'
            metrics['_help'] = 'EMR metrics may not be available if cluster is terminated or not running jobs'
        
        return metrics
    
    def analyze_costs(self, regions, days=7):
        """
        Analyze costs using Cost Explorer
        
        Args:
            regions: List of regions
            days: Number of days to analyze
        
        Returns:
            dict with cost analysis
        """
        try:
            ce = self.session.client('ce', region_name='us-east-1')
            
            end_date = datetime.utcnow().date()
            start_date = end_date - timedelta(days=days)
            
            # Get total costs
            response = ce.get_cost_and_usage(
                TimePeriod={
                    'Start': start_date.isoformat(),
                    'End': end_date.isoformat()
                },
                Granularity='DAILY',
                Metrics=['UnblendedCost'],
                GroupBy=[
                    {'Type': 'DIMENSION', 'Key': 'SERVICE'},
                    {'Type': 'DIMENSION', 'Key': 'REGION'}
                ]
            )
            
            # Process results
            costs_by_service = {}
            costs_by_region = {}
            daily_costs = []
            
            for result in response['ResultsByTime']:
                date = result['TimePeriod']['Start']
                day_total = 0
                
                for group in result['Groups']:
                    service = group['Keys'][0]
                    region = group['Keys'][1]
                    amount = float(group['Metrics']['UnblendedCost']['Amount'])
                    
                    costs_by_service[service] = costs_by_service.get(service, 0) + amount
                    costs_by_region[region] = costs_by_region.get(region, 0) + amount
                    day_total += amount
                
                daily_costs.append({'date': date, 'cost': day_total})
            
            total_cost = sum(d['cost'] for d in daily_costs)
            
            return {
                'period': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
                'total_cost': round(total_cost, 2),
                'daily_average': round(total_cost / days, 2),
                'by_service': {k: round(v, 2) for k, v in sorted(costs_by_service.items(), key=lambda x: x[1], reverse=True)[:10]},
                'by_region': {k: round(v, 2) for k, v in sorted(costs_by_region.items(), key=lambda x: x[1], reverse=True)},
                'daily_costs': daily_costs
            }
            
        except Exception as e:
            logger.error(f"Cost analysis error: {e}")
            return {'error': str(e)}
    
    def check_alerts(self, resources, thresholds):
        """
        Check resources against thresholds and detect issues
        
        Args:
            resources: List of resources with metrics
            thresholds: dict like {'cpu': 80, 'memory': 85, 'disk': 90}
        
        Returns:
            dict with alerts and issues
        """
        alerts = {
            'critical': [],
            'warning': [],
            'info': []
        }
        
        # Get metrics for resources
        metrics = self.get_metrics(resources, period=300)
        
        for resource_key, resource_metrics in metrics.items():
            resource_type, resource_id = resource_key.split(':', 1)
            
            # Check CPU
            if 'cpuutilization' in resource_metrics:
                cpu = resource_metrics['cpuutilization']['current']
                threshold = thresholds.get('cpu', 80)
                
                if cpu > threshold:
                    alerts['critical'].append({
                        'resource': resource_id,
                        'type': resource_type,
                        'metric': 'CPU',
                        'current': cpu,
                        'threshold': threshold,
                        'message': f"CPU utilization {cpu:.1f}% exceeds threshold {threshold}%"
                    })
                elif cpu > threshold * 0.8:
                    alerts['warning'].append({
                        'resource': resource_id,
                        'type': resource_type,
                        'metric': 'CPU',
                        'current': cpu,
                        'message': f"CPU utilization {cpu:.1f}% approaching threshold"
                    })
            
            # Check Lambda errors
            if resource_type == 'lambda' and 'errors' in resource_metrics:
                errors = resource_metrics['errors']['current']
                if errors > 0:
                    alerts['warning'].append({
                        'resource': resource_id,
                        'type': resource_type,
                        'metric': 'Errors',
                        'current': errors,
                        'message': f"Lambda function has {errors} errors"
                    })
            
            # Check RDS connections
            if resource_type == 'rds' and 'databaseconnections' in resource_metrics:
                connections = resource_metrics['databaseconnections']['current']
                max_connections = thresholds.get('max_db_connections', 100)
                
                if connections > max_connections * 0.9:
                    alerts['critical'].append({
                        'resource': resource_id,
                        'type': resource_type,
                        'metric': 'Connections',
                        'current': connections,
                        'threshold': max_connections,
                        'message': f"Database connections {connections} near limit"
                    })
        
        return alerts
