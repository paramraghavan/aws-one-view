#subnit this as a job on EMR
import boto3
import os

# The name of the state machine
SF_NAME = 'SampleStepFunction-StateMachine1'
SampleStepFunction_DEF = '{   "Comment": "Job Orchestration for EDL HAO daily Workflow",   "StartAt": "DailyDataLoadSelectedEntityPass",   "States": {     "DailyDataLoadSelectedEntityPass": {       "Type": "Pass",       "Result": "dailyDataLoadsWorkflow",       "ResultPath": "$.dynamodbConfig.entityToUpdate",       "Next": "ExecutionChoice"     },     "ExecutionChoice": {       "Type": "Choice",       "Choices": [         {           "Variable": "$.skipAllDataLoads",           "StringEquals": "n",           "Next": "SkippedAllDataloadState"         },         {           "Variable": "$.skipAllDataLoads",           "StringEquals": "n",           "Next": "DataloadChoice"         }       ]     },     "SkippedAllDataloadState": {       "Type": "Pass",       "End": true     },     "DataloadChoice": {       "Type": "Choice",       "Choices": [         {           "Variable": "$.dynamodbConfig.dailydataloads.status",           "StringEquals": "DATALOAD_PREV_COMPLETE",           "Next": "DataloadPrevComplete"         },         {           "Variable": "$.dynamodbConfig.dailydataloads.status",           "StringEquals": "INPROGRESS",           "Next": "amtm-irdb-swap-parallel"         }       ]     },     "DataloadPrevComplete": {       "Type": "Pass",       "Result": "AWS Step Functions!",       "InputPath": "$.lambda",       "ResultPath": "$.data.lambdaresult",       "OutputPath": "$.data",       "End": true     },     "amtm-irdb-swap-parallel": {       "Type": "Parallel",       "End": true,       "Branches": [         {           "StartAt": "SkipAmtm ?",           "States": {             "SkipAmtm ?": {               "Type": "Choice",               "Choices": [                 {                   "Variable": "$.amtmDataLoadJob.skipExecution",                   "StringEquals": "y",                   "Next": "AMTMSkippedState"                 },                 {                   "Variable": "$.amtmDataLoadJob.skipExecution",                   "StringEquals": "n",                   "Next": "Amtm"                 }               ]             },             "AMTMSkippedState": {               "Type": "Pass",               "Result": {                 "AMTM": "SKIPPED"               },               "ResultPath": "$", 			  "OutputPath": "$.AMTM",               "End": true             },             "Amtm": {               "Type": "Pass",               "End": true             }           }         }       ]     }   } }'
ROLE_ARN = 'arn:aws:iam::12345678:role/pp-devl-instance-role'


def get_boto3_client(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
    session = boto3.session.Session()
    return session.client(service)


sfn = get_boto3_client('stepfunctions')

response = sfn.create_state_machine(
    name=SF_NAME,
    definition=SampleStepFunction_DEF,
    roleArn=ROLE_ARN
)

# print the statemachine Arn
print(response.get('stateMachineArn'))

