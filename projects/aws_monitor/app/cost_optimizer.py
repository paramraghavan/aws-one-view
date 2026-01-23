"""
Cost Optimization Engine - Automatically find cost savings opportunities.
Analyzes resources and recommends ways to reduce spending.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging
from collections import defaultdict

from app.aws_client import AWSClient
from app.config import Config

logger = logging.getLogger(__name__)


class CostOptimizer:
    """
    Analyze AWS resources and identify cost savings opportunities.
    """
    
    def __init__(self):
        """Initialize the cost optimizer."""
        self.aws_client = AWSClient()
        
        # Pricing estimates (on-demand, us-east-1)
        self.ec2_pricing = {
            't2.nano': 0.0058, 't2.micro': 0.0116, 't2.small': 0.023,
            't2.medium': 0.0464, 't2.large': 0.0928, 't2.xlarge': 0.1856,
            't3.nano': 0.0052, 't3.micro': 0.0104, 't3.small': 0.0208,
            't3.medium': 0.0416, 't3.large': 0.0832, 't3.xlarge': 0.1664,
            'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
            'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
        }
        
        self.rds_pricing = {
            'db.t3.micro': 0.017, 'db.t3.small': 0.034, 'db.t3.medium': 0.068,
            'db.t3.large': 0.136, 'db.m5.large': 0.192, 'db.m5.xlarge': 0.384,
        }
    
    def analyze_all(self, regions: List[str]) -> Dict[str, Any]:
        """
        Run all optimization checks and return recommendations.
        
        Args:
            regions: List of AWS regions to analyze
        
        Returns:
            Dictionary with recommendations and potential savings
        """
        logger.info("Starting cost optimization analysis")
        
        recommendations = {
            'idle_instances': [],
            'underutilized_instances': [],
            'unattached_volumes': [],
            'old_snapshots': [],
            'right_sizing': [],
            'reserved_instance_opportunities': [],
            'total_monthly_savings': 0.0,
            'quick_wins': [],
            'analyzed_at': datetime.utcnow().isoformat()
        }
        
        for region in regions:
            try:
                logger.info(f"Analyzing resources in {region}")
                
                # Check for idle instances
                idle = self._find_idle_instances(region)
                recommendations['idle_instances'].extend(idle)
                
                # Check for underutilized instances
                underutilized = self._find_underutilized_instances(region)
                recommendations['underutilized_instances'].extend(underutilized)
                
                # Check for unattached volumes
                unattached = self._find_unattached_volumes(region)
                recommendations['unattached_volumes'].extend(unattached)
                
                # Check for old snapshots
                old_snapshots = self._find_old_snapshots(region)
                recommendations['old_snapshots'].extend(old_snapshots)
                
                # Right-sizing opportunities
                right_size = self._find_right_sizing_opportunities(region)
                recommendations['right_sizing'].extend(right_size)
                
                # Reserved instance opportunities
                ri_opps = self._find_reserved_instance_opportunities(region)
                recommendations['reserved_instance_opportunities'].extend(ri_opps)
                
            except Exception as e:
                logger.error(f"Error analyzing {region}: {e}")
        
        # Calculate total savings
        total_savings = 0.0
        for category in ['idle_instances', 'underutilized_instances', 'unattached_volumes', 
                        'old_snapshots', 'right_sizing', 'reserved_instance_opportunities']:
            for item in recommendations[category]:
                total_savings += item.get('monthly_savings', 0)
        
        recommendations['total_monthly_savings'] = round(total_savings, 2)
        
        # Identify quick wins (easy to implement, high value)
        quick_wins = []
        quick_wins.extend([r for r in recommendations['idle_instances'] if r['monthly_savings'] > 10])
        quick_wins.extend([r for r in recommendations['unattached_volumes'] if r['monthly_savings'] > 5])
        quick_wins.extend([r for r in recommendations['old_snapshots'][:5]])  # Top 5 oldest
        
        recommendations['quick_wins'] = sorted(quick_wins, key=lambda x: x['monthly_savings'], reverse=True)[:10]
        
        logger.info(f"Analysis complete. Total potential savings: ${total_savings:.2f}/month")
        
        return recommendations
    
    def _find_idle_instances(self, region: str) -> List[Dict[str, Any]]:
        """Find EC2 instances with very low CPU usage (< 5% avg for 7 days)."""
        idle_instances = []
        
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            cloudwatch = self.aws_client.session.client('cloudwatch', region_name=region)
            
            # Get running instances
            response = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    
                    try:
                        # Get CPU metrics for last 7 days
                        cpu_data = cloudwatch.get_metric_statistics(
                            Namespace='AWS/EC2',
                            MetricName='CPUUtilization',
                            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=86400,  # Daily
                            Statistics=['Average']
                        )
                        
                        if cpu_data['Datapoints']:
                            avg_cpu = sum(d['Average'] for d in cpu_data['Datapoints']) / len(cpu_data['Datapoints'])
                            
                            if avg_cpu < 5.0:
                                hourly_cost = self.ec2_pricing.get(instance_type, 0.10)
                                monthly_savings = hourly_cost * 24 * 30
                                
                                idle_instances.append({
                                    'resource_id': instance_id,
                                    'resource_type': 'ec2',
                                    'region': region,
                                    'instance_type': instance_type,
                                    'avg_cpu_7d': round(avg_cpu, 2),
                                    'monthly_savings': round(monthly_savings, 2),
                                    'recommendation': 'Stop or terminate this idle instance',
                                    'severity': 'high' if monthly_savings > 50 else 'medium',
                                    'category': 'idle_instance'
                                })
                    
                    except Exception as e:
                        logger.debug(f"Error checking {instance_id}: {e}")
            
        except Exception as e:
            logger.error(f"Error finding idle instances in {region}: {e}")
        
        return idle_instances
    
    def _find_underutilized_instances(self, region: str) -> List[Dict[str, Any]]:
        """Find instances with consistently low CPU (5-20% avg) that could be downsized."""
        underutilized = []
        
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            cloudwatch = self.aws_client.session.client('cloudwatch', region_name=region)
            
            response = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    
                    try:
                        cpu_data = cloudwatch.get_metric_statistics(
                            Namespace='AWS/EC2',
                            MetricName='CPUUtilization',
                            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                            StartTime=start_time,
                            EndTime=end_time,
                            Period=86400,
                            Statistics=['Average', 'Maximum']
                        )
                        
                        if cpu_data['Datapoints']:
                            avg_cpu = sum(d['Average'] for d in cpu_data['Datapoints']) / len(cpu_data['Datapoints'])
                            max_cpu = max(d['Maximum'] for d in cpu_data['Datapoints'])
                            
                            if 5.0 <= avg_cpu <= 20.0 and max_cpu < 40.0:
                                # Suggest smaller instance type
                                smaller_type = self._suggest_smaller_instance(instance_type)
                                if smaller_type:
                                    current_cost = self.ec2_pricing.get(instance_type, 0.10) * 24 * 30
                                    new_cost = self.ec2_pricing.get(smaller_type, 0.05) * 24 * 30
                                    monthly_savings = current_cost - new_cost
                                    
                                    if monthly_savings > 0:
                                        underutilized.append({
                                            'resource_id': instance_id,
                                            'resource_type': 'ec2',
                                            'region': region,
                                            'current_type': instance_type,
                                            'suggested_type': smaller_type,
                                            'avg_cpu_7d': round(avg_cpu, 2),
                                            'max_cpu_7d': round(max_cpu, 2),
                                            'monthly_savings': round(monthly_savings, 2),
                                            'recommendation': f'Downsize from {instance_type} to {smaller_type}',
                                            'severity': 'medium',
                                            'category': 'right_sizing'
                                        })
                    
                    except Exception as e:
                        logger.debug(f"Error checking {instance_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error finding underutilized instances in {region}: {e}")
        
        return underutilized
    
    def _find_unattached_volumes(self, region: str) -> List[Dict[str, Any]]:
        """Find EBS volumes not attached to any instance."""
        unattached = []
        
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            
            response = ec2.describe_volumes(
                Filters=[{'Name': 'status', 'Values': ['available']}]
            )
            
            for volume in response['Volumes']:
                volume_id = volume['VolumeId']
                size_gb = volume['Size']
                volume_type = volume['VolumeType']
                created = volume['CreateTime']
                
                # Calculate age
                age_days = (datetime.now(created.tzinfo) - created).days
                
                # Calculate cost (GP2: $0.10/GB/month)
                monthly_cost = size_gb * 0.10
                
                unattached.append({
                    'resource_id': volume_id,
                    'resource_type': 'ebs',
                    'region': region,
                    'size_gb': size_gb,
                    'volume_type': volume_type,
                    'age_days': age_days,
                    'monthly_savings': round(monthly_cost, 2),
                    'recommendation': 'Delete if not needed or attach to instance',
                    'severity': 'high' if age_days > 30 else 'low',
                    'category': 'unattached_volume'
                })
        
        except Exception as e:
            logger.error(f"Error finding unattached volumes in {region}: {e}")
        
        return unattached
    
    def _find_old_snapshots(self, region: str) -> List[Dict[str, Any]]:
        """Find snapshots older than 90 days."""
        old_snapshots = []
        
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            
            # Get snapshots owned by account
            response = ec2.describe_snapshots(OwnerIds=['self'])
            
            cutoff_date = datetime.now(datetime.utcnow().astimezone().tzinfo) - timedelta(days=90)
            
            for snapshot in response['Snapshots']:
                snapshot_id = snapshot['SnapshotId']
                start_time = snapshot['StartTime']
                volume_size = snapshot['VolumeSize']
                
                if start_time < cutoff_date:
                    age_days = (datetime.now(start_time.tzinfo) - start_time).days
                    
                    # Snapshot cost: $0.05/GB/month
                    monthly_cost = volume_size * 0.05
                    
                    old_snapshots.append({
                        'resource_id': snapshot_id,
                        'resource_type': 'snapshot',
                        'region': region,
                        'size_gb': volume_size,
                        'age_days': age_days,
                        'created': start_time.isoformat(),
                        'monthly_savings': round(monthly_cost, 2),
                        'recommendation': f'Delete snapshot (>90 days old)',
                        'severity': 'low',
                        'category': 'old_snapshot'
                    })
        
        except Exception as e:
            logger.error(f"Error finding old snapshots in {region}: {e}")
        
        return old_snapshots
    
    def _find_right_sizing_opportunities(self, region: str) -> List[Dict[str, Any]]:
        """Find RDS instances that could be downsized."""
        opportunities = []
        
        try:
            rds = self.aws_client.session.client('rds', region_name=region)
            cloudwatch = self.aws_client.session.client('cloudwatch', region_name=region)
            
            response = rds.describe_db_instances()
            
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)
            
            for db in response['DBInstances']:
                db_id = db['DBInstanceIdentifier']
                db_class = db['DBInstanceClass']
                
                try:
                    cpu_data = cloudwatch.get_metric_statistics(
                        Namespace='AWS/RDS',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                        StartTime=start_time,
                        EndTime=end_time,
                        Period=86400,
                        Statistics=['Average', 'Maximum']
                    )
                    
                    if cpu_data['Datapoints']:
                        avg_cpu = sum(d['Average'] for d in cpu_data['Datapoints']) / len(cpu_data['Datapoints'])
                        max_cpu = max(d['Maximum'] for d in cpu_data['Datapoints'])
                        
                        if avg_cpu < 20.0 and max_cpu < 50.0:
                            smaller_class = self._suggest_smaller_rds(db_class)
                            if smaller_class:
                                current_cost = self.rds_pricing.get(db_class, 0.10) * 24 * 30
                                new_cost = self.rds_pricing.get(smaller_class, 0.05) * 24 * 30
                                monthly_savings = current_cost - new_cost
                                
                                if monthly_savings > 0:
                                    opportunities.append({
                                        'resource_id': db_id,
                                        'resource_type': 'rds',
                                        'region': region,
                                        'current_class': db_class,
                                        'suggested_class': smaller_class,
                                        'avg_cpu_7d': round(avg_cpu, 2),
                                        'max_cpu_7d': round(max_cpu, 2),
                                        'monthly_savings': round(monthly_savings, 2),
                                        'recommendation': f'Downsize from {db_class} to {smaller_class}',
                                        'severity': 'medium',
                                        'category': 'right_sizing'
                                    })
                
                except Exception as e:
                    logger.debug(f"Error checking {db_id}: {e}")
        
        except Exception as e:
            logger.error(f"Error finding RDS right-sizing in {region}: {e}")
        
        return opportunities
    
    def _find_reserved_instance_opportunities(self, region: str) -> List[Dict[str, Any]]:
        """Identify instances running 24/7 that would benefit from Reserved Instances."""
        opportunities = []
        
        try:
            ec2 = self.aws_client.session.client('ec2', region_name=region)
            
            response = ec2.describe_instances(
                Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
            )
            
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instance_id = instance['InstanceId']
                    instance_type = instance['InstanceType']
                    launch_time = instance['LaunchTime']
                    
                    # Check if running for > 30 days (likely 24/7)
                    age_days = (datetime.now(launch_time.tzinfo) - launch_time).days
                    
                    if age_days > 30:
                        on_demand_monthly = self.ec2_pricing.get(instance_type, 0.10) * 24 * 30
                        # RI typically 40% cheaper
                        ri_monthly = on_demand_monthly * 0.60
                        monthly_savings = on_demand_monthly - ri_monthly
                        
                        opportunities.append({
                            'resource_id': instance_id,
                            'resource_type': 'ec2',
                            'region': region,
                            'instance_type': instance_type,
                            'running_days': age_days,
                            'monthly_savings': round(monthly_savings, 2),
                            'annual_savings': round(monthly_savings * 12, 2),
                            'recommendation': f'Purchase 1-year Reserved Instance for {instance_type}',
                            'severity': 'medium',
                            'category': 'reserved_instance'
                        })
        
        except Exception as e:
            logger.error(f"Error finding RI opportunities in {region}: {e}")
        
        return opportunities
    
    def _suggest_smaller_instance(self, current_type: str) -> str:
        """Suggest next smaller instance type."""
        size_progression = {
            't2.small': 't2.micro',
            't2.medium': 't2.small',
            't2.large': 't2.medium',
            't2.xlarge': 't2.large',
            't3.small': 't3.micro',
            't3.medium': 't3.small',
            't3.large': 't3.medium',
            't3.xlarge': 't3.large',
            'm5.xlarge': 'm5.large',
            'm5.2xlarge': 'm5.xlarge',
            'c5.xlarge': 'c5.large',
            'c5.2xlarge': 'c5.xlarge',
        }
        return size_progression.get(current_type)
    
    def _suggest_smaller_rds(self, current_class: str) -> str:
        """Suggest next smaller RDS instance class."""
        size_progression = {
            'db.t3.small': 'db.t3.micro',
            'db.t3.medium': 'db.t3.small',
            'db.t3.large': 'db.t3.medium',
            'db.m5.xlarge': 'db.m5.large',
        }
        return size_progression.get(current_class)


# Global optimizer instance
cost_optimizer = CostOptimizer()
