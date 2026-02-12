import boto3

from datetime import datetime, timedelta, timezone
from common_utils.constants import previous_generation_instance_types
from common_utils.metrics import metrics_check, p99_check


ec2 = boto3.client('ec2')
ag =  boto3.client('autoscaling')
cloudwatch = boto3.client('cloudwatch')

stopped_instance = []
previous_generation_instance_id = []
low_cpu_instances = []
low_network_instances =[]
t_windows_instances=[]
dedicated_Tenancy_instance=[]
without_Graviton_instance = []
low_network_3hrs=[]
not_AMD_instances = []
failed_health_check_instances=[]
instance_ids = {}
count = 0

#to check instance is part of ASG or not
def standalone_instance(instance_id):
    response = ag.describe_auto_scaling_instances(InstanceIds=[instance_id])
    if len(response['AutoScalingInstances']) == 0:
        return True
    else:
        return False

#check for network utilization
def network_utilization(instance_id):
    threshold = 100 * 1024
    network_in = metrics_check(instance_id, 'NetworkIn', 'Maximum', 'Bytes', 900, True, 'AWS/EC2', 'InstanceId')
    network_out = metrics_check(instance_id, 'NetworkOut', 'Maximum', 'Bytes', 900, True, 'AWS/EC2', 'InstanceId')
    #check for threshold
    if network_in and network_out:
        print(f"max network in value for instance {instance_id} ", max(network_in))
        print(f"max network out value for {instance_id}", max(network_out))
        if max(network_in) < threshold and max(network_out) < threshold:
            return True
        else:
            return False


#Standalone EC2 instances shouldn't experience very low network activity of Network In/Out less than a specified threshold consistently for more than 3 hours in a day.
def network_usage(instance_id):
    threshold = 100 * 1024  # 100KB
    network_in = metrics_check(instance_id, 'NetworkIn', 'Maximum', 'Bytes', 900, False, 'AWS/EC2', 'InstanceId')
    network_out = metrics_check(instance_id, 'NetworkOut', 'Maximum', 'Bytes', 900, False, 'AWS/EC2', 'InstanceId')
    # Ensure the data points are sorted by timestamp
    sorted_data_points_in = sorted(network_in, key=lambda dp: dp['Timestamp'])
    sorted_data_points_out = sorted(network_out, key=lambda dp: dp['Timestamp'])
    # Organize datapoints by day
    daily_data_in = {}
    in_network = False
    out_network = False
    for datapoint_in in sorted_data_points_in:
        # Convert timestamp to date (YYYY-MM-DD)
        day = datapoint_in['Timestamp'].date()
        if day not in daily_data_in:
            daily_data_in[day] = []
        daily_data_in[day].append(datapoint_in['Maximum'])
    # Check each day for low activity periods consistently 3hrs
    for day, data_points in daily_data_in.items():
        low_in_activity_count = 0
        for value in data_points:
            if value < threshold:
                low_in_activity_count += 1
            else:
                low_in_activity_count = 0 
            # Check if low activity occurred for more than 3 hours (12 intervals)
            if low_in_activity_count >= 12:  # 12 data points = 3 hours of 15-minute intervals
            #return True  # Low activity detected for at least one day consistently for 3 hours
                in_network = True
                break
        if in_network:
            break

    daily_data_out = {}
    for datapoint_out in sorted_data_points_out:
        # Convert timestamp to date (YYYY-MM-DD)
        day = datapoint_out['Timestamp'].date()
        if day not in daily_data_out:
            daily_data_out[day] = []
        daily_data_out[day].append(datapoint_out['Maximum'])
    # Check each day for low activity periods consistently 3hrs
    for day, data_points in daily_data_out.items():
        low_out_activity_count = 0
        for value in data_points:
            if value < threshold:
                low_out_activity_count += 1
            else:
                low_out_activity_count = 0 
            # Check if low activity occurred for more than 3 hours (12 intervals)
            if low_out_activity_count >= 12:  # 12 data points = 3 hours of 15-minute intervals
                #return True  # Low activity detected for at least one day consistently for 3 hours
                out_network = True
                break
        if out_network:
            break
    if in_network and out_network:
        return True
    return False


#identify EC2 instances that have failed health checks more than 100 times in a single day
def health_check(instance_id):
    hc_metric = metrics_check(instance_id, 'StatusCheckFailed', 'Sum', 'Count', 86400, True, 'AWS/EC2', 'InstanceId')
    if any(value >= 100.0 for value in hc_metric):
        return True

#listing instance which are stopped for last 15 days
def stopped_instances(instance_id, stopped_date, days=15):
    global stopped_instance
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    if stopped_date <= cutoff_date:
        stopped_instance.append(instance_id)
        

#cpu p99
def ec2_cpu_metrics(instance_id, metric_name, statistics, unit, period, namespace, dim_name):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=15)
    metrics = cloudwatch.get_metric_statistics(
        Period=period,  # data points interval
        StartTime=start_time,
        EndTime=end_time,
        MetricName=metric_name,
        Namespace=namespace,
        #Statistics = ['Average'],
        ExtendedStatistics=[statistics],
        Dimensions=[{'Name': dim_name, 'Value': instance_id}],
        Unit = unit
    )
    return [datapoint['ExtendedStatistics']['p99'] for datapoint in metrics['Datapoints']]

def check_graviton(instance_type):
    family = instance_type.split('.')[0]
    return 'g' not in family

def check_amd(instance_type):
    family = instance_type.split('.')[0]
    return 'a' not in family

def check_ec2():
    global previous_generation_instance_id
    global low_cpu_instances 
    global low_network_instances
    instance_details = ec2.describe_instances()
    global t_windows_instances
    global dedicated_Tenancy_instance 
    global low_network_3hrs 
    global not_AMD_instances
    global without_Graviton_instance
    global failed_health_check_instances
    global instance_ids
    graviton_instance_type = ('c7g','m7g','t4g', 'r7g')
    global count
    for reservation in instance_details['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            platform = instance['PlatformDetails']
            Tenancy = instance['Placement']['Tenancy']
            #list all ec2 instance we have
            instance_name = ""
            for name in instance['Tags']:
                if name['Key'] == "Name":
                    instance_name = name['Value']
                    break   
            instance_ids[instance_id] = instance_name
            #for stopped instances
            instance_state = instance['State']['Name']
            if instance_state == 'stopped':
                state_transition_time = instance.get('StateTransitionReason', '')
                if "User initiated" in state_transition_time:
                    try:
                        # Extract date from StateTransitionReason
                        stopped_date_str = state_transition_time.split('(')[-1].split(')')[0]
                        stopped_date = datetime.strptime(stopped_date_str, "%Y-%m-%d %H:%M:%S %Z").replace(tzinfo=timezone.utc)
                        stopped_instances(instance_id, stopped_date)   
                    except ValueError:
                        print(f"Warning: Unrecognized date format: {stopped_date_str}")

            if instance_state == 'stopped' or instance_state == 'running':
                print(f"for {instance_id} and its platform is {platform}")
                #checking for previous generation or not
                if instance_type in previous_generation_instance_types:
                    previous_generation_instance_id.append(instance_id)
                #checking for standalone or not
                if standalone_instance(instance_id):
                    print(f"{instance_id} is standalone")
                    #check for cpu utilization
                    cpu_metric_values = ec2_cpu_metrics(instance_id, 'CPUUtilization', 'p99', 'Percent', 900, 'AWS/EC2', 'InstanceId')
                    if p99_check(instance_id, 5.0, cpu_metric_values):
                        low_cpu_instances.append(instance_id)
                    if network_utilization(instance_id):
                        low_network_instances.append(instance_id)
                    if not instance_type.startswith('t'):
                        if platform == 'windows' and ec2.describe_instance_types(InstanceTypes=[instance_type])['InstanceTypes'][0]['VCpuInfo']['DefaultVCpus'] <= 8 :
                            t_windows_instances.append(instance_id)
                    if Tenancy == 'dedicated':
                        dedicated_Tenancy_instance.append(instance_id)
                    if check_graviton(instance_type):
                        without_Graviton_instance.append(instance_id)
                    if network_usage(instance_id):
                        low_network_3hrs.append(instance_id)
                    if check_amd(instance_type):
                        not_AMD_instances.append(instance_id)
                    if health_check(instance_id):
                        failed_health_check_instances.append(instance_id)
                count +=1
    print("************************final EC2 output is ******************************")
    print("previous Generation instances are: ", previous_generation_instance_id)
    print("instance with AVG cpu utlisation less than 5 for last 15 days: ", low_cpu_instances)
    print("instance with max network in and out less than 100 KB for last 15 days: ", low_network_instances)
    print("Instances running Windows OS with base reqirement of 8vCPU or less, hosted other than T instance family ", t_windows_instances)
    print("Instances with dedicated Tenancy are: ", dedicated_Tenancy_instance)
    print("instances which are running without Graviton Processor: ", without_Graviton_instance)
    print('low network in/out for consistently 3hrs in day instances are: ',low_network_3hrs)
    print('instances without AMD processor :', not_AMD_instances)
    print('failed health checks 100 times on a single day in the last 15 days: ', failed_health_check_instances)
    print('instance stopped from last 15 days are:', stopped_instance)
    print('total instance we have:', count)
    print('len of all instances is:', len(instance_ids))
    without_Graviton_instance.clear()
    print('graviton instances are:', without_Graviton_instance)
