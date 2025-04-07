import boto3
import zipfile
from io import BytesIO
import time


def fetch_cloudwatch_logs_for_command(command_id):
    """
    Fetches CloudWatch logs related to an SSM command execution and returns them as a zip file.

    Args:
        command_id: The SSM command ID to fetch logs for

    Returns:
        BytesIO object containing the zipped logs
    """
    # Initialize AWS clients
    ssm_client = boto3.client('ssm')
    logs_client = boto3.client('logs')
    logs_zip = BytesIO()

    # First, get command invocation details to find the instance IDs
    try:
        command_result = ssm_client.list_command_invocations(
            CommandId=command_id,
            Details=True
        )

        invocations = command_result.get('CommandInvocations', [])
        if not invocations:
            raise Exception(f"No invocations found for command {command_id}")

        with zipfile.ZipFile(logs_zip, 'w') as zip_file:
            for invocation in invocations:
                instance_id = invocation.get('InstanceId')
                invocation_id = invocation.get('CommandId')

                # The log stream follows a pattern based on instance ID and command ID
                log_group = '/aws/ssm/AWS-RunShellScript'
                # Note: this pattern might vary slightly based on your AWS setup
                log_stream_pattern = f"{instance_id}/{invocation_id}"

                # List log streams that match our pattern
                streams_response = logs_client.describe_log_streams(
                    logGroupName=log_group,
                    logStreamNamePrefix=instance_id
                )

                for stream in streams_response.get('logStreams', []):
                    stream_name = stream.get('logStreamName')

                    # Check if this stream is related to our command
                    if invocation_id in stream_name:
                        # Get the log events
                        events_response = logs_client.get_log_events(
                            logGroupName=log_group,
                            logStreamName=stream_name,
                            startFromHead=True
                        )

                        stdout_log = []
                        stderr_log = []

                        # Categorize events as stdout or stderr
                        for event in events_response.get('events', []):
                            message = event.get('message', '')
                            timestamp = event.get('timestamp', int(time.time() * 1000))

                            if 'stdout' in message.lower():
                                stdout_log.append(f"[{timestamp}] {message}")
                            elif 'stderr' in message.lower():
                                stderr_log.append(f"[{timestamp}] {message}")

                        # Write logs to zip file
                        if stdout_log:
                            zip_file.writestr(f"{instance_id}_stdout.log", "\n".join(stdout_log))
                        if stderr_log:
                            zip_file.writestr(f"{instance_id}_stderr.log", "\n".join(stderr_log))

        logs_zip.seek(0)
        return logs_zip

    except Exception as e:
        # Handle specific exceptions based on your requirements
        print(f"Error fetching logs for command {command_id}: {str(e)}")
        # Create a zip with error information
        with zipfile.ZipFile(logs_zip, 'w') as zip_file:
            zip_file.writestr("error.log", f"Failed to fetch logs: {str(e)}")
        logs_zip.seek(0)
        return logs_zip


# Example usage in a Flask route
"""
@app.route('/download/<command_id>')
def download_logs(command_id):
    logs_zip = fetch_cloudwatch_logs_for_command(command_id)
    return send_file(
        logs_zip,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'command_logs_{command_id}.zip'
    )
"""