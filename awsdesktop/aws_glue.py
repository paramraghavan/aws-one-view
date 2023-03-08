import boto3
boto3.__version__
import os, time


import os, time
from dateutil import tz
# if os.name == 'nt':
#     def _naive_is_dst(self, dt):
#         timestamp = tz.tz._datetime_to_timestamp(dt)
#         # workaround the bug of negative offset UTC prob
#         if timestamp+time.timezone < 0:
#             current_time = timestamp + time.timezone + 31536000
#         else:
#             current_time = timestamp + time.timezone
#         return time.localtime(current_time).tm_isdst
# tz.tzlocal._naive_is_dst = _naive_is_dst


def get_boto3_client(service='glue'):
    # os.environ['HTTPS_PROXY'] = 'proxy.com:10000'
    # os.environ['HTTP_PROXY'] = 'proxy.com:10000'
    return boto3.client(service)

def get_databases():
    """
    Returns the databases available in the Glue data catalog

    :return: list of databases
    """
    return [dat["Name"] for dat in get_boto3_client('glue').get_databases()["DatabaseList"]]

def get_tables_for_database(database):
    """
    Returns a list of tables in a Glue database catalog

    :param database: Glue database
    :return: list of tables
    """
    starting_token = None
    next_page = True
    tables = []
    while next_page:
        paginator = get_boto3_client('glue').get_paginator(operation_name="get_tables")
        response_iterator = paginator.paginate(
            DatabaseName=database,
            PaginationConfig={"PageSize": 100, "StartingToken": starting_token},
        )
        for elem in response_iterator:
            tables += [
                {
                    "name": table["Name"],
                }
                for table in elem["TableList"]
            ]
            try:
                starting_token = elem["NextToken"]
            except:
                next_page = False
    return tables

# https://docs.aws.amazon.com/glue/latest/webapi/API_CreateTable.html
#https://boto3.amazonaws.com/v1/documentation/api/1.9.185/reference/services/glue.html#Glue.Client.create_table
#"TableType" : "EXTERNAL_TABLE"
def create_table(database_name, table_name, comment, location, columns, partition_keys):

    params = {
        #"CatalogId": "1234567890",
        "DatabaseName": database_name,
        "TableInput": {
            "Name": table_name,
            "Description": comment,
            "StorageDescriptor": {
                "Columns": columns,
                "Location": location,
                "InputFormat": "org.apache.hadoop.mapred.TextInputFormat",
                "OutputFormat": "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat",
                "SerdeInfo": {
                    "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe",
                    "Parameters": {
                        "field.delim": ",",
                        "serialization.format": ",",
                        #"spark.sql.sources.schema.numPartCols": "1"
                    }
                }
            },
            "PartitionKeys": partition_keys,
            "TableType": "EXTERNAL_TABLE"
        }
    }
    #params['TableInput'].update({'Name': table_name})
    #params['DatabaseName'].update({'Name': database_name})

    glue_client = get_boto3_client('glue')
    resp= glue_client.create_table(**params)
    print(resp)




def get_current_schema_partition(database_name):
    resp = get_tables_for_database(database)
    #print(resp)
    for dict in resp:
        #print(dict['name'])
        table_name= dict['name']
        #if table_name.startswith('fl_'):
        if True:
            response = get_boto3_client('glue').get_table(
            DatabaseName=database_name,
            Name=table_name)
            #print( 'Tablename/Partition/TableType {}/{}/{}'.format(table_name,response['Table']['PartitionKeys'],response['Table']['TableType']))
            #print('{} {}'.format(table_name, response['Table']['PartitionKeys'][0]['Name']))
            col_val =''
            for col in response['Table']['PartitionKeys']:
                col_val += col['Name'] + ' '
            print('{} {}'.format(table_name.upper(),col_val.lower()))

def get_current_schema(database_name, table_name):
    response = get_boto3_client('glue').get_table(
        DatabaseName=database_name,
        Name=table_name)

    table_data = {}
    table_data['input_format'] = response['Table']['StorageDescriptor']['InputFormat']
    table_data['output_format'] = response['Table']['StorageDescriptor']['OutputFormat']
    table_data['table_location'] = response['Table']['StorageDescriptor']['Location']
    table_data['serde_info'] = response['Table']['StorageDescriptor']['SerdeInfo']
    table_data['partition_keys'] = response['Table']['PartitionKeys']

    return table_data



def create_partition(database_name, table_name, location_partition, key_values, input_format, output_format, serde_info):
    params = [{
        "Values":key_values,
        "StorageDescriptor": {
                "InputFormat": input_format,
                "Location": location_partition,
                "OutputFormat": output_format,
                "Compressed": False,
                "SerdeInfo": serde_info
            },
        }]

    #params['TableInput'].update({'Name': table_name})
    #params['DatabaseName'].update({'Name': database_name})

    glue_client = get_boto3_client('glue')

    create_partition_response = glue_client.batch_create_partition(
        #CatalogId="12345671",
        DatabaseName=database_name,
        TableName=table_name,
        PartitionInputList=params
    )

    # resp =glue_client.create_partition(**params)
    #print(create_partition_response)
    return create_partition_response


'''
    database_name
    table_name
    location, "s3://pp-database/tables/" + table_name + "/date=20140401"
    part_key_values_in_order, "19690" #airlines=19690
'''
def add_partition(database_name, table_name, location, part_key_values_in_order):
    #create partition, first get table schema
    table_info = get_current_schema(database_name, table_name)
    input_format =  table_info["input_format"]
    output_format = table_info["output_format"]
    serde_info_ser_library = table_info["serde_info"]

    print("input_format: " +  input_format )
    print("output_format: " + output_format)
    print("SerializationLibrary: " + str(serde_info_ser_library))

    location_partition = "s3://pp-database/tables/" + table_name + "/date=20140401"
    location_partition = location
    key_values_input = part_key_values_in_order
    key_values = key_values_input.split(',')

    #create partition
    resp = create_partition(database_name, table_name, location_partition, key_values, input_format, output_format, serde_info_ser_library)
    print('partition creation successful')
    print(resp)
    #print('---')
    return resp



if __name__ == '__main__':
    #resp = get_databases()
    database = 'sample_db'
    table_name= 'flights'

    #resp = get_current_schema(database, table_name )
    #print(resp)

    # resp = get_tables_for_database(database)
    # print(resp)
    # for dict in resp:
    #     print(dict['name'])

    get_current_schema_partition(database)