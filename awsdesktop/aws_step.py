import boto3
import json
import os

def get_boto3_client(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
    #return boto3.client(service)
    #aws_access_key_id, aws_secret_access_key, aws_session_token, region = getAWSKeys()
    #os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    #os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    session = boto3.session.Session()
    return session.client(service)

# from datetime import datetime
#
# timestamp = 1605704375.449
# dt_object = datetime.fromtimestamp(timestamp)
#
# print("dt_object =", dt_object)
# print("type(dt_object) =", type(dt_object))

import boto3
from dateutil.parser import parse
import json

client = get_boto3_client('stepfunctions')
list_state_machines_paginator = client.get_paginator('list_state_machines')
response_iterator_0 = list_state_machines_paginator.paginate()
stateMachine_arns_list  = []

for items in response_iterator_0:
    for x in items['stateMachines']:
        if True: #'pp-' in x['stateMachineArn']:
            #print(x['stateMachineArn'],x['name'],x['creationDate'])
            stateMachine_arns_list.append(x['stateMachineArn'])

print(stateMachine_arns_list)

def get_timestamp_from_str(str_time):
    return parse(str_time).timestamp()

#input_start_date_time = get_timestamp_from_str("2020-10-08 11:00:00")
#input_end_date_time = get_timestamp_from_str("2020-10-08 12:00:00")

input_start_date_time = get_timestamp_from_str("2020-12-28 07:00:00")
input_end_date_time = get_timestamp_from_str("2020-12-31 08:00:00")

failed_executions_arns_list = []

list_executions_paginator = client.get_paginator("list_executions")
for arns_0 in stateMachine_arns_list:
    response_iterator_1 = list_executions_paginator.paginate(stateMachineArn=arns_0)
    if response_iterator_1['nextToken']:
        print(response_iterator_1['nextToken'])
    for stepfn_executions in response_iterator_1:
        for values in stepfn_executions['executions']:
            #print(values)
            if values['status'] == 'failed'.upper():
                failed_executions_arns = values['executionArn']
                #print(failed_executions_arns, values['startDate'])
                stepfn_start_date_time = get_timestamp_from_str(str(values['startDate']))
                stepfn_end_date_time = get_timestamp_from_str(str(values['stopDate']))
                if stepfn_start_date_time >= input_start_date_time and stepfn_end_date_time <= input_end_date_time:
                    #print(failed_executions_arns,values['startDate'],values['stopDate'])
                    failed_executions_arns_list.append(failed_executions_arns)
#print(failed_executions_arns_list)

for arns_1 in failed_executions_arns_list:
    execution_history = client.get_execution_history(executionArn=arns_1)
    #print(execution_history)
    dataList = execution_history['events']
    for index in range(len(dataList)):
        # print(datalist[index])
        for k, v in (dataList[index]).items():
            # print(v)
            if k == 'lambdaFunctionScheduledEventDetails':
                # print(v)
                for i, j in v.items():
                    if 'Succeeded'.upper() not in j:
                        print(json.loads(j))
