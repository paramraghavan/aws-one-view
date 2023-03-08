# read properties file ito a dict

def read_properties_file(file_name):
    properties = {}
    with open(file_name) as fp:
        for line in fp:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('[default') :
                continue

            key, value = __parse_line__(line)
            print('key, value : {0}, {1}'.format(key, value))
            properties[key] = value
    return properties

def __parse_line__(input):
    key, value = input.split('=', maxsplit=1)
    key = key.strip()  # handles key = value as well as key=value
    value = value.strip()

    return key, value


# read aws credential tokens
from pathlib import Path
import os
import boto3

aws_profile = 'dev'

def get_boto3_resource(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
    session = boto3.session.Session(profile_name=aws_profile)
    return session.resource(service)
    #return boto3.resource(service)


def get_boto3_client(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
    #return boto3.client(service)
    #aws_access_key_id, aws_secret_access_key, aws_session_token, region = getAWSKeys()
    #os.environ['AWS_ACCESS_KEY_ID'] = aws_access_key_id
    #os.environ['AWS_SECRET_ACCESS_KEY'] = aws_secret_access_key
    session = boto3.session.Session(profile_name=aws_profile)
    return session.client(service)


if __name__ == "__main__":
    print(__name__)
    s3 = get_boto3_client('s3')
    # Retrieve the list of existing buckets
    s3 = boto3.client('s3')
    response = s3.list_buckets()

    # Output the bucket names
    print('Existing buckets:')
    for bucket in response['Buckets']:
        print(f'  {bucket["Name"]}')
