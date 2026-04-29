#!/usr/bin/env python3
"""
Split combined costs CSV into separate monthly files

Takes costs_raw.csv (all months) and creates individual files:
  - costs_2025_01.csv
  - costs_2025_02.csv
  - costs_2025_03.csv
  ... etc

Usage:
    python3 split_costs_by_month.py [--input costs_raw.csv] [--output-dir .]
"""

import pandas as pd
import os
from pathlib import Path
import argparse

def split_by_month(input_file, output_dir='.'):
    """Split CSV by month into separate files"""

    # Load data
    if not os.path.exists(input_file):
        print(f"✗ Error: {input_file} not found")
        print(f"  Run: bash run_chargeback.sh real csv")
        return False

    df = pd.read_csv(input_file)

    if 'Month' not in df.columns:
        print(f"✗ Error: 'Month' column not found in {input_file}")
        return False

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(" SPLIT COSTS BY MONTH")
    print(f"{'='*70}\n")

    print(f"Input file: {input_file}")
    print(f"Output directory: {output_dir}")
    print(f"Total rows: {len(df)}")
    print(f"Date range: {df['Month'].min()} to {df['Month'].max()}\n")

    # Get unique months
    months = sorted(df['Month'].unique())
    print(f"Creating {len(months)} monthly files...\n")

    files_created = []
    total_cost = 0

    # Split by month
    for month in months:
        month_df = df[df['Month'] == month].copy()

        # Create filename: costs_2025_01.csv
        filename = f"costs_{month.replace('-', '_')}.csv"
        filepath = output_dir / filename

        # Save to CSV
        month_df.to_csv(filepath, index=False)

        # Get statistics
        rows = len(month_df)
        cost = month_df['FairshareValue'].sum()
        total_cost += cost

        files_created.append({
            'month': month,
            'filename': filename,
            'rows': rows,
            'cost': cost
        })

        print(f"  ✓ {filename:<25} {rows:>3} rows  ${cost:>12,.2f}")

    print(f"\n{'='*70}")
    print(" SUMMARY")
    print(f"{'='*70}\n")

    print(f"Files created: {len(files_created)}")
    print(f"Total cost (all months): ${total_cost:,.2f}")
    print(f"\nMonthly breakdown:")

    for item in files_created:
        print(f"  {item['month']}: ${item['cost']:>12,.2f}")

    print(f"\nFiles saved to: {output_dir}/")
    print(f"\nUsage:")
    print(f"  View a specific month:  head costs_2025_01.csv")
    print(f"  Import to Excel:        open costs_*.csv")
    print(f"  Archive:                tar -czf costs_monthly.tar.gz costs_*.csv")

    return True

def main():
    parser = argparse.ArgumentParser(
        description='Split combined costs CSV into monthly files'
    )
    parser.add_argument(
        '--input',
        default='costs_raw.csv',
        help='Input CSV file (default: costs_raw.csv)'
    )
    parser.add_argument(
        '--output-dir',
        default='.',
        help='Output directory for monthly files (default: current directory)'
    )

    args = parser.parse_args()

    success = split_by_month(args.input, args.output_dir)

    if not success:
        exit(1)

    print("\n✓ Split complete!\n")

if __name__ == '__main__':
    main()
