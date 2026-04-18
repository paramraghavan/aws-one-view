#!/usr/bin/env python
"""
Example Job Script
This is an example of a script that can be called from callback_myjob()

Usage:
    python scripts/example_job.py --input /path/to/file --env dev

In callback_myjob(), call it like:
    from job_runner import run_python_script
    exit_code = run_python_script(
        "./scripts/example_job.py",
        args=["--input", file_path, "--env", environment]
    )
"""

import argparse
import time
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Example job script')
    parser.add_argument('--input', required=True, help='Input file path')
    parser.add_argument('--env', required=True, help='Environment')
    args = parser.parse_args()

    file_path = args.input
    env = args.env
    password = os.getenv('JOB_PASSWORD', 'no-password-provided')

    print(f"Example Job Starting")
    print(f"  Input: {file_path}")
    print(f"  Environment: {env}")
    print(f"  Password set: {password != 'no-password-provided'}")
    print()

    # Check if file exists
    if not os.path.exists(file_path):
        print(f"❌ ERROR: File not found: {file_path}")
        return 1

    file_size = os.path.getsize(file_path)
    print(f"File Info:")
    print(f"  Size: {file_size} bytes")
    print(f"  Name: {Path(file_path).name}")
    print()

    # Simulate processing
    print("Processing...")
    for i in range(5):
        print(f"  Step {i+1}/5: Processing...")
        time.sleep(0.5)

    print()
    print("✓ Job completed successfully!")
    return 0


if __name__ == '__main__':
    exit(main())
