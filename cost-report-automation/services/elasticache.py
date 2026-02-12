import boto3
from common_utils.constants import previous_generation_ElastiCache_instance_types
from common_utils.metrics import metrics_check, p99_check

old_generation_clusters = []
without_Graviton_clusters = []
idle_redis_clusters = []
idle_memcached_clusters = []
redis_no_reads = []
underutilized_memcached_clusters = []
underutilized_redis_clusters = []
replica_redis_clusters = []
all_clusters = []


def idle_memcached_elasticache(cluster_id):
    read = False
    write = False
    read_metrics = metrics_check(cluster_id, 'BytesReadIntoMemcached', 'Average', 'Bytes', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    if read_metrics:
        avg_read_metrics = sum(read_metrics)/len(read_metrics)
        if avg_read_metrics <= 0:
            read = True
        else:
            read = False
    
    write_metrics = metrics_check(cluster_id, 'BytesWrittenOutFromMemcached', 'Average', 'Bytes', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    if write_metrics:
        avg_write_metrics = sum(write_metrics)/len(write_metrics)
        if avg_write_metrics <= 0:
            write = True
        else:
            write = False

    if read and write:
        return True
    else:
        return False


def idle_redis_elasticache(cluster_id):
    In = False
    out = False
    In_metrics = metrics_check(cluster_id, 'NetworkBytesIn', 'Average', 'Bytes', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    if In_metrics:
        avg_in_metrics = sum(In_metrics)/len(In_metrics)
        if avg_in_metrics <= 0:
            In = True
        else:
            In = False
    
    out_metrics = metrics_check(cluster_id, 'NetworkBytesOut', 'Average', 'Bytes', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    if out_metrics:
        avg_out_metrics = sum(out_metrics)/len(out_metrics)
        if avg_out_metrics <= 0:
            out = True
        else:
            out = False

    if In and out:
        return True
    else:
        return False

def underutilized_Memcached(cluster_id):
    cpu_metric = metrics_check(cluster_id, 'CPUUtilization', 'Maximum', 'Percent', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    cpu = False
    connection = False
    if cpu_metric:
        if p99_check(cluster_id, 5.0, cpu_metric):
            cpu = True
    #check for connections
    connection_counts = metrics_check(cluster_id, 'CurrConnections', 'Average', 'Count', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    if connection_counts:
        if sum(connection_counts)/len(connection_counts) <= 0:
            connection = True
    if cpu and connection:
        return True
    else:
        return False

def underutilized_Redis(cluster_id):
    cpu_metric = metrics_check(cluster_id, 'CPUUtilization', 'Maximum', 'Percent', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    cpu = False
    connection = False
    if cpu_metric:
        if p99_check(cluster_id, 5.0, cpu_metric):
            cpu = True
    #check for connections
    connection_counts = metrics_check(cluster_id, 'CurrConnections', 'Average', 'Count', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
    if connection_counts:
        if sum(connection_counts)/len(connection_counts) <= 0:
            connection = True
    if cpu and connection:
        return True
    else:
        return False

def check_graviton(instance_type):
    family = instance_type.split('.')[1]
    return 'g' not in family

def check_elasticcache():
    elasticache = boto3.client('elasticache')
    global old_generation_clusters
    global without_Graviton_clusters
    global idle_redis_clusters
    global idle_memcached_clusters
    global redis_no_reads
    global underutilized_memcached_clusters
    global underutilized_redis_clusters
    global replica_redis_clusters
    global all_clusters
    paginator = elasticache.get_paginator('describe_cache_clusters')
    #response = elasticache.describe_cache_clusters(ShowCacheNodeInfo = True)
    count = 0
    for response in paginator.paginate(ShowCacheNodeInfo=True):
        for cluster in response['CacheClusters']:
            cluster_id = cluster['CacheClusterId']
            all_clusters.append(cluster_id)
            node_type = cluster['CacheNodeType'] 
            print('checking for cluster', cluster_id, node_type)   
            if node_type in previous_generation_ElastiCache_instance_types:
                old_generation_clusters.append(cluster_id)
            if check_graviton(node_type):
                without_Graviton_clusters.append(cluster_id)
            #check for idle cluster
            #for redis
            if cluster['Engine'] == 'redis':
                if idle_redis_elasticache(cluster_id):
                    idle_redis_clusters.append(cluster_id)
                #Redis clusters without replication having no reads should be deleted
                replication_group_id = cluster.get('ReplicationGroupId')
                print('replication group id is: ',replication_group_id)
                if not replication_group_id:
                    cachehits = metrics_check(cluster_id, 'CacheHits', 'Average', 'Count', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
                    cachemisses = metrics_check(cluster_id, 'CacheMisses', 'Average', 'Count', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
                    if cachehits and cachemisses:
                        if sum(cachehits)/len(cachehits) <=0  and sum(cachemisses)/len(cachemisses) <= 0:
                            redis_no_reads.append(cluster_id)
                if underutilized_Redis(cluster_id):
                    underutilized_redis_clusters.append(cluster_id)
                #check for replica in redis cluster
                if replication_group_id:
                    read_replica = elasticache.describe_replication_groups(ReplicationGroupId=replication_group_id)
                    replication_group = read_replica['ReplicationGroups'][0]
                    node_groups = replication_group['NodeGroups']
                    for node_group in node_groups:
                        for NodeGroupMember in node_group['NodeGroupMembers']:
                            if 'CurrentRole' in NodeGroupMember and NodeGroupMember['CurrentRole'] == 'replica':
                                print(f"replica: {NodeGroupMember['CacheClusterId']} of id {NodeGroupMember['CacheNodeId']}")
                                cachehits = metrics_check(cluster_id, 'CacheHits', 'Average', 'Count', 900, True, 'AWS/ElastiCache', 'CacheClusterId')
                                if cachehits:
                                    if sum(cachehits)/len(cachehits) <=0:
                                        replica_redis_clusters.append(NodeGroupMember['CacheClusterId'])

            #for memcached
            if cluster['Engine'] == 'memcached':
                if idle_memcached_elasticache(cluster_id):
                    idle_memcached_clusters.append(cluster_id)
                if underutilized_Memcached(cluster_id):
                    underutilized_memcached_clusters.append(cluster_id)
            count +=1

    print('***************************final Elasticache output is*******************************************')
    print('cluster with previous generation types are:', old_generation_clusters)
    print('cluster which does not have graviton instance type:', without_Graviton_clusters)
    print('ideal redis cluser are:', idle_redis_clusters)
    print('ideal memcached cluser are:', idle_memcached_clusters)
    print('Redis clusters without replication having no reads', redis_no_reads)
    print('underutilized Redis clusters are:', underutilized_redis_clusters)
    print('underutilized memcached clusters are:', underutilized_memcached_clusters)
    print('ElastiCache Redis cluster replicas with zero reads are:', replica_redis_clusters)
    print('we have total Elastic cashe cluster are:', count)
    without_Graviton_clusters.clear()
    print('graviton instances are:', without_Graviton_clusters)