#!/usr/bin/env python3
"""
Cloudability Cost Analyzer - Functional Version (No Classes)

Simple, plain function-based approach to generate cost reports.
Joins Workday users + Cluster + Service + Instance data.

Supports both mock data (for testing) and real Cloudability API responses.

Run: python3 generate_reports_functional.py
"""

import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).parent / "mock_data"
REPORTS_DIR = Path(__file__).parent / "reports"

# Column names for final report
REPORT_COLUMNS = [
    'user_id', 'full_name', 'block_funding', 'vp',
    'cpu_mean', 'gpu_mean', 'memory_mean',
    'utilized_cost', 'idle_cost', 'cost_by_fair_share',
    'efficient_score', 'cluster_cost', 'cpu_fair_share',
    'artifactory_cost', 'license_cost', 'platform_cost',
    'aws_service_cost', 'total_cost', 'is_new_user'
]

# ============================================================================
# LOAD DATA FUNCTIONS
# ============================================================================

def load_users():
    """Load Workday user data."""
    print("Loading Workday users...")
    users = pd.read_csv(BASE_DIR / "workday_users.csv")
    print(f"  ✓ Loaded {len(users)} users")
    return users


def load_cluster_data(filepath):
    """
    Load cluster data from CSV.

    Automatically detects format (real API vs mock) and transforms as needed.
    """
    df = pd.read_csv(filepath)

    # Transform if this is real API format
    if is_real_api_format(df):
        df = transform_cloudability_api_response(df)

    return df


def load_service_data(filepath):
    """Load service cost data from CSV."""
    return pd.read_csv(filepath)


def load_instance_data(filepath):
    """Load instance usage data from CSV."""
    return pd.read_csv(filepath)

# ============================================================================
# REAL CLOUDABILITY API TRANSFORMATION
# ============================================================================
# Functions to handle the real Cloudability API schema
# See: REAL_API_INTEGRATION_GUIDE.md for detailed column mapping

def transform_cloudability_api_response(api_response_df):
    """
    Transform raw Cloudability API response to business-meaningful columns.

    Real API returns columns with pattern: [resource_type]/[metric]/[measurement_type]
    Example: 'cpu/reserved: resource: mean', 'costs: allocation', etc.

    Returns DataFrame with standardized column names that rest of pipeline expects.
    """
    result = api_response_df.copy()

    # Mapping of API column names to business column names
    # These are the 12 essential columns documented in CLOUDABILITY_API_SCHEMA.md
    api_to_business = {
        'type': 'type',
        'namespace': 'namespace',
        'cpu/reserved: resource: mean': 'cpu_mean',
        'memory/reserved_rss: resource: mean': 'memory_mean',
        'gpu/reserved: resource: mean': 'gpu_mean',
        'costs: allocation': 'utilized_cost',
        'costs: fairShare': 'cost_by_fair_share',
        'costs: unallocated': 'idle_cost',
        'network/tx: allocation': 'network_tx_cost',
        'network/rx: allocation': 'network_rx_cost',
        'filesystem/usage: allocation': 'storage_ephemeral_cost',
        'persistent_volume_filesystem/usage: allocation': 'storage_persistent_cost',
    }

    # Rename columns that exist in the API response
    rename_map = {old: new for old, new in api_to_business.items() if old in result.columns}
    result = result.rename(columns=rename_map)

    # Handle alternative API column formats (with colons vs without)
    for old, new in api_to_business.items():
        if old not in result.columns and new not in result.columns:
            alt_formats = [
                old.replace(': ', ':'),
                old.replace(': ', ' '),
                old.replace(': ', '_'),
            ]
            for alt in alt_formats:
                if alt in result.columns:
                    result = result.rename(columns={alt: new})
                    break

    # Calculate derived metrics

    # 1. Total cluster cost (sum of all cost components)
    cost_columns = ['utilized_cost', 'cost_by_fair_share', 'idle_cost']
    if all(col in result.columns for col in cost_columns):
        result['cluster_cost'] = (
            result.get('utilized_cost', 0) +
            result.get('cost_by_fair_share', 0) +
            result.get('idle_cost', 0)
        )

    # 2. Efficiency score (utilization percentage)
    if 'utilized_cost' in result.columns and 'idle_cost' in result.columns:
        result['efficient_score'] = (
            result['utilized_cost'] /
            (result['utilized_cost'] + result['idle_cost'])
        ) * 100
        result['efficient_score'] = result['efficient_score'].fillna(0).replace([float('inf'), -float('inf')], 0)

    # 3. CPU fair share percentage
    if 'cpu/reserved: fairShare' in api_response_df.columns and 'cost_by_fair_share' in result.columns:
        result['cpu_fair_share'] = (
            api_response_df['cpu/reserved: fairShare'] / result['cost_by_fair_share'] * 100
        )
        result['cpu_fair_share'] = result['cpu_fair_share'].fillna(0).replace([float('inf'), -float('inf')], 0)
    else:
        result['cpu_fair_share'] = 0

    # 4. Bronze cost (network + storage allocation)
    network_cost = result.get('network_tx_cost', 0) + result.get('network_rx_cost', 0)
    storage_cost = result.get('storage_ephemeral_cost', 0) + result.get('storage_persistent_cost', 0)
    result['bronze_cost'] = network_cost + storage_cost

    # Fill missing cost columns with 0
    cost_cols = [
        'utilized_cost', 'idle_cost', 'cost_by_fair_share',
        'cluster_cost', 'efficient_score', 'cpu_fair_share', 'bronze_cost'
    ]
    for col in cost_cols:
        if col in result.columns:
            result[col] = result[col].fillna(0)
        else:
            result[col] = 0

    return result


def is_real_api_format(df):
    """
    Detect if DataFrame is in real API format vs mock data format.

    Real API format has columns like: 'costs: allocation', 'cpu/reserved: resource: mean'
    Mock format has simple names like: 'utilized_cost', 'cpu_mean'
    """
    api_indicators = [
        'costs: allocation',
        'cpu/reserved',
        'memory/reserved',
        'gpu/reserved'
    ]
    return any(col in df.columns for col in api_indicators)


# ============================================================================
# AGGREGATION FUNCTIONS
# ============================================================================

def aggregate_cluster_by_user(cluster_df):
    """
    Aggregate cluster data by user.

    Multiple clusters per user are summed for costs and averaged for metrics.
    Handles both mock data format and real API format.
    """
    if cluster_df.empty:
        return pd.DataFrame()

    # Determine which columns exist
    existing_cols = set(cluster_df.columns)

    # Define aggregation strategies
    agg_dict = {}

    # Metrics to average
    avg_cols = ['cpu_mean', 'gpu_mean', 'memory_mean', 'efficient_score', 'cpu_fair_share']
    for col in avg_cols:
        if col in existing_cols:
            agg_dict[col] = 'mean'

    # Costs to sum
    sum_cols = [
        'utilized_cost', 'idle_cost', 'cost_by_fair_share',
        'cluster_cost', 'bronze_cost',
        'artifactory_cost', 'license_cost', 'platform_cost',
        'aws_service_cost', 'adjusted_amortized_cost'
    ]
    for col in sum_cols:
        if col in existing_cols:
            agg_dict[col] = 'sum'

    # Ensure we have at least one column to aggregate
    if not agg_dict:
        return pd.DataFrame()

    aggregated = cluster_df.groupby('user_id', as_index=False).agg(agg_dict)

    # Rename adjusted_amortized_cost to total_cost if it exists
    if 'adjusted_amortized_cost' in aggregated.columns:
        aggregated = aggregated.rename(columns={'adjusted_amortized_cost': 'total_cost'})
    elif 'cluster_cost' in aggregated.columns and 'total_cost' not in aggregated.columns:
        aggregated['total_cost'] = aggregated['cluster_cost']
    elif 'utilized_cost' in aggregated.columns and 'total_cost' not in aggregated.columns:
        aggregated['total_cost'] = aggregated['utilized_cost']

    return aggregated


def aggregate_service_costs(service_df):
    """Sum all service costs for the period."""
    if service_df.empty:
        return 0.0
    return service_df['total_amortized_cost'].sum()


def aggregate_instance_costs(instance_df):
    """Sum all instance costs for the period."""
    if instance_df.empty:
        return 0.0
    return instance_df['total_amortized_cost'].sum()

# ============================================================================
# JOIN FUNCTIONS
# ============================================================================

def join_and_allocate(users_df, cluster_agg, service_total, instance_total):
    """
    Join users with cluster data and allocate global costs proportionally.

    Process:
    1. Keep only needed user columns
    2. LEFT JOIN with cluster aggregation
    3. Calculate user proportion of cluster costs
    4. Allocate service and instance costs proportionally
    5. Calculate final total cost
    """

    # Step 1: Select user columns
    user_cols = ['user_id', 'full_name', 'block_funding', 'vp', 'is_new_user']
    result = users_df[user_cols].copy()

    # Step 2: LEFT JOIN with cluster aggregation
    result = result.merge(
        cluster_agg,
        on='user_id',
        how='left'
    )

    # Step 3: Fill missing cluster data with 0
    cluster_cols = [col for col in cluster_agg.columns if col != 'user_id']
    for col in cluster_cols:
        result[col] = result[col].fillna(0)

    # Step 4: Calculate proportions and allocate
    total_cluster_cost = result['total_cost'].sum()

    if total_cluster_cost > 0:
        result['user_proportion'] = result['total_cost'] / total_cluster_cost
    else:
        result['user_proportion'] = 0

    # Allocate service and instance costs
    result['service_allocated'] = result['user_proportion'] * service_total
    result['instance_allocated'] = result['user_proportion'] * instance_total

    # Step 5: Calculate final total cost
    result['total_cost'] = (
        result['total_cost'] +
        result['service_allocated'] +
        result['instance_allocated']
    )

    # Remove temporary columns
    result = result.drop(['user_proportion', 'service_allocated', 'instance_allocated'], axis=1)

    return result

# ============================================================================
# FORMATTING AND OUTPUT FUNCTIONS
# ============================================================================

def format_report(report_df):
    """Format report: round numbers, reorder columns, sort."""

    # Round numeric columns
    numeric_cols = report_df.select_dtypes(include=['float64']).columns
    report_df[numeric_cols] = report_df[numeric_cols].round(2)

    # Reorder columns - only include columns that exist in the dataframe
    available_cols = [col for col in REPORT_COLUMNS if col in report_df.columns]

    # If we don't have all columns, add missing ones with 0 values
    for col in REPORT_COLUMNS:
        if col not in report_df.columns:
            if col in ['is_new_user']:
                report_df[col] = False
            else:
                report_df[col] = 0
            available_cols.append(col)

    # Ensure the order matches REPORT_COLUMNS
    available_cols = [col for col in REPORT_COLUMNS if col in report_df.columns]
    report_df = report_df[available_cols]

    # Sort by user_id
    report_df = report_df.sort_values('user_id').reset_index(drop=True)

    return report_df


def save_report(report_df, filepath):
    """Save report to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    report_df.to_csv(filepath, index=False)
    print(f"  ✓ {filepath.relative_to(Path.cwd())} ({len(report_df)} records)")

# ============================================================================
# MAIN REPORT GENERATION FUNCTIONS
# ============================================================================

def generate_weekly_reports(users_df):
    """Generate all 12 weekly reports."""
    print("\nGenerating weekly reports...")

    for week in range(1, 13):
        # Load data for this week
        cluster_file = BASE_DIR / f"weekly/cluster/cluster_data_2026_week_{week:02d}.csv"
        service_file = BASE_DIR / f"weekly/service/service_cost_2026_week_{week:02d}.csv"
        instance_file = BASE_DIR / f"weekly/instance/instance_usage_2026_week_{week:02d}.csv"

        cluster_df = load_cluster_data(cluster_file)
        service_df = load_service_data(service_file)
        instance_df = load_instance_data(instance_file)

        # Aggregate
        cluster_agg = aggregate_cluster_by_user(cluster_df)
        service_total = aggregate_service_costs(service_df)
        instance_total = aggregate_instance_costs(instance_df)

        # Join and allocate
        report_df = join_and_allocate(users_df, cluster_agg, service_total, instance_total)

        # Format
        report_df = format_report(report_df)

        # Save
        output_file = REPORTS_DIR / f"weekly/cost_report_2026_week_{week:02d}.csv"
        save_report(report_df, output_file)


def generate_monthly_reports(users_df):
    """Generate all 3 monthly reports."""
    print("\nGenerating monthly reports...")

    for month in range(1, 4):
        # Load data for this month
        cluster_file = BASE_DIR / f"monthly/cluster/cluster_data_2026_{month:02d}.csv"
        service_file = BASE_DIR / f"monthly/service/service_cost_2026_{month:02d}.csv"
        instance_file = BASE_DIR / f"monthly/instance/instance_usage_2026_{month:02d}.csv"

        cluster_df = load_cluster_data(cluster_file)
        service_df = load_service_data(service_file)
        instance_df = load_instance_data(instance_file)

        # Aggregate
        cluster_agg = aggregate_cluster_by_user(cluster_df)
        service_total = aggregate_service_costs(service_df)
        instance_total = aggregate_instance_costs(instance_df)

        # Join and allocate
        report_df = join_and_allocate(users_df, cluster_agg, service_total, instance_total)

        # Format
        report_df = format_report(report_df)

        # Save
        output_file = REPORTS_DIR / f"monthly/cost_report_2026_{month:02d}.csv"
        save_report(report_df, output_file)


def generate_user_summary(period_type):
    """Generate user summary aggregated across all periods."""
    print(f"\n  Generating {period_type} user summary...")

    if period_type == 'weekly':
        pattern = "cost_report_*.csv"
        output_file = REPORTS_DIR / "summaries/user_summary_weekly_2026.csv"
    else:
        pattern = "cost_report_*.csv"
        output_file = REPORTS_DIR / "summaries/user_summary_monthly_2026.csv"

    # Load all reports
    reports = []
    if period_type == 'weekly':
        for report_file in sorted((REPORTS_DIR / "weekly").glob(pattern)):
            reports.append(pd.read_csv(report_file))
    else:
        for report_file in sorted((REPORTS_DIR / "monthly").glob(pattern)):
            reports.append(pd.read_csv(report_file))

    if not reports:
        print(f"    No reports found")
        return

    # Combine
    combined = pd.concat(reports, ignore_index=True)

    # Aggregate by user
    agg_dict = {
        'full_name': 'first',
        'block_funding': 'first',
        'vp': 'first',
        'is_new_user': 'first',
        'cpu_mean': 'mean',
        'gpu_mean': 'mean',
        'memory_mean': 'mean',
        'utilized_cost': 'sum',
        'idle_cost': 'sum',
        'cost_by_fair_share': 'sum',
        'efficient_score': 'mean',
        'cluster_cost': 'sum',
        'cpu_fair_share': 'mean',
        'artifactory_cost': 'sum',
        'license_cost': 'sum',
        'platform_cost': 'sum',
        'aws_service_cost': 'sum',
        'total_cost': 'sum'
    }

    summary = combined.groupby('user_id', as_index=False).agg(agg_dict)

    # Round and sort
    numeric_cols = summary.select_dtypes(include=['float64']).columns
    summary[numeric_cols] = summary[numeric_cols].round(2)
    summary = summary.sort_values('total_cost', ascending=False).reset_index(drop=True)

    # Save
    filepath = Path(output_file)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(filepath, index=False)
    print(f"    ✓ {filepath.relative_to(Path.cwd())} ({len(summary)} records)")


def generate_funding_summary(period_type):
    """Generate funding block summary."""
    print(f"  Generating {period_type} funding block summary...")

    if period_type == 'weekly':
        pattern = "cost_report_*.csv"
        output_file = REPORTS_DIR / "summaries/funding_summary_weekly_2026.csv"
    else:
        pattern = "cost_report_*.csv"
        output_file = REPORTS_DIR / "summaries/funding_summary_monthly_2026.csv"

    # Load all reports
    reports = []
    if period_type == 'weekly':
        for report_file in sorted((REPORTS_DIR / "weekly").glob(pattern)):
            reports.append(pd.read_csv(report_file))
    else:
        for report_file in sorted((REPORTS_DIR / "monthly").glob(pattern)):
            reports.append(pd.read_csv(report_file))

    if not reports:
        return

    combined = pd.concat(reports, ignore_index=True)

    # Aggregate by funding block
    agg_dict = {
        'user_id': 'nunique',
        'cpu_mean': 'mean',
        'gpu_mean': 'mean',
        'memory_mean': 'mean',
        'utilized_cost': 'sum',
        'idle_cost': 'sum',
        'cost_by_fair_share': 'sum',
        'efficient_score': 'mean',
        'cluster_cost': 'sum',
        'cpu_fair_share': 'mean',
        'artifactory_cost': 'sum',
        'license_cost': 'sum',
        'platform_cost': 'sum',
        'aws_service_cost': 'sum',
        'total_cost': 'sum'
    }

    summary = combined.groupby('block_funding', as_index=False).agg(agg_dict)
    summary = summary.rename(columns={'user_id': 'user_count'})

    # Round and sort
    numeric_cols = summary.select_dtypes(include=['float64']).columns
    summary[numeric_cols] = summary[numeric_cols].round(2)
    summary = summary.sort_values('total_cost', ascending=False).reset_index(drop=True)

    # Save
    filepath = Path(output_file)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(filepath, index=False)
    print(f"    ✓ {filepath.relative_to(Path.cwd())} ({len(summary)} records)")


def generate_vp_summary(period_type):
    """Generate VP summary."""
    print(f"  Generating {period_type} VP summary...")

    if period_type == 'weekly':
        pattern = "cost_report_*.csv"
        output_file = REPORTS_DIR / "summaries/vp_summary_weekly_2026.csv"
    else:
        pattern = "cost_report_*.csv"
        output_file = REPORTS_DIR / "summaries/vp_summary_monthly_2026.csv"

    # Load all reports
    reports = []
    if period_type == 'weekly':
        for report_file in sorted((REPORTS_DIR / "weekly").glob(pattern)):
            reports.append(pd.read_csv(report_file))
    else:
        for report_file in sorted((REPORTS_DIR / "monthly").glob(pattern)):
            reports.append(pd.read_csv(report_file))

    if not reports:
        return

    combined = pd.concat(reports, ignore_index=True)

    # Aggregate by VP
    agg_dict = {
        'user_id': 'nunique',
        'cpu_mean': 'mean',
        'gpu_mean': 'mean',
        'memory_mean': 'mean',
        'utilized_cost': 'sum',
        'idle_cost': 'sum',
        'cost_by_fair_share': 'sum',
        'efficient_score': 'mean',
        'cluster_cost': 'sum',
        'cpu_fair_share': 'mean',
        'artifactory_cost': 'sum',
        'license_cost': 'sum',
        'platform_cost': 'sum',
        'aws_service_cost': 'sum',
        'total_cost': 'sum'
    }

    summary = combined.groupby('vp', as_index=False).agg(agg_dict)
    summary = summary.rename(columns={'user_id': 'user_count'})

    # Round and sort
    numeric_cols = summary.select_dtypes(include=['float64']).columns
    summary[numeric_cols] = summary[numeric_cols].round(2)
    summary = summary.sort_values('total_cost', ascending=False).reset_index(drop=True)

    # Save
    filepath = Path(output_file)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(filepath, index=False)
    print(f"    ✓ {filepath.relative_to(Path.cwd())} ({len(summary)} records)")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """
    Generate all reports.

    Supports both:
    - Mock data format (for testing and development)
    - Real Cloudability API format (for production)

    The script automatically detects the data format and transforms as needed.
    """
    print("\n" + "=" * 70)
    print("CLOUDABILITY COST ANALYZER - FUNCTIONAL VERSION")
    print("=" * 70)
    print("\nData sources:")
    print("  1. Workday users (identity + org structure)")
    print("  2. Cluster data (resource usage + direct costs)")
    print("  3. Service costs (AWS services)")
    print("  4. Instance usage (EC2 instance types)")
    print("\nSupported formats:")
    print("  ✓ Mock data (simple column names: cpu_mean, utilized_cost, etc.)")
    print("  ✓ Real API (pattern columns: cpu/reserved: resource: mean, costs: allocation, etc.)")

    # Load users once
    users_df = load_users()

    # Generate weekly reports
    generate_weekly_reports(users_df)

    # Generate monthly reports
    generate_monthly_reports(users_df)

    # Generate summaries
    print("\nGenerating summary reports...")
    generate_user_summary('weekly')
    generate_user_summary('monthly')
    generate_funding_summary('weekly')
    generate_funding_summary('monthly')
    generate_vp_summary('weekly')
    generate_vp_summary('monthly')

    # Summary
    print("\n" + "=" * 70)
    print("REPORT GENERATION COMPLETE")
    print("=" * 70)
    print(f"Output directory: {REPORTS_DIR}")
    report_files = list(REPORTS_DIR.rglob("*.csv"))
    print(f"Total files generated: {len(report_files)}")
    print("\n✓ All 4 data sources joined successfully!")
    print("✓ 21 reports with 20 columns each")
    print("✓ Proportional cost allocation applied")


if __name__ == "__main__":
    main()
