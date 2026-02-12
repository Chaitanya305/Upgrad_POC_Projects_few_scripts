import boto3
from common_utils.constants import previous_generation_db_instance_types
from common_utils.metrics import metrics_check
from common_utils.metrics import p99_check

cloudwatch = boto3.client('cloudwatch')
rds = boto3.client('rds')

previous_generation_db_instance_id = []
idle_rds_instance = []
retention_period_instances = []
read_replica_retention_period = []
no_graviton_instance = []
rds_instances = []


def idle_rds(instance_id):
    cpu = False
    connection = False
    read_iops = False
    write_iops = False
    #checking for cpu usage
    cpu_utilization_threshold = 10.0  
    cpu_metrics = metrics_check(instance_id, 'CPUUtilization', 'Maximum', 'Percent', 900, True, 'AWS/RDS', 'DBInstanceIdentifier')
    if p99_check(instance_id, cpu_utilization_threshold, cpu_metrics):
        cpu = True
    else:
        cpu = False  
    #checking for Read IOPS
    read_iops_threshold = 5
    read_iops_metrics = metrics_check(instance_id, 'ReadIOPS', 'Average', 'Count/Second', 900, True, 'AWS/RDS', 'DBInstanceIdentifier')
    if sum(read_iops_metrics)/len(read_iops_metrics) <= read_iops_threshold:
        read_iops = True

    #check write iops
    write_iops_threshold = 5
    write_iops_metrics = metrics_check(instance_id, 'WriteIOPS', 'Average', 'Count/Second', 900, True, 'AWS/RDS', 'DBInstanceIdentifier')
    if sum(write_iops_metrics)/len(write_iops_metrics) <= write_iops_threshold:
        write_iops = True

    #database connections threshold
    connection_threshold = 0
    db_connections = metrics_check(instance_id, 'DatabaseConnections', 'Average', 'Count', 86400, True, 'AWS/RDS', 'DBInstanceIdentifier')
    if sum(db_connections)/len(db_connections) <= connection_threshold:
        connection = True
    
    if cpu and read_iops and write_iops and connection:
        return True
    else:
        return False
    

def check_graviton(instance_type):
    family = instance_type.split('.')[1]
    return 'g' not in family


def rds_check():
    rds_info = rds.describe_db_instances()
    global previous_generation_db_instance_id
    global idle_rds_instance
    global retention_period_instances
    global read_replica_retention_period
    global no_graviton_instance
    global rds_instances
    count = 0
    for dbinstances in rds_info['DBInstances']:
        instance_id = dbinstances['DBInstanceIdentifier']
        rds_instances.append(instance_id)
        instance_class = dbinstances['DBInstanceClass']
        print("checking for instance", instance_id)
        #checking instance class is previous generation
        if instance_class in previous_generation_db_instance_types:
            previous_generation_db_instance_id.append(instance_id)
        #checking idle RDS instance
        if idle_rds(instance_id):
            idle_rds_instance.append(instance_id)    
        #checking for retention period for read replica
        if dbinstances.get('ReadReplicaSourceDBInstanceIdentifier'):
            replica_retention_period = dbinstances.get('BackupRetentionPeriod')
            if replica_retention_period:
                if dbinstances.get('BackupRetentionPeriod') >= 20:
                    read_replica_retention_period.append(instance_id)
        #checking for retention period
        retention_period = dbinstances.get('BackupRetentionPeriod')
        if retention_period:
            if dbinstances.get('BackupRetentionPeriod') >= 20:
                retention_period_instances.append(instance_id)
        #RDS DB instances should use Graviton processor
        if check_graviton(instance_class):
            no_graviton_instance.append(instance_id)
        count +=1

    print('********************** Final RDS Output ***************************')
    print("previous Generation RDS instances are: ", previous_generation_db_instance_id)
    print("idle rds instance are: ", idle_rds_instance)
    print("RDS Read Replica instance with retention period more than 20 days:", read_replica_retention_period)
    print("RDS instance with retention period more than 20 days:", retention_period_instances)
    print("RDS instance which are running without Graviton Processor:", no_graviton_instance)
    print('Total RDS instance we have:', count)
    no_graviton_instance.clear()
    print('graviton instances are:', no_graviton_instance)
