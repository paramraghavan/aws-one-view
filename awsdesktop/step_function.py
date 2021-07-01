import boto3
import os
import pprint


def get_boto3_client(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
    session = boto3.session.Session()
    return session.client(service)


def list_step_functions(filter='hao-'):
    sfn_list = []
    sfn = get_boto3_client('stepfunctions')
    response = sfn.list_state_machines()
    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(response)
    #print(response['stateMachines']) #stateMachineArn
    if  'stateMachines' in response and response['stateMachines'] and len(response['stateMachines']) > 0:
        for item_dict in response['stateMachines']:
            if filter in item_dict['stateMachineArn']:
                sfn_list.append(item_dict['stateMachineArn'])

    for nextToken in response:
        if nextToken:
            response = sfn.list_state_machines(
                nextToken = response['nextToken']
            )
        if 'stateMachines' in response and response['stateMachines'] and len(response['stateMachines']) > 0:
            for item_dict in response['stateMachines']:
                if filter in item_dict['stateMachineArn']:
                    sfn_list.append(item_dict['stateMachineArn'])

    return sfn_list

def list_executions(list_state_machine, filter_start_time, filter_end_time, allowed_states=['SUCCEEDED', 'FAILED', 'ABORTED'],):
    list_of_executions = []
    #sfn = boto3.client('stepfunctions')
    sfn = get_boto3_client('stepfunctions')

    # The Amazon Resource Name (ARN) of the state machine to execute.
    # Example - arn:aws:states:us-west-2:112233445566:stateMachine:HelloWorld-StateMachine
    #STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:123456789:stateMachine:ygpp-devl-workflow-v01'
    state = ''
    for sm in list_state_machine:
        response = sfn.list_executions( stateMachineArn = sm)
        #pp = pprint.PrettyPrinter(indent=4)
        #pp.pprint(response)
        #print(response['executions'])
        if 'executions' in response and response['executions'] and len(response['executions']) > 0:
            for item_dict in response['executions']:
                if item_dict['status'] in allowed_states:
                    state = check_status(item_dict, list_of_executions, filter_start_time, filter_end_time)
                    if state == 'stop':
                        break;

        if state != 'stop':
            while 'nextToken' in response.keys():
                if state == 'stop':
                    break;
                pp = pprint.PrettyPrinter(indent=4)
                pp.pprint(response)
                response = sfn.list_executions( stateMachineArn=sm, nextToken = response['nextToken'])
                if 'executions' in response and response['executions'] and len(response['executions']) > 0:
                    for item_dict in response['executions']:
                        if item_dict['status'] in allowed_states:
                            state = check_status(item_dict, list_of_executions, filter_start_time, filter_end_time)
                            if state == 'stop':
                                break;

    return list_of_executions


def check_status(item_dict, list_of_executions, filter_start_time, filter_end_time):
    state = ''
    status = item_dict['status']
    stateMachineArn = item_dict['stateMachineArn']
    name = item_dict['name']
    start_date = item_dict['startDate']
    stop_date = item_dict['stopDate']
    start_timestamp = start_date.timestamp()
    if start_timestamp < filter_start_time:
        # stop
        state = 'stop'
    if start_timestamp >= filter_start_time and start_timestamp <= filter_end_time:
        result = '{0},{1},{2},{3},{4},{5}'.format(name, status, stateMachineArn.split(':')[-1], get_timestamp_str(start_date), get_timestamp_str(stop_date), stateMachineArn)
        #print(result)
        list_of_executions.append(result)

    return state

#2020-12-01 07:00:00
#20201201125826782000
def get_timestamp_str(datetime_val):
    #return datetime_val.strftime('%Y-%m-%d %H:%M:%S%f')
    return datetime_val.strftime('%Y-%m-%d %H:%M:%S')


#  The default is 10,000 events.
MAX_EVENTS_PER_CALL = 10000
from collections import deque
import sys, traceback
import datetime
import json
def list_jobs(filter='hao'):
    # The Amazon Resource Name (ARN) of the state machine to execute.
    # Example - arn:aws:states:us-west-2:112233445566:stateMachine:HelloWorld-StateMachine
    STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:112233445566:stateMachine:ygpp-devl-workflow-v01'

    batch_client = get_boto3_client('batch')
    #paginator = batch.get_paginator("list_jobs")
    # for page in paginator.paginate(**kwargs):
    #     for group in page.get('logGroups', []):
    #         yield group['logGroupName']

    do_wait = object()
    def generator():
        #interleaving_sanity = deque(maxlen=MAX_EVENTS_PER_CALL)
        kwargs = {'jobQueue': 'ygpp-prod-app-01-02',  'jobStatus':'SUCCEEDED'}
        #'jobStatus': 'SUBMITTED', 'jobStatus':'PENDING', 'jobStatus':'RUNNABLE', 'jobStatus':'STARTING', 'jobStatus':'RUNNING', , 'jobStatus':'FAILED'

        while True:
            response = batch_client.list_jobs(**kwargs)
            pp = pprint.PrettyPrinter(indent=4)
            pp.pprint(response)
            for event in response.get('jobSummaryList', []):
                if filter in event['jobName'] :
                #if event['jobName'] not in interleaving_sanity:
                    eventCreatedAt, eventStartedAt, eventStoppedAt = '', '', ''
                    if event['createdAt']:
                        eventCreatedAt =  str(datetime.datetime.fromtimestamp(event['createdAt'] / 1e3))
                    if event['startedAt']:
                        eventStartedAt =  str(datetime.datetime.fromtimestamp(event['startedAt'] / 1e3))
                    if event['stoppedAt']:
                        eventStoppedAt = str(datetime.datetime.fromtimestamp(event['stoppedAt'] / 1e3))

                    #interleaving_sanity.append(event['jobName'] + ", " + event['status'] + ", " + eventCreatedAt + ", " + eventStartedAt + ", " + eventStoppedAt )
                    yield event['jobName'] + ", " + event['status'] + ", " + eventCreatedAt + ", " + eventStartedAt + ", " + eventStoppedAt

            if 'nextToken' in response:
                kwargs['nextToken'] = response['nextToken']
            else:
                yield do_wait

    def consumer():
        list = []
        for event in generator():
            if event is do_wait:
                return
            list.append(event)
        return list

    try:
        print('Download started!')
        print('------------------------------------------------------------------------------------------')
        lst= consumer()
        data = {}
        data["list"] = lst
        jsonData = json.dumps(data)
        log_output = True
        if log_output:
            print(jsonData)
            sys.stdout.flush()
        print('Download complete!')
        print('------------------------------------------------------------------------------------------')
    except KeyboardInterrupt:
        print('Closing...\n')
        os._exit(0)
    except :
        traceback.print_exc()
        raise

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