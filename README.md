# aws-one-view
Consolidated views of all the services associated with a single aws account. This runs standalone and tested on windows pc. Assumes the aws credentails are setup.
**See picture below:**
![image](https://user-images.githubusercontent.com/52529498/124082769-1a96e180-da1b-11eb-8bc4-8ef75a9f711f.png)



- cloudwatch logs - view and download. I had a tough time to search for logs, but using the user interface, inputing the time window and log group and plan to search via the user interface
- emr - Given the yarn application id, download the logs. We do have scheduled  processes which pull the yarn logs into the s3 folder, the intention of this option is to pull the logs right away after the job is complete without logging into EMR
- aws batch dashboard
- aws step function dashboard
- s3 file/folder upload and download
