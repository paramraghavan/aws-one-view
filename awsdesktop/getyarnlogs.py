import botocore
import os
import sys
import boto3
import traceback

LOG = 'awslocaldesktop/applications_log'
SSE_KMS_ID = 'alias/xxxx/app'
sse_args={"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": SSE_KMS_ID}

#
#help
#aws emr add-steps --cluster-id j-1VM63QTKSPER6  --steps Type=spark,Name=GetYarnLogs,ActionOnFailure=CONTINUE,Args=s3://pp/paramraghavan/scripts/getyarnlogs.py,devl,application_1608812452978_0013
#aws emr add-steps --cluster-id j-1VM63QTKSPER6  --steps Type=spark,Name=GetYarnLogs,ActionOnFailure=CANCEL_AND_WAIT,Args=s3://pp/paramraghavan/scripts/getyarnlogs.py,devl,application_1608812452978_0013
#
# aws emr cancel-steps --cluster-id j-1VM63QTKSPER6 --step-ids s-3M8DXXXXXXXXX s-3M8DXXXXXXXXX --step-cancellation-option SEND_INTERRUPT
# aws emr cancel-steps --cluster-id j-1VM63QTKSPER6 --step-ids s-3M8DXXXXXXXXX --step-cancellation-option SEND_INTERRUPT

import os

def get_application_log(bucket_name, application_id):
    cmd = []
    try:
        #cmd = "yarn logs -applicationId {0} > /tmp/{1}".format(application_id, str(application_id) + ".log")
        cmd.append('yarn')
        cmd.append('logs')
        cmd.append('-applicationId')
        cmd.append(str(application_id))

        print(cmd)
        msg,file = call_exec_file(cmd, application_id)
        print(msg)
        print('file {0}'.format(file))

        path = os.getcwd()
        print('current working dir {0}'.format(path))
        file_path = path + os.sep + file
        print('file- with path {0}'.format(file_path))
        if file:
            src = file_path
            tgt = 's3://{0}/{1}/{2}'.format(bucket_name, LOG, file)
            copy_command = s3_copy(src,tgt)
            print('command {0}'.format(copy_command))
            run_command(copy_command)
            msg = 'Success {0}'.format(copy_command)

        print(msg)
    except botocore.exceptions.ClientError as e:
        msg = 'AWS Error : ' + str(e)
        traceback.print_exc()
        msg = "Error performing get_application_log " + str(e)
        print(msg)
        raise e
    except Exception as e:
        msg = "Error performing get_application_log " + str(e)
        traceback.print_exc()
        print(msg)
        raise e


def s3_copy(source_datalocation,target_datalocation):
    s3_command = 'aws s3 cp '+source_datalocation+" "+target_datalocation + " --sse aws:kms --sse-kms-key-id " + sse_args["SSEKMSKeyId"]
    #filter_hedgedates_by_accounting_period = 'aws s3 cp '+hao_ln_pool_intl_rslt_eod_location+' "./filtered_hedgedates" --recursive --exclude "*"  --include "'+accounting_period+'*"'
    return s3_command

#for python 2.7
def run_command(cmd):
    call(cmd,shell=True)



import subprocess
from subprocess import call

#for python 2.7
def call_exec_file(command_arr, application_id, shell=False):
    msg = {}
    file = str(application_id) + ".log"
    try:
        with open(file, 'w') as f:
            process = subprocess.Popen(command_arr, stdout=f)
        stdout, stderr = process.communicate()
        msg["stdout"] = "Success invoking {}".format(command_arr)
        print(msg)
        return msg, file
    except subprocess.CalledProcessError as e:
        print("Calledprocerr")
        print(traceback.format_exc())
        msg["Error"] = "Error invoking {}".format(command_arr) + str(e)
        print(msg)
        raise e

    return msg, None


import os
import boto3



def get_boto3_client(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'zsproxy.ygpp.com:10000'
    # os.environ['HTTP_PROXY'] = 'zsproxy.ygpp.com:10000'
    session = boto3.session.Session()
    return session.client(service)

def upload_to_s3(filename, key, bucket_name):
    try:
        s3 = get_boto3_client('s3')
        s3.upload_file(
            Bucket=bucket_name,
            Filename=filename,
            Key=key,
            ExtraArgs=sse_args)
    except botocore.exceptions.ClientError as e:
        msg = 'AWS Error' + str(e)
        print(msg)
        traceback.print_exc()
        raise e
    except Exception as e:
        msg = 'Error connecting to AWS' + str(e)
        traceback.print_exc()
        raise e

# for python 3.x
def runtime_exec(command, shell=False):
    msg = {}
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if int(result.returncode) != 0:
            print('script output: {0}'.format(result.stdout))
            print('script error: {0}'.format(result.stderr))
            msg["stderr"] = str(result.stderr)
        msg["stdout"] = result.stdout
        print('script executed successfully {0}'.format(result.stdout))
        return msg
    except subprocess.CalledProcessError as e:
        print("Calledprocerr")
        print(traceback.format_exc())
        msg["Error"] = "Error performing get_application_log " + str(e)
    return msg


if __name__ == '__main__':
    #call_exec(['ls', '-l', '-t'], 'test')

    if len(sys.argv) != 3:
        print('There should be 2 arguments, but only {0}'.format(len(sys.argv)))
        exit(-1)
    bucket_name = sys.argv[1]
    application_id = sys.argv[2]
    try:
        get_application_log(bucket_name, application_id)
    except Exception as e:
        msg = "Error performing get_application_log " + str(e)
        traceback.print_exc()
        print(msg)
        exit(-1)
    exit(0)