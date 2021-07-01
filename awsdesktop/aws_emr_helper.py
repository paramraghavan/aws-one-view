from awsdesktop import aws_utils



def getMyclusterInfo(cluster_name):
    client = aws_utils.get_boto3_client('emr')
    response = client.list_clusters(
        ClusterStates=['RUNNING', 'WAITING']
    )
    cluster_id = ''
    #print(response)
    for cluster in response['Clusters']:
        if cluster['Name'] and cluster['Name'].lower() == cluster_name.lower():
            print('Name {0}'.format(cluster['Name']))
            print('Cluster Id {0}'.format(cluster['Id']))
            #print('State {0}'.format(cluster['Status']))
            #print(cluster)
            cluster_id = cluster['Id']
            break

    return cluster_id

def get_cluster_info(filter=''):
    list = []
    client = aws_utils.get_boto3_client('emr')
    response = client.list_clusters(
        ClusterStates=['RUNNING', 'WAITING']
    )
    cluster_id = ''
    #print(response)
    for cluster in response['Clusters']:
        cluster_name =  cluster['Name']
        if filter not in cluster_name:
            continue
        cluster_id = cluster['Id']
        cluster_status = cluster['Status']['State']
        master_node_ip = getMasterIPAddress(cluster_id)
        nameandid = cluster_name + " || " + cluster_status + " || " + cluster_id + " || " +  master_node_ip
        list.append(nameandid)

    return list


def  getMasterIPAddress(cluster_id):
    ip_address = ''
    try:
        client = aws_utils.get_boto3_client('emr')
        response = client.describe_cluster(ClusterId=cluster_id)
    except Exception as e:
        # e.response['Error']['Code'] == 'ResourceNotFoundException'
        return None
    masterdns = response['Cluster']['MasterPublicDnsName']
    if masterdns:
        ip_address =  masterdns.replace('ip-','').replace('.ec2.internal','').replace('-','.')

    return ip_address

if __name__ == '__main__':
    #print("get all cluster id's {0}".format(get_cluster_name_ids()))
    cluster_id = getMyclusterInfo('ygpp-devl-compute01')
    result = getMasterIPAddress(cluster_id)
    print(result)