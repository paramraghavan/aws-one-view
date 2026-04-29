#!/usr/bin/env python3
"""
Generate sample Cloudability cost data for testing chargeback analysis

This creates realistic mock data that mimics the structure and patterns
of actual Cloudability cost exports.

Usage:
    python3 generate_sample_cloudability_data.py [--output costs_raw.csv]
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse

# User namespaces
USERS = [
    'analytics-prod',
    'data-science-team-1',
    'data-science-team-2',
    'ml-engineering',
    'quant-research',
    'research-lab',
    'trading-systems',
    'risk-modeling',
]

# Service namespaces
SERVICES = [
    'kube-system',
    'kube-node-lease',
    'prometheus',
    'grafana',
    'ingress-nginx',
    'cert-manager',
    'logging',
    'vault',
]

# Generate months from Jan 2025 to Feb 2026
def get_months():
    """Generate month strings (YYYY-MM) for Jan 2025 to Feb 2026"""
    start = datetime(2025, 1, 1)
    end = datetime(2026, 2, 28)
    months = []
    current = start
    while current <= end:
        months.append(current.strftime('%Y-%m'))
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    return months

def generate_sample_data():
    """Generate realistic sample cost data"""

    months = get_months()
    rows = []

    # Base monthly cost for cluster
    base_cluster_cost = 40000

    # Generate user costs
    user_base_costs = {
        'analytics-prod': 5000,
        'data-science-team-1': 3500,
        'data-science-team-2': 3000,
        'ml-engineering': 2500,
        'quant-research': 2000,
        'research-lab': 2000,
        'trading-systems': 1500,
        'risk-modeling': 1200,
    }

    print("Generating sample data...")
    print(f"  Months: {len(months)} (Jan 2025 - Feb 2026)")
    print(f"  Users: {len(USERS)}")
    print(f"  Services: {len(SERVICES)}")

    # Generate user costs with realistic variance
    for month in months:
        month_num = int(month.split('-')[1])

        # Seasonal variation (higher usage in Q4, Q1)
        seasonal_factor = 1.0
        if month_num in [11, 12, 1, 2]:
            seasonal_factor = 1.15
        elif month_num in [7, 8]:
            seasonal_factor = 0.90

        for user in USERS:
            base = user_base_costs[user]

            # Add month-to-month growth (~2% per month)
            month_idx = months.index(month)
            growth = (1.02 ** month_idx)

            # Random variation ±10%
            noise = np.random.uniform(0.9, 1.1)

            cost = base * seasonal_factor * growth * noise

            rows.append({
                'Month': month,
                'Namespace': user,
                'Service': 'pod',
                'FairshareValue': round(cost, 2)
            })

    # Generate service costs (proportional to total user cost)
    service_base_costs = {
        'kube-system': 800,
        'kube-node-lease': 50,
        'prometheus': 500,
        'grafana': 200,
        'ingress-nginx': 300,
        'cert-manager': 100,
        'logging': 600,
        'vault': 250,
    }

    for month in months:
        month_idx = months.index(month)
        growth = (1.02 ** month_idx)

        for service in SERVICES:
            base = service_base_costs[service]
            noise = np.random.uniform(0.95, 1.05)
            cost = base * growth * noise

            rows.append({
                'Month': month,
                'Namespace': service,
                'Service': 'pod',
                'FairshareValue': round(cost, 2)
            })

    df = pd.DataFrame(rows)

    # Verify fairshare (distribute service costs proportionally)
    print("\nApplying fairshare distribution...")

    # Fairshare: costs are already proportionally distributed by namespace
    # In real Cloudability, fairshare would redistribute idle capacity
    # For this sample, we'll add a small idle allocation factor

    total_before = df['FairshareValue'].sum()

    # Add ~5% idle cost redistribution
    user_df = df[df['Namespace'].isin(USERS)].copy()
    user_total_by_month = user_df.groupby('Month')['FairshareValue'].sum()

    idle_adjustment = 0.05  # 5% idle
    df_user = df[df['Namespace'].isin(USERS)].copy()
    df_service = df[df['Namespace'].isin(SERVICES)].copy()

    # Users absorb idle proportionally
    for idx in df_user.index:
        month = df.loc[idx, 'Month']
        month_user_total = df_user[df_user['Month'] == month]['FairshareValue'].sum()
        proportion = df.loc[idx, 'FairshareValue'] / month_user_total
        idle_amount = df_service[df_service['Month'] == month]['FairshareValue'].sum() * idle_adjustment * proportion
        df.loc[idx, 'FairshareValue'] = round(df.loc[idx, 'FairshareValue'] + idle_amount, 2)

    total_after = df['FairshareValue'].sum()

    return df

def main():
    parser = argparse.ArgumentParser(
        description='Generate sample Cloudability cost data for testing'
    )
    parser.add_argument(
        '--output',
        default='costs_raw.csv',
        help='Output CSV filename (default: costs_raw.csv)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )

    args = parser.parse_args()

    # Set seed for reproducibility
    np.random.seed(args.seed)

    print(f"\n{'='*70}")
    print(" SAMPLE CLOUDABILITY DATA GENERATOR")
    print(f"{'='*70}\n")

    df = generate_sample_data()

    # Sort for readability
    df = df.sort_values(['Month', 'Namespace']).reset_index(drop=True)

    # Save to CSV
    df.to_csv(args.output, index=False)

    # Display statistics
    print(f"\nGenerated data statistics:")
    print(f"  Total rows: {len(df)}")
    print(f"  Months: {df['Month'].nunique()}")
    print(f"  Namespaces: {df['Namespace'].nunique()}")
    print(f"  Total fairshare cost: ${df['FairshareValue'].sum():,.2f}")
    print(f"  Date range: {df['Month'].min()} to {df['Month'].max()}")

    print(f"\nNamespaces ({df['Namespace'].nunique()}):")
    for ns in sorted(df['Namespace'].unique()):
        cost = df[df['Namespace'] == ns]['FairshareValue'].sum()
        count = len(df[df['Namespace'] == ns])
        print(f"  - {ns:<25} ${cost:>10,.2f} ({count} rows)")

    print(f"\nMonthly totals (sample):")
    monthly = df.groupby('Month')['FairshareValue'].sum().sort_index()
    for month in monthly.index[:3]:
        print(f"  {month}: ${monthly[month]:>10,.2f}")
    print("  ...")
    for month in monthly.index[-2:]:
        print(f"  {month}: ${monthly[month]:>10,.2f}")

    print(f"\n✓ Sample data saved to: {args.output}")
    print(f"\nNext step:")
    print(f"  python3 chargeback_analysis.py --input {args.output}")
    print()

if __name__ == '__main__':
    main()
