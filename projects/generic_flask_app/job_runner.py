"""
Helper module to run external Python scripts and capture their output.
All print statements automatically appear in the browser.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_python_script(script_path: str, args: list = None, password: str = None):
    """
    Run an external Python script and capture its output.
    All print() statements appear in browser automatically.

    Args:
        script_path: Path to the Python script (e.g., "./scripts/my_job.py")
        args: List of arguments to pass to the script
        password: Password (accessible via os.getenv('JOB_PASSWORD') in script)

    Returns:
        exit_code: The script's exit code (0 = success)

    Example:
        exit_code = run_python_script(
            "./scripts/data_ingest.py",
            args=["--input", "/path/to/file"],
            password=password
        )
        if exit_code != 0:
            print(f"Script failed with exit code {exit_code}")
    """

    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    print(f"📌 Running: {' '.join(cmd)}")
    print(f"📂 Working directory: {Path.cwd()}")
    print()

    # Prepare environment
    env = os.environ.copy()
    if password:
        env['JOB_PASSWORD'] = password

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr to stdout
            text=True,
            bufsize=1,  # Line buffered
            env=env
        )

        # Read output line by line (automatically goes to buffer)
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())

        process.wait()
        return process.returncode

    except FileNotFoundError:
        print(f"❌ ERROR: Script not found: {script_path}")
        return 1
    except Exception as e:
        print(f"❌ ERROR: Failed to run script: {e}")
        return 1


def run_shell_command(command: str):
    """
    Run a shell command and capture its output.

    Args:
        command: Shell command to run

    Returns:
        exit_code: Command exit code

    Example:
        run_shell_command('aws s3 ls')
    """

    print(f"📌 Running: {command}")
    print()

    try:
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())

        process.wait()
        return process.returncode

    except Exception as e:
        print(f"❌ ERROR: Failed to run command: {e}")
        return 1


# Example usage in callback_myjob:
"""
def callback_myjob(password: str, files: list):
    from job_runner import run_python_script

    print(f"Processing {len(files)} files")

    for idx, file_path in enumerate(files, 1):
        print(f"[{idx}/{len(files)}] Processing: {file_path}")

        # Call external script
        exit_code = run_python_script(
            "./scripts/my_job.py",
            args=["--input", file_path],
            password=password
        )

        if exit_code != 0:
            print(f"  ⚠️ Script failed with exit code {exit_code}")
        else:
            print(f"  ✓ Successfully processed")

    print("✅ All files completed")
"""
