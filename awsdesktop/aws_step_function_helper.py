import boto3
import os
import pprint
from awsdesktop import aws_utils
from awsdesktop import send_data_to_aws

def list_step_functions(filter='pp-'):
    sfn_list = []
    sfn = aws_utils.get_boto3_client('stepfunctions')
    response = sfn.list_state_machines()
    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(response)
    #print(response['stateMachines']) #stateMachineArn
    if  'stateMachines' in response and response['stateMachines'] and len(response['stateMachines']) > 0:
        for item_dict in response['stateMachines']:
            if filter in item_dict['stateMachineArn']:
                sfn_list.append(item_dict['stateMachineArn'])


    while 'nextToken' in response :
        response = sfn.list_state_machines(
            nextToken = response['nextToken']
        )
        if 'stateMachines' in response and response['stateMachines'] and len(response['stateMachines']) > 0:
            for item_dict in response['stateMachines']:
                if filter in item_dict['stateMachineArn']:
                    sfn_list.append(item_dict['stateMachineArn'])

    return sfn_list

def list_executions(list_state_machine, filter_start_time_in, filter_end_time_in, allowed_states=['RUNNING','SUCCEEDED', 'FAILED', 'ABORTED'],):
    list_of_executions = []
    #sfn = boto3.client('stepfunctions')
    sfn = aws_utils.get_boto3_client('stepfunctions')
    filter_start_time = get_timestamp_from_str(filter_start_time_in)
    filter_end_time = get_timestamp_from_str(filter_end_time_in)
    # The Amazon Resource Name (ARN) of the state machine to execute.
    # Example - arn:aws:states:us-west-2:112233445566:stateMachine:HelloWorld-StateMachine
    #STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:112233445566:stateMachine:ygpp-devl-workflow-v01'
    state = ''
    for sm in list_state_machine:
        response = sfn.list_executions( stateMachineArn = sm)
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(response)
        #print(response['executions'])
        if 'executions' in response and response['executions'] and len(response['executions']) > 0:
            for item_dict in response['executions']:
                if item_dict['status'] in allowed_states:
                    state = check_status(sfn, item_dict, list_of_executions, filter_start_time, filter_end_time)
                    if state == 'stop':
                        break;

        if state != 'stop':
            while 'nextToken' in response.keys():
                if state == 'stop':
                    break;
                # pp = pprint.PrettyPrinter(indent=4)
                # pp.pprint(response)
                response = sfn.list_executions( stateMachineArn=sm, nextToken = response['nextToken'])
                if 'executions' in response and response['executions'] and len(response['executions']) > 0:
                    for item_dict in response['executions']:
                        if item_dict['status'] in allowed_states:
                            state = check_status(sfn, item_dict, list_of_executions, filter_start_time, filter_end_time)
                            if state == 'stop':
                                break;

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(list_of_executions)
    return list_of_executions

import datetime
def check_status(sfn, item_dict, list_of_executions, filter_start_time, filter_end_time):
    state = ''
    executionArn = item_dict['executionArn']
    applicationId = ''

    status = item_dict['status']
    # if status != 'SUCCEEDED' :
    #     applicationId = getExecutionDetails(sfn, executionArn)

    stateMachineArn = item_dict['stateMachineArn']
    start_date = item_dict['startDate']
    if status == 'RUNNING':
        stop_date = datetime.datetime.now()
    else:
        stop_date = item_dict['stopDate']

    start_timestamp = start_date.timestamp()
    if start_timestamp < filter_start_time:
        # stop
        state = 'stop'

    start_date_str =  get_timestamp_str(start_date)
    stop_date_str  = get_timestamp_str(stop_date)
    name = '{0} {1} {2} {3}'.format(item_dict['name'], applicationId, start_date_str, stop_date_str)
    if start_timestamp >= filter_start_time and start_timestamp <= filter_end_time:
        result = '{0},{1},{2},{3},{4},{5}'.format(name, status, stateMachineArn.split(':')[-1], start_date_str, stop_date_str, executionArn)
        #print(result)
        list_of_executions.append(result)

    return state

import json


def getExecutionAppId(executionArn):
    sfn = aws_utils.get_boto3_client('stepfunctions')
    return getExecutionDetails(sfn, executionArn)

import json
from flask import send_file

def getExecutionDetails(sfn, executionArn):
    execution_history = sfn.get_execution_history(executionArn=executionArn)
    #print(execution_history)
    applicationId = ''
    dataList = execution_history['events']
    listToStr = ' '.join([str(elem) for elem in dataList])
    localdir = send_data_to_aws.getLocalDir()
    filename = executionArn.split(':')[-1]
    filewithpath = localdir + filename
    #jsonData = json.dumps(dataList)
    f = open(filewithpath, "w")
    f.write(listToStr)
    f.close()
    return zip_file(listToStr, filewithpath, filename)


import io
import zipfile
import time
def zip_file1(info, filewithpath, filename, localdir):
    file_name_zip = '{0}.zip'.format(filename)
    file_zip = '{0}{1}.zip'.format(localdir, filename)
    print('creating archive')
    zf = zipfile.ZipFile(file_zip, mode='w')
    try:
        print('adding' + filewithpath)
        zf.write(filewithpath)
    finally:
        print('closing')
        zf.close()

    #return send_file(memory_file, attachment_filename=file_zip, as_attachment=True)
    return send_file(file_zip, mimetype='application/zip', attachment_filename=file_name_zip, as_attachment=True)


def zip_file(info, filewithpath, filename):
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w') as zf:
        zf.write(filewithpath)
    memory_file.seek(0)
    file_zip = '{0}.zip'.format(filename)
    #return send_file(memory_file, attachment_filename=file_zip, as_attachment=True)
    return send_file(memory_file, mimetype='application/zip', attachment_filename=file_zip, as_attachment=True)




def getExecutionDetails_prev(sfn, executionArn):
    execution_history = sfn.get_execution_history(executionArn=executionArn)
    #print(execution_history)
    applicationId = ''
    dataList = execution_history['events']
    listToStr = ' '.join([str(elem) for elem in dataList])
    result = listToStr.split('"emrStepId":')
    if len(result) > 1:
        result1 = result[1].split('"emrStepApplicationHost":')
        if len(result) > 0:
            applicationId = result1[0]

    return applicationId

def getExecutionDetails1(sfn, executionArn):
    execution_history = sfn.get_execution_history(executionArn=executionArn)
    #print(execution_history)
    dataList = execution_history['events']
    applicationId = 'Application Log Id is not available.'
    for index in range(len(dataList)):
        # print(datalist[index])
        for k, v in (dataList[index]).items():
            #print(k)
            if k == 'stateEnteredEventDetails':
                #print(v)
                for i, j in v.items():
                    if i == 'input':
                        result =j.split('"emrStepId":')
                        if result and len(result) > 1:
                            applicationId = applicationId + result[1].split(',')[1]
                            return applicationId
    return applicationId


def get_executions_by_step_func_arn(start_date_time, end_date_time, filter='pp'):
    list_filter = filter.split(',')
    list_sfn = []
    for item in list_filter:
        list = list_step_functions(item)
        list_sfn.extend(list)

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(list_sfn)

    list_of_executions = list_executions(list_sfn, start_date_time, end_date_time)
    pp.pprint(list_of_executions)

    return  list_of_executions

#2020-12-01 07:00:00
#20201201125826782000
def get_timestamp_str(datetime_val):
    #return datetime_val.strftime('%Y-%m-%d %H:%M:%S%f')
    return datetime_val.strftime('%Y-%m-%d %H:%M:%S')

def get_timestamp_str_mmddyyyy(datetime_val):
    #return datetime_val.strftime('%Y-%m-%d %H:%M:%S%f')
    return datetime_val.strftime('%m/%d/%Y %H:%M:%S')

from dateutil.parser import parse
def get_timestamp_from_str(str_time):
    return parse(str_time).timestamp()

#input_start_date_time = get_timestamp_from_str("2020-10-08 11:00:00")
#input_end_date_time = get_timestamp_from_str("2020-10-08 12:00:00")

if __name__ == "__main__":
    #list_jobs()
    #list_executions()
    list_sfn = list_step_functions()
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(list_sfn)
    start_date_time = get_timestamp_from_str("2020-12-01 07:00:00")
    end_date_time = get_timestamp_from_str("2020-12-31 08:00:00")

    list_of_executions = list_executions(list_sfn, start_date_time,end_date_time)
    pp.pprint(list_of_executions)