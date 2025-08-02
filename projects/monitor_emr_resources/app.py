from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime, timedelta
import json
import io
import csv

app = Flask(__name__)


class JobResourceMonitor:
    def __init__(self, spark_history_url, yarn_rm_url):
        self.spark_history_url = spark_history_url
        self.yarn_rm_url = yarn_rm_url

    def get_running_jobs_detailed(self):
        """Get detailed information for currently running jobs"""
        try:
            url = f"{self.yarn_rm_url}/ws/v1/cluster/apps"
            params = {'states': 'RUNNING'}
            response = requests.get(url, params=params, timeout=10)
            apps = response.json().get('apps', {}).get('app', [])

            running_jobs = []
            for app in apps:
                started_time = app.get('startedTime', 0)
                elapsed_time = app.get('elapsedTime', 0)

                # Handle string timestamps and convert to int
                try:
                    started_time = int(started_time) if started_time else 0
                    elapsed_time = int(elapsed_time) if elapsed_time else 0
                except (ValueError, TypeError):
                    started_time = 0
                    elapsed_time = 0

                start_time = datetime.fromtimestamp(started_time / 1000) if started_time > 0 else datetime.now()
                elapsed_seconds = elapsed_time / 1000

                # Safe conversion of numeric fields
                try:
                    allocated_mb = float(app.get('allocatedMB', 0))
                    allocated_vcores = int(app.get('allocatedVCores', 0))
                    running_containers = int(app.get('runningContainers', 0))
                    progress = float(app.get('progress', 0))
                except (ValueError, TypeError):
                    allocated_mb = 0
                    allocated_vcores = 0
                    running_containers = 0
                    progress = 0

                job_info = {
                    'Job ID': app.get('id'),
                    'Job Name': app.get('name', 'Unknown')[:50],  # Truncate long names
                    'User': app.get('user'),
                    'Queue': app.get('queue'),
                    'App Type': app.get('applicationType'),
                    'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Elapsed Time (mins)': round(elapsed_seconds / 60, 1),
                    'Memory (GB)': round(allocated_mb / 1024, 2),
                    'vCores': allocated_vcores,
                    'Containers': running_containers,
                    'Progress (%)': round(progress, 1),
                    'Status': 'RUNNING',
                    'Memory-Hours': round((allocated_mb / 1024) * (elapsed_seconds / 3600), 2),
                    'vCore-Hours': round(allocated_vcores * (elapsed_seconds / 3600), 2)
                }
                running_jobs.append(job_info)

            return pd.DataFrame(running_jobs)
        except Exception as e:
            print(f"Error fetching running jobs: {e}")
            return pd.DataFrame()

    def get_completed_jobs_detailed(self, limit=100):
        """Get detailed information for completed Spark jobs"""
        try:
            url = f"{self.spark_history_url}/api/v1/applications"
            params = {'limit': limit}
            response = requests.get(url, params=params, timeout=10)
            apps = response.json()

            completed_jobs = []
            for app in apps:
                app_id = app['id']

                try:
                    # Get executor information
                    executors_url = f"{self.spark_history_url}/api/v1/applications/{app_id}/executors"
                    executors_response = requests.get(executors_url, timeout=5)
                    executors = executors_response.json()

                    # Calculate metrics with safe type conversion
                    total_cores = 0
                    max_memory_mb = 0

                    for ex in executors:
                        try:
                            cores = int(ex.get('totalCores', 0))
                            memory = int(ex.get('maxMemory', 0))
                            total_cores += cores
                            max_memory_mb += memory
                        except (ValueError, TypeError):
                            continue

                    max_memory_mb = max_memory_mb // (1024 * 1024)  # Convert bytes to MB

                    # Time calculations with safe conversion
                    start_time_ms = app.get('attempts', [{}])[0].get('startTime', 0)
                    end_time_ms = app.get('attempts', [{}])[0].get('endTime', 0)
                    duration_ms = app.get('attempts', [{}])[0].get('duration', 0)

                    try:
                        start_time_ms = int(start_time_ms) if start_time_ms else 0
                        end_time_ms = int(end_time_ms) if end_time_ms else 0
                        duration_ms = int(duration_ms) if duration_ms else 0
                    except (ValueError, TypeError):
                        start_time_ms = 0
                        end_time_ms = 0
                        duration_ms = 0

                    start_time = datetime.fromtimestamp(start_time_ms / 1000) if start_time_ms > 0 else None
                    end_time = datetime.fromtimestamp(end_time_ms / 1000) if end_time_ms > 0 else None
                    duration_hours = duration_ms / (1000 * 60 * 60) if duration_ms > 0 else 0

                    job_info = {
                        'Job ID': app_id,
                        'Job Name': app.get('name', 'Unknown')[:50],
                        'User': app.get('sparkUser'),
                        'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'Unknown',
                        'End Time': end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'Unknown',
                        'Duration (mins)': round(duration_ms / (1000 * 60), 1) if duration_ms else 0,
                        'Memory (GB)': round(max_memory_mb / 1024, 2),
                        'vCores': total_cores,
                        'Status': 'COMPLETED' if app.get('attempts', [{}])[0].get('completed', False) else 'FAILED',
                        'Memory-Hours': round((max_memory_mb / 1024) * duration_hours, 2),
                        'vCore-Hours': round(total_cores * duration_hours, 2)
                    }
                    completed_jobs.append(job_info)

                except Exception as e:
                    # For failed requests, add minimal info with safe conversions
                    start_time_ms = app.get('attempts', [{}])[0].get('startTime', 0)
                    try:
                        start_time_ms = int(start_time_ms) if start_time_ms else 0
                        start_time = datetime.fromtimestamp(start_time_ms / 1000) if start_time_ms > 0 else None
                    except (ValueError, TypeError):
                        start_time = None

                    job_info = {
                        'Job ID': app_id,
                        'Job Name': app.get('name', 'Unknown')[:50],
                        'User': app.get('sparkUser', 'Unknown'),
                        'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'Unknown',
                        'End Time': 'Error',
                        'Duration (mins)': 0,
                        'Memory (GB)': 0,
                        'vCores': 0,
                        'Status': 'ERROR',
                        'Memory-Hours': 0,
                        'vCore-Hours': 0
                    }
                    completed_jobs.append(job_info)
                    continue

            return pd.DataFrame(completed_jobs)
        except Exception as e:
            print(f"Error fetching completed jobs: {e}")
            return pd.DataFrame()

    def get_aggregated_by_job_submission(self, df, time_window_hours=24):
        """Aggregate jobs by submission time windows"""
        if df.empty:
            return pd.DataFrame()

        # Safe datetime conversion
        def safe_datetime_convert(time_str):
            if pd.isna(time_str) or time_str == 'Unknown' or time_str == 'Error':
                return pd.NaT

            try:
                # Try different datetime formats
                if isinstance(time_str, str):
                    # Format: "2024-01-01 10:30:00"
                    if len(time_str) >= 19:
                        return pd.to_datetime(time_str, format='%Y-%m-%d %H:%M:%S', errors='coerce')
                    else:
                        return pd.to_datetime(time_str, errors='coerce')
                else:
                    return pd.to_datetime(time_str, errors='coerce')
            except:
                return pd.NaT

        # Convert submit time to datetime with error handling
        df['Submit DateTime'] = df['Submit Time'].apply(safe_datetime_convert)

        # Remove rows with invalid dates
        df = df.dropna(subset=['Submit DateTime'])

        if df.empty:
            return pd.DataFrame()

        # Create time windows (hourly aggregation)
        df['Submit Hour'] = df['Submit DateTime'].dt.floor('H')

        # Aggregate by hour
        hourly_agg = df.groupby('Submit Hour').agg({
            'Job ID': 'count',
            'Memory (GB)': ['sum', 'mean', 'max'],
            'vCores': ['sum', 'mean', 'max'],
            'Duration (mins)': ['mean', 'max'],
            'Memory-Hours': 'sum',
            'vCore-Hours': 'sum',
            'User': lambda x: len(x.unique())
        }).round(2)

        # Flatten column names
        hourly_agg.columns = [
            'Job Count', 'Total Memory (GB)', 'Avg Memory (GB)', 'Max Memory (GB)',
            'Total vCores', 'Avg vCores', 'Max vCores',
            'Avg Duration (mins)', 'Max Duration (mins)',
            'Total Memory-Hours', 'Total vCore-Hours', 'Unique Users'
        ]

        # Reset index to make Submit Hour a column
        hourly_agg = hourly_agg.reset_index()
        hourly_agg['Submit Hour'] = hourly_agg['Submit Hour'].dt.strftime('%Y-%m-%d %H:00')

        return hourly_agg.sort_values('Submit Hour', ascending=False)


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/running-jobs')
def get_running_jobs():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')

    monitor = JobResourceMonitor(spark_url, yarn_url)
    df = monitor.get_running_jobs_detailed()

    if df.empty:
        return jsonify({'data': [], 'summary': {}})

    # Calculate summary metrics
    summary = {
        'total_jobs': len(df),
        'total_memory': round(df['Memory (GB)'].sum(), 1),
        'total_vcores': df['vCores'].sum(),
        'total_containers': df['Containers'].sum()
    }

    return jsonify({
        'data': df.to_dict('records'),
        'summary': summary,
        'columns': df.columns.tolist()
    })


@app.route('/api/completed-jobs')
def get_completed_jobs():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')
    limit = int(request.args.get('limit', 200))

    monitor = JobResourceMonitor(spark_url, yarn_url)
    df = monitor.get_completed_jobs_detailed(limit)

    if df.empty:
        return jsonify({'data': [], 'summary': {}})

    # Calculate summary metrics
    total_memory_hours = df['Memory-Hours'].sum()
    total_vcore_hours = df['vCore-Hours'].sum()
    success_rate = (df['Status'] == 'COMPLETED').mean() * 100

    summary = {
        'total_jobs': len(df),
        'total_memory_hours': round(total_memory_hours, 1),
        'total_vcore_hours': round(total_vcore_hours, 1),
        'success_rate': round(success_rate, 1)
    }

    return jsonify({
        'data': df.to_dict('records'),
        'summary': summary,
        'columns': df.columns.tolist()
    })


@app.route('/api/hourly-aggregation')
def get_hourly_aggregation():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')

    monitor = JobResourceMonitor(spark_url, yarn_url)
    completed_df = monitor.get_completed_jobs_detailed(200)

    if completed_df.empty:
        return jsonify({'data': [], 'summary': {}})

    hourly_agg = monitor.get_aggregated_by_job_submission(completed_df)

    if hourly_agg.empty:
        return jsonify({'data': [], 'summary': {}})

    # Calculate summary statistics
    summary = {
        'peak_hour_jobs': hourly_agg.loc[hourly_agg['Job Count'].idxmax(), 'Submit Hour'],
        'peak_hour_memory': hourly_agg.loc[hourly_agg['Total Memory (GB)'].idxmax(), 'Submit Hour'],
        'peak_hour_vcores': hourly_agg.loc[hourly_agg['Total vCores'].idxmax(), 'Submit Hour'],
        'avg_jobs_per_hour': round(hourly_agg['Job Count'].mean(), 1),
        'avg_memory_per_hour': round(hourly_agg['Total Memory (GB)'].mean(), 1),
        'avg_vcores_per_hour': round(hourly_agg['Total vCores'].mean(), 1)
    }

    return jsonify({
        'data': hourly_agg.to_dict('records'),
        'summary': summary,
        'columns': hourly_agg.columns.tolist()
    })


@app.route('/api/job-summary')
def get_job_summary():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')

    monitor = JobResourceMonitor(spark_url, yarn_url)
    running_df = monitor.get_running_jobs_detailed()
    completed_df = monitor.get_completed_jobs_detailed(200)

    all_jobs = []

    if not running_df.empty:
        running_summary = running_df.copy()
        running_summary['Job Type'] = 'RUNNING'
        if 'End Time' not in running_summary.columns:
            running_summary['End Time'] = 'Still Running'
        if 'Duration (mins)' not in running_summary.columns:
            running_summary['Duration (mins)'] = running_summary.get('Elapsed Time (mins)', 0)
        all_jobs.append(running_summary)

    if not completed_df.empty:
        completed_summary = completed_df.copy()
        completed_summary['Job Type'] = 'COMPLETED'
        if 'Elapsed Time (mins)' not in completed_summary.columns:
            completed_summary['Elapsed Time (mins)'] = completed_summary.get('Duration (mins)', 0)
        if 'Progress (%)' not in completed_summary.columns:
            completed_summary['Progress (%)'] = 100.0
        if 'Containers' not in completed_summary.columns:
            completed_summary['Containers'] = 0
        all_jobs.append(completed_summary)

    if not all_jobs:
        return jsonify({'data': [], 'summary': {}})

    try:
        # Align columns before concatenating
        if len(all_jobs) > 1:
            all_columns = set()
            for df in all_jobs:
                all_columns.update(df.columns)

            for i, df in enumerate(all_jobs):
                for col in all_columns:
                    if col not in df.columns:
                        if col in ['Memory (GB)', 'Memory-Hours', 'vCore-Hours']:
                            df[col] = 0.0
                        elif col in ['vCores', 'Containers']:
                            df[col] = 0
                        elif col in ['Progress (%)', 'Duration (mins)', 'Elapsed Time (mins)']:
                            df[col] = 0.0
                        else:
                            df[col] = 'N/A'
                all_jobs[i] = df

        combined_df = pd.concat(all_jobs, ignore_index=True, sort=False)

        # Clean and ensure proper data types
        numeric_columns = ['Memory (GB)', 'vCores', 'Memory-Hours', 'vCore-Hours']
        for col in numeric_columns:
            if col in combined_df.columns:
                combined_df[col] = pd.to_numeric(combined_df[col], errors='coerce').fillna(0)

        # Handle Duration columns
        if 'Duration (mins)' in combined_df.columns and 'Elapsed Time (mins)' in combined_df.columns:
            combined_df['Effective Duration (mins)'] = combined_df.apply(
                lambda row: row['Elapsed Time (mins)'] if row['Job Type'] == 'RUNNING' else row['Duration (mins)'],
                axis=1
            )
        elif 'Duration (mins)' in combined_df.columns:
            combined_df['Effective Duration (mins)'] = combined_df['Duration (mins)']
        elif 'Elapsed Time (mins)' in combined_df.columns:
            combined_df['Effective Duration (mins)'] = combined_df['Elapsed Time (mins)']
        else:
            combined_df['Effective Duration (mins)'] = 0

        combined_df['Effective Duration (mins)'] = pd.to_numeric(
            combined_df['Effective Duration (mins)'], errors='coerce'
        ).fillna(0)

        # Remove invalid job names
        combined_df = combined_df.dropna(subset=['Job Name'])
        combined_df = combined_df[combined_df['Job Name'].str.strip() != '']
        combined_df = combined_df[combined_df['Job Name'] != 'Unknown']

        if combined_df.empty:
            return jsonify({'data': [], 'summary': {}})

        # Job aggregation
        agg_dict = {
            'Job ID': 'count',
            'User': lambda x: ', '.join(x.dropna().unique()[:5])
        }

        if 'Memory (GB)' in combined_df.columns:
            agg_dict['Memory (GB)'] = ['sum', 'mean', 'max']
        if 'vCores' in combined_df.columns:
            agg_dict['vCores'] = ['sum', 'mean', 'max']
        if 'Memory-Hours' in combined_df.columns:
            agg_dict['Memory-Hours'] = 'sum'
        if 'vCore-Hours' in combined_df.columns:
            agg_dict['vCore-Hours'] = 'sum'
        if 'Effective Duration (mins)' in combined_df.columns:
            agg_dict['Effective Duration (mins)'] = 'mean'

        job_summary = combined_df.groupby('Job Name').agg(agg_dict).round(2)

        # Flatten column names
        new_columns = []
        for col in job_summary.columns:
            if isinstance(col, tuple):
                if col[1] == 'sum' and col[0] == 'Memory (GB)':
                    new_columns.append('Total Memory (GB)')
                elif col[1] == 'mean' and col[0] == 'Memory (GB)':
                    new_columns.append('Avg Memory (GB)')
                elif col[1] == 'max' and col[0] == 'Memory (GB)':
                    new_columns.append('Max Memory (GB)')
                elif col[1] == 'sum' and col[0] == 'vCores':
                    new_columns.append('Total vCores')
                elif col[1] == 'mean' and col[0] == 'vCores':
                    new_columns.append('Avg vCores')
                elif col[1] == 'max' and col[0] == 'vCores':
                    new_columns.append('Max vCores')
                elif col[1] == 'sum' and col[0] == 'Memory-Hours':
                    new_columns.append('Total Memory-Hours')
                elif col[1] == 'sum' and col[0] == 'vCore-Hours':
                    new_columns.append('Total vCore-Hours')
                elif col[1] == 'mean' and col[0] == 'Effective Duration (mins)':
                    new_columns.append('Avg Duration (mins)')
                else:
                    new_columns.append(f"{col[0]} {col[1]}")
            else:
                if col == 'Job ID':
                    new_columns.append('Total Runs')
                else:
                    new_columns.append(col)

        job_summary.columns = new_columns

        # Add job type breakdown
        try:
            job_types = combined_df.groupby(['Job Name', 'Job Type']).size().unstack(fill_value=0)
            job_summary = job_summary.join(job_types, how='left').fillna(0)
        except Exception:
            pass

        # Sort by total resource usage
        sort_column = 'Total Memory-Hours'
        if sort_column not in job_summary.columns:
            if 'Total Memory (GB)' in job_summary.columns:
                sort_column = 'Total Memory (GB)'
            elif 'Total Runs' in job_summary.columns:
                sort_column = 'Total Runs'
            else:
                sort_column = job_summary.columns[0]

        job_summary = job_summary.sort_values(sort_column, ascending=False)

        return jsonify({
            'data': job_summary.reset_index().to_dict('records'),
            'columns': job_summary.reset_index().columns.tolist()
        })

    except Exception as e:
        print(f"Error in job summary: {e}")
        return jsonify({'data': [], 'summary': {}})


@app.route('/download/<data_type>')
def download_csv(data_type):
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')

    monitor = JobResourceMonitor(spark_url, yarn_url)

    if data_type == 'running':
        df = monitor.get_running_jobs_detailed()
        filename = 'running_jobs.csv'
    elif data_type == 'completed':
        df = monitor.get_completed_jobs_detailed(200)
        filename = 'completed_jobs.csv'
    elif data_type == 'hourly':
        completed_df = monitor.get_completed_jobs_detailed(200)
        df = monitor.get_aggregated_by_job_submission(completed_df)
        filename = 'hourly_aggregation.csv'
    else:
        return "Invalid data type", 400

    if df.empty:
        return "No data available", 404

    # Create CSV in memory
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)

    # Convert to BytesIO for send_file
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8'))
    mem.seek(0)

    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)