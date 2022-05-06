# aws-one-view
Consolidated views of all the services associated with a single aws account. This runs standalone and tested on windows pc. Assumes the aws credentials are setup.
**See picture below:**
![image](https://user-images.githubusercontent.com/52529498/124082769-1a96e180-da1b-11eb-8bc4-8ef75a9f711f.png)



- cloudwatch logs - view and download. I had a tough time to search for logs, but using the user interface, inputing the time window and log group and plan to search via the user interface
- emr - Given the yarn application id, download the logs. We do have scheduled  processes which pull the yarn logs into the s3 folder, the intention of this option is to pull the logs right away after the job is complete without logging into EMR
- aws batch dashboard
- aws step function dashboard
- s3 file/folder upload and download

## CloudWatch
- Cloudwatch alarms 
- Cloudwatch events rules - based on events or create cron jobs
  - Event pattern- create an event when any EC2 instance goes into running state
  - Schedule - create a scheduled job like a cronjob in unix
- Cloudwatch logs
- Cloudwatch log metrics- and we can add alarm to cloud watch log metrics
   https://insight.full360.com/how-to-turn-your-logs-into-valuable-metrics-and-actionable-alarms-using-cloudwatch-c38bfccfd8a5