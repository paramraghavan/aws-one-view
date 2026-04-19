#!/usr/bin/env python3
"""
Generate sample data for the Reporting Engine.

Creates realistic sample datasets for testing and demonstration:
- weekly_costs.csv - 52 weeks of cost data
- monthly_costs.csv - 12 months of cost data
- departments.csv - Department reference data
- projects.csv - Project reference data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
from pathlib import Path

# Sample data
DEPARTMENTS = [
    {'cost_center': 'ENG', 'department_name': 'Engineering', 'manager': 'Alice Johnson', 'budget_allocated': 500000},
    {'cost_center': 'MKT', 'department_name': 'Marketing', 'manager': 'Bob Smith', 'budget_allocated': 250000},
    {'cost_center': 'SAL', 'department_name': 'Sales', 'manager': 'Carol Davis', 'budget_allocated': 300000},
    {'cost_center': 'OPS', 'department_name': 'Operations', 'manager': 'David Miller', 'budget_allocated': 200000},
    {'cost_center': 'FIN', 'department_name': 'Finance', 'manager': 'Emma Wilson', 'budget_allocated': 150000},
]

PROJECTS = [
    {'project': 'PROJ001', 'project_name': 'Cloud Migration', 'status': 'active', 'priority': 'high'},
    {'project': 'PROJ002', 'project_name': 'Data Pipeline', 'status': 'active', 'priority': 'high'},
    {'project': 'PROJ003', 'project_name': 'Mobile App', 'status': 'active', 'priority': 'medium'},
    {'project': 'PROJ004', 'project_name': 'Analytics Platform', 'status': 'planning', 'priority': 'medium'},
    {'project': 'PROJ005', 'project_name': 'Security Upgrade', 'status': 'active', 'priority': 'high'},
]

RESOURCE_TYPES = ['compute', 'storage', 'network', 'database', 'cache', 'ml-service']

USERS = [
    'alice.johnson', 'bob.smith', 'carol.davis', 'david.miller', 'emma.wilson',
    'frank.brown', 'grace.lee', 'henry.white', 'iris.chen', 'john.taylor'
]


def generate_weekly_costs(weeks=52, num_users=10):
    """Generate weekly cost data."""
    print(f"Generating weekly costs for {weeks} weeks with {num_users} users...")

    rows = []
    start_date = datetime.now() - timedelta(days=weeks * 7)

    for week in range(weeks):
        week_start = start_date + timedelta(days=week * 7)
        week_end = week_start + timedelta(days=6)

        for _ in range(np.random.randint(50, 150)):  # 50-150 cost entries per week
            dept = np.random.choice([d['cost_center'] for d in DEPARTMENTS])
            project = np.random.choice([p['project'] for p in PROJECTS])
            user = np.random.choice(USERS[:num_users])
            resource = np.random.choice(RESOURCE_TYPES)

            cost = np.random.lognormal(7, 1.5)  # Log-normal distribution for realistic costs
            hours = np.random.randint(1, 168)

            rows.append({
                'start_date': week_start.strftime('%Y-%m-%d'),
                'end_date': week_end.strftime('%Y-%m-%d'),
                'cost_center': dept,
                'project': project,
                'user': user,
                'resource_type': resource,
                'cost': round(cost, 2),
                'usage_hours': hours
            })

    df = pd.DataFrame(rows)
    return df


def generate_monthly_costs(months=12, num_users=10):
    """Generate monthly cost data."""
    print(f"Generating monthly costs for {months} months...")

    rows = []
    start_date = datetime.now() - timedelta(days=months * 30)

    for month in range(months):
        month_start = start_date + timedelta(days=month * 30)
        month_end = month_start + timedelta(days=29)

        for _ in range(np.random.randint(200, 500)):  # 200-500 cost entries per month
            dept = np.random.choice([d['cost_center'] for d in DEPARTMENTS])
            project = np.random.choice([p['project'] for p in PROJECTS])
            user = np.random.choice(USERS[:num_users])
            resource = np.random.choice(RESOURCE_TYPES)

            cost = np.random.lognormal(7.5, 1.5)  # Higher costs for monthly
            hours = np.random.randint(10, 720)

            rows.append({
                'start_date': month_start.strftime('%Y-%m-%d'),
                'end_date': month_end.strftime('%Y-%m-%d'),
                'cost_center': dept,
                'project': project,
                'user': user,
                'resource_type': resource,
                'cost': round(cost, 2),
                'usage_hours': hours
            })

    df = pd.DataFrame(rows)
    return df


def main():
    parser = argparse.ArgumentParser(description='Generate sample data for Reporting Engine')
    parser.add_argument('--weeks', type=int, default=52, help='Number of weeks of data (default: 52)')
    parser.add_argument('--months', type=int, default=12, help='Number of months of data (default: 12)')
    parser.add_argument('--users', type=int, default=10, help='Number of users to include (default: 10)')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).parent.parent,
                        help='Output directory (default: project root)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    reports_dir = output_dir / 'reports'
    data_dir = output_dir / 'data'

    # Create directories if they don't exist
    reports_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)

    # Generate and save weekly costs
    weekly_df = generate_weekly_costs(args.weeks, args.users)
    weekly_path = reports_dir / 'weekly_costs.csv'
    weekly_df.to_csv(weekly_path, index=False)
    print(f"✓ Generated {len(weekly_df)} weekly cost records → {weekly_path}")

    # Generate and save monthly costs
    monthly_df = generate_monthly_costs(args.months, args.users)
    monthly_path = reports_dir / 'monthly_costs.csv'
    monthly_df.to_csv(monthly_path, index=False)
    print(f"✓ Generated {len(monthly_df)} monthly cost records → {monthly_path}")

    # Save department reference data
    dept_df = pd.DataFrame(DEPARTMENTS)
    dept_path = data_dir / 'departments.csv'
    dept_df.to_csv(dept_path, index=False)
    print(f"✓ Generated {len(dept_df)} departments → {dept_path}")

    # Save project reference data
    proj_df = pd.DataFrame(PROJECTS)
    proj_path = data_dir / 'projects.csv'
    proj_df.to_csv(proj_path, index=False)
    print(f"✓ Generated {len(proj_df)} projects → {proj_path}")

    print("\n" + "="*70)
    print("Sample data generated successfully!")
    print("="*70)
    print(f"Weekly costs: {len(weekly_df)} rows")
    print(f"Monthly costs: {len(monthly_df)} rows")
    print(f"Departments: {len(dept_df)} rows")
    print(f"Projects: {len(proj_df)} rows")
    print("\nYou can now run the application:")
    print("  python app.py")


if __name__ == '__main__':
    main()
