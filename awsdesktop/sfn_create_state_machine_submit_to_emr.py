#subnit this as a job on EMR
import boto3
import os

# The name of the state machine
SF_NAME = 'SampleStepFunction-StateMachine'


SampleStepFunction_DEF = '{   "Comment": "Job Orchestration for EDL HAO daily Workflow",   "StartAt": "DailyDataLoadSelectedEntityPass",   "States": {     "DailyDataLoadSelectedEntityPass": {       "Type": "Pass",       "Result": "dailyDataLoadsWorkflow",       "ResultPath": "$.dynamodbConfig.entityToUpdate",       "Next": "ExecutionChoice"     },     "ExecutionChoice": {       "Type": "Choice",       "Choices": [         {           "Variable": "$.skipAllDataLoads",           "StringEquals": "n",           "Next": "SkippedAllDataloadState"         },         {           "Variable": "$.skipAllDataLoads",           "StringEquals": "n",           "Next": "DataloadChoice"         }       ]     },     "SkippedAllDataloadState": {       "Type": "Pass",       "End": true     },     "DataloadChoice": {       "Type": "Choice",       "Choices": [         {           "Variable": "$.dynamodbConfig.dailydataloads.status",           "StringEquals": "DATALOAD_PREV_COMPLETE",           "Next": "DataloadPrevComplete"         },         {           "Variable": "$.dynamodbConfig.dailydataloads.status",           "StringEquals": "INPROGRESS",           "Next": "amtm-irdb-swap-parallel"         }       ]     },     "DataloadPrevComplete": {       "Type": "Pass",       "Result": "AWS Step Functions!",       "InputPath": "$.lambda",       "ResultPath": "$.data.lambdaresult",       "OutputPath": "$.data",       "End": true     },     "amtm-irdb-swap-parallel": {       "Type": "Parallel",       "End": true,       "Branches": [         {           "StartAt": "SkipAmtm ?",           "States": {             "SkipAmtm ?": {               "Type": "Choice",               "Choices": [                 {                   "Variable": "$.amtmDataLoadJob.skipExecution",                   "StringEquals": "y",                   "Next": "AMTMSkippedState"                 },                 {                   "Variable": "$.amtmDataLoadJob.skipExecution",                   "StringEquals": "n",                   "Next": "Amtm"                 }               ]             },             "AMTMSkippedState": {               "Type": "Pass",               "Result": {                 "AMTM": "SKIPPED"               },               "ResultPath": "$", 			  "OutputPath": "$.AMTM",               "End": true             },             "Amtm": {               "Type": "Pass",               "End": true             }           }         }       ]     }   } }'
# at command line type
# aws emr add-steps --cluster-id j-4GWN3RORYMZC --steps Type=spark,Name=SubmitJobFromLocalDesktop,ActionOnFailure=CONTINUE,Args=s3://pp/awslocaldesktop/scripts/sfn_create_state_machine_submit_to_emr.py
#
# Arn of the IAM role to use for this state machine
# Replace the value with a valid RoleArn
ROLE_ARN = 'arn:aws:iam::12345678:role/ygpp-devl-instance-role'
sfn = boto3.client('stepfunctions')

response = sfn.create_state_machine(
    name=SF_NAME,
    definition=SampleStepFunction_DEF,
    roleArn=ROLE_ARN
)

# print the statemachine Arn
print(response.get('stateMachineArn'))