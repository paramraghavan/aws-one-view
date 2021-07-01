import boto3
import os
import pprint
from awsdesktop import aws_utils
from awsdesktop import send_data_to_aws

# comma separated filter criteria, this filters by queue name
def get_all_jobs_queues(start_date_time, end_date_time, filter='pp'):
    list_filter = filter.split(',')
    list_of_job_queues = []
    for item in list_filter:
        list = list_job_queues(item)
        list_of_job_queues.extend(list)

    #pp = pprint.PrettyPrinter(indent=4)
    #pp.pprint(list_sfn)

    list_of_job_executions = list_jobs(list_of_job_queues, start_date_time, end_date_time)
    #pp.pprint(list_of_job_executions)

    return  list_of_job_executions


def list_job_queues(filter='pp'):
    job_queue_list = []
    batch = aws_utils.get_boto3_client('batch')
    response = batch.describe_job_queues()
    # pp = pprint.PrettyPrinter(indent=4)
    # pp.pprint(response)
    print(response['jobQueues']) #stateMachineArn
    if  'jobQueues' in response and response['jobQueues'] and len(response['jobQueues']) > 0:
        for item_dict in response['jobQueues']:
            if filter == '*' and 'ENABLED' in item_dict['state'] and 'VALID' in item_dict['status']:
                job_queue_list.append(item_dict['jobQueueArn'])
            elif filter in item_dict['jobQueueArn'] and 'ENABLED' in item_dict['state'] and 'VALID' in item_dict['status']:
                job_queue_list.append(item_dict['jobQueueArn'])


    while 'nextToken' in response :
        response = batch.describe_job_queues(
            nextToken = response['nextToken']
        )
        if 'jobQueues' in response and response['jobQueues'] and len(response['jobQueues']) > 0:
            for item_dict in response['jobQueues']:
                if filter == '*' and 'ENABLED' in item_dict['state'] and 'VALID' in item_dict['status']:
                    job_queue_list.append(item_dict['jobQueueArn'])
                elif filter in item_dict['jobQueueArn'] and 'ENABLED' in item_dict['state'] and 'VALID' in item_dict[
                    'status']:
                    job_queue_list.append(item_dict['jobQueueArn'])

    return job_queue_list
#allowed_states=['RUNNING','SUCCEEDED', 'FAILED', 'PENDING', 'RUNNABLE','STARTING','SUBMITTED']
#allowed_states=['SUCCEEDED
# unlike the step function execution list wherein the list are returned in descending order, the jobs executions are not returned in any particular order
# hence using max iteration count
def list_jobs(job_queue_list, filter_start_time_in, filter_end_time_in, max_iter_count = 21, allowed_states=['RUNNING', 'SUCCEEDED', 'FAILED', 'PENDING', 'RUNNABLE', 'STARTING', 'SUBMITTED'], ):
    list_of_job_executions = []
    batch = aws_utils.get_boto3_client('batch')
    filter_start_time = get_timestamp_from_str(filter_start_time_in)
    filter_end_time = get_timestamp_from_str(filter_end_time_in)
    # The Amazon Resource Name (ARN) of the state machine to execute.
    # Example - arn:aws:states:us-west-2:112233445566:stateMachine:HelloWorld-StateMachine
    #STATE_MACHINE_ARN = 'arn:aws:states:us-east-1:123456678:stateMachine:pp-devl-workflow-v01'
    state = ''
    #max_iter_count = 20
    current_loop_count = 0
    for q in job_queue_list:
        current_loop_count = 0
        for s in  allowed_states:
            current_loop_count = 1
            response = batch.list_jobs( jobQueue = q, jobStatus = s)
            #pp = pprint.PrettyPrinter(indent=4)
            #pp.pprint(response)
            #print(response['executions'])
            if 'jobSummaryList' in response and response['jobSummaryList'] and len(response['jobSummaryList']) > 0:
                for item_dict in response['jobSummaryList']:
                    if item_dict['status'] in allowed_states:
                        check_status(batch, item_dict, list_of_job_executions, filter_start_time, filter_end_time, q)

            while 'nextToken' in response.keys():
                # pp = pprint.PrettyPrinter(indent=4)
                # pp.pprint(response)
                current_loop_count = current_loop_count + 1
                if max_iter_count == current_loop_count:
                    break;
                response = batch.list_jobs(  jobQueue = q, jobStatus = s, nextToken = response['nextToken'])
                if 'jobSummaryList' in response and response['jobSummaryList'] and len(response['jobSummaryList']) > 0:
                    for item_dict in response['jobSummaryList']:
                        if item_dict['status'] in allowed_states:
                            check_status(batch, item_dict, list_of_job_executions, filter_start_time,
                                                 filter_end_time, q)

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(list_of_job_executions)
    return list_of_job_executions

import datetime
def check_status(batch, item_dict, list_of_job_executions, filter_start_time, filter_end_time, q):
    job_name = item_dict['jobName']
    job_id = item_dict['jobId']
    job_arn = item_dict['jobArn']
    job_status = item_dict['status']
    #createdAt
    status = item_dict['status']
    #print('status job_id {} {}'.format(status, job_id))
    #print('job_start_date {}'.format(item_dict['startedAt']))
    if 'startedAt' in item_dict:
        job_start_date = item_dict['startedAt']/1e3
    else:
        print('Using createdAt instead of startAt')
        job_start_date = item_dict['createdAt'] / 1e3

    if status == 'RUNNING':
        job_stop_date = datetime.datetime.now().timestamp()
    else:
        if 'stoppedAt' in item_dict:
            job_stop_date = item_dict['stoppedAt']/1e3
        else:
            job_stop_date = 'NA'

    job_start_timestamp = get_datetime_from_num(job_start_date)
    if job_start_date < filter_start_time:
        # skip
        return

    start_date_str =  get_timestamp_str(job_start_timestamp)
    stop_date_str  = get_timestamp_str(get_datetime_from_num(job_stop_date))

    if job_start_date >= filter_start_time and job_start_date <= filter_end_time:
        result = '{0},{1},{2},{3},{4},{5},{6}'.format(q, start_date_str, stop_date_str, job_name, job_id, job_arn, status)
        #print(result)
        list_of_job_executions.append(result)
    else:
        pass # skip

#aws batch describe-jobs --jobs 2ab1612e-2e5a-4ac3-a9ac-f96bd86281f8
#["jobs][0]["jobName"]
#["jobs][0]["container"][ "logStreamName"]
#["jobs][0]["container"][ "taskArn"]
#["jobs][0]["container"][ "command"]
def get_batch_job_details(job_id):
    batch = aws_utils.get_boto3_client('batch')
    response = batch.describe_jobs(jobs=[job_id,])
    job_details_map = {}
    if 'jobs' in response:
        job_details_map["jobName"] = response["jobs"][0]["jobName"]
        job_details_map["jobId"] = job_id
        job_details_map["logStreamName"] = response["jobs"][0]["container"]["logStreamName"]
        job_details_map["taskArn"] = response["jobs"][0]["container"]["taskArn"]
        job_details_map["command"] = response["jobs"][0]["container"]["command"]
        job_details_map["createdAt"] = response["jobs"][0]["createdAt"]
        job_details_map["startedAt"] = response["jobs"][0]["startedAt"]
        job_details_map["stoppedAt"] = response["jobs"][0]["stoppedAt"]
        job_details_map["jobDefinition"] = response["jobs"][0]["jobDefinition"]
        job_details_map["statusReason"] = response["jobs"][0]["statusReason"]
        job_details_map["status"] = response["jobs"][0]["status"]
        job_details_map["fullDetails"] = response["jobs"][0]

    return job_details_map


def get_datetime_from_num(date_time_num):
    if date_time_num == 'NA':
        return date_time_num
    return datetime.datetime.fromtimestamp(date_time_num)

#2020-12-01 07:00:00
#20201201125826782000
def get_timestamp_str(datetime_val):
    if datetime_val == 'NA':
        return datetime_val
    #return datetime_val.strftime('%Y-%m-%d %H:%M:%S')
    return datetime_val.strftime('%m/%d/%Y %H:%M:%S')

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
    #list_sfn = list_job_queues('*')
    list_sfn = list_job_queues()
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(list_sfn)
    start_date_time = get_timestamp_from_str("2021-01-14 07:00:00")
    end_date_time = get_timestamp_from_str("2021-01-15 08:00:00")
    #
    list_of_executions = list_jobs(list_sfn, '2021-01-14 07:00:00','2021-01-15 08:00:0')
    pp.pprint(list_of_executions)