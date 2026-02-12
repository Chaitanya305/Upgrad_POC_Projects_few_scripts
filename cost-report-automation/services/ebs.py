import boto3
from services.ec2 import stopped_instance

ec2_client = boto3.client('ec2')

available_volume = []
not_gp3_volume = []
unused_attached_ebs = []
all_ebs_volumes = []

def check_ebs():
    global available_volume
    global not_gp3_volume
    global unused_attached_ebs
    count = 0
    paginator = ec2_client.get_paginator('describe_volumes')
    for page in paginator.paginate():
        ebs_response = page['Volumes']
        for volume in ebs_response:
            volume_id = volume['VolumeId']
            volume_type = volume['VolumeType']
            all_ebs_volumes.append(volume_id)
            #check volume is attached or not 
            if volume['State'] == 'available':
                available_volume.append(volume_id)
            #check general purpose volume should be of gp3 type 
            if 'g' in volume_type and volume_type != 'gp3':
                not_gp3_volume.append(volume_id)
            #check if volume attahed to instnace which is stopped from last 15 days
            if volume['State'] == 'in-use':
                attached_instance_id = volume['Attachments'][0]['InstanceId']
                if attached_instance_id in stopped_instance:
                    unused_attached_ebs.append(volume_id)
            count +=1

    print('******************** EBS Final Outptu is **************************')
    print('Volumes which are available state are:', available_volume)
    print('General purpose EBS volumes with gp2 type are:', not_gp3_volume)
    print('EBS volumes attached to instances stopped for last 15 days', unused_attached_ebs)
    print('We have Total EBS are:', count)
