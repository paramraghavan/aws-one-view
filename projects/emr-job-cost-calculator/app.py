from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import boto3
from datetime import datetime, timezone
import json
import os
from botocore.exceptions import ClientError, NoCredentialsError

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


class EMRJobCostCalculator:
    def __init__(self, region_name='us-east-1'):
        """Initialize the cost calculator with AWS clients."""
        try:
            self.emr_client = boto3.client('emr', region_name=region_name)
            self.ec2_client = boto3.client('ec2', region_name=region_name)
        except NoCredentialsError:
            raise Exception("AWS credentials not found. Please configure your credentials.")

    def get_cluster_info(self, cluster_id):
        """Get cluster configuration information."""
        try:
            response = self.emr_client.describe_cluster(ClusterId=cluster_id)
            cluster = response['Cluster']

            # Get instance groups
            instance_groups = self.emr_client.list_instance_groups(ClusterId=cluster_id)

            cluster_config = {
                'cluster_id': cluster_id,
                'name': cluster.get('Name', 'Unknown'),
                'state': cluster.get('Status', {}).get('State', 'Unknown'),
                'created_time': cluster.get('Status', {}).get('Timeline', {}).get('CreationDateTime'),
                'instance_groups': {}
            }

            # Parse instance groups
            for group in instance_groups['InstanceGroups']:
                group_type = group['InstanceGroupType'].lower()
                cluster_config['instance_groups'][group_type] = {
                    'instance_type': group['InstanceType'],
                    'instance_count': group['RequestedInstanceCount'],
                    'running_count': group['RunningInstanceCount'],
                    'market': group.get('Market', 'ON_DEMAND').lower()
                }

            return cluster_config

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidClusterId':
                raise Exception(f"Cluster {cluster_id} not found")
            elif error_code == 'AccessDenied':
                raise Exception("Access denied. Check your AWS permissions.")
            else:
                raise Exception(f"AWS Error: {e.response['Error']['Message']}")

    def get_spark_jobs(self, cluster_id, job_name_filter=None):
        """Get Spark applications/steps from the cluster."""
        try:
            # List steps (Spark jobs) on the cluster
            paginator = self.emr_client.get_paginator('list_steps')
            page_iterator = paginator.paginate(ClusterId=cluster_id)

            spark_jobs = []
            for page in page_iterator:
                for step in page['Steps']:
                    # Filter by job name if specified
                    if job_name_filter and job_name_filter.lower() not in step['Name'].lower():
                        continue

                    # Only include completed jobs
                    if step['Status']['State'] == 'COMPLETED':
                        timeline = step['Status']['Timeline']
                        start_time = timeline.get('StartDateTime')
                        end_time = timeline.get('EndDateTime')

                        job_info = {
                            'step_id': step['Id'],
                            'name': step['Name'],
                            'state': step['Status']['State'],
                            'start_time': start_time.isoformat() if start_time else None,
                            'end_time': end_time.isoformat() if end_time else None,
                        }

                        # Calculate duration
                        if start_time and end_time:
                            duration = end_time - start_time
                            job_info['duration_hours'] = duration.total_seconds() / 3600
                        else:
                            job_info['duration_hours'] = 0

                        spark_jobs.append(job_info)

            return spark_jobs

        except ClientError as e:
            raise Exception(f"Error getting jobs: {e.response['Error']['Message']}")

    def calculate_job_costs(self, jobs, pricing_config, cluster_config):
        """Calculate costs for jobs based on pricing configuration."""

        # Calculate base cost (master + core nodes - always running)
        base_hourly_cost = 0.0
        job_hourly_cost = 0.0  # Cost that only applies during job execution

        cost_breakdown = {
            'master': {'count': 0, 'rate': 0, 'cost': 0, 'always_on': True},
            'core': {'count': 0, 'rate': 0, 'cost': 0, 'always_on': True},
            'task': {'count': 0, 'rate': 0, 'cost': 0, 'always_on': False}
        }

        for group_type, group_info in cluster_config['instance_groups'].items():
            instance_count = group_info['instance_count']
            market_type = group_info['market']  # 'on_demand' or 'spot'

            # Get pricing based on node type and market
            if group_type == 'master':
                rate = pricing_config.get(f'master_{market_type}', pricing_config.get('master_on_demand', 0.27))
                base_hourly_cost += rate * instance_count
                cost_breakdown['master'] = {
                    'count': instance_count, 'rate': rate, 'cost': rate * instance_count, 'always_on': True
                }
            elif group_type == 'core':
                rate = pricing_config.get(f'core_{market_type}', pricing_config.get('core_on_demand', 0.27))
                base_hourly_cost += rate * instance_count
                cost_breakdown['core'] = {
                    'count': instance_count, 'rate': rate, 'cost': rate * instance_count, 'always_on': True
                }
            else:  # task nodes
                # For task nodes, get weighted average of spot and on-demand pricing
                spot_percentage = pricing_config.get('task_spot_percentage', 70) / 100  # Default 70% spot
                spot_rate = pricing_config.get('task_spot', 0.08)
                ondemand_rate = pricing_config.get('task_on_demand', 0.27)

                weighted_rate = (spot_rate * spot_percentage) + (ondemand_rate * (1 - spot_percentage))
                job_hourly_cost += weighted_rate * instance_count
                cost_breakdown['task'] = {
                    'count': instance_count, 'rate': weighted_rate, 'cost': weighted_rate * instance_count,
                    'always_on': False, 'spot_percentage': spot_percentage * 100
                }

        total_hourly_cost = base_hourly_cost + job_hourly_cost

        # Calculate cost for each job
        job_costs = []
        total_job_cost = 0.0
        total_base_cost = 0.0

        for job in jobs:
            # Job cost = (base cost for always-on nodes * duration) + (task nodes cost * duration)
            base_cost = job['duration_hours'] * base_hourly_cost
            task_cost = job['duration_hours'] * job_hourly_cost
            total_cost = base_cost + task_cost

            job_cost_info = {
                'job_name': job['name'],
                'step_id': job['step_id'],
                'duration_hours': round(job['duration_hours'], 4),
                'start_time': job['start_time'],
                'end_time': job['end_time'],
                'base_cost': round(base_cost, 4),  # Master + Core cost
                'task_cost': round(task_cost, 4),  # Task nodes cost
                'estimated_cost': round(total_cost, 4)
            }

            job_costs.append(job_cost_info)
            total_job_cost += total_cost
            total_base_cost += base_cost

        # Sort by cost descending
        job_costs.sort(key=lambda x: x['estimated_cost'], reverse=True)

        return {
            'jobs': job_costs,
            'total_cost': round(total_job_cost, 4),
            'total_base_cost': round(total_base_cost, 4),
            'hourly_rate': round(total_hourly_cost, 4),
            'base_hourly_rate': round(base_hourly_cost, 4),
            'task_hourly_rate': round(job_hourly_cost, 4),
            'cost_breakdown': cost_breakdown
        }


# Global calculator instance
calculator = None


@app.route('/')
def index():
    """Serve the main UI page."""
    return render_template('index.html', title='EMR job cost calculator')


@app.route('/api/calculate-costs', methods=['POST'])
def calculate_costs():
    """API endpoint to calculate EMR job costs."""
    try:
        data = request.get_json()

        # Validate required fields
        cluster_id = data.get('cluster_id')
        region = data.get('region', 'us-east-1')

        if not cluster_id:
            return jsonify({'error': 'Cluster ID is required'}), 400

        # Initialize calculator with specified region
        global calculator
        calculator = EMRJobCostCalculator(region_name=region)

        # Get cluster information
        cluster_info = calculator.get_cluster_info(cluster_id)

        # Get jobs with optional filtering
        job_name_filter = data.get('job_name_filter')
        jobs = calculator.get_spark_jobs(cluster_id, job_name_filter)

        if not jobs:
            return jsonify({
                'cluster_info': cluster_info,
                'jobs': [],
                'total_cost': 0.0,
                'hourly_rate': 0.0,
                'message': 'No completed jobs found'
            })

        # Get pricing configuration
        pricing_config = data.get('pricing', {
            'master_on_demand': 0.27,
            'master_spot': 0.08,
            'core_on_demand': 0.27,
            'core_spot': 0.08,
            'task_on_demand': 0.27,
            'task_spot': 0.08,
            'task_spot_percentage': 70  # Percentage of task nodes that are spot instances
        })

        # Calculate costs
        cost_results = calculator.calculate_job_costs(jobs, pricing_config, cluster_info)

        # Prepare response
        response = {
            'cluster_info': {
                'name': cluster_info['name'],
                'state': cluster_info['state'],
                'master_nodes': cluster_info['instance_groups'].get('master', {}).get('instance_count', 0),
                'core_nodes': cluster_info['instance_groups'].get('core', {}).get('instance_count', 0),
                'task_nodes': cluster_info['instance_groups'].get('task', {}).get('instance_count', 0),
                'created_time': cluster_info.get('created_time').isoformat() if cluster_info.get(
                    'created_time') else None
            },
            'jobs': cost_results['jobs'],
            'total_cost': cost_results['total_cost'],
            'total_base_cost': cost_results['total_base_cost'],
            'hourly_rate': cost_results['hourly_rate'],
            'base_hourly_rate': cost_results['base_hourly_rate'],
            'task_hourly_rate': cost_results['task_hourly_rate'],
            'cost_breakdown': cost_results['cost_breakdown'],
            'job_count': len(cost_results['jobs'])
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Test AWS credentials
        sts = boto3.client('sts')
        sts.get_caller_identity()
        return jsonify({'status': 'healthy', 'aws_configured': True})
    except:
        return jsonify({'status': 'healthy', 'aws_configured': False})



if __name__ == '__main__':
    print("EMR Cost Calculator Server Starting...")
    print("Make sure your AWS credentials are configured!")
    print("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)