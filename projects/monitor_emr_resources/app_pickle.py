from flask import Flask, render_template, request, jsonify, send_file
import requests
import pandas as pd
from datetime import datetime, timedelta
import pickle
import io
import csv
import os
from collections import defaultdict

app = Flask(__name__)

# Path for persistent storage - using pickle
STATE_FILE = 'resource_state.pkl'


class ResourceStateManager:
    """Manages persistent state for max resource tracking using pickle"""
    
    def __init__(self, state_file=STATE_FILE):
        self.state_file = state_file
        self.state = self.load_state()
    
    def load_state(self):
        """Load state from pickle file"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                print(f"Error loading state from pickle: {e}")
        
        # Default state structure
        return {
            'cluster_max': {},  # cluster_id -> {max_memory, max_vcores, timestamp}
            'job_max': {}       # job_id -> {max_memory, max_vcores, cluster_id, timestamp}
        }
    
    def save_state(self):
        """Save state to pickle file"""
        try:
            with open(self.state_file, 'wb') as f:
                pickle.dump(self.state, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception as e:
            print(f"Error saving state to pickle: {e}")
    
    def update_cluster_max(self, cluster_id, memory_gb, vcores):
        """Update max resources for a cluster"""
        if cluster_id not in self.state['cluster_max']:
            self.state['cluster_max'][cluster_id] = {
                'max_memory_gb': memory_gb,
                'max_vcores': vcores,
                'first_seen': datetime.now(),
                'last_updated': datetime.now()
            }
        else:
            current = self.state['cluster_max'][cluster_id]
            updated = False
            
            if memory_gb > current['max_memory_gb']:
                current['max_memory_gb'] = memory_gb
                updated = True
            
            if vcores > current['max_vcores']:
                current['max_vcores'] = vcores
                updated = True
            
            if updated:
                current['last_updated'] = datetime.now()
        
        self.save_state()
    
    def update_job_max(self, job_id, cluster_id, memory_gb, vcores, job_name=None):
        """Update max resources for a job"""
        if job_id not in self.state['job_max']:
            self.state['job_max'][job_id] = {
                'max_memory_gb': memory_gb,
                'max_vcores': vcores,
                'cluster_id': cluster_id,
                'job_name': job_name or 'Unknown',
                'first_seen': datetime.now(),
                'last_updated': datetime.now()
            }
        else:
            current = self.state['job_max'][job_id]
            updated = False
            
            if memory_gb > current['max_memory_gb']:
                current['max_memory_gb'] = memory_gb
                updated = True
            
            if vcores > current['max_vcores']:
                current['max_vcores'] = vcores
                updated = True
            
            if updated:
                current['last_updated'] = datetime.now()
            
            # Update job name if it was unknown before
            if current.get('job_name') == 'Unknown' and job_name:
                current['job_name'] = job_name
        
        self.save_state()
    
    def get_cluster_max_stats(self):
        """Get max stats for all clusters"""
        return self.state['cluster_max']
    
    def get_job_max_stats(self):
        """Get max stats for all jobs"""
        return self.state['job_max']
    
    def clear_state(self):
        """Clear all state"""
        self.state = {
            'cluster_max': {},
            'job_max': {}
        }
        self.save_state()
    
    def clear_cluster_state(self, cluster_id):
        """Clear state for specific cluster"""
        if cluster_id in self.state['cluster_max']:
            del self.state['cluster_max'][cluster_id]
            self.save_state()
    
    def clear_job_state(self, job_id):
        """Clear state for specific job"""
        if job_id in self.state['job_max']:
            del self.state['job_max'][job_id]
            self.save_state()
    
    def export_state_to_json(self, filepath='resource_state_export.json'):
        """Export state to JSON for backup/inspection"""
        import json
        export_data = {
            'cluster_max': {},
            'job_max': {}
        }
        
        # Convert datetime objects to ISO format strings for JSON
        for cluster_id, stats in self.state['cluster_max'].items():
            export_data['cluster_max'][cluster_id] = {
                'max_memory_gb': stats['max_memory_gb'],
                'max_vcores': stats['max_vcores'],
                'first_seen': stats['first_seen'].isoformat(),
                'last_updated': stats['last_updated'].isoformat()
            }
        
        for job_id, stats in self.state['job_max'].items():
            export_data['job_max'][job_id] = {
                'max_memory_gb': stats['max_memory_gb'],
                'max_vcores': stats['max_vcores'],
                'cluster_id': stats['cluster_id'],
                'job_name': stats['job_name'],
                'first_seen': stats['first_seen'].isoformat(),
                'last_updated': stats['last_updated'].isoformat()
            }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return filepath


class JobResourceMonitor:
    def __init__(self, spark_history_url, yarn_rm_url, state_manager):
        self.spark_history_url = spark_history_url
        self.yarn_rm_url = yarn_rm_url
        self.state_manager = state_manager

    def get_running_jobs_detailed(self):
        """Get detailed information for currently running jobs"""
        try:
            url = f"{self.yarn_rm_url}/ws/v1/cluster/apps"
            params = {'states': 'RUNNING'}
            response = requests.get(url, params=params, timeout=10)
            apps = response.json().get('apps', {}).get('app', [])

            # Track current usage by cluster (queue)
            cluster_usage = defaultdict(lambda: {'memory': 0, 'vcores': 0})
            
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

                memory_gb = allocated_mb / 1024
                cluster_id = app.get('queue', 'default')
                job_id = app.get('id')
                job_name = app.get('name', 'Unknown')[:50]
                
                # Update cluster usage
                cluster_usage[cluster_id]['memory'] += memory_gb
                cluster_usage[cluster_id]['vcores'] += allocated_vcores
                
                # Update max tracking for this job
                self.state_manager.update_job_max(
                    job_id, cluster_id, memory_gb, allocated_vcores, job_name
                )

                job_info = {
                    'Job ID': job_id,
                    'Job Name': job_name,
                    'User': app.get('user'),
                    'Queue': cluster_id,
                    'App Type': app.get('applicationType'),
                    'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'Elapsed Time (mins)': round(elapsed_seconds / 60, 1),
                    'Memory (GB)': round(memory_gb, 2),
                    'vCores': allocated_vcores,
                    'Containers': running_containers,
                    'Progress (%)': round(progress, 1),
                    'Status': 'RUNNING',
                    'Memory-Hours': round(memory_gb * (elapsed_seconds / 3600), 2),
                    'vCore-Hours': round(allocated_vcores * (elapsed_seconds / 3600), 2)
                }
                running_jobs.append(job_info)
            
            # Update cluster max usage
            for cluster_id, usage in cluster_usage.items():
                self.state_manager.update_cluster_max(
                    cluster_id, usage['memory'], usage['vcores']
                )

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
                    memory_gb = max_memory_mb / 1024

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

                    job_name = app.get('name', 'Unknown')[:50]
                    
                    # Update max tracking for completed job (use app_id as cluster)
                    self.state_manager.update_job_max(
                        app_id, 'spark_history', memory_gb, total_cores, job_name
                    )

                    job_info = {
                        'Job ID': app_id,
                        'Job Name': job_name,
                        'User': app.get('sparkUser'),
                        'Submit Time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else 'Unknown',
                        'End Time': end_time.strftime('%Y-%m-%d %H:%M:%S') if end_time else 'Unknown',
                        'Duration (mins)': round(duration_ms / (1000 * 60), 1) if duration_ms else 0,
                        'Memory (GB)': round(memory_gb, 2),
                        'vCores': total_cores,
                        'Status': 'COMPLETED' if app.get('attempts', [{}])[0].get('completed', False) else 'FAILED',
                        'Memory-Hours': round(memory_gb * duration_hours, 2),
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
                        return pd.to_datetime(time_str[:19], format='%Y-%m-%d %H:%M:%S')
                    return pd.to_datetime(time_str)
                return pd.to_datetime(time_str)
            except Exception:
                return pd.NaT

        df['submit_dt'] = df['Submit Time'].apply(safe_datetime_convert)
        df = df.dropna(subset=['submit_dt'])

        if df.empty:
            return pd.DataFrame()

        df['submit_hour'] = df['submit_dt'].dt.floor('H')

        # Group by hour
        hourly_agg = df.groupby('submit_hour').agg({
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
            'Total vCores', 'Avg vCores', 'Max vCores', 'Avg Duration (mins)',
            'Max Duration (mins)', 'Total Memory-Hours', 'Total vCore-Hours', 'Unique Users'
        ]

        hourly_agg = hourly_agg.reset_index()
        hourly_agg['Submit Hour'] = hourly_agg['submit_hour'].dt.strftime('%Y-%m-%d %H:00')
        hourly_agg = hourly_agg.drop('submit_hour', axis=1)

        # Reorder columns
        cols = ['Submit Hour'] + [col for col in hourly_agg.columns if col != 'Submit Hour']
        hourly_agg = hourly_agg[cols]

        return hourly_agg.sort_values('Submit Hour', ascending=False)


# Global state manager
state_manager = ResourceStateManager()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/running_jobs')
def running_jobs():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')

    monitor = JobResourceMonitor(spark_url, yarn_url, state_manager)
    df = monitor.get_running_jobs_detailed()

    if df.empty:
        return jsonify({
            'data': [],
            'columns': [],
            'summary': {
                'total_jobs': 0,
                'total_memory_gb': 0,
                'total_vcores': 0,
                'total_containers': 0
            }
        })

    summary = {
        'total_jobs': len(df),
        'total_memory_gb': round(df['Memory (GB)'].sum(), 2),
        'total_vcores': int(df['vCores'].sum()),
        'total_containers': int(df['Containers'].sum())
    }

    return jsonify({
        'data': df.to_dict('records'),
        'columns': df.columns.tolist(),
        'summary': summary
    })


@app.route('/completed_jobs')
def completed_jobs():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')
    limit = int(request.args.get('limit', 100))

    monitor = JobResourceMonitor(spark_url, yarn_url, state_manager)
    df = monitor.get_completed_jobs_detailed(limit)

    if df.empty:
        return jsonify({'data': [], 'columns': [], 'summary': {}})

    summary = {
        'total_jobs': len(df),
        'completed': len(df[df['Status'] == 'COMPLETED']),
        'failed': len(df[df['Status'] == 'FAILED']),
        'total_memory_hours': round(df['Memory-Hours'].sum(), 2),
        'total_vcore_hours': round(df['vCore-Hours'].sum(), 2)
    }

    return jsonify({
        'data': df.to_dict('records'),
        'columns': df.columns.tolist(),
        'summary': summary
    })


@app.route('/hourly_aggregation')
def hourly_aggregation():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')

    monitor = JobResourceMonitor(spark_url, yarn_url, state_manager)
    completed_df = monitor.get_completed_jobs_detailed(200)
    hourly_df = monitor.get_aggregated_by_job_submission(completed_df)

    if hourly_df.empty:
        return jsonify({'data': [], 'columns': [], 'summary': {}})

    summary = {
        'total_hours': len(hourly_df),
        'total_jobs': int(hourly_df['Job Count'].sum()),
        'avg_jobs_per_hour': round(hourly_df['Job Count'].mean(), 1),
        'peak_memory_gb': round(hourly_df['Total Memory (GB)'].max(), 2),
        'peak_vcores': int(hourly_df['Total vCores'].max())
    }

    return jsonify({
        'data': hourly_df.to_dict('records'),
        'columns': hourly_df.columns.tolist(),
        'summary': summary
    })


@app.route('/cluster_max_stats')
def cluster_max_stats():
    """Get maximum resource usage by cluster"""
    cluster_stats = state_manager.get_cluster_max_stats()
    
    data = []
    for cluster_id, stats in cluster_stats.items():
        data.append({
            'Cluster ID': cluster_id,
            'Max Memory (GB)': round(stats['max_memory_gb'], 2),
            'Max vCores': stats['max_vcores'],
            'First Seen': stats['first_seen'].isoformat(),
            'Last Updated': stats['last_updated'].isoformat()
        })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('Max Memory (GB)', ascending=False)
    
    return jsonify({
        'data': df.to_dict('records') if not df.empty else [],
        'columns': df.columns.tolist() if not df.empty else []
    })


@app.route('/job_max_stats')
def job_max_stats():
    """Get maximum resource usage by job"""
    job_stats = state_manager.get_job_max_stats()
    
    data = []
    for job_id, stats in job_stats.items():
        data.append({
            'Job ID': job_id,
            'Job Name': stats['job_name'],
            'Cluster ID': stats['cluster_id'],
            'Max Memory (GB)': round(stats['max_memory_gb'], 2),
            'Max vCores': stats['max_vcores'],
            'First Seen': stats['first_seen'].isoformat(),
            'Last Updated': stats['last_updated'].isoformat()
        })
    
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values('Max Memory (GB)', ascending=False)
    
    return jsonify({
        'data': df.to_dict('records') if not df.empty else [],
        'columns': df.columns.tolist() if not df.empty else []
    })


@app.route('/clear_state', methods=['POST'])
def clear_state():
    """Clear all state or specific items"""
    data = request.json or {}
    action = data.get('action', 'all')
    
    if action == 'all':
        state_manager.clear_state()
        return jsonify({'success': True, 'message': 'All state cleared'})
    elif action == 'cluster':
        cluster_id = data.get('cluster_id')
        if cluster_id:
            state_manager.clear_cluster_state(cluster_id)
            return jsonify({'success': True, 'message': f'Cluster {cluster_id} state cleared'})
    elif action == 'job':
        job_id = data.get('job_id')
        if job_id:
            state_manager.clear_job_state(job_id)
            return jsonify({'success': True, 'message': f'Job {job_id} state cleared'})
    
    return jsonify({'success': False, 'message': 'Invalid action'})


@app.route('/export_state')
def export_state():
    """Export pickle state to JSON for inspection"""
    try:
        filepath = state_manager.export_state_to_json()
        return send_file(
            filepath,
            mimetype='application/json',
            as_attachment=True,
            download_name='resource_state_export.json'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/job_summary')
def job_summary():
    spark_url = request.args.get('spark_url', 'http://your-master-node:18080')
    yarn_url = request.args.get('yarn_url', 'http://your-master-node:8088')

    monitor = JobResourceMonitor(spark_url, yarn_url, state_manager)

    running_df = monitor.get_running_jobs_detailed()
    completed_df = monitor.get_completed_jobs_detailed(200)

    all_jobs = []

    if not running_df.empty:
        running_summary = running_df.copy()
        running_summary['Job Type'] = 'RUNNING'
        if 'End Time' not in running_summary.columns:
            running_summary['End Time'] = 'N/A'
        if 'Duration (mins)' not in running_summary.columns:
            running_summary['Duration (mins)'] = running_summary['Elapsed Time (mins)']
        if 'Progress (%)' not in running_summary.columns:
            running_summary['Progress (%)'] = 0.0
        if 'Containers' not in running_summary.columns:
            running_summary['Containers'] = 0
        all_jobs.append(running_summary)

    if not completed_df.empty:
        completed_summary = completed_df.copy()
        completed_summary['Job Type'] = completed_summary['Status']
        if 'Elapsed Time (mins)' not in completed_summary.columns:
            completed_summary['Elapsed Time (mins)'] = completed_summary['Duration (mins)']
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

    monitor = JobResourceMonitor(spark_url, yarn_url, state_manager)

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
    elif data_type == 'cluster_max':
        cluster_stats = state_manager.get_cluster_max_stats()
        data = []
        for cluster_id, stats in cluster_stats.items():
            data.append({
                'Cluster ID': cluster_id,
                'Max Memory (GB)': round(stats['max_memory_gb'], 2),
                'Max vCores': stats['max_vcores'],
                'First Seen': stats['first_seen'].isoformat(),
                'Last Updated': stats['last_updated'].isoformat()
            })
        df = pd.DataFrame(data)
        filename = 'cluster_max_resources.csv'
    elif data_type == 'job_max':
        job_stats = state_manager.get_job_max_stats()
        data = []
        for job_id, stats in job_stats.items():
            data.append({
                'Job ID': job_id,
                'Job Name': stats['job_name'],
                'Cluster ID': stats['cluster_id'],
                'Max Memory (GB)': round(stats['max_memory_gb'], 2),
                'Max vCores': stats['max_vcores'],
                'First Seen': stats['first_seen'].isoformat(),
                'Last Updated': stats['last_updated'].isoformat()
            })
        df = pd.DataFrame(data)
        filename = 'job_max_resources.csv'
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
