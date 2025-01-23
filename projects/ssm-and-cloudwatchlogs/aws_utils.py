import boto3

aws_profile = 'dev'

def get_boto3_resource(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
    session = boto3.session.Session(profile_name=aws_profile)
    return session.resource(service)


def get_boto3_client(service='s3'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10009'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10009'
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
