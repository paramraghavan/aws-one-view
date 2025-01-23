from flask import Flask, request, render_template, send_file
import boto3
from datetime import datetime, timedelta
import pytz
from io import BytesIO
import zipfile
from botocore.config import Config

app = Flask(__name__)

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


def get_command_history(ssm_client, search_term, start_time, end_time):
    paginator = ssm_client.get_paginator('list_commands')
    command_list = []

    for page in paginator.paginate():
        for command in page['Commands']:
            if start_time <= command['RequestedDateTime'] <= end_time:
                if 'Comment' in command and search_term.lower() in command['Comment'].lower():
                    command_list.append({
                        'CommandId': command['CommandId'],
                        'Comment': command.get('Comment', ''),
                        'Status': command['Status'],
                        'RequestedDateTime': command['RequestedDateTime'].strftime('%Y-%m-%d %H:%M:%S'),
                        'InstanceIds': command.get('InstanceIds', [])
                    })

    return command_list


def fetch_cloudwatch_logs(logs_client, command_id):
    log_group = '/aws/ssm/AWS-RunShellScript'
    logs_zip = BytesIO()

    with zipfile.ZipFile(logs_zip, 'w') as zip_file:
        paginator = logs_client.get_paginator('filter_log_events')

        for page in paginator.paginate(
                logGroupName=log_group,
                filterPattern=f'"{command_id}"'
        ):
            for event in page['events']:
                file_name = f"{event['timestamp']}_{event['logStreamName']}.log"
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

        ssm, _ = init_aws_clients()
        commands = get_command_history(ssm, search_term, start_utc, end_utc)

        return render_template('results.html', commands=commands)

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


if __name__ == '__main__':
    app.run(debug=True)