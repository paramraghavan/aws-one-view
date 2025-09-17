#!/usr/bin/env python3
"""
Script to get EMR cluster IDs and update config.yaml
This script helps you discover your EMR clusters and their details.
"""

import boto3
import yaml
import sys
import json
from datetime import datetime, timedelta


def get_emr_clusters():
    """Get all EMR clusters from AWS"""
    try:
        emr = boto3.client('emr')

        # Get active clusters
        print("🔍 Fetching EMR clusters...")
        response = emr.list_clusters(
            ClusterStates=['STARTING', 'BOOTSTRAPPING', 'RUNNING', 'WAITING']
        )

        clusters = []
        for cluster in response['Clusters']:
            cluster_id = cluster['Id']

            # Get detailed cluster info
            detail_response = emr.describe_cluster(ClusterId=cluster_id)
            cluster_detail = detail_response['Cluster']

            master_dns = cluster_detail.get('MasterPublicDnsName', 'Not Available')

            clusters.append({
                'id': cluster_id,
                'name': cluster['Name'],
                'state': cluster['Status']['State'],
                'master_dns': master_dns,
                'created': cluster['Status']['Timeline']['CreationDateTime'],
                'details': cluster_detail
            })

        return clusters

    except Exception as e:
        print(f"❌ Error fetching clusters: {e}")
        print("Make sure you have:")
        print("  - AWS CLI configured (aws configure)")
        print("  - Proper EMR permissions")
        print("  - Internet connectivity")
        return []


def display_clusters(clusters):
    """Display clusters in a nice format"""
    if not clusters:
        print("❌ No active EMR clusters found")
        return

    print(f"\n✅ Found {len(clusters)} active EMR cluster(s):")
    print("=" * 80)

    for i, cluster in enumerate(clusters, 1):
        created_date = cluster['created'].strftime('%Y-%m-%d %H:%M:%S')
        print(f"\n{i}. 🏷️  Cluster: {cluster['name']}")
        print(f"   📋 AWS ID: {cluster['id']}")
        print(f"   📊 State: {cluster['state']}")
        print(f"   🌐 Master: {cluster['master_dns']}")
        print(f"   📅 Created: {created_date}")

        # Show instance groups
        instance_groups = cluster['details'].get('InstanceGroups', [])
        if instance_groups:
            print(f"   💻 Instance Groups:")
            for ig in instance_groups:
                ig_type = ig.get('InstanceGroupType', 'UNKNOWN')
                instance_count = ig.get('RequestedInstanceCount', 0)
                instance_type = ig.get('InstanceType', 'unknown')
                print(f"      - {ig_type}: {instance_count}x {instance_type}")


def generate_config(clusters):
    """Generate config.yaml entries"""
    if not clusters:
        return

    print(f"\n🔧 Generating config.yaml entries:")
    print("=" * 50)

    config_entries = {}

    for cluster in clusters:
        # Create a friendly name for the config
        friendly_name = cluster['name'].lower().replace(' ', '-').replace('_', '-')

        # Remove special characters
        friendly_name = ''.join(c for c in friendly_name if c.isalnum() or c == '-')

        master_dns = cluster['master_dns']
        if master_dns == 'Not Available':
            print(f"⚠️  Skipping {cluster['name']} - no public DNS available")
            continue

        config_entries[friendly_name] = {
            'name': cluster['name'],
            'spark_url': f"http://{master_dns}:18080",
            'yarn_url': f"http://{master_dns}:8088",
            'description': f"EMR cluster created on {cluster['created'].strftime('%Y-%m-%d')}",
            'aws_cluster_id': cluster['id']
        }

    # Print YAML format
    yaml_output = yaml.dump({'emr_clusters': config_entries}, default_flow_style=False, indent=2)
    print(yaml_output)

    return config_entries


def update_config_file(config_entries):
    """Update existing config.yaml file"""
    config_file = 'config.yaml'

    try:
        # Try to load existing config
        try:
            with open(config_file, 'r') as f:
                existing_config = yaml.safe_load(f) or {}
        except FileNotFoundError:
            existing_config = {}

        # Update or create emr_clusters section
        if 'emr_clusters' not in existing_config:
            existing_config['emr_clusters'] = {}

        # Ask user which clusters to add/update
        print(f"\n📝 Update {config_file}?")
        for cluster_key, cluster_config in config_entries.items():
            if cluster_key in existing_config['emr_clusters']:
                response = input(f"Update existing '{cluster_key}'? (y/n): ").lower()
            else:
                response = input(f"Add new '{cluster_key}'? (y/n): ").lower()

            if response == 'y':
                existing_config['emr_clusters'][cluster_key] = cluster_config
                print(f"✅ {'Updated' if cluster_key in existing_config['emr_clusters'] else 'Added'} {cluster_key}")

        # Write back to file
        with open(config_file, 'w') as f:
            yaml.dump(existing_config, f, default_flow_style=False, indent=2)

        print(f"\n✅ Updated {config_file}")

    except Exception as e:
        print(f"❌ Error updating config file: {e}")


def check_connectivity(clusters):
    """Check if clusters are accessible"""
    import requests

    print(f"\n🔗 Checking connectivity to clusters...")
    print("=" * 40)

    for cluster in clusters:
        if cluster['master_dns'] == 'Not Available':
            continue

        master_dns = cluster['master_dns']

        print(f"\n🏷️  {cluster['name']} ({cluster['id']})")

        # Check Spark History Server
        try:
            spark_url = f"http://{master_dns}:18080"
            response = requests.get(f"{spark_url}/api/v1/applications", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ Spark History Server (18080): Accessible")
            else:
                print(f"   ❌ Spark History Server (18080): HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ Spark History Server (18080): {str(e)[:50]}...")

        # Check YARN ResourceManager
        try:
            yarn_url = f"http://{master_dns}:8088"
            response = requests.get(f"{yarn_url}/ws/v1/cluster/info", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ YARN ResourceManager (8088): Accessible")
            else:
                print(f"   ❌ YARN ResourceManager (8088): HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ YARN ResourceManager (8088): {str(e)[:50]}...")


def main():
    """Main function"""
    print("🚀 EMR Cluster Discovery Tool")
    print("=" * 40)

    # Check if AWS CLI is configured
    try:
        boto3.Session().get_credentials()
    except Exception:
        print("❌ AWS credentials not found. Please run 'aws configure' first.")
        sys.exit(1)

    # Get clusters
    clusters = get_emr_clusters()

    if not clusters:
        print("\n💡 Tips:")
        print("  - Make sure you have active EMR clusters")
        print("  - Check your AWS region (current region in AWS CLI)")
        print("  - Verify EMR permissions in your AWS account")
        sys.exit(1)

    # Display clusters
    display_clusters(clusters)

    # Generate config
    config_entries = generate_config(clusters)

    if config_entries:
        # Ask if user wants to update config file
        response = input(f"\n❓ Update config.yaml file? (y/n): ").lower()
        if response == 'y':
            update_config_file(config_entries)

        # Ask if user wants to check connectivity
        response = input(f"\n❓ Test connectivity to clusters? (y/n): ").lower()
        if response == 'y':
            check_connectivity(clusters)

    print(f"\n🎉 Done! You can now run your EMR monitoring tool.")


if __name__ == '__main__':
    main()