#!/usr/bin/env python3
"""
Configuration Validation Script for EMR Monitoring Tool
Validates config.yaml and tests connectivity to EMR clusters.
"""

import yaml
import json
import requests
import sys
import os
from datetime import datetime


def load_config():
    """Load and validate configuration file"""
    config_files = ['config.yaml', 'config.yml', 'config.json']

    for config_file in config_files:
        if os.path.exists(config_file):
            print(f"📄 Found configuration file: {config_file}")
            try:
                if config_file.endswith('.json'):
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                else:
                    with open(config_file, 'r') as f:
                        config = yaml.safe_load(f)

                print("✅ Configuration file loaded successfully")
                return config, config_file

            except Exception as e:
                print(f"❌ Error loading {config_file}: {e}")
                continue

    print("❌ No valid configuration file found!")
    print("Expected files: config.yaml, config.yml, or config.json")
    return None, None


def validate_config_structure(config):
    """Validate configuration structure"""
    print("\n🔍 Validating configuration structure...")

    if not isinstance(config, dict):
        print("❌ Configuration must be a dictionary/object")
        return False

    if 'emr_clusters' not in config:
        print("❌ Missing 'emr_clusters' section in configuration")
        return False

    clusters = config['emr_clusters']
    if not isinstance(clusters, dict):
        print("❌ 'emr_clusters' must be a dictionary/object")
        return False

    if len(clusters) == 0:
        print("❌ No clusters defined in 'emr_clusters'")
        return False

    print(f"✅ Found {len(clusters)} cluster(s) in configuration")

    # Validate each cluster
    for cluster_id, cluster_config in clusters.items():
        print(f"\n📋 Validating cluster '{cluster_id}':")

        if not isinstance(cluster_config, dict):
            print(f"❌ Cluster '{cluster_id}' configuration must be a dictionary")
            return False

        required_fields = ['name', 'spark_url', 'yarn_url']
        for field in required_fields:
            if field not in cluster_config:
                print(f"❌ Missing required field '{field}' in cluster '{cluster_id}'")
                return False

            if not cluster_config[field]:
                print(f"❌ Empty value for required field '{field}' in cluster '{cluster_id}'")
                return False

            print(f"✅ {field}: {cluster_config[field]}")

        # Optional fields
        optional_fields = ['description', 'aws_cluster_id']
        for field in optional_fields:
            if field in cluster_config:
                print(f"✅ {field}: {cluster_config[field]}")

    return True


def test_cluster_connectivity(cluster_id, cluster_config):
    """Test connectivity to a specific cluster"""
    print(f"\n🔗 Testing connectivity to cluster '{cluster_id}'...")

    spark_url = cluster_config.get('spark_url')
    yarn_url = cluster_config.get('yarn_url')

    results = {'spark': False, 'yarn': False}

    # Test Spark History Server
    if spark_url:
        try:
            print(f"🔍 Testing Spark History Server: {spark_url}")
            response = requests.get(f"{spark_url}/api/v1/applications", timeout=10)
            if response.status_code == 200:
                apps = response.json()
                print(f"✅ Spark History Server accessible ({len(apps)} applications found)")
                results['spark'] = True
            else:
                print(f"⚠️ Spark History Server responded with status {response.status_code}")
        except requests.exceptions.ConnectTimeout:
            print("❌ Spark History Server connection timeout (check network/firewall)")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ Spark History Server connection error: {e}")
        except Exception as e:
            print(f"❌ Spark History Server error: {e}")

    # Test YARN ResourceManager
    if yarn_url:
        try:
            print(f"🔍 Testing YARN ResourceManager: {yarn_url}")
            response = requests.get(f"{yarn_url}/ws/v1/cluster/info", timeout=10)
            if response.status_code == 200:
                info = response.json()
                cluster_info = info.get('clusterInfo', {})
                cluster_name = cluster_info.get('clusterName', 'Unknown')
                print(f"✅ YARN ResourceManager accessible (cluster: {cluster_name})")
                results['yarn'] = True
            else:
                print(f"⚠️ YARN ResourceManager responded with status {response.status_code}")
        except requests.exceptions.ConnectTimeout:
            print("❌ YARN ResourceManager connection timeout (check network/firewall)")
        except requests.exceptions.ConnectionError as e:
            print(f"❌ YARN ResourceManager connection error: {e}")
        except Exception as e:
            print(f"❌ YARN ResourceManager error: {e}")

    return results


def test_all_clusters(config):
    """Test connectivity to all configured clusters"""
    print("\n🚀 Testing connectivity to all clusters...")

    clusters = config.get('emr_clusters', {})
    overall_results = {}

    for cluster_id, cluster_config in clusters.items():
        results = test_cluster_connectivity(cluster_id, cluster_config)
        overall_results[cluster_id] = results

    return overall_results


def generate_summary(config, connectivity_results):
    """Generate validation summary"""
    print("\n" + "=" * 60)
    print("📊 VALIDATION SUMMARY")
    print("=" * 60)

    clusters = config.get('emr_clusters', {})
    total_clusters = len(clusters)

    spark_accessible = sum(1 for r in connectivity_results.values() if r['spark'])
    yarn_accessible = sum(1 for r in connectivity_results.values() if r['yarn'])
    fully_accessible = sum(1 for r in connectivity_results.values() if r['spark'] and r['yarn'])

    print(f"📋 Total clusters configured: {total_clusters}")
    print(f"✅ Spark History accessible: {spark_accessible}/{total_clusters}")
    print(f"✅ YARN ResourceManager accessible: {yarn_accessible}/{total_clusters}")
    print(f"🎯 Fully accessible clusters: {fully_accessible}/{total_clusters}")

    if fully_accessible == total_clusters:
        print("\n🎉 All clusters are properly configured and accessible!")
        print("✅ Ready to start EMR monitoring tool")
    else:
        print(f"\n⚠️ {total_clusters - fully_accessible} cluster(s) have connectivity issues")
        print("❗ Please check network connectivity, URLs, and EMR cluster status")

    # Individual cluster status
    print(f"\n📋 Individual Cluster Status:")
    for cluster_id, results in connectivity_results.items():
        spark_status = "✅" if results['spark'] else "❌"
        yarn_status = "✅" if results['yarn'] else "❌"
        print(f"  {cluster_id}: Spark {spark_status} | YARN {yarn_status}")


def provide_troubleshooting_tips():
    """Provide troubleshooting tips for common issues"""
    print("\n" + "=" * 60)
    print("🛠️ TROUBLESHOOTING TIPS")
    print("=" * 60)
    print("""
Common issues and solutions:

🔹 Connection Timeout:
   - Check if EMR cluster is running
   - Verify security group allows access to ports 18080 and 8088
   - Check if you're on the correct network/VPN

🔹 Connection Refused:
   - Spark History Server might not be running (check port 18080)
   - YARN ResourceManager might not be running (check port 8088)
   - Verify the master node hostname/IP is correct

🔹 DNS Resolution Issues:
   - Use IP address instead of hostname
   - Check /etc/hosts file or DNS configuration

🔹 Network Access:
   - Use SSH tunneling for private clusters:
     ssh -L 18080:master-private-ip:18080 user@bastion-host
     ssh -L 8088:master-private-ip:8088 user@bastion-host
   - Then use http://localhost:18080 and http://localhost:8088

🔹 Configuration Issues:
   - Check YAML syntax (indentation matters)
   - Ensure all required fields are present
   - Verify URLs use correct format: http://hostname:port

For more help, check the README.md file or EMR documentation.
""")


def create_sample_config():
    """Create a sample configuration file"""
    print("\n📝 Creating sample configuration file...")

    sample_config = {
        'emr_clusters': {
            'staging': {
                'name': 'Staging EMR',
                'spark_url': 'http://staging-master:18080',
                'yarn_url': 'http://staging-master:8088',
                'description': 'Staging EMR cluster',
                'aws_cluster_id': 'j-EXAMPLE123456'
            },
            'production': {
                'name': 'Production EMR',
                'spark_url': 'http://production-master:18080',
                'yarn_url': 'http://production-master:8088',
                'description': 'Production EMR cluster',
                'aws_cluster_id': 'j-EXAMPLE789012'
            }
        }
    }

    try:
        with open('config.yaml.sample', 'w') as f:
            yaml.dump(sample_config, f, default_flow_style=False, indent=2)

        print("✅ Sample configuration created: config.yaml.sample")
        print("📝 Copy this file to config.yaml and update with your EMR details")

    except Exception as e:
        print(f"❌ Error creating sample config: {e}")


def main():
    """Main validation function"""
    print("🚀 EMR Monitoring Tool - Configuration Validator")
    print("=" * 60)
    print(f"⏰ Validation started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load configuration
    config, config_file = load_config()

    if not config:
        print("\n❓ Would you like to create a sample configuration file?")
        response = input("Create sample config? (y/n): ").lower()
        if response == 'y':
            create_sample_config()
        provide_troubleshooting_tips()
        sys.exit(1)

    # Validate configuration structure
    if not validate_config_structure(config):
        print("\n❌ Configuration validation failed!")
        provide_troubleshooting_tips()
        sys.exit(1)

    # Test connectivity
    connectivity_results = test_all_clusters(config)

    # Generate summary
    generate_summary(config, connectivity_results)

    # Check if any clusters failed connectivity
    failed_clusters = [
        cluster_id for cluster_id, results in connectivity_results.items()
        if not (results['spark'] and results['yarn'])
    ]

    if failed_clusters:
        provide_troubleshooting_tips()
        print(f"\n⚠️ Clusters with issues: {', '.join(failed_clusters)}")
        sys.exit(1)
    else:
        print(f"\n🎯 Configuration validation completed successfully!")
        print("✅ You can now start the EMR monitoring tool with: python app.py")
        sys.exit(0)


if __name__ == '__main__':
    main()