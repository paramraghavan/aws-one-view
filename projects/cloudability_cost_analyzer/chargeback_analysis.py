#!/usr/bin/env python3
"""
EMR on Kubernetes Cloudability Chargeback Analysis
Processes monthly costs by user from raw Cloudability CSV data

Usage:
    python3 chargeback_analysis.py [--input costs_raw.csv] [--output-dir .]
"""

import pandas as pd
import sys
import os
from pathlib import Path
import argparse

# Service namespaces - these are infrastructure, not user workloads
SERVICE_NAMESPACES = {
    'kube-system', 'kube-node-lease', 'kube-public',           # Kubernetes core
    'prometheus', 'grafana', 'loki', 'logging',                 # Monitoring/logging
    'ingress-nginx', 'cert-manager', 'vault',                   # Networking/security
    'external-dns', 'cluster-autoscaler', 'kyverno',           # Cluster management
}

def print_section(title):
    """Print a formatted section header"""
    print(f"\n{'='*75}")
    print(f" {title}")
    print(f"{'='*75}\n")

def load_data(input_file):
    """Load raw Cloudability CSV data"""
    print_section("STEP 1: LOAD DATA")

    if not os.path.exists(input_file):
        print(f"✗ File not found: {input_file}")
        print("\n  Run this first:")
        print("    export CLOUDABILITY_API_KEY='your-key'")
        print("    export CLOUDABILITY_CLUSTER_ID='your-id'")
        print("    bash fetch_cloudability_data.sh")
        sys.exit(1)

    df = pd.read_csv(input_file)

    print(f"✓ Loaded {len(df)} rows from {input_file}")
    print(f"  Date range: {df['Month'].min()} to {df['Month'].max()}")
    print(f"  Unique namespaces: {df['Namespace'].nunique()}")
    print(f"  Total fairshare cost: ${df['FairshareValue'].sum():,.2f}")

    return df

def classify_namespaces(df):
    """Separate user vs service namespaces"""
    print_section("STEP 2: CLASSIFY NAMESPACES")

    user_ns = df[~df['Namespace'].isin(SERVICE_NAMESPACES)].copy()
    service_ns = df[df['Namespace'].isin(SERVICE_NAMESPACES)].copy()

    print(f"✓ User namespaces: {user_ns['Namespace'].nunique()}")
    for ns in sorted(user_ns['Namespace'].unique()):
        cost = user_ns[user_ns['Namespace'] == ns]['FairshareValue'].sum()
        print(f"  - {ns:<30} ${cost:>12,.2f}")

    print(f"\n✓ Service namespaces: {service_ns['Namespace'].nunique()}")
    for ns in sorted(service_ns['Namespace'].unique()):
        cost = service_ns[service_ns['Namespace'] == ns]['FairshareValue'].sum()
        print(f"  - {ns:<30} ${cost:>12,.2f}")

    print(f"\nCost breakdown:")
    print(f"  User namespaces:    ${user_ns['FairshareValue'].sum():>12,.2f}")
    print(f"  Service namespaces: ${service_ns['FairshareValue'].sum():>12,.2f}")
    print(f"  TOTAL:              ${df['FairshareValue'].sum():>12,.2f}")

    return user_ns, service_ns

def calculate_user_costs(user_ns):
    """Calculate monthly costs by user (before service distribution)"""
    print_section("STEP 3: MONTHLY COSTS BY USER (Before service distribution)")

    user_monthly = user_ns.groupby(['Month', 'Namespace'])['FairshareValue'].sum().reset_index()
    user_monthly.rename(columns={'Namespace': 'User', 'FairshareValue': 'DirectCost'}, inplace=True)

    # Pivot for readability
    user_pivot = user_monthly.pivot(index='Month', columns='User', values='DirectCost').fillna(0)

    print("User costs by month (first 3 months):")
    print(user_pivot.iloc[:3].to_string())

    print(f"\nTotal per user (all months):")
    totals = user_pivot.sum().sort_values(ascending=False)
    for user, cost in totals.items():
        print(f"  {user:<30} ${cost:>12,.2f}")

    return user_monthly

def distribute_service_costs(user_monthly, service_ns):
    """Distribute service costs proportionally to users"""
    print_section("STEP 4: DISTRIBUTE SERVICE COSTS PROPORTIONALLY")

    # Get total service cost per month
    service_monthly = service_ns.groupby('Month')['FairshareValue'].sum().reset_index()
    service_monthly.rename(columns={'FairshareValue': 'ServiceCost'}, inplace=True)

    print("Service costs by month:")
    for _, row in service_monthly.iterrows():
        print(f"  {row['Month']}: ${row['ServiceCost']:>10,.2f}")

    # Calculate each user's proportion of total user cost per month
    user_total_by_month = user_monthly.groupby('Month')['DirectCost'].sum().reset_index()
    user_total_by_month.rename(columns={'DirectCost': 'TotalUserCost'}, inplace=True)

    user_monthly = user_monthly.merge(user_total_by_month, on='Month')
    user_monthly['Proportion'] = user_monthly['DirectCost'] / user_monthly['TotalUserCost']

    # Merge service cost and calculate allocation
    user_monthly = user_monthly.merge(service_monthly, on='Month')
    user_monthly['ServiceAllocation'] = user_monthly['ServiceCost'] * user_monthly['Proportion']

    # Show example distribution
    print("\nService allocation example (first month):")
    first_month = user_monthly[user_monthly['Month'] == user_monthly['Month'].min()]
    display_cols = ['User', 'DirectCost', 'Proportion', 'ServiceCost', 'ServiceAllocation']
    print(first_month[display_cols].to_string(index=False))

    # Verify sums match
    first_month_allocation = first_month['ServiceAllocation'].sum()
    first_month_service = first_month['ServiceCost'].iloc[0]
    print(f"\nVerification:")
    print(f"  Sum of allocations:  ${first_month_allocation:>10,.2f}")
    print(f"  Actual service cost: ${first_month_service:>10,.2f}")
    if abs(first_month_allocation - first_month_service) < 0.01:
        print(f"  ✓ Distribution sums correctly")

    return user_monthly

def build_chargeback(user_monthly):
    """Build final chargeback table"""
    print_section("STEP 5: FINAL CHARGEBACK (User + Service)")

    chargeback = user_monthly[['Month', 'User', 'DirectCost', 'ServiceAllocation']].copy()
    chargeback['TotalCost'] = chargeback['DirectCost'] + chargeback['ServiceAllocation']
    chargeback = chargeback.sort_values(['Month', 'User']).reset_index(drop=True)

    print("Full chargeback table (first 15 rows):")
    print(chargeback.head(15).to_string(index=False))

    print(f"\n✓ {len(chargeback)} total rows (users × months)")

    return chargeback

def validate_totals(chargeback, df):
    """Validate that calculated totals match Cloudability"""
    print_section("STEP 6: VALIDATION - Monthly Totals vs Cloudability")

    # What Cloudability reports (all namespaces)
    cloudability_total = df.groupby('Month')['FairshareValue'].sum().reset_index()
    cloudability_total.rename(columns={'FairshareValue': 'CloudabilityTotal'}, inplace=True)

    # What we calculated
    our_total = chargeback.groupby('Month')['TotalCost'].sum().reset_index()
    our_total.rename(columns={'TotalCost': 'OurTotal'}, inplace=True)

    # Compare
    validation = cloudability_total.merge(our_total, on='Month')
    validation['Difference'] = validation['CloudabilityTotal'] - validation['OurTotal']
    validation['DiffPct'] = (validation['Difference'] / validation['CloudabilityTotal'] * 100).round(6)

    print("Validation results (all months):")
    print(validation.to_string(index=False))

    # Check if valid
    is_valid = (validation['DiffPct'].abs() < 0.01).all()
    print(f"\n{'✓' if is_valid else '✗'} Validation {'PASSED' if is_valid else 'FAILED'}")
    if not is_valid:
        print("\nMismatches:")
        for _, row in validation[validation['DiffPct'].abs() >= 0.01].iterrows():
            print(f"  {row['Month']}: {row['DiffPct']:.6f}%")

    return validation

def calculate_mom_changes(chargeback):
    """Calculate month-over-month changes per user"""
    print_section("STEP 7: MONTH-OVER-MONTH CHANGES")

    chargeback_sorted = chargeback.sort_values(['User', 'Month']).reset_index(drop=True)
    chargeback_sorted['MoMDollarChange'] = chargeback_sorted.groupby('User')['TotalCost'].diff()
    chargeback_sorted['MoMPercentChange'] = (
        chargeback_sorted.groupby('User')['TotalCost'].pct_change() * 100
    ).round(2)

    # Show example for first user
    first_user = chargeback_sorted['User'].iloc[0]
    user_data = chargeback_sorted[chargeback_sorted['User'] == first_user][
        ['Month', 'TotalCost', 'MoMDollarChange', 'MoMPercentChange']
    ].head(10)

    print(f"MoM changes for {first_user} (example):")
    print(user_data.to_string(index=False))

    # Show latest changes
    print("\nLatest month-over-month changes (by user):")
    latest_mom = chargeback_sorted.dropna(subset=['MoMPercentChange']).sort_values('Month').groupby('User').tail(1)
    latest_mom = latest_mom[['Month', 'User', 'TotalCost', 'MoMDollarChange', 'MoMPercentChange']]
    print(latest_mom.sort_values('MoMPercentChange', ascending=False).to_string(index=False))

    return chargeback_sorted

def generate_summary(chargeback):
    """Generate summary statistics"""
    print_section("STEP 8: SUMMARY STATISTICS")

    summary = chargeback.groupby('User').agg({
        'DirectCost': 'sum',
        'ServiceAllocation': 'sum',
        'TotalCost': ['sum', 'mean', 'min', 'max', 'std']
    }).round(2)

    summary.columns = ['DirectCost', 'ServiceAllocated', 'TotalCost', 'AvgMonthly', 'MinMonth', 'MaxMonth', 'StdDev']
    summary = summary.sort_values('TotalCost', ascending=False)

    print("Cost summary by user (Jan 2025 - Feb 2026):")
    print(summary.to_string())

    print(f"\n\nGrand total (all users, all months): ${summary['TotalCost'].sum():,.2f}")

    return summary

def save_outputs(chargeback, chargeback_sorted, validation, summary, output_dir):
    """Save all output files"""
    print_section("STEP 9: SAVING OUTPUT FILES")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = {
        'chargeback_by_user_monthly.csv': chargeback,
        'chargeback_with_mom_changes.csv': chargeback_sorted,
        'validation_monthly_totals.csv': validation,
        'summary_by_user.csv': summary,
    }

    for filename, df in files.items():
        filepath = output_dir / filename
        df.to_csv(filepath, index=False)
        print(f"✓ {filename:<40} ({len(df)} rows)")

def main():
    parser = argparse.ArgumentParser(
        description='EMR on Kubernetes Cloudability Chargeback Analysis'
    )
    parser.add_argument(
        '--input',
        default='costs_raw.csv',
        help='Input CSV file from Cloudability (default: costs_raw.csv)'
    )
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Output directory for CSV files (default: current directory)'
    )

    args = parser.parse_args()

    print("\n" + "="*75)
    print(" EMR ON KUBERNETES CLOUDABILITY CHARGEBACK ANALYSIS")
    print(" Jan 2025 - Feb 2026 | Monthly by User")
    print("="*75)

    # Execute pipeline
    df = load_data(args.input)
    user_ns, service_ns = classify_namespaces(df)
    user_monthly = calculate_user_costs(user_ns)
    user_monthly = distribute_service_costs(user_monthly, service_ns)
    chargeback = build_chargeback(user_monthly)
    validation = validate_totals(chargeback, df)
    chargeback_sorted = calculate_mom_changes(chargeback)
    summary = generate_summary(chargeback)
    save_outputs(chargeback, chargeback_sorted, validation, summary, args.output_dir)

    # Final summary
    print_section("ANALYSIS COMPLETE")
    print(f"✓ All output files saved to: {args.output_dir}/")
    print(f"\n  Main files:")
    print(f"    • chargeback_by_user_monthly.csv    (chargeback table)")
    print(f"    • summary_by_user.csv               (totals & statistics)")
    print(f"    • chargeback_with_mom_changes.csv   (month-over-month changes)")
    print(f"    • validation_monthly_totals.csv     (validation vs Cloudability)")
    print("\n")

if __name__ == '__main__':
    main()
