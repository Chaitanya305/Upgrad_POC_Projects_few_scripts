import pymysql
import boto3
from services.ec2 import previous_generation_instance_id, instance_ids
from services.ec2 import low_cpu_instances, low_network_instances, t_windows_instances, dedicated_Tenancy_instance, low_network_3hrs, not_AMD_instances, without_Graviton_instance, failed_health_check_instances, stopped_instance

from services.rds import previous_generation_db_instance_id, idle_rds_instance, retention_period_instances, read_replica_retention_period, no_graviton_instance, rds_instances
from services.s3 import all_buckets, incomplete_object, non_multipart_object_buckets
from services.nat import data_loss_nat, no_packets_out, no_packets_in, unused_eip, no_outgoing_traffic, pub_ips, all_nats
from services.elasticache import old_generation_clusters, without_Graviton_clusters, idle_memcached_clusters, idle_redis_clusters, redis_no_reads, underutilized_memcached_clusters, underutilized_redis_clusters, replica_redis_clusters, all_clusters
from services.dynamodb import inactive_gsi_tables, underutilized_gsi_read_capacity, underutilized_gsi_write_capacity, underutilized_read_capacity, underutilized_write_capacity, underutilized_capacity_table, all_dynamodb_tables, all_gsi
from services.opensearch import red_clusters, idle_cluster, no_gp3_ebs, idle_master_nodes, node_without_graviton, node_with_previous_generation, all_opensearch_clusters, all_opensearch_nodes
from services.lambda_fun import error_functions, unutilized_provision_concurrency, non_graviton_functions, underutilized_provision_concurrency_functions, underutilized_functions, all_functions
from services.elb import inactive_alb, inactive_nlb, inactive_gtw, all_elbs
from services.cloudwatch import all_log_groups, all_cloudwatch, insufficient_alarm, inappropriate_log_groups, no_retention_period
from services.redshift import idle_redshift, all_redshifts
from services.ebs import all_ebs_volumes, available_volume, not_gp3_volume, unused_attached_ebs


ec2 = boto3.client('ec2')
region = ec2.meta.region_name
sts = boto3.client('sts')
account_id = sts.get_caller_identity()['Account']

# Database connection settings
db_user = 'devopsuser'
db_password = '79SAy53zVx'
db_host = 'upgrad-dev-mysql-devops.cscyttgt1cwf.us-east-1.rds.amazonaws.com'  
db_name = 'cost_reports'
connection = pymysql.connect(
    host=db_host,
    user=db_user,
    password=db_password,
    database=db_name
)

# Create a cursor object to interact with the database
cursor = connection.cursor()

def update_query(table, values, col_name, primary_col):
    for data  in values:
        query = f'''UPDATE {table} SET {col_name} = 'YES' WHERE {primary_col} = '{data}' AND account_id = '{account_id}' AND region = '{region}';'''
        cursor.execute(query)
        connection.commit()  # Commit the transaction

def clean_data(table_name):
    count_query = f'''SELECT COUNT(*) FROM {table_name} WHERE account_id = '{account_id}' AND region = '{region}';'''
    cursor.execute(count_query)
    result = cursor.fetchone()
    if result[0] > 0:
        print('cleaning old data')
        delete_query = f'''DELETE FROM {table_name} where account_id = '{account_id}' AND region = '{region}';'''
        cursor.execute(delete_query)
        connection.commit()

def insert_ec2_data():
    clean_data('ec2_report')
    #inserting all instnaces 
    for instance_id, instance_name in instance_ids.items():
        insert_query = f'''INSERT INTO ec2_report (instance_id, instance_name, account_id, region) 
        VALUES ('{instance_id}', '{instance_name}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()

    #updte query for previous gen instnaces 
    update_query('ec2_report', previous_generation_instance_id, "previous_gen_instances", 'instance_id')
    #update values for low cpu
    update_query('ec2_report' ,low_cpu_instances, "cpu_less_than_5", 'instance_id')
    #updare value for network_IO_less_100_KB
    update_query('ec2_report', low_network_instances, "network_IO_less_100_KB", 'instance_id')
    #update for windows_instance_T_family
    update_query('ec2_report', t_windows_instances, 'windows_instance_T_family', 'instance_id')
    #update for dedicated_tenancy
    update_query('ec2_report', dedicated_Tenancy_instance, 'dedicated_tenancy', 'instance_id')
    #updte for no graviton
    update_query('ec2_report', without_Graviton_instance, 'no_graviton', 'instance_id')
    #update for low_network_3hrs
    update_query('ec2_report', low_network_3hrs, 'network_io_less_100_kb_3hrs', 'instance_id')
    #update for no_amd
    update_query('ec2_report', not_AMD_instances, 'no_amd', 'instance_id')
    #update for failed health instance
    update_query('ec2_report', failed_health_check_instances, "failed_health_check", 'instance_id')
    #update for stopped instance
    update_query('ec2_report', stopped_instance, 'stopped_instances_last_15Days', 'instance_id')


def insert_rds_data():
    clean_data('rds_report')
    #inserting all RDS instnaces 
    for instnace_id in rds_instances:
        insert_query = f'''INSERT INTO rds_report (DBInstance_id, account_id, region) 
        VALUES ('{instnace_id}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()

    #update for previous_gen_RDS_instances
    update_query('rds_report', previous_generation_db_instance_id, 'previous_gen_rds_instances', 'DBInstance_id')
    #update for idle_rds_instances
    update_query('rds_report', idle_rds_instance, 'idle_rds_instances', 'DBInstance_id')
    #update for read_replica_rp_more_than_20
    update_query('rds_report', read_replica_retention_period, 'read_replica_rp_more_than_20', 'DBInstance_id')
    #update for rds_rp_more_than_20
    update_query('rds_report', retention_period_instances, 'rds_rp_more_than_20', 'DBInstance_id')
    #update for rds_no_graviton
    update_query('rds_report', no_graviton_instance, 'rds_no_graviton', 'DBInstance_id')

def insert_s3_data():
    #clean data if table has data in it
    count_query = f'''SELECT COUNT(*) FROM s3_report WHERE account_id = '{account_id}';'''
    cursor.execute(count_query)
    result = cursor.fetchone()
    if result[0] > 0:
        delete_query = f'''DELETE FROM s3_report where account_id = '{account_id}';'''
        cursor.execute(delete_query)
        connection.commit()

    #inserting all S3 buckets
    for bucket in all_buckets:
        insert_query = f'''INSERT INTO s3_report (bucket_name,  account_id) 
        VALUES ('{bucket}', '{account_id}');'''
        cursor.execute(insert_query)
        connection.commit()

    #insert for remaning buckets
    for bucket, upload_keys in incomplete_object.items():
        for upload_key in upload_keys:
            insert_query = f'''INSERT INTO s3_report (bucket_name, upload_key, account_id, incomplete_object_buckets) 
            VALUES ('{bucket}', '{upload_key}', '{account_id}', 'YES');'''
            cursor.execute(insert_query)
            connection.commit()


def insert_elasticache_data():
    clean_data('elasticache_report')
    #inserting all clusters id
    for cluster_id in all_clusters:
        insert_query = f'''INSERT INTO elasticache_report (cluster_id, account_id, region) 
        VALUES ('{cluster_id}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()

    #updating for old_gen_clusters
    update_query('elasticache_report', old_generation_clusters, 'old_gen_clusters', 'cluster_id')
    #updating for no_graviton
    update_query('elasticache_report', without_Graviton_clusters, 'no_graviton', 'cluster_id')
    #updating for idle_redis_cluster 
    update_query('elasticache_report', idle_redis_clusters, 'idle_redis_cluster', 'cluster_id')
    #updating for idle_memcached_cluster
    update_query('elasticache_report', idle_memcached_clusters, 'idle_memcached_cluster', 'cluster_id')
    #updating for redis_no_read
    update_query('elasticache_report', redis_no_reads, 'redis_no_read', 'cluster_id')
    #updating for underutilized_memcached_cluster
    update_query('elasticache_report', underutilized_memcached_clusters, 'underutilized_memcached_cluster', 'cluster_id')
    #updating for underutilized_redis_cluster
    update_query('elasticache_report', underutilized_redis_clusters, 'underutilized_redis_cluster', 'cluster_id')
    #updating for replica_redis_cluster
    update_query('elasticache_report', replica_redis_clusters, 'replica_redis_cluster', 'cluster_id')

def insert_vpc_data():
    clean_data('vpc_report')
    #inserting all EIP's
    for eips in pub_ips:
        insert_query = f'''INSERT INTO vpc_report (eip, account_id, region) 
        VALUES ('{eips}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()
    
    #inserting for NAT gateway id
    for nat_ids in all_nats:
        nat_update_query = f'''UPDATE vpc_report SET nat_id = '{nat_ids}' WHERE nat_id is NULL AND account_id = '{account_id}' AND region = '{region}' limit 1;'''
        cursor.execute(nat_update_query)
        connection.commit()
      
    #udating for data_loss_nats
    update_query('vpc_report', data_loss_nat, 'data_loss_nats', 'nat_id')
    #updating for no_packet_out
    update_query('vpc_report', no_packets_out, 'no_packet_out', 'nat_id')
    #updating for no_packet_in
    update_query('vpc_report', no_packets_in, 'no_packet_in', 'nat_id')
    #updating for no_outgoing_traffic
    update_query('vpc_report', no_outgoing_traffic, 'no_outgoing_traffic_nat', 'nat_id')
    #updating for unused_eips
    update_query('vpc_report', unused_eip, 'unused_eips', 'eip')


def insert_dynamodb_data():
    clean_data('dynamodb_report')
    #calculate max len of rows
    max_rows = max(len(all_dynamodb_tables),len(all_gsi))

    #inserting all rows
    for i in range(max_rows):
        insert_query = f'''INSERT INTO dynamodb_report (account_id, region) 
        VALUES ('{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()   

    #inserting all gsi
    for table_name,gsis in all_gsi.items():
        for gsi in gsis:
            gsi_update_query = f'''UPDATE dynamodb_report SET table_name = '{table_name}', gsi ='{gsi}' where gsi is NULL AND account_id = '{account_id}' AND region = '{region}' limit 1;'''
            cursor.execute(gsi_update_query)
            connection.commit()
            all_dynamodb_tables.remove(table_name)

    #inserting for remianing tables
    for table_name in all_dynamodb_tables:
        table_update_query = f'''UPDATE dynamodb_report SET table_name = '{table_name}' where table_name is NULL AND account_id = '{account_id}' AND region = '{region}' limit 1;'''
        cursor.execute(table_update_query)
        connection.commit()

    def check_gsi_update_query(table, values, col_name):
        for table_name,gsis  in values.items():
            for gsi in gsis:
                #print(f'table is {table_name} and gsi is {gsi}')
                query = f'''UPDATE {table} SET {col_name} = 'YES' WHERE table_name = '{table_name}' AND gsi = '{gsi}' AND account_id = '{account_id}' AND region = '{region}';'''
                cursor.execute(query)
                connection.commit()  # Commit the transaction

    #update for inactive_gsi_table
    check_gsi_update_query('dynamodb_report', inactive_gsi_tables, 'inactive_gsi_table')
    #update for underutilized_gsi_reads_capacity
    check_gsi_update_query('dynamodb_report', underutilized_gsi_read_capacity, 'underutilized_gsi_reads_capacity')
    #update for underutilized_gsi_writes_capacity
    check_gsi_update_query('dynamodb_report', underutilized_gsi_write_capacity, 'underutilized_gsi_writes_capacity')
    #update for underutilized_reads_capacity
    update_query('dynamodb_report', underutilized_read_capacity, 'underutilized_reads_capacity', 'table_name')
    #update for underutilized_writes_capacity
    update_query('dynamodb_report', underutilized_write_capacity, 'underutilized_writes_capacity', 'table_name')
    #update for underutilized_capacity_tables
    update_query('dynamodb_report', underutilized_capacity_table, 'underutilized_capacity_tables', 'table_name')

    
def insert_opensearch_data():
    clean_data('opensearch_report')
    #inserting all Nodes data
    for cluster,nodes in all_opensearch_nodes.items():
        for node in nodes:
            insert_query = f'''INSERT INTO opensearch_report (cluster_name, node_id, account_id, region) 
            VALUES ('{cluster}', '{node}', '{account_id}', '{region}');'''
            cursor.execute(insert_query)
            connection.commit()

    #updating for red_cluster
    update_query('opensearch_report', red_clusters, 'red_cluster', 'cluster_name')
    #updating for idle_cluster
    update_query('opensearch_report', idle_cluster, 'idle_cluster', 'cluster_name')
    #updating for no_gp3_ebs
    update_query('opensearch_report', no_gp3_ebs, 'no_gp3_ebs', 'cluster_name')
    #update for idle_master_nodes
    update_query('opensearch_report', idle_master_nodes, 'idle_master_nodes', 'node_id')
    #update for node_with_previous_generation
    update_query('opensearch_report', node_with_previous_generation, 'node_with_previous_generation', 'node_id')
    #update for node_without_graviton
    update_query('opensearch_report', node_without_graviton, 'node_without_graviton', 'node_id')
       

def insert_lambda_data():
    clean_data('lambda_report')
    #inserting for all lambda fucntions
    for function in all_functions:
        insert_query = f'''INSERT INTO lambda_report (function_name, account_id, region) 
        VALUES ('{function}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()

    #update for error_function
    update_query('lambda_report', error_functions, 'error_function', 'function_name')
    #update for unutilized_provision_concurrency
    update_query('lambda_report', unutilized_provision_concurrency, 'unutilized_provision_concurrency', 'function_name')
    #update for non_graviton_function
    update_query('lambda_report', non_graviton_functions, 'non_graviton_function', 'function_name')
    #update for underutilized_provision_concurrency_fucntion
    update_query('lambda_report', underutilized_provision_concurrency_functions, 'underutilized_provision_concurrency_fucntion', 'function_name')
    #update for underutilized_function
    update_query('lambda_report', underutilized_functions, 'underutilized_function', 'function_name')


def insert_elb_data():
    clean_data('elb_report')
    #inserting for all ELB
    for elb in all_elbs:
        insert_query = f'''INSERT INTO elb_report (elb_name, account_id, region) 
        VALUES ('{elb}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()

    #update for inactive_alb
    update_query('elb_report', inactive_alb, 'inactive_alb', 'elb_name')
    #update for inactive_nlb
    update_query('elb_report', inactive_nlb, 'inactive_nlb', 'elb_name')
    #update for inactive_gtw
    update_query('elb_report', inactive_gtw, 'inactive_gtw', 'elb_name')
    
    
def insert_cloudwatch_data():
    clean_data('cloudwatch_report')
    #check for max rows
    max_row = max(len(all_cloudwatch),len(all_log_groups))
    
    #insert for all rows
    for i in range(max_row):
        insert_query = f'''INSERT INTO cloudwatch_report (account_id, region) 
        VALUES ('{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()  

    #insert for cloudwatch
    for alarm in all_cloudwatch:
        alarm_update_query = f'''UPDATE cloudwatch_report SET alarm_name = '{alarm}' where alarm_name is NULL AND account_id = '{account_id}' AND region = '{region}' limit 1;'''
        cursor.execute(alarm_update_query)
        connection.commit()
    
    #insert for all log groups
    for logs in all_log_groups:
        logs_update_query = f'''UPDATE cloudwatch_report SET log_groups = '{logs}' where log_groups is NULL AND account_id = '{account_id}' AND region = '{region}' limit 1;'''
        cursor.execute(logs_update_query)
        connection.commit()

    #update for insufficient_alarm
    update_query('cloudwatch_report', insufficient_alarm, 'insufficient_alarm', 'alarm_name')
    #update for inappropriate_log_groups
    update_query('cloudwatch_report', inappropriate_log_groups, 'inappropriate_log_groups', 'log_groups')
    #update for no_retention_period
    update_query('cloudwatch_report', no_retention_period, 'no_retention_period', 'log_groups')


def insert_redshift_data():
    clean_data('redshift_report')
    #inserting for all Redshift
    for cluster in all_redshifts:
        insert_query = f'''INSERT INTO redshift_report (redshift_clusters, account_id, region) 
        VALUES ('{cluster}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()

    #update for idle_redshift cluster
    update_query('redshift_report', idle_redshift, 'idle_redshift', 'redshift_clusters')


def insert_ebs_data():
    #clean data if table has data in it
    clean_data('ebs_report')

    #inserting for all EBS
    for ebs in all_ebs_volumes:
        insert_query = f'''INSERT INTO ebs_report (EBS_volume_id, account_id, region) 
        VALUES ('{ebs}', '{account_id}', '{region}');'''
        cursor.execute(insert_query)
        connection.commit()

    #update for available_volume
    update_query('ebs_report', available_volume, 'available_volume', 'EBS_volume_id')
    #update for not_gp3_volume
    update_query('ebs_report', not_gp3_volume, 'not_gp3_volume', 'EBS_volume_id')
    #update for unused_attached_ebs
    update_query('ebs_report', unused_attached_ebs, 'unused_attached_ebs', 'EBS_volume_id')


    cursor.close()
    connection.close()