import boto3
from common_utils.metrics import metrics_check


redshift = boto3.client('redshift')

idle_redshift = []
all_redshifts = []

def check_redshift():
    global idle_redshift
    global all_redshifts
    count = 0
    response = redshift.describe_clusters()
    for cluster in response['Clusters']:
        cluster_id = cluster['ClusterIdentifier']
        db_name = cluster['DBName']
        all_redshifts.append(cluster_id)
        print('checking for cluster:', cluster_id)
        #get readiops metrics of  cluster
        try:
            readiops_metric = metrics_check(cluster_id, 'ReadIOPS', 'Average', 'Count/Second', 900, True, 'AWS/Redshift', 'ClusterIdentifier')
            if sum(readiops_metric)/len(readiops_metric) <= 0:
                writeiops_metric =  metrics_check(cluster_id, 'WriteIOPS', 'Average', 'Count/Second', 900, True, 'AWS/Redshift', 'ClusterIdentifier')
                if sum(writeiops_metric)/len(writeiops_metric) <=0:
                    idle_redshift.append(cluster_id)
        except:
            print('There are no Metrics for :', cluster_id)
        count +=1

    print('**********************Final Output for redshift is****************************')            
    print('Redshift cluster with no read and write iops', idle_redshift)
    print('We have Total redshift cluster are:', count)
