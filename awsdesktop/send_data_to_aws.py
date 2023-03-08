import traceback
from flask import Flask, render_template, request, send_file, jsonify, abort,  send_from_directory
from flask_cors import CORS
import botocore
import os
import sys
import boto3
import json

#import awsdesktop


# client = boto3.client(
#     's3',
#     aws_access_key_id=ACCESS_KEY,
#     aws_secret_access_key=SECRET_KEY,
#     aws_session_token=SESSION_TOKEN
# )


# https://stackoverflow.com/questions/20646822/how-to-serve-static-files-in-flask
from werkzeug.utils import secure_filename
# from win32com.server import exception
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

#TODO not used any more, to cleanup
global BUCKET_NAME
BUCKET_NAME = None
local_dir = None
sse_args={"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": ''}

@app.route('/assets/img/favicon.png')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/')
def index():
    return render_template("local_aws_desktop.html")
    #return render_template("aws_desktop_access.html")

@app.route('/local_aws_desktop')
def sidebar():
    return render_template("local_aws_desktop.html")

def list_bucket(s3_client, filter):
    list = []
    list_of_bucket =  s3_client.list_buckets()
    for bucket in list_of_bucket['Buckets']:
        if filter in bucket["Name"]:
            print(f'  {bucket["Name"]}')
            list.append(bucket["Name"])
    return list

@app.route("/getbuckets", methods=['GET'])
def getbuckets():
    msg =''
    s3 = aws_utils.get_boto3_client('s3')
    bucket_filter = ''
    if request.method == 'GET':
        if 'filter' in request.args:
            bucket_filter = request.args['filter']
    buckets_list = list_bucket(s3, bucket_filter.strip())
    data = {}
    data["list"] = buckets_list
    jsonData = json.dumps(data)

    return app.response_class(
        response=jsonData,
        status=200,
        mimetype='application/json'
    )

@app.errorhandler(Exception)
def all_exception_handler(e):
    error = str(traceback.format_exc())

@app.errorhandler(500)
def internal_server_error(error):
    app.logger.error('Server Error: %s', (error))
    return render_template('error.htm'), 500

@app.errorhandler(Exception)
def unhandled_exception(e):
    app.logger.error('Unhandled Exception: %s', (e))
    return render_template('error.html', msglog=str(e)), 500

@app.route('/bucket',methods=['post'])
def bucket():
    msg = ''
    global BUCKET_NAME
    global sse_args
    if request.method == 'POST':
        bucket_value = request.form['bucket']
        if bucket_value:
            BUCKET_NAME = bucket_value
            # # set kms key
            # sse_args['SSEKMSKeyId'] = value.split(',')[1]
            # msg = 'bucket selected : ' + BUCKET_NAME + ' kms : ' + sse_args['SSEKMSKeyId']
        else:
            msg = 'error with bucket selection : '

    print(msg)
    #return render_template("aws_desktop_access.html",bucketselected =msg)
    return msg


@app.route('/upload',methods=['post'])
def upload():
    msg = ''
    #s3 = boto3.client('s3')
    s3 = aws_utils.get_boto3_client('s3')
    metadata = {}
    checksum_arr = []
    if request.method == 'POST':
        img = request.files['file']
        key = request.form['key'].strip('/')
        checksum = request.form['checksum'].strip()
        upload_bucket_file = request.form['upload_bucket_file']
        kms_key_up_file = request.form['kms_key_up_file']

        if checksum:
            checksum_arr = checksum.split(',')
            if len(checksum_arr) == 2 and checksum_arr[0] and checksum_arr[1]:
                metadata[checksum_arr[0]] = checksum_arr[1]
            else:
                msg = 'Error setting up checksum.'
                return msg

        if img and key and upload_bucket_file:
            try:
                filename = secure_filename(img.filename)
                img.save(filename)
                sse_args_copy = sse_args.copy()
                if metadata:
                    sse_args_copy['Metadata'] = metadata

                if isEmptyStr(kms_key_up_file) :
                    s3.upload_file(
                            Bucket = upload_bucket_file,
                            Filename=filename,
                            Key = key + '/' + filename)
                else:
                    sse_args_copy['SSEKMSKeyId'] = kms_key_up_file
                    s3.upload_file(
                            Bucket = upload_bucket_file,
                            Filename=filename,
                            Key = key + '/' + filename,
                            ExtraArgs=sse_args_copy)

                msg = "Upload Done ! " + " key : " + key + '/' + filename
            except botocore.exceptions.ClientError as e:
                msg = 'Message: AWS Error' + str(e)
                print(msg)
                traceback.print_exc()
            except Exception as e:
                msg = 'Message: Error connecting to AWS' + str(e)
                traceback.print_exc()
        else:
            msg = 'Message: Either key path or the file to be uploaded is not selected'
        print(msg)
        #return render_template("aws_desktop_access.html",msg =msg)
        return msg


def getLocalDir(dir=None):
    if isEmptyStr(dir):
        if not local_dir:
            msg = 'please configure local_dir in config.properties'
            print(msg)
            raise ValueError("Error: {0}".format(msg))
        dir = local_dir + os.sep + getCurrentTimestamp() + os.sep
    else:
        dir = dir + os.sep + getCurrentTimestamp() + os.sep

    makeLocalDir(dir)
    return dir


# make dir if it does not exist
def makeLocalDir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


@app.route('/uploadfolder',methods=['post'])
def uploadfolder():
    msg = ''
    if request.method == 'POST':
        key = request.form['keyfolder'].strip('/')
        #local_directory = getLocalDir(request.form['folder'])
        local_directory = request.form['folder']
        upload_bucket_folder = request.form['upload_bucket_folder']
        kms_key_up_folder = request.form['kms_key_up_folder']

        if key and local_directory and upload_bucket_folder:
            msg = uploaddir(local_directory, upload_bucket_folder, key, kms_key_up_folder)
            #msg = "Upload Done ! "
        else:
            msg = 'Message: nothing to upload as folder or key not set.'
        print(msg)
        #return render_template("aws_desktop_access.html",msgfolder =msg)
        return msg

from awsdesktop import aws_emr_helper

@app.route("/listclusters", methods=['GET', 'POST'])
def listclusters():
    msg = ''
    list= []
    clusterfilter = request.form['clusterfilter']
    try:
        list = aws_emr_helper.get_cluster_info(clusterfilter)
    except Exception as e:
        msg = 'Error connecting to AWS' + str(e)
        list = [msg]
    #print(''.join(list))
    #return render_template("aws_desktop_access.html",list =list)
    data = {}
    data["list"] = list
    jsonData = json.dumps(data)

    return app.response_class(
        response=jsonData,
        status=200,
        mimetype='application/json'
    )


yarn_log_command = 'aws emr add-steps --cluster-id {0}  --steps Type=spark,Name=GetYarnLogs,ActionOnFailure=CANCEL_AND_WAIT,Args=s3://{1}/awslocaldesktop/scripts/getyarnlogs.py,{1},{2}'
LOG_SCRIPTS = 'awslocaldesktop/scripts'

@app.route("/getyarnlogs", methods=['GET', 'POST'])
def getyarnlogs():
    msg = {}
    cluster = request.form['selectedcluster']
    env = request.form['emr_env']
    app_id = request.form['yarn_app_id']

    if cluster and env and app_id:
        #list
        try:
            code_file = "getyarnlogs.py"
            path = os.getcwd()
            print("current working dir {0}".format(path))
            code_file_path = path + os.sep + "awsdesktop" + os.sep + code_file
            print('code file path {0}'.format(code_file_path))

            tgt = 's3://{0}/{1}/{2}'.format(BUCKET_NAME, LOG_SCRIPTS, code_file)
            code_copy_cmd = s3_copy_across(code_file_path, tgt)
            #print('code_copy_cmd {0}'.format(code_copy_cmd))
            result = runtime_exec(code_copy_cmd)
            msg['copy'] = result
            print(result)
            #bucket_name = dictConfig[env]
            command = yarn_log_command.format(cluster, BUCKET_NAME, app_id)
            result_log = runtime_exec(command)
            print(result_log)
            msg['log'] = result_log
            msg['Success'] = 'Request submitted, see @: ' + 's3://{0}/{1}/{2}'.format(BUCKET_NAME, 'awslocaldesktop/application_logs', str(app_id) + '.log')
        except botocore.exceptions.ClientError as e:
            msg['Error'] = 'AWS Error : ' + str(e)
            traceback.print_exc()
        except Exception as e:
            msg['Error'] = "Error performing local copy " + str(e)
            traceback.print_exc()

        print(msg)
        return jsonify(msg), 200
    else:
        msg = 'Cluster , Env or App Id is not selected'
        return jsonify(msg), 400


def s3_copy_across(source_datalocation,target_datalocation):
    s3_command = 'aws s3 cp '+source_datalocation+" "+target_datalocation + " --sse aws:kms --sse-kms-key-id " + sse_args["SSEKMSKeyId"]
    return s3_command


@app.route("/listgroups", methods=['GET', 'POST'])
def listgroups():
    msg = ''
    loggroupfilter = request.form['loggroupfilter']
    if loggroupfilter:
        #list
        try:
            #logs_client = boto3.client("logs")
            logs_client = aws_utils.get_boto3_client('logs')
            list = list_groups(logs_client, loggroupfilter)
        except Exception as e:
            msg = 'Error connecting to AWS' + str(e)
            list = [msg]
    else:
        list = ['Log group filter not set']
    print(''.join(list))
    #return render_template("aws_desktop_access.html",list =list)
    data = {}
    data["list"] = list
    jsonData = json.dumps(data)

    return app.response_class(
        response=jsonData,
        status=200,
        mimetype='application/json'
    )


def list_groups(logs_client, loggroupfilter):
    list = []
    i = 0
    """Lists available CloudWatch logs groups"""
    for group in get_groups(logs_client, loggroupfilter):

        log_output = app.config.get('log_output')
        if log_output:
            print(group)
        else:
            if i == 0:
                print('.', end="")
                i = 1
            else:
                print(':', end="")
                i = 0

        print(group)
        list.append(group)

    return list

from datetime import datetime

def getCurrentTimestamp():
    return datetime.now().strftime('%Y%m%d%H%M%S%f')

def get_groups(logs_client, loggroupfilter):
    log_group_prefix = loggroupfilter
    print('log_group_prefix {0}'.format(log_group_prefix))
    """Returns available CloudWatch logs groups"""
    kwargs = {}
    if log_group_prefix is not None:
        kwargs = {'logGroupNamePrefix': log_group_prefix}
    paginator = logs_client.get_paginator('describe_log_groups')
    for attr in dir(paginator):
        print("obj.%s = %r" % (attr, getattr(paginator, attr)))
    for page in paginator.paginate(**kwargs):
        for group in page.get('logGroups', []):
            yield group['logGroupName']


def uploaddir(local_directory, bucket, destination, kms_key_up_folder):
    #s3 = boto3.client('s3')
    s3 = aws_utils.get_boto3_client('s3')
    msg ='Message: Nothing to upload or uploaded.'
    # enumerate local files recursively
    for root, dirs, files in os.walk(local_directory):
        for filename in files:
            # construct the full local path
            local_path = os.path.join(root, filename)

            # construct the full Dropbox path
            relative_path = os.path.relpath(local_path, local_directory)
            s3_path = os.path.join(destination, relative_path)
            s3_path = s3_path.replace('\\', '/')

            # relative_path = os.path.relpath(os.path.join(root, filename))

            print('Searching "%s" in "%s"' % (s3_path, bucket))
            try:
                s3.head_object(Bucket=bucket, Key=s3_path)
                print("Path found on S3! Skipping %s..." % s3_path)

                # try:
                # client.delete_object(Bucket=bucket, Key=s3_path)
                # except:
                # print "Unable to delete %s..." % s3_path
            except Exception as e:
                # this is expected.
                if 'HeadObject operation: Not Found' in e.args[0]:
                    print("Uploading %s..." % s3_path)
                    try:
                        if isEmptyStr(kms_key_up_folder):
                            s3.upload_file(local_path, bucket, s3_path)
                        else:
                            sse_args_copy = sse_args.copy()
                            sse_args_copy['SSEKMSKeyId'] = kms_key_up_folder
                            s3.upload_file(local_path, bucket, s3_path, ExtraArgs=sse_args_copy)

                        msg = 'Upload done!'
                    except botocore.exceptions.ClientError as e:
                        msg = 'Message: AWS Error' + str(e)
                        print(msg)
                        traceback.print_exc()
                    except Exception as e:
                        msg = 'Message: Error connecting to AWS' + str(e)
                        traceback.print_exc()
                else:
                    msg = 'Message: AWS Error' + str(e)
                    print(msg)
                    traceback.print_exc()
    return msg

@app.route("/download", methods=['POST'])
def download():
    msg = ''
    key_filename = request.form['dwn_key']
    dir = getLocalDir(request.form['local_dir'])
    download_bucket_file = request.form['download_bucket_file']

    filepath =  None
    if request.method == 'POST':
        if key_filename and dir and download_bucket_file:
            try:
                output = download_file(key_filename, dir, download_bucket_file)
                msg = 'download complete'
                print(msg)
                msg = "file downloaded to {0}".format(output)
                #return send_file(output, as_attachment=True)
                #return render_template("info.html", msglog=msg)
                return msg;
            except botocore.exceptions.ClientError as e:
                msg = 'AWS Error : ' + str(e)
                traceback.print_exc()
                #return render_template("error.html", msglog=msg)
                return msg
            except Exception as e:
                msg = "Error Downloading  %s..." % key_filename + str(e)
                print(msg)
                traceback.print_exc()
                #return render_template("error.html", msglog=msg)
                return msg
            finally:
                if filepath:
                    os.remove(filepath)
        else:
            msg = 'File to be downloaded not mentioned'
            #return render_template("error.html",msglog =msg)
            return msg

def download_file(file_name, dir, download_bucket_file):
    """
    Function to download a given file from an S3 bucket
    """
    s3 = aws_utils.get_boto3_resource('s3') #boto3.resource('s3')
    output = file_name.split('/')[-1]
    output = dir  + output
    filepath = output
    print('file to download {0}'.format(output))

    try:
        print("BUCKET_NAME : {0}".format(download_bucket_file))
        s3.Bucket(download_bucket_file).download_file(file_name, output)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            # printing stack trace
            traceback.print_exc()
            raise e

    return output

@app.route("/downloadfolder", methods=['POST'])
def downloadfolder():
    msg = ''
    s3_folder = request.form['dwn_folder_key']
    dir = getLocalDir(request.form['local_dir'])
    download_bucket_folder = request.form['download_bucket_folder']

    if request.method == 'POST':
        if s3_folder and dir and download_bucket_folder:
            try:
                print("BUCKET_NAME : {0}".format(BUCKET_NAME))
                output = download_s3_folder(s3_folder, download_bucket_folder, dir)
                msg = 'folder download complete --> ' + dir
                print(msg)
                #return render_template("aws_desktop_access.html", msgfolderdownload=msg)
            except ValueError as ve:
                msg = str(ve)
                #return render_template("error.html", msglog=msg1)
                return msg;
            except Exception as e:
                msg = "Error Downloading  %s..." % s3_folder + str(e)
                print(msg)
                traceback.print_exc()
                #return render_template("error.html", msglog=msg1)
                return msg;
        else:
            msg = 'S3 Folder or the local folder to be downloaded is not mentioned'
            #return render_template("error.html", msglog=msg)
            return msg;

        #return render_template("info.html", msglog=msg)
        return msg;

def download_s3_folder(s3_folder, bucket_name, dir=None):
    """
    Download the contents of a folder directory
    Args:
        bucket_name: the name of the s3 bucket
        s3_folder: the folder path in the s3 bucket
        local_dir: a relative or absolute directory path in the local file system
    """
    s3 = aws_utils.get_boto3_resource('s3') #boto3.resource('s3')
    bucketFolder = s3.Bucket(bucket_name)
    for obj in bucketFolder.objects.filter(Prefix = s3_folder):
        windowspath = obj.key.split(s3_folder)[1].replace('/', '\\')
        target = dir + windowspath
        # else os.path.join(local_dir, os.path.basename(obj.key))
        print(target)
        if not os.path.exists(os.path.dirname(target)):
            os.makedirs(os.path.dirname(target))
        print(obj.key)
        try:
            bucketFolder.download_file(obj.key, target)
        except botocore.exceptions.ClientError as e:
            #traceback.print_exc()
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
                raise ValueError("The object does not exist.")
            else:
                msg = 'AWS Error : '
                print( msg + str(e))
                raise ValueError(msg)



@app.route("/locals3copy", methods=['POST'])
def locals3copy():
    source = {'Bucket': '', 'Key': ''}
    msg = ''
    recursive = False
    s3_src_folder = request.form['source_folder_key']
    s3_tgt_folder = request.form['target_folder_key']
    src_bucket = request.form['s3copy_bucket_src']
    tgt_bucket = request.form['s3copy_bucket_tgt']
    kms_key_s3copy = request.form['kms_key_s3copy']
    if request.method == 'POST':
        if src_bucket and tgt_bucket and s3_src_folder and s3_tgt_folder:
            try:
                if isEmptyStr(kms_key_s3copy):
                    cmd = "aws --profile default s3 cp s3://{0}/{1} s3://{2}/{3} --recursive ".format(
                        src_bucket, s3_src_folder, tgt_bucket, s3_tgt_folder.strip('/'))
                else:
                    cmd = "aws --profile default s3 cp s3://{0}/{1} s3://{2}/{3} --recursive --sse aws:kms --sse-kms-key-id {4}".format(
                        src_bucket, s3_src_folder, tgt_bucket, s3_tgt_folder.strip('/'), sse_args["SSEKMSKeyId"])

                #' --recursive --exclude "'+exclude_filter_key+'"  --include "'+include_filter_key+'*"'
                # if 'recursive' not in request.form:
                #     cmd = cmd.replace('--recursive', '')
                if 'include' in request.form and request.form['include']:
                    cmd += ' --include "' + request.form['include'] + '" '
                if 'exclude' in request.form and request.form['exclude']:
                    cmd += ' --exclude "' + request.form['exclude'] + '" '
                print(cmd)
                msg = runtime_exec(cmd)
            except botocore.exceptions.ClientError as e:
                msg = 'AWS Error : ' + str(e)
                traceback.print_exc()
            except Exception as e:
                msg = "Error performing local copy " + str(e)
                print(msg)
                traceback.print_exc()
            return msg
        else:
            msg = 'Source or Target folder is empty'
            return msg

import subprocess
def runtime_exec(command,shell=False):
    msg = {}
    try:
        print('command {0}'.format(command))
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
        msg["Error"] = "Error performing local copy " + str(e)
    return msg

def s3_copy(source_datalocation,target_datalocation,include_filter_key,exclude_filter_key='*'):
    s3_command = 'aws s3 cp '+source_datalocation+" "+target_datalocation+' --recursive --exclude "'+exclude_filter_key+'"  --include "'+include_filter_key+'*"'
    return s3_command

# def download_s3_folder1(s3_folder, bucket_name, local_dir=None):
#     """
#     Download the contents of a folder directory
#     Args:
#         bucket_name: the name of the s3 bucket
#         s3_folder: the folder path in the s3 bucket
#         local_dir: a relative or absolute directory path in the local file system
#     """
#     s3 = boto3.resource('s3')
#     bucketFolder = s3.Bucket(bucket_name)
#     for obj in bucketFolder.objects.filter(Prefix = s3_folder):
#         windowspath = obj.key.split(s3_folder)[1].replace('/', '\\')
#         target = local_dir + windowspath
#         # else os.path.join(local_dir, os.path.basename(obj.key))
#         print(target)
#         if not os.path.exists(os.path.dirname(target)):
#             os.makedirs(os.path.dirname(target))
#         print(obj.key)
#         try:
#             bucketFolder.download_file(obj.key, target)
#         except botocore.exceptions.ClientError as e:
#             #traceback.print_exc()
#             if e.response['Error']['Code'] == "404":
#                 print("The object does not exist.")
#                 raise ValueError("The object does not exist.")
#             else:
#                 msg = 'AWS Error'
#                 print( msg + " for " + obj.key )
#                 raise ValueError(msg)


import awsdesktop.aws_glue as aws_glue


'''
    database_name
    table_name
    location, "s3://pp-database/tables/" + table_name + "/date=20140401"
    part_key_values_in_order, "19690,1" #airlines=19690, flight_number=1
'''
@app.route("/addpartition", methods=['GET', 'POST'])
def addpartition():
    msg = ''
    databasename = request.form['databasename']
    tablename = request.form['tablename']
    location = request.form['location']
    partkeyvalue = request.form['partkeyvalue']
    print('databasename, tablename, location, partkeyvalue {0} {1} {2} {3}'.format(databasename, tablename, location, partkeyvalue ))

    if databasename and tablename and location and partkeyvalue:
        try:
            msg =aws_glue.add_partition(databasename, tablename, location, partkeyvalue)
            if msg and len(msg['Errors']) == 0 :
                success_msg = "Partition created for {}.{}".format(databasename,tablename)
                msg = {"Success": success_msg}
            else:
                msg = msg['Errors']
        except botocore.exceptions.ClientError as e:
            # traceback.print_exc()
            if e.response['Error']['Code'] == "404":
                msg = "Error adding partition. " + str(e)
                print(msg)
            else:
                msg = 'AWS Error' + str(e)
                print(msg)
            # render_template("error.html", msglog=msg)
            return jsonify(msg), 500
        except Exception as e:
            msg = 'Error connecting to AWS' + str(e)
            # printing stack trace
            traceback.print_exc()
            # return render_template("error.html", msglog=msg)
            return jsonify(msg), 500
        return jsonify(msg), 200
    else:
        msg = 'databasename, tablename, location, partition key values not selected.'
        return jsonify(msg), 400



@app.route("/getlogs", methods=['GET', 'POST'])
def getlogs():
    msg = ''
    loggroup = request.form['loggroup']
    starttime = request.form['starttime']
    endtime = request.form['endtime']
    if 'window' in request.form:
        window = request.form['window']
    else:
        window = 0
    print('loggroup, starttime, endtime {0} {1} {2}'.format(loggroup, starttime, endtime))
    # streams or groups
    log_type = request.form['optradio']
    stream_args = ''
    if log_type == 'streams':
        stream_args = request.form['streams']
    if loggroup and starttime and endtime:
        #list
        try:
            #logs_client = boto3.client("logs")
            logs_client = aws_utils.get_boto3_client('logs')
            #list_streams(logs_client, loggroup, parse_datetime(starttime), parse_datetime(endtime))
            memory_file, zipfileName, fileName = list_logs_extend_window(logs_client,loggroup, parse_datetime_est_to_equivalent_utc(starttime), parse_datetime_est_to_equivalent_utc(endtime), log_type, stream_args, window)
            if memory_file:
                os.remove(fileName)
                return send_file(memory_file, mimetype='application/zip', attachment_filename=zipfileName, as_attachment=True)
        except botocore.exceptions.ClientError as e:
            #traceback.print_exc()
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
                msg ="The object does not exist." + str(e)
            else:
                msg = 'AWS Error' + str(e)
                print( msg)
            #render_template("error.html", msglog=msg)
            return jsonify(msg), 500
        except Exception as e:
            msg = 'Error connecting to AWS' + str(e)
            # printing stack trace
            traceback.print_exc()
            #return render_template("error.html", msglog=msg)
            return jsonify(msg), 500
    else:
        msg = 'Log group , start time or endtime not selected'
        return jsonify(msg), 400
    #return render_template("info.html",msglog =msg)
    #return render_template("info.html", msglog=msg)
    return msg



def list_streams(logs_client, loggroup, starttime, endtime):
    """Lists available CloudWatch logs streams in ``log_group_name``."""
    for stream in get_streams(logs_client, loggroup, starttime, endtime):
        print(stream)

def get_streams(logs_client, log_group_name, start, end):
    """Returns available CloudWatch logs streams in ``log_group_name``."""
    kwargs = {'logGroupName': log_group_name}
    window_start = start or 0
    window_end = end or sys.float_info.max

    paginator = logs_client.get_paginator('describe_log_streams')
    for page in paginator.paginate(**kwargs):
        for stream in page.get('logStreams', []):
            if 'firstEventTimestamp' not in stream:
                # This is a specified log stream rather than
                # a filter on the whole log group, so there's
                # no firstEventTimestamp.
                yield stream['logStreamName']
            elif max(stream['firstEventTimestamp'], window_start) <= \
                    min(stream['lastIngestionTime'], window_end):
                yield stream['logStreamName']

import re
from datetime import datetime, timedelta
from dateutil.parser import parse
from dateutil.tz import tzutc

def parse_datetime(datetime_text):
    """Parse ``datetime_text`` into a ``datetime``."""

    if not datetime_text:
        return None

    ago_regexp = r'(\d+)\s?(m|minute|minutes|h|hour|hours|d|day|days|w|weeks|weeks)(?: ago)?'
    ago_match = re.match(ago_regexp, datetime_text)

    if ago_match:
        amount, unit = ago_match.groups()
        amount = int(amount)
        unit = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}[unit[0]]
        date = datetime.utcnow() + timedelta(seconds=unit * amount * -1)
    else:
        try:
            date = parse(datetime_text)
        except ValueError:
            raise ValueError(datetime_text)

    if date.tzinfo:
        if date.utcoffset != 0:
            date = date.astimezone(tzutc())
        date = date.replace(tzinfo=None)

    return int(total_seconds(date - datetime(1970, 1, 1))) * 1000


def parse_datetime_est_to_equivalent_utc(datetime_text):
    """Parse ``datetime_text`` into a ``datetime``."""

    if not datetime_text:
        return None

    ago_regexp = r'(\d+)\s?(m|minute|minutes|h|hour|hours|d|day|days|w|weeks|weeks)(?: ago)?'
    ago_match = re.match(ago_regexp, datetime_text)

    if ago_match:
        amount, unit = ago_match.groups()
        amount = int(amount)
        unit = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}[unit[0]]
        date = datetime.utcnow() + timedelta(seconds=unit * amount * -1)
    else:
        try:
            date = parse(datetime_text)
        except ValueError:
            raise ValueError(datetime_text)
    date = date.astimezone(tzutc())
    date = date.replace(tzinfo=None)
    print( date.strftime('%m/%d/%Y %H:%M:%S'))
    return int(total_seconds(date - datetime(1970, 1, 1))) * 1000

def total_seconds(delta):
    """
    Returns the total seconds in a ``datetime.timedelta``.

    Python 2.6 does not have ``timedelta.total_seconds()``, so we have
    to calculate this ourselves. On 2.7 or better, we'll take advantage of the
    built-in method.

    The math was pulled from the ``datetime`` docs
    (http://docs.python.org/2.7/library/datetime.html#datetime.timedelta.total_seconds).

    :param delta: The timedelta object
    :type delta: ``datetime.timedelta``
    """
    if sys.version_info[:2] != (2, 6):
        return delta.total_seconds()

    day_in_seconds = delta.days * 24 * 3600.0
    micro_in_seconds = delta.microseconds / 10.0**6
    return day_in_seconds + delta.seconds + micro_in_seconds


from collections import deque
from botocore.compat import json, total_seconds
import errno

#  The default is 10,000 events.
MAX_EVENTS_PER_CALL = 10000



#window minus or plus seconds to increase the start and emd time window
def list_logs_extend_window(client, log_group_name,start, end, log_type, streams, window=0):
    return list_logs(client, log_group_name, (start - window), (end + window), log_type, streams)

import time
import io
import zipfile

def list_logs(client, log_group_name,start, end, log_type, streams):
    #streams = []
    timestr = time.strftime("%Y%m%d-%H%M%S")
    nl = "\n"
    logfileName = "cloudwatchlogs" + timestr + ".log"
    zipfileName = "cloudwatchlogs" + timestr + ".zip"
    fileName = getLocalDir() #"c:/tmp")
    fileName = fileName + os.sep + logfileName

    print(" log file name : {0}".format(fileName))

    # Note: filter_log_events paginator is broken
    # ! Error during pagination: The same next token was received twice
    do_wait = object()
    watch = 'watch'
    watch_interval = 1
    def generator():
        # ref: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/logs.html
        interleaving_sanity = deque(maxlen=MAX_EVENTS_PER_CALL)
        # interleaved (boolean)
        # If the value is true, the operation makes a best effort to provide responses that contain events from multiple log streams
        # within the log group, interleaved in a single response.
        # If the value is false, all the matched log events in the first log stream are searched first, then those in the next
        # log stream, and so on. The default is false.

        kwargs = {}
        #log_group_name = '/aws/batch/job'
        #streams = ['ygpp01-devl-app-java8-jobDef/default/6d2ea1380ddb4626b583c305b754fe6c']

        kwargs = {'logGroupName': log_group_name,
                      'interleaved': True}

        if log_type == 'streams':
            kwargs['logStreamNames'] = streams.replace(' ','').split(',')

        if start:
            kwargs['startTime'] = start

        if end:
            kwargs['endTime'] = end

        #if filter_pattern:
        #    kwargs['filterPattern'] = filter_pattern

        while True:
            response = client.filter_log_events(**kwargs)

            for event in response.get('events', []):
                if event['eventId'] not in interleaving_sanity:
                    interleaving_sanity.append(event['eventId'])
                    yield event

            if 'nextToken' in response:
                kwargs['nextToken'] = response['nextToken']
            else:
                yield do_wait

    query= None
    query_expression = None

    def consumer():
        f = open(fileName, "w")
        i = 0
        for event in generator():
            if event is do_wait:
                return

            output = []
            message = event['message']
            if query is not None and message[0] == '{':
                parsed = json.loads(event['message'])
                message = query_expression.search(parsed)
                if not isinstance(message, str):
                    message = json.dumps(message)
            output.append(message.rstrip())

            log_output = app.config.get('log_output')
            if log_output:
                print(' '.join(output))
            else :
                i = i+1
                if i %2 == 0:
                    print('.', end ="")
                else:
                    print(':', end ="")

                if i == 80:
                    print('\n', end="")
                    i = 0

            f.write(' '.join(output)+ nl)

            try:
                if log_output:
                    sys.stdout.flush()
                f.flush()
            except IOError as e:
                f.close()
                os.remove(fileName)
                if e.errno == errno.EPIPE:
                    # SIGPIPE received, so exit
                    os._exit(0)
                else:
                    # We don't want to handle any other errors from this
                    raise
        f.flush()
        f.close()
    try:
        print('Download started!')
        print('------------------------------------------------------------------------------------------')
        consumer()
        print('Download complete!')
        print('------------------------------------------------------------------------------------------')
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w') as zf:
            #data = zipfile.ZipInfo(fileName)
            #data.date_time = time.localtime(time.time())[:6]
            #data.compress_type = zipfile.ZIP_DEFLATED
            #zf.writestr(data, fileName)
            zf.write(fileName)
        memory_file.seek(0)
        return memory_file, zipfileName, fileName
    except KeyboardInterrupt:
        print('Closing...\n')
        os._exit(0)
    except :
        traceback.print_exc()
        raise

def milis2iso(milis):
    res = datetime.utcfromtimestamp(milis/1000.0).isoformat()
    return (res + ".000")[:23] + 'Z'

def _get_streams_from_pattern(self, group, pattern):
    """Returns streams in ``group`` matching ``pattern``."""
    pattern = '.*' if pattern == self.ALL_WILDCARD else pattern
    reg = re.compile('^{0}'.format(pattern))
    for stream in self.get_streams(group):
        if re.match(reg, stream):
            yield stream


def isEmptyStr(str_value):
    if str_value is None or str_value and len(str_value.strip()) == 0:
        return True
    else:
        return False


@app.route('/checks3filestatus',methods=['post'])
def checkS3FileStatus():
    msg = {}
    latest_files = True
    try:
        #s3 = boto3.client('s3')
        s3 = aws_utils.get_boto3_client('s3')
        paginator = s3.get_paginator("list_objects")
        s3_bucket = BUCKET_NAME
        print('BUCKET_NAME {}'.format(BUCKET_NAME))
        if request.method == 'POST':
            list_of_paths = request.form['path_list']
            apply_filter  =  request.form['apply_filter']
            if 'latest' in request.form:
                latest_files = True
            else:
                latest_files = False

            list_of_paths_arr = list_of_paths.split(",")
            apply_filter_arr = apply_filter.split(",")
            if list_of_paths_arr:
                resp = []
                for prefixes in list_of_paths_arr:
                    prefixes = prefixes.strip('\n').strip('\r')
                    operation_parameters = {"Bucket": s3_bucket, "Prefix": "@@"}
                    operation_parameters["Prefix"] = prefixes
                    # print(operation_parameters)
                    page_iterator = paginator.paginate(**operation_parameters)
                    for page in page_iterator:
                        if 'Contents' not in page:
                            resp.append('Not found: {}'.format(page['Prefix']))
                            continue;
                        all = page['Contents']
                        if latest_files:
                            latest = max(all, key=lambda x: x['LastModified'])
                            file_name = latest['Key'].split('/')[-1]
                            metadata = '';
                            try:
                                metadata = s3.head_object(Bucket=BUCKET_NAME, Key=latest['Key'])
                                print(metadata)
                            except:
                                print("Failed metadata {}".format(latest['Key']))

                            if not any(filter in file_name for filter in apply_filter_arr):
                                continue
                            val = file_name + " , " + str(latest['LastModified']) + " , " + str(metadata['Metadata'])
                            print(val)
                            resp.append(val)
                        else:
                            for file in all:
                                file_name = file['Key'].split('/')[-1]
                                metadata = '';
                                try:
                                    metadata = s3.head_object(Bucket=BUCKET_NAME, Key=file['Key'])
                                    print(metadata)
                                except:
                                    print("Failed metadata {}".format(file['Key']))

                                if not any(filter in file_name for filter in apply_filter_arr):
                                    continue
                                val = file_name + " , " + str(file['LastModified']) + " , " + str(
                                    metadata['Metadata'])
                                print(val)
                                resp.append(val)

                msg["Success"]  = resp
            else:
                msg["Error"] = 'filelist is empty'
    except botocore.exceptions.ClientError as e:
        traceback.print_exc()
        msg["Error"] = 'AWS Error' + str(e)
        print(msg)
        return jsonify(msg), 500
    except Exception as e:
        msg["Error"] = 'Error connecting to AWS' + str(e)
        traceback.print_exc()
        return jsonify(msg), 500

    return jsonify(msg)


list_header = ['JOB_QUEUE,START DATE,STOP DATE,JOB NAME,JOB ID,JOB ARN,STATUS']

from awsdesktop import aws_batch_helper
@app.route("/getbatchjobinfo", methods=['GET', 'POST'])
def getbatchjobinfo():
    list = []
    msg = ''
    status = 200
    filter = request.form['filter_batch_by_app_prefix']
    if 'max_iter_count' in request.form:
        max_iter_count = request.form['maxresultsdepth']
    else:
        max_iter_count = 21
    start_time = request.form['starttime_batch']
    end_time = request.form['endtime_batch']

    if filter and start_time and end_time:
        try:
            list_data = aws_batch_helper.get_all_jobs_queues(start_time, end_time, filter)
            if len(list_data) > 0:
                # append the header
                list.extend(list_header)
                # append data
                list.extend(list_data)

        except botocore.exceptions.ClientError as e:
            msg = 'AWS Error : ' + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
        except Exception as e:
            msg = "Error getting etl job status " + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
    else:
        msg = 'App Prefix Filter , Start or End date/time is not selected'
        list = [msg]

    print(''.join(list))
    # return render_template("aws_desktop_access.html",list =list)
    data = {}
    data["list"] = list
    jsonData = json.dumps(data)

    return app.response_class(
        response=jsonData,
        status=status,
        mimetype='application/json'
    )


@app.route("/getbatchjoblogs", methods=['GET', 'POST'])
def getbatchjoblogs():
    list = []
    msg = 'Success'
    status = 200
    increased_time_windows_in_seconds = 300
    if request.method == 'POST':
        job_id = request.form['job_id']
        start_time = request.form['start_time']
        stop_time = request.form['stop_time']
    if request.method == 'GET':
        job_id = request.args['job_id']
        start_time = request.form['start_time']
        stop_time = request.form['stop_time']

    if job_id and stop_time and start_time:
        try:
            job_details_map = aws_batch_helper.get_batch_job_details(job_id)
            #starttime =  job_details_map["startedAt"]
            #endtime = job_details_map["stoppedAt"]
            logStreamName = job_details_map["logStreamName"]
            logGroup = '/aws/batch/job'
            logs_client = aws_utils.get_boto3_client('logs')
            #list_streams(logs_client, loggroup, parse_datetime(starttime), parse_datetime(endtime))
            memory_file, zipfileName, fileName = list_logs_extend_window(logs_client,logGroup, parse_datetime_est_to_equivalent_utc(start_time), parse_datetime_est_to_equivalent_utc(stop_time), 'streams', logStreamName, increased_time_windows_in_seconds)
            if memory_file:
                os.remove(fileName)
                return send_file(memory_file, mimetype='application/zip', attachment_filename=zipfileName, as_attachment=True)
        except botocore.exceptions.ClientError as e:
            traceback.print_exc()
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
                msg ="The object does not exist." + str(e)
            else:
                msg = 'AWS Error' + str(e)
                print( msg)
            #render_template("error.html", msglog=msg)
            return jsonify(msg), 500
        except Exception as e:
            status=500
            msg = 'Error connecting to AWS' + str(e)
            # printing stack trace
            traceback.print_exc()
            #return render_template("error.html", msglog=msg)
            return jsonify(msg), 500
    else:
        msg = 'Job Id or Start Time or Stop Time is not selected'
        #list = [msg]
        return jsonify(msg), 400
    # data = {}
    # data["list"] = msg
    # jsonData = json.dumps(data)
    # print('jsondata {0}'.format(jsonData))
    #
    # return app.response_class(
    #     response=jsonData,
    #     status=status,
    #     mimetype='application/json'
    # )




@app.route("/getbatchjobdetails", methods=['GET', 'POST'])
def getbatchjobdetails():
    list = []
    msg = ''
    status = 200
    job_id = request.form['job_id']
    if job_id:
        try:
            mapOfDetails = aws_batch_helper.get_batch_job_details(job_id)
        except botocore.exceptions.ClientError as e:
            msg = 'AWS Error : ' + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
        except Exception as e:
            msg = "Error getting etl job status " + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
    else:
        msg = 'Job Id is not selected'
        list = [msg]


    # return render_template("aws_desktop_access.html",list =list)
    data = {}
    data["list"] = mapOfDetails
    jsonData = json.dumps(data)
    print('jsondata {0}'.format(jsonData))

    return app.response_class(
        response=jsonData,
        status=status,
        mimetype='application/json'
    )

from awsdesktop import aws_step_function_helper
@app.route("/getjobinfo", methods=['GET', 'POST'])
def getjobinfo():
    msg = ''
    status = 200
    filter = request.form['filter_by_app_prefix']
    start_time = request.form['starttime_dash']
    end_time = request.form['endtime_dash']

    if filter and start_time and end_time:
        try:
            list = aws_step_function_helper.get_executions_by_step_func_arn(start_time, end_time, filter)
        except botocore.exceptions.ClientError as e:
            msg = 'AWS Error : ' + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
        except Exception as e:
            msg = "Error getting etl job status " + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
    else:
        msg = 'App Prefix Filter , Start or End date/time is not selected'
        list = [msg]

    print(''.join(list))
    # return render_template("aws_desktop_access.html",list =list)
    data = {}
    data["list"] = list
    jsonData = json.dumps(data)

    return app.response_class(
        response=jsonData,
        status=status,
        mimetype='application/json'
    )


@app.route("/getexecutionappid", methods=['GET', 'POST'])
def getexecutionappid():
    msg = ''
    status = 200
    if request.method == 'POST':
        execution_arn = request.form['executionArn']
    if request.method == 'GET':
        execution_arn = request.args['executionArn']

    if execution_arn:
        try:
            return aws_step_function_helper.getExecutionAppId(execution_arn)
            #list = [applogId]
        except botocore.exceptions.ClientError as e:
            msg = 'AWS Error : ' + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
            return jsonify(msg), 500
        except Exception as e:
            msg = "Error getting etl job status " + str(e)
            list = [msg]
            traceback.print_exc()
            status = 500
            return jsonify(msg), 500
    else:
        msg = 'Execution Arn is not available.'
        list = [msg]
        return jsonify(msg), 400
    # print(''.join(list))
    # # return render_template("aws_desktop_access.html",list =list)
    # data = {}
    # data["list"] = list
    # jsonData = json.dumps(data)
    #
    # return app.response_class(
    #     response=jsonData,
    #     status=status,
    #     mimetype='application/json'
    # )


# read from config

#from . import aws_utils
import awsdesktop.aws_utils as aws_utils

def readConfigProps():
    dictConfig = None
    global BUCKET_NAME
    global sse_args
    global local_dir
    try:
        currWrkingDir = os.getcwd()
        print(currWrkingDir)
        config_file =  currWrkingDir + os.path.sep + 'config.properties'
        print(config_file)
        dictConfig = aws_utils.read_properties_file(config_file)
        if not dictConfig or len(dictConfig.keys()) == 0:
            msg = 'config.properties file is empty.'
            print(msg)
            raise ValueError(msg)
        # read first item from dict and default  assign
        dict_values = dictConfig.values()
        dict_iter = iter(dict_values)
        first_line_value = next(dict_iter)
        BUCKET_NAME = first_line_value.split(',')[0]
        print("default bucket : {0}".format( BUCKET_NAME))
        # set kms key
        if ',' in first_line_value:
            sse_args['SSEKMSKeyId'] = first_line_value.split(',')[1]
        else:
            sse_args['SSEKMSKeyId'] = ''
        print("default kms key : {0}".format( sse_args['SSEKMSKeyId']))
        local_dir = dictConfig['local_dir']
        print("default local dir : {0}".format(local_dir))

    except :
        traceback.print_exc()
        msg = 'Please create config.properties file.'
        print(msg)
        raise ValueError(msg)
    return dictConfig

readConfigProps()

import webbrowser


log_output = None
if len(sys.argv) > 1 :
    log_output= sys.argv[1]
print(log_output)
if log_output:
    app.config['log_output'] = log_output
app.debug=True
# enable CORS
CORS(app, resources={r'/*': {'origins': '*'}})
#webbrowser.open_new('http://127.0.0.1:8080/local_aws_desktop')
#webbrowser.open('http://127.0.0.1:8080/local_aws_desktop')
#app.run(port=8080)
app.run(host = '0.0.0.0',port=8080)


