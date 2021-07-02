`#########################################################################################################################
## Motivation to build this :  A task was assigned, this is to search for irdb logs in cloudwatch, it was very painful.##
#########################################################################################################################


####  Alpha version ######


#Pre-requisites:
-----------------
1. python 3.5 + above, aws cli, boto3, flask
2. On our laptop's we may just need flask
3. python -m pip install flask --user --trusted-host pypi.org
4. python -m pip install flask_cors --user --trusted-host pypi.org
5. python -m pip install awscli --user --trusted-host pypi.org --> you should be already have this installed.

AWS CLI
------------------
- Install aws cli
  python -m pip aws
  install aws cli msi executable
  - https://s3.amazonaws.com/aws-cli/AWSCLI64PY3.msi

- run  'aws configure' from command line
AWS Access Key ID [None]: accesskey
AWS Secret Access Key [None]: secretkey
Default region name [None]: 
Default output format [None]

-run  'aws configure' from command line
AWS Access Key ID [None]: accesskey
AWS Secret Access Key [None]: secretkey
Default region name [None]: 
Default output format [None]

#Modify:
-------------
1. Modify the config.properties with correct bucket name(s) and kms key(s):
    envdev=dev-us-east-1-edl,alias/kmskey/ab0
2. Update the proxy values as need in aws_utils.py:
    os.environ['HTTPS_PROXY'] = 'abc.company.com:3071'
    os.environ['HTTP_PROXY'] = 'abc.company.com:3071'

#Steps to run:
-----------------
1. next run run.bat
2. In the browser utl type -->  localhost:8080

#Errors
If you getting Aws Error, this means the you may not be connected to VPN and/or your aws credentials have expired.
set "HTTP_PROXY=http://proxy.com:10009"
set "HTTPS_PROXY=http://proxy.com:10009"



#Initial Setup
In order to run these tests, we’ll need to create a Python virtual environment with venv to install the dependencies in test-requirements.txt. To do this we can follow these steps:

To create a virtual environment called venv run: python -m venv venv
To activate the environment (on a Mac and most Linux machines): source venv/bin/activate
To activate the environment (on Windows with cmd.exe): venv\Scripts\activate.bat
To activate the environment (on Windows with PowerShell): venv\Scripts\Activate.ps1
Then, install the dependencies: pip3 install -r requirements.txt
python -m pip install  -r requirements.txt  --trusted-host pypi.org

#References:
----------
1. Got the idea for cloudwatch logs from  https://github.com/jorgebastida/awslogs. 
   This is a command line to pull logs, it has lots of options.
2. https://stackoverflow.com/questions/20646822/how-to-serve-static-files-in-flask
3. https://stackoverflow.com/questions/4545311/download-a-file-by-jquery-ajax
4. manage htmlpage state --> https://stackoverflow.com/questions/30244915/maintain-state-of-page-after-refresh
5. http://bl.ocks.org/dk8996/5538271

#Python threading
https://realpython.com/intro-to-python-threading/

