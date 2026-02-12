import boto3

region="ap-south-1"


ec2_client = boto3.client('ec2',region_name=region)