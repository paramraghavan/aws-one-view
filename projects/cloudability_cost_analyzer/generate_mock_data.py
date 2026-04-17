#!/usr/bin/env python3
"""
Generate mock Cloudability and Workday data for testing.

Creates:
- 1 Workday users CSV (75 users)
- 36 weekly Cloudability CSVs (12 weeks × 3 types: cluster, service, instance)
- 9 monthly Cloudability CSVs (3 months × 3 types)

Total: 46 CSV files in mock_data/ directory
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

# Configuration
NUM_USERS = 75
NUM_WEEKS = 12
WEEKS_START = "2026-01-05"
MONTHS = ["2026-01", "2026-02", "2026-03"]

# Seed for reproducibility
np.random.seed(42)

BASE_DIR = Path(__file__).parent / "mock_data"


def create_directories():
    """Create directory structure."""
    dirs = [
        BASE_DIR,
        BASE_DIR / "weekly" / "cluster",
        BASE_DIR / "weekly" / "service",
        BASE_DIR / "weekly" / "instance",
        BASE_DIR / "monthly" / "cluster",
        BASE_DIR / "monthly" / "service",
        BASE_DIR / "monthly" / "instance",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created directory structure in {BASE_DIR}")


def generate_workday_users():
    """Generate 75 Workday users with org hierarchy."""
    vps = [f"user{i:03d}" for i in range(100, 103)]
    block_fundings = ["Engineering", "Product", "Platform", "Finance", "Marketing", "Operations", "Research"]
    first_names = ["Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Harper", "Ivan", "Julia",
                   "Kelly", "Leo", "Mia", "Noah", "Olivia", "Parker", "Quinn", "Rachel", "Sam", "Taylor",
                   "Uma", "Victor", "Wendy", "Xavier", "Yuki", "Zoe"]
    last_names = ["Anderson", "Baker", "Chen", "Davis", "Evans", "Fisher", "Garcia", "Harris", "Ito", "Johnson",
                  "Khan", "Lopez", "Martinez", "Nelson", "O'Brien", "Patel", "Quinn", "Rodriguez", "Smith", "Taylor",
                  "Ueda", "Volkov", "Wang", "Xavier", "Yamamoto", "Zhang"]

    users = []
    for i in range(NUM_USERS):
        user_id = f"user{i:03d}"
        first = np.random.choice(first_names)
        last = np.random.choice(last_names)
        namespace = f"team-{np.random.choice(['data-science', 'platform', 'backend', 'frontend', 'infra', 'analytics'])}"

        users.append({
            'user_id': user_id,
            'namespace': namespace,
            'full_name': f"{first} {last}",
            'reports_to': np.random.choice(vps[:2]) if i > 0 else vps[0],
            'vp': np.random.choice(vps),
            'block_funding': np.random.choice(block_fundings),
            'is_new_user': np.random.choice([True, False], p=[0.2, 0.8])
        })

    df = pd.DataFrame(users)
    output_path = BASE_DIR / "workday_users.csv"
    df.to_csv(output_path, index=False)
    print(f"✓ Generated {len(df)} Workday users → {output_path.relative_to(Path.cwd())}")
    return df


def generate_cluster_data(week_num=None, month_num=None):
    """Generate cluster data for a specific week or month."""
    users = pd.read_csv(BASE_DIR / "workday_users.csv")

    records = []
    for _, user in users.iterrows():
        # Generate 3-5 containers per user
        num_containers = np.random.randint(3, 6)
        for c in range(num_containers):
            base_cost = np.random.uniform(1000, 5000)
            idle_factor = np.random.uniform(0.2, 0.5)

            records.append({
                'user_id': user['user_id'],
                'namespace': user['namespace'],
                'type': 'container',
                'cpu_mean': np.random.uniform(2, 8),
                'gpu_mean': np.random.choice([0, 0, 0, 1, 2]),
                'memory_mean': np.random.uniform(16, 64),
                'utilized_cost': base_cost,
                'idle_cost': base_cost * idle_factor,
                'cost_by_fair_share': base_cost * 0.5,
                'efficient_score': np.random.uniform(60, 90),
                'cluster_cost': base_cost * (1 + idle_factor + 0.5),
                'cpu_fair_share': np.random.uniform(50, 70),
                'artifactory_cost': np.random.uniform(100, 500),
                'license_cost': np.random.uniform(500, 2000),
                'platform_cost': np.random.uniform(300, 1500),
                'aws_service_cost': np.random.uniform(500, 3000),
                'adjusted_amortized_cost': base_cost * (1 + idle_factor + 0.5),
            })

    df = pd.DataFrame(records)

    if week_num:
        output_path = BASE_DIR / f"weekly/cluster/cluster_data_2026_week_{week_num:02d}.csv"
    else:
        output_path = BASE_DIR / f"monthly/cluster/cluster_data_2026_{month_num:02d}.csv"

    df.to_csv(output_path, index=False)
    return output_path


def generate_service_data(week_num=None, month_num=None):
    """Generate service cost data."""
    services = [
        'EC2', 'S3', 'RDS', 'Lambda', 'EKS', 'ELB',
        'CloudFront', 'DynamoDB', 'ElastiCache', 'SNS', 'SQS', 'API Gateway'
    ]

    records = []
    for service in services:
        cost = np.random.uniform(50000, 500000)
        records.append({
            'service_name': service,
            'usage_family': np.random.choice(['Compute', 'Storage', 'Database', 'Networking']),
            'total_amortized_cost': cost
        })

    df = pd.DataFrame(records)

    if week_num:
        output_path = BASE_DIR / f"weekly/service/service_cost_2026_week_{week_num:02d}.csv"
    else:
        output_path = BASE_DIR / f"monthly/service/service_cost_2026_{month_num:02d}.csv"

    df.to_csv(output_path, index=False)
    return output_path


def generate_instance_data(week_num=None, month_num=None):
    """Generate instance usage data."""
    instance_types = [
        't3.large', 't3.xlarge', 'm5.large', 'm5.xlarge', 'm5.2xlarge',
        'c5.large', 'c5.xlarge', 'c5.2xlarge', 'r5.large', 'r5.xlarge',
        'p3.2xlarge', 'p3.8xlarge', 'i3.large', 'i3.xlarge'
    ]
    lease_types = ['On-Demand', 'Reserved', 'Spot']

    records = []
    for instance_type in instance_types:
        for lease_type in lease_types:
            records.append({
                'instance_type': instance_type,
                'instance_category': np.random.choice(['Compute', 'Memory Optimized', 'GPU', 'Storage Optimized']),
                'lease_type': lease_type,
                'total_amortized_cost': np.random.uniform(100, 50000)
            })

    df = pd.DataFrame(records)

    if week_num:
        output_path = BASE_DIR / f"weekly/instance/instance_usage_2026_week_{week_num:02d}.csv"
    else:
        output_path = BASE_DIR / f"monthly/instance/instance_usage_2026_{month_num:02d}.csv"

    df.to_csv(output_path, index=False)
    return output_path


def main():
    """Generate all mock data."""
    print("\n" + "=" * 70)
    print("MOCK DATA GENERATOR")
    print("=" * 70)

    # Create directories
    create_directories()

    # Generate Workday users
    print("\nGenerating Workday data...")
    generate_workday_users()

    # Generate weekly data
    print("\nGenerating weekly data (12 weeks)...")
    for week in range(1, NUM_WEEKS + 1):
        generate_cluster_data(week_num=week)
        generate_service_data(week_num=week)
        generate_instance_data(week_num=week)
    print(f"✓ Generated 36 weekly files (12 weeks × 3 types)")

    # Generate monthly data
    print("\nGenerating monthly data (3 months)...")
    for i, month in enumerate(MONTHS, 1):
        generate_cluster_data(month_num=i)
        generate_service_data(month_num=i)
        generate_instance_data(month_num=i)
    print(f"✓ Generated 9 monthly files (3 months × 3 types)")

    # Summary
    print("\n" + "=" * 70)
    print("MOCK DATA GENERATION COMPLETE")
    print("=" * 70)
    print(f"Generated 46 CSV files in: {BASE_DIR}")
    print("\nContents:")
    print("  • 1 Workday users file (75 users)")
    print("  • 36 weekly Cloudability files (12 weeks)")
    print("  • 9 monthly Cloudability files (3 months)")
    print("\nReady to use with: python3 generate_reports_functional.py")
    print()


if __name__ == "__main__":
    main()
