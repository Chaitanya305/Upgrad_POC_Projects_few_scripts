import boto3
from common_utils.metrics import metrics_check, p99_check
from datetime import datetime, timedelta, timezone
from common_utils.constants import previous_generation_opensearch_instance_types


opensearch = boto3.client('opensearch')
cloudwatch = boto3.client('cloudwatch')
sts = boto3.client('sts')

Account_id = sts.get_caller_identity()['Account']

red_clusters = []
idle_cluster = []
no_gp3_ebs = []
idle_master_nodes = []
node_without_graviton = []
node_with_previous_generation = []
all_opensearch_clusters =[]
all_opensearch_nodes = {}

def es_node_metrics(metric_name, domain_name, node_id, stat):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=15)
    metric_data = cloudwatch.get_metric_statistics(
    Namespace='AWS/ES', 
    MetricName=metric_name,
    Dimensions=[
        {
            'Name': 'DomainName', 
            'Value': domain_name
        },
        {
            'Name': 'NodeId', 
            'Value': node_id  
        },
        {
            'Name': 'ClientId', 
            'Value': Account_id
        }
    ],
    StartTime=start_time, 
    EndTime=end_time,
    Period=900,
    Statistics=[stat] 
    )
    return [datapoint[stat] for datapoint in metric_data['Datapoints']]


def idel_master_node(domain_name, node_id):
    #checkimg for JVMPressure
    jvm = False
    jvm_metrics = es_node_metrics('JVMMemoryPressure', domain_name, node_id, 'Average')
    if jvm_metrics:
        if p99_check(node_id, 50, jvm_metrics):
            jvm = True
    #cpu usage
    cpu = False
    cpu_metrics = es_node_metrics('CPUUtilization', domain_name, node_id, 'Maximum')
    if cpu_metrics:
        if p99_check(node_id, 30, cpu_metrics):
            cpu = True
    #check for oldjvm
    oldjvm = False
    oldjvm_metrics = es_node_metrics('OldGenJVMMemoryPressure', domain_name, node_id, 'Average')
    if oldjvm_metrics:
        if p99_check(node_id, 50, oldjvm_metrics):
            oldjvm = True
    if jvm and oldjvm and cpu:
        return True
    else:
        return False


def es_cluster_metric(metric_name, domain_name, stat):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=15)
    metric_data = cloudwatch.get_metric_statistics(
    Namespace='AWS/ES', 
    MetricName=metric_name,
    Dimensions=[
        {
            'Name': 'DomainName', 
            'Value': domain_name
        },
        {
            'Name': 'ClientId', 
            'Value': Account_id
        }
    ],
    StartTime=start_time, 
    EndTime=end_time,
    Period=900,
    Statistics=[stat] 
    )
    return [datapoint[stat] for datapoint in metric_data['Datapoints']]

def idle_opensearch_data_node(domain_name):
    #checking for cpu usage
    cpu = False
    cpu_metric = es_cluster_metric('CPUUtilization', domain_name, 'Maximum')
    if cpu_metric:
        if p99_check(domain_name, 10, cpu_metric):
            cpu = True
    #check for search rate
    searchrate = False
    search_rate_metrics = es_cluster_metric('SearchRate', domain_name, 'Average')
    if search_rate_metrics:
        if sum(search_rate_metrics)/len(search_rate_metrics) <= 500:
            searchrate = True
    #check for indexing rate
    indexingrate = False
    indexing_rate_metrics = es_cluster_metric('IndexingRate', domain_name, 'Average')
    if indexing_rate_metrics:
        if sum(indexing_rate_metrics)/len(indexing_rate_metrics) <= 500:
            indexingrate = True
    
    if cpu and searchrate and indexingrate:
        return True
    else:
        return False

def check_graviton(instance_type):
    family = instance_type.split('.')[0]
    return 'g' not in family

def check_opensearch():
    global red_clusters
    global idle_cluster
    global no_gp3_ebs
    global idle_master_nodes
    global node_without_graviton
    global node_with_previous_generation
    global all_opensearch_clusters
    global all_opensearch_nodes
    count = 0
    response = opensearch.list_domain_names()
    for name in response['DomainNames']:
        domain_name = name['DomainName']
        domain_info = opensearch.describe_domain(DomainName=domain_name)
        domain_health = opensearch.describe_domain_health(DomainName=domain_name)
        domain_nodes_info = opensearch.describe_domain_nodes(DomainName=domain_name)
        print('checking for ', domain_name)
        all_opensearch_clusters.append(domain_name)
        #cluster with red status
        if domain_health['ClusterHealth'] == 'Red':
            red_metrics = es_cluster_metric('ClusterStatus.Red', domain_name)
            if red_metrics:
                if sum(red_metrics)/len(red_metrics) >=1:
                    red_clusters.append(domain_name)
        #checking for ideal cluster
        if idle_opensearch_data_node(domain_name):
            idle_cluster.append(domain_name)
        #Check if EBS is enabled and yes then check it is gp3 or not
        ebs_options = domain_info['DomainStatus']['EBSOptions']
        if ebs_options['EBSEnabled']:
            volume_type = ebs_options['VolumeType']
            if volume_type != 'gp3':
                no_gp3_ebs.append(domain_name)
        #checking type of node
        all_node_id = []
        for domainstatus in domain_nodes_info['DomainNodesStatusList']:
            node_id = domainstatus['NodeId']
            all_node_id.append(node_id)
            all_opensearch_nodes[domain_name] = all_node_id
            node_type = domainstatus['NodeType']
            instance_type = domainstatus['InstanceType']
            if check_graviton(instance_type):
                node_without_graviton.append(node_id)
            if node_type in previous_generation_opensearch_instance_types:
                node_with_previous_generation.append(node_id)
            if node_type == 'Data':
                pass
                    
            if node_type == 'Master':
                if idel_master_node(domain_name, node_id):
                    idle_master_nodes.append(node_id)
        count +=1

        
        

    print('***************final output for opensearch***************************')
    print('opensearch cluster which is currently red status: ', red_clusters)
    print('opensearch cluster which are idle are:', idle_cluster)
    print('opensearch cluster which use ebs type other than gp3 :', no_gp3_ebs)
    print('opensearch cluster which are having idle master node are:', idle_master_nodes)
    print('opensearch cluster which are not have graviton type node are:', node_without_graviton)
    print('opensearch cluster which have old instance type node are:', node_with_previous_generation)
    print('We have total Opensearch cluster:', count)
    node_without_graviton.clear()
    print('graviton instances are:', node_without_graviton)
