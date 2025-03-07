from flask import Flask, request, render_template, send_file, jsonify
import boto3
from datetime import datetime, timedelta
import pytz
from io import BytesIO
import zipfile
from botocore.config import Config
import atexit
import signal
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__, static_url_path='/static')

# Configure boto3 with retry settings
config = Config(
    retries=dict(
        max_attempts=3
    )
)


def init_aws_clients():
    ssm = boto3.client('ssm', config=config)
    logs = boto3.client('logs', config=config)
    return ssm, logs


def convert_to_utc(est_datetime):
    est = pytz.timezone('America/New_York')
    utc = pytz.UTC
    est_dt = est.localize(est_datetime)
    return est_dt.astimezone(utc)


def get_command_history(ssm_client, search_term, start_time, end_time, status_filter="", limit=500):
    paginator = ssm_client.get_paginator('list_commands')
    command_list = []

    # Use the provided limit instead of hardcoding 500
    result_limit = limit

    for page in paginator.paginate():
        for command in page['Commands']:
            if len(command_list) >= result_limit:
                return command_list, True

            if start_time <= command['RequestedDateTime'] <= end_time:
                # Apply status filter if provided
                if status_filter and command['Status'] != status_filter:
                    continue

                if 'Comment' in command and search_term.lower() in command['Comment'].lower():
                    command_list.append({
                        'CommandId': command['CommandId'],
                        'Comment': command.get('Comment', ''),
                        'Status': command['Status'],
                        'RequestedDateTime': command['RequestedDateTime'].strftime('%Y-%m-%d %H:%M:%S'),
                        'InstanceIds': command.get('InstanceIds', [])
                    })

    return command_list, False


def fetch_cloudwatch_logs_for_command(command_id, invocation_id=None):
    """
    Fetches CloudWatch logs related to an SSM command execution and returns them as a zip file.

    Args:
        command_id: The SSM command ID to fetch logs for
        invocation_id: Optional specific invocation ID

    Returns:
        BytesIO object containing the zipped logs
    """
    # Initialize AWS clients
    ssm_client = boto3.client('ssm')
    logs_client = boto3.client('logs')
    logs_zip = BytesIO()

    try:
        # Step 1: Get command details
        if invocation_id:
            # If invocation ID is provided, get that specific invocation
            invocations_response = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=invocation_id
            )
            invocations = [invocations_response]  # Convert to list format for consistency
        else:
            # Otherwise get all invocations for this command
            command_result = ssm_client.list_command_invocations(
                CommandId=command_id,
                Details=True
            )
            invocations = command_result.get('CommandInvocations', [])

        if not invocations:
            raise Exception(f"No invocations found for command {command_id}")

        # Step 2: First discover the correct log group by listing all available log groups
        log_groups = []
        paginator = logs_client.get_paginator('describe_log_groups')

        for page in paginator.paginate():
            for group in page.get('logGroups', []):
                group_name = group.get('logGroupName', '')
                if 'ssm' in group_name.lower() or 'aws-runshellscript' in group_name.lower():
                    log_groups.append(group_name)

        with zipfile.ZipFile(logs_zip, 'w') as zip_file:
            # Add command information
            command_info = {
                'command_id': command_id,
                'invocations': [inv.get('CommandId') for inv in invocations],
                'log_groups_checked': log_groups
            }
            zip_file.writestr('command_info.json', json.dumps(command_info, indent=2))

            # For each invocation, try to find logs in each potential log group
            logs_found = False

            for invocation in invocations:
                instance_id = invocation.get('InstanceId')

                for log_group in log_groups:
                    try:
                        # Try different potential stream name patterns
                        potential_prefixes = [
                            instance_id,  # Just the instance ID
                            f"{instance_id}/",  # Instance ID with slash
                            command_id,  # Just the command ID
                            f"{command_id}/",  # Command ID with slash
                            f"{instance_id}/{command_id}"  # Both IDs combined
                        ]

                        for prefix in potential_prefixes:
                            try:
                                # List log streams matching the prefix
                                streams_response = logs_client.describe_log_streams(
                                    logGroupName=log_group,
                                    logStreamNamePrefix=prefix
                                )

                                for stream in streams_response.get('logStreams', []):
                                    stream_name = stream.get('logStreamName')

                                    # Check if stream looks relevant to our command
                                    if command_id in stream_name or instance_id in stream_name:
                                        # Get the log events
                                        events_response = logs_client.get_log_events(
                                            logGroupName=log_group,
                                            logStreamName=stream_name,
                                            startFromHead=True
                                        )

                                        events = events_response.get('events', [])
                                        if events:
                                            logs_found = True
                                            log_content = "\n".join([
                                                f"[{event.get('timestamp')}] {event.get('message')}"
                                                for event in events
                                            ])

                                            # Categorize logs based on content
                                            if any("stdout" in event.get('message', '').lower() for event in events):
                                                zip_file.writestr(
                                                    f"{instance_id}_{stream_name}_stdout.log",
                                                    log_content
                                                )
                                            elif any("stderr" in event.get('message', '').lower() for event in events):
                                                zip_file.writestr(
                                                    f"{instance_id}_{stream_name}_stderr.log",
                                                    log_content
                                                )
                                            else:
                                                zip_file.writestr(
                                                    f"{instance_id}_{stream_name}.log",
                                                    log_content
                                                )
                            except logs_client.exceptions.ResourceNotFoundException:
                                # This prefix doesn't exist in this log group, try the next one
                                continue
                    except logs_client.exceptions.ResourceNotFoundException:
                        # This log group doesn't exist, try the next one
                        continue

            # If no logs were found, add a note to the zip
            if not logs_found:
                zip_file.writestr('README.txt',
                                  f"No logs found for command {command_id}.\n"
                                  f"Checked log groups: {', '.join(log_groups)}\n"
                                  f"This could be because:\n"
                                  f"1. Logs have expired or been deleted\n"
                                  f"2. Command logging was not enabled\n"
                                  f"3. The log group name is different in your setup\n"
                                  f"4. Insufficient permissions to access logs"
                                  )

        logs_zip.seek(0)
        return logs_zip

    except Exception as e:
        # Create a zip with error information
        with zipfile.ZipFile(logs_zip, 'w') as zip_file:
            zip_file.writestr("error.log", f"Failed to fetch logs: {str(e)}")
        logs_zip.seek(0)
        return logs_zip


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_term = request.form['search_term']

        # Check if the is_command_id checkbox was selected
        is_command_id = 'is_command_id' in request.form

        # If it's a command ID, redirect to the command details page
        if is_command_id:
            from flask import redirect, url_for
            return redirect(url_for('get_command_details', command_id=search_term))

        # Otherwise, proceed with the normal search functionality
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')

        start_utc = convert_to_utc(start_date)
        end_utc = convert_to_utc(end_date)

        result_limit = int(request.form.get('result_limit', 500))
        status_filter = request.form.get('status', '')

        ssm, _ = init_aws_clients()
        commands, limit_reached = get_command_history(ssm, search_term, start_utc, end_utc, status_filter=status_filter,
                                                      limit=result_limit)

        return render_template('results.html', commands=commands, limit_reached=limit_reached)

    return render_template('index.html')


@app.route('/download/<command_id>')
def download_logs(command_id):
    _, logs = init_aws_clients()
    logs_zip = fetch_cloudwatch_logs(logs, command_id)

    return send_file(
        logs_zip,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f'command_logs_{command_id}.zip'
    )


@app.route('/command/<command_id>')
def get_command_details(command_id):
    ssm, _ = init_aws_clients()
    try:
        # Get invocation details for each instance
        invocations = ssm.list_command_invocations(
            CommandId=command_id,
            Details=True
        )['CommandInvocations']

        instance_details = []
        for invocation in invocations:
            output_logs = ""
            error_logs = ""

            try:
                output = ssm.get_command_invocation(
                    CommandId=command_id,
                    InstanceId=invocation['InstanceId']
                )
                output_logs = output.get('StandardOutputContent', '')
                error_logs = output.get('StandardErrorContent', '')
                parameters = output.get('Parameters', {})
            except Exception as e:
                print(f"Error fetching logs for instance {invocation['InstanceId']}: {str(e)}")

            instance_details.append({
                'InstanceId': invocation['InstanceId'],
                'Status': invocation['Status'],
                'OutputContent': output_logs,
                'ErrorContent': error_logs
            })

        return render_template('command_details.html',
                               command_id=command_id,
                               parameters=parameters,
                               instance_details=instance_details)
    except Exception as e:
        return f"Error retrieving command details: {str(e)}", 500


def view_logs(command_id):
    _, logs = init_aws_clients()
    log_group = '/aws/ssm/AWS-RunShellScript'
    output_logs = []
    error_logs = []

    # Fetch output logs
    paginator = logs.get_paginator('filter_log_events')
    for page in paginator.paginate(
            logGroupName=log_group,
            filterPattern=f'"{command_id}" "stdout"'
    ):
        output_logs.extend([event['message'] for event in page['events']])

    # Fetch error logs
    for page in paginator.paginate(
            logGroupName=log_group,
            filterPattern=f'"{command_id}" "stderr"'
    ):
        error_logs.extend([event['message'] for event in page['events']])

    return {
        'output': '\n'.join(output_logs),
        'error': '\n'.join(error_logs)
    }


def send_email_notification():
    # Replace these with your email configuration
    sender_email = "your_email@example.com"
    sender_password = "your_password"
    recipient_email = "recipient@example.com"
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    try:
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = "Server Shutdown Alert"

        body = f"Server shutdown detected at {datetime.now()}"
        message.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)

        logging.info("Shutdown notification email sent successfully")
    except Exception as e:
        logging.error(f"Failed to send email notification: {str(e)}")

def shutdown_handler(signum, frame):
    """Handler for shutdown signals"""
    logging.info(f"Received shutdown signal: {signal.Signals(signum).name}")
    send_email_notification()
"""
Handles multiple types of shutdown scenarios:
SIGTERM (termination signal)
SIGINT (interrupt signal, Ctrl+C)
"""
# Register shutdown handlers
signal.signal(signal.SIGTERM, shutdown_handler)  # Termination signal
signal.signal(signal.SIGINT, shutdown_handler)   # Interrupt signal (Ctrl+C)

# Normal interpreter shutdown (via atexit)
# Register function to be called on normal interpreter shutdown
atexit.register(lambda: logging.info("Server shutting down via atexit"))
atexit.register(send_email_notification)


if __name__ == '__main__':
    app.run(debug=True)