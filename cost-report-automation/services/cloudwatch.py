import boto3
from datetime import datetime, timedelta, timezone

cloudwatch = boto3.client('cloudwatch')
logs = boto3.client('logs')

insufficient_alarm = []
inappropriate_log_groups = []
no_retention_period = []
all_log_groups = []
all_cloudwatch = []

def log_retention():
    #check for log retention Period
    global inappropriate_log_groups
    global no_retention_period
    loggroup_count = 0
    paginator = logs.get_paginator('describe_log_groups')
    for page in paginator.paginate():
        log_response = page['logGroups']
        for loggroup in log_response:
            loggroup_name = loggroup['logGroupName']
            all_log_groups.append(loggroup_name)
            retention = False
            #check retention priod is set or not
            if 'retentionInDays' in loggroup:
                retention_period = loggroup['retentionInDays']
                if retention_period >= 7:
                    retention = True
            else:
                #as no retention period is set
                no_retention_period.append(loggroup_name)
                retention = True
            #data stored in log group
            stored = False    
            storage = loggroup['storedBytes']
            if storage >= 1 * 1073741824:
                stored = True
            #age of log group
            age = False
            age_threshold = datetime.now(timezone.utc) - timedelta(days=30)
            creation_time_ms = loggroup['creationTime']
            creation_time = datetime.fromtimestamp(creation_time_ms / 1000.0,  tz=timezone.utc)
            if creation_time <= age_threshold:
                age = True
            if retention and stored and age:
                inappropriate_log_groups.append(loggroup_name)
            loggroup_count +=1
    return inappropriate_log_groups, no_retention_period, loggroup_count


def check_alarm():
    #list alarms
    global insufficient_alarm
    alarm_count = 0
    paginator = cloudwatch.get_paginator('describe_alarms')
    for page in paginator.paginate():
        cloudwatch_response = page['MetricAlarms']
        for alarm in cloudwatch_response:
            alarm_name = alarm['AlarmName']
            all_cloudwatch.append(alarm_name)
            alarm_arn = alarm['AlarmArn']
            if alarm['StateValue'] == 'INSUFFICIENT_DATA':
                threshold_time = datetime.now(timezone.utc) - timedelta(days=2)
                #check for state update time
                state_updated_time = alarm['StateUpdatedTimestamp']
                if state_updated_time < threshold_time:
                    insufficient_alarm.append(alarm_name)
            alarm_count +=1


    inappropriate_log_groups, no_retention_period, loggroup_count = log_retention()
    print('****************cloudwatch final output is***************')    
    print('CloudWatch Alarms are in insufficient state for more than 2 days are:', insufficient_alarm)
    print('CloudWatch log groups which have unappropriate log retention period:', inappropriate_log_groups)
    print('CloudWatch log groups which have no log retention period set:', no_retention_period, len(no_retention_period))
    print('We have Total Alarms', alarm_count)
    print('We have Total Log Groups are', loggroup_count)