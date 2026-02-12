import boto3
from common_utils.metrics import metrics_check

elb = boto3.client('elbv2') 

inactive_alb = []
inactive_nlb = []
inactive_gtw = []
all_elbs = []

def check_elb():
    global inactive_alb
    global inactive_nlb
    global inactive_gtw
    count = 0
    paginator = elb.get_paginator('describe_load_balancers')
    for page in paginator.paginate():
        elb_response = page['LoadBalancers']
        for lb in elb_response:
            elb_name = lb['LoadBalancerName']
            all_elbs.append(elb_name)
            elb_arn = lb['LoadBalancerArn']
            elb_type = lb['Type']
            if elb_type == 'application':
                alb_modified_arn = 'app/' + elb_arn.split('/')[-2] + '/' + elb_arn.split('/')[-1]
                #check for alb connctions
                try:
                    alb_connection_metrics = metrics_check(alb_modified_arn, 'ActiveConnectionCount', 'Average', 'Count', 900, True, 'AWS/ApplicationELB', 'LoadBalancer')
                    if sum(alb_connection_metrics)/len(alb_connection_metrics) <= 0:
                        inactive_alb.append(elb_name) 
                except:
                    print(f"alb {elb_name} has no alb connection metrics")
            if elb_type == 'network':
                #check for ActiveFlowCount
                nlb_modified_arn = 'net/' + elb_arn.split('/')[-2] + '/' + elb_arn.split('/')[-1]
                try:
                    nlb_flow_metrics = metrics_check(nlb_modified_arn, 'ActiveFlowCount', 'Average', 'Count', 900, True, 'AWS/NetworkELB', 'LoadBalancer')
                    print('nlb metrics are:', nlb_flow_metrics)
                    if sum(nlb_flow_metrics)/len(nlb_flow_metrics) <= 0:
                        inactive_nlb.append(elb_name)
                except Exception as e:
                    print(f"Error for {elb_name}",e)
            if elb_type == 'gateway':
                #check for metrics
                gtw_modified_arn = 'gateway/' + elb_arn.split('/')[-2] + '/' + elb_arn.split('/')[-1]
                try:
                    gtw_flow_metrics = metrics_check(gtw_modified_arn, 'ActiveFlowCount', 'Average', 'Count', 900, True, 'AWS/NetworkELB', 'LoadBalancer')
                    print('gateway lb metrics are:', gtw_flow_metrics)
                    if sum(gtw_flow_metrics)/len(gtw_flow_metrics) <= 0:
                        inactive_gtw.append(elb_name)
                except Exception as e:
                    print(f"Error for {elb_name}",e)
            count +=1

    
    print('*************************ELB Final Output***************************')
    print('ALB which has AVG of 0 connection from past 15 Days:', inactive_alb)
    print('NLB which has AVG of 0 connection from past 15 Days:', inactive_nlb)
    print('Gateway which has AVG of 0 connection from past 15 Days:', inactive_gtw)
    print('We have Total ELB are', count)
