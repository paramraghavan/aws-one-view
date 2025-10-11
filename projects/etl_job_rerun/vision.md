'''
Build a python, pyflask based tool to rerun jobs
user shoudl be able to specify aws profile
start date tiem and end date time. if not specidiced assume all the data sets need to be ingested
idf startd date is specified and end date is not then pull all dataset from the start date time onwards
Source bucket s3:\\source_bucket\entity_name\dataset
Target bucket s3:\\destination_bucket\stage\entity_name\file_to_be_ingested.dat - .dat or .zip
we have a config file where we specify
source_entity and target entity for example
FHL source maps to FHL\stage
FNM source maps to FNM\stage
The source data looks like the following
s3://source_bucket/entity_name/Dataset134/year=2025/month=01/day=10/ENTITY_LDST_20250110_172614_r925264123.DAT
s3://source_bucket/entity_name/Dataset135/year=2025/month=01/day=2/ENTITY_LDST_20250210_172614_r925264123.DAT
Once the users chooses the profile, source and target bucket and enters the date
We parse the data from source bucket and add a row to pickle file for each of the entity specified in the config file
entityname, dataset, year, month, day, filename
FHL,Dataset123,2025,01,10,ENTITY_LDST_20250110_172614_r925264123.DAT
FHL,Dataset123,2025,02,10,ENTITY_LDST_20250210_172614_r925264123.DAT

Above is a pickle file, the pickle file is suffixed the aws profile name and datetimestamp
if this file exists user has option to choose this file to be loaded instead of parsing the source bucket to build the
entire pickle file, user can always go with creating new pickle file by parsing s3 source bucket again

We we can query this file from the ui from another tab and get only the relevant rows we need
Once we get the relevant rows, next step is
to make s3 call to copy the each file to destination bucket(called staging bucket) s3:
\\destination_bucket\stage\entity_name
so in our example we copy for entity FHL with no start and end data copy file to staging bucket - s3:
\\destination_bucket\stage\entity_name
ENTITY_LDST_20250110_172614_r925264123.DAT and ENTITY_LDST_20250210_172614_r925264123.DAT

In some case when we make a copy the file to destination bucket we to have a hook to call cleanup function for each of
the s3 calls, in some cases these calls are pass through
the cleanup is specify to dataset at entity level
so for FHL entity and Dataset134 the clean up is a pass thru but for Dataset135 we have to do specific action - could to
clean up some snowfalke tables udapted as part of the previous failed partial run of Dataset135
'''

Create tool for rerunning data ingestion jobs. Let me break down the requirements:

User inputs:

AWS profile selection
Start date/time (optional)
End date/time (optional)
Source bucket and target/staging bucket

Date handling logic:

If no dates specified: ingest all datasets
If only start date: ingest from start date onwards
If both dates: ingest between dates

Bucket structure:

Source: s3://source_bucket/entity_name/Dataset###/year=YYYY/month=MM/day=DD/ENTITY_LDST_YYYYMMDD_HHMMSS_r######.DAT
Target: s3://destination_bucket/stage/entity_name/filename.dat (or .zip)

Config file:

Maps source entities to target entities
Example: FHL source → FHL/stage, FNM source → FNM/stage

Workflow:
a. Parse source bucket based on config entities and date range
b. Store results in pickle file with columns: entityname, dataset, year, month, day, filename
c. Pickle file naming: suffixed with AWS profile name and timestamp
d. Option to load existing pickle file or create new one
e. Query/filter pickle file from UI (separate tab)
f. Copy filtered files from source to destination bucket
g. Execute cleanup hooks for specific entity/dataset combinations (some are pass-through)
Cleanup hooks:

Dataset-specific at entity level
Some are pass-through (no action)
Some require specific actions (e.g., Snowflake table cleanup for failed partial runs)
