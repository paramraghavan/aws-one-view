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


def get_command_history(ssm_client, search_term, start_time, end_time, limit=500):
    paginator = ssm_client.get_paginator('list_commands')
    command_list = []
    result_limit = 500

    for page in paginator.paginate():
        for command in page['Commands']:
            if len(command_list) >= result_limit:
                return command_list, True

            if start_time <= command['RequestedDateTime'] <= end_time:
                if 'Comment' in command and search_term.lower() in command['Comment'].lower():
                    command_list.append({
                        'CommandId': command['CommandId'],
                        'Comment': command.get('Comment', ''),
                        'Status': command['Status'],
                        'RequestedDateTime': command['RequestedDateTime'].strftime('%Y-%m-%d %H:%M:%S'),
                        'InstanceIds': command.get('InstanceIds', [])
                    })

    return command_list, False


def fetch_cloudwatch_logs(logs_client, command_id):
    log_group = '/aws/ssm/AWS-RunShellScript'
    logs_zip = BytesIO()

    with zipfile.ZipFile(logs_zip, 'w') as zip_file:
        paginator = logs_client.get_paginator('filter_log_events')

        # Fetch Output logs
        output_events = []
        for page in paginator.paginate(
                logGroupName=log_group,
                filterPattern=f'"{command_id}" "stdout"'
        ):
            output_events.extend(page['events'])

        # Fetch Error logs
        error_events = []
        for page in paginator.paginate(
                logGroupName=log_group,
                filterPattern=f'"{command_id}" "stderr"'
        ):
            error_events.extend(page['events'])

        # Write Output logs
        if output_events:
            for event in output_events:
                file_name = f"output_{event['timestamp']}_{event['logStreamName']}.log"
                zip_file.writestr(file_name, event['message'])

        # Write Error logs
        if error_events:
            for event in error_events:
                file_name = f"error_{event['timestamp']}_{event['logStreamName']}.log"
                zip_file.writestr(file_name, event['message'])

    logs_zip.seek(0)
    return logs_zip


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_term = request.form['search_term']
        start_date = datetime.strptime(request.form['start_date'], '%Y-%m-%dT%H:%M')
        end_date = datetime.strptime(request.form['end_date'], '%Y-%m-%dT%H:%M')

        start_utc = convert_to_utc(start_date)
        end_utc = convert_to_utc(end_date)

        result_limit = int(request.form.get('result_limit', 500))
        ssm, _ = init_aws_clients()
        commands, limit_reached = get_command_history(ssm, search_term, start_utc, end_utc, limit=result_limit)

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
        download_name=f'logs_{command_id}.zip'
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