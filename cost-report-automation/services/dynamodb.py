import boto3
from common_utils.metrics import metrics_check
from datetime import datetime, timedelta, timezone

dynamo_db = boto3.client('dynamodb')
cloudwatch = boto3.client('cloudwatch')


inactive_gsi_tables = {}
underutilized_gsi_read_capacity = {}
underutilized_gsi_write_capacity = {}
underutilized_read_capacity = []
underutilized_write_capacity = []
underutilized_capacity_table = []
all_dynamodb_tables = []
all_gsi = {}

def check_dynamodb():
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=15)
    global inactive_gsi_tables
    global underutilized_gsi_read_capacity
    global underutilized_gsi_write_capacity
    global underutilized_read_capacity
    global underutilized_write_capacity
    global underutilized_capacity_table
    global all_dynamodb_tables
    global all_gsi
    count = 0
    # Get a list of all DynamoDB tables
    #tables_list = dynamo_db.list_tables()
    paginator = dynamo_db.get_paginator('list_tables')
    for tables_list in paginator.paginate():
        # all_dynamodb_tables.append(tables_list['TableNames'])
        for table_name in tables_list['TableNames']:
            all_dynamodb_tables.append(table_name)
            # Describe the table to get its GSIs
            table_description = dynamo_db.describe_table(TableName=table_name)
            gsis = table_description['Table'].get('GlobalSecondaryIndexes', [])
            gsi_index_names = []
            if gsis:
                # Check for read and write metrics for the table
                for gsi in gsis:
                    gsi_index_name = gsi['IndexName']
                    gsi_index_names.append(gsi_index_name)
                    all_gsi[table_name] = gsi_index_names
                    # Get the read capacity units consumed metrics for the GSI
                    read_metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedReadCapacityUnits',
                    Dimensions=[
                        {'Name': 'TableName', 'Value': table_name},
                        {'Name': 'GlobalSecondaryIndexName', 'Value': gsi_index_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=900,  # 15 Min
                    Statistics=['Average']
                    )

                    # Get the write capacity units consumed metrics for the GSI
                    write_metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/DynamoDB',
                    MetricName='ConsumedWriteCapacityUnits',
                    Dimensions=[
                        {'Name': 'TableName', 'Value': table_name},
                        {'Name': 'GlobalSecondaryIndexName', 'Value': gsi_index_name}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=900,  # 1 day
                    Statistics=['Average']
                    )
                    #get metrics
                    gsi_read_metric = [point['Average'] for point in read_metrics['Datapoints']]
                    gsi_write_metrics = [point['Average'] for point in write_metrics['Datapoints']]
                    if gsi_read_metric and gsi_write_metrics:
                        # Check if any of the metric data points are non-zero
                        if any(value > 0 for value in gsi_read_metric) or any(value > 0 for value in gsi_write_metrics):
                            print(f"table {table_name} with gsi {gsi_index_name} has some activity")
                        else:
                            inactive_gsi_tables[table_name] = gsi_index_names
                        
                        # Extract the read capacity for the table gsi
                        gsi_provisionThroughput = gsi.get('ProvisionedThroughput')
                        if gsi_provisionThroughput:
                            gsi_read_capacity =  gsi_provisionThroughput.get('ReadCapacityUnits')
                            if sum(gsi_read_metric)/len(gsi_read_metric) <= 0.8 * gsi_read_capacity:
                                underutilized_gsi_read_capacity[table_name] = gsi_index_names
                            # Extract the write capacity for the table gsi
                            gsi_write_capacity = gsi_provisionThroughput.get('WriteCapacityUnits')
                            if sum(gsi_write_metrics)/len(gsi_write_metrics) <= 0.8 * gsi_write_capacity:
                                underutilized_gsi_write_capacity[table_name] = gsi_index_names


            # Extract the read capacity for the table
            provisionThroughput = table_description['Table'].get('ProvisionedThroughput')
            if provisionThroughput:
                read_capacity = provisionThroughput.get('ReadCapacityUnits')
                #get read capacity metrics for table
                if read_capacity:
                    read_capacity_metrics =  metrics_check(table_name, 'ConsumedReadCapacityUnits', 'Average', 'Count', 900, True, 'AWS/DynamoDB', 'TableName')
                    avg_read_capacity_metrics = sum(read_capacity_metrics)/len(read_capacity_metrics)
                    if avg_read_capacity_metrics <= 0.8 * read_capacity:
                        underutilized_read_capacity.append(table_name)
                # Extract the Write capacity for the table
                write_capacity =  provisionThroughput.get('WriteCapacityUnits')
                #get write capacity metrics for table
                if write_capacity:
                    write_capacity_metrics =  metrics_check(table_name, 'ConsumedWriteCapacityUnits', 'Average', 'Count', 900, True, 'AWS/DynamoDB', 'TableName')
                    avg_write_capacity_metrics = sum(write_capacity_metrics)/len(write_capacity_metrics)
                    if avg_write_capacity_metrics <= 0.8 * write_capacity:
                        underutilized_write_capacity.append(table_name)
                # Check if the table has provisioned capacity
                if read_capacity > 0 and write_capacity > 0:
                    # check if it has no reads or writes.
                    if avg_write_capacity_metrics <= 0 and avg_read_capacity_metrics <= 0:
                        underutilized_capacity_table.append(table_name)
            count +=1

    print('**************dynamodb final ouput is********************************')
    print('DynamoDB tables gsi which has no read and write operations:', inactive_gsi_tables)
    print('DynamoDB tables gsi which has underutilized read capacity:', underutilized_gsi_read_capacity)
    print('DynamoDB tables gsi which has underutilized write capacity:', underutilized_gsi_write_capacity)
    print('DynamoDB tables which has underutilized red capacity:', underutilized_read_capacity)
    print('DynamoDB tables which has underutilized write capacity:', underutilized_write_capacity)
    print('DynamoDB tables which has no read and write operations:', underutilized_capacity_table)
    print('We have Total dynamo db tables are', count)
