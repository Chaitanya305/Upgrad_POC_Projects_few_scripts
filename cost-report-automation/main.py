import boto3

from services.ec2 import check_ec2
from services.rds import rds_check
from services.s3 import s3_check
from services.nat import check_vpc
from services.elasticache import check_elasticcache
from services.dynamodb import check_dynamodb
from services.opensearch import check_opensearch
from services.lambda_fun import check_lambda
from services.elb import check_elb
from services.cloudwatch import check_alarm
from services.redshift import check_redshift
from services.ebs import check_ebs
from mysql_files.mysql_code import insert_ec2_data, insert_rds_data, insert_s3_data, insert_vpc_data, insert_elasticache_data, insert_dynamodb_data, insert_opensearch_data, insert_lambda_data, insert_elb_data, insert_cloudwatch_data, insert_redshift_data, insert_ebs_data

ec2 = boto3.client('ec2')
sts = boto3.client('sts')
region = ec2.meta.region_name
account_id = sts.get_caller_identity()['Account']

def cost_check():
    print("checking for aws region is: ", region)
    print("checking for aws_account is: ", account_id) 
    print('******************** check for EC2 **************************')
    check_ec2()
    print('*****************Inserting data into mysql for EC2 *******************')
    insert_ec2_data()
    print('******************** check for RDS **************************')
    rds_check()
    print('*****************Inserting data into mysql for RDS *******************')
    insert_rds_data()
    if region == "ap-south-1":
        print('******************** check for S3 **************************')
        s3_check()
        print('*****************Inserting data into mysql for S3 *******************')
        insert_s3_data()
    else:
        print(f"skiping s3 for {region}")
    print('***********checking for elasticache***********************')
    check_elasticcache()
    print('*****************Inserting data into mysql for ELASTICACHE *******************')
    insert_elasticache_data()
    print('***********checking for VPC***********************')
    check_vpc()
    print('*****************Inserting data into mysql for VPC *******************')
    insert_vpc_data()
    print('******************checking for dynamodb***************')
    check_dynamodb()
    print('*****************Inserting data into mysql for DynamoDB *******************')
    insert_dynamodb_data()
    print('******************checking for opensearch ***************')
    check_opensearch()
    print('*****************Inserting data into mysql for OpenSearch *******************')
    insert_opensearch_data()
    print('*******************checking for Lambda*******************')
    check_lambda()
    print('*****************Inserting data into mysql for lambda *******************')
    insert_lambda_data()
    print('*******************checking for ELB*******************')
    check_elb()
    print('*****************Inserting data into mysql for ELB *******************')
    insert_elb_data()
    print('*******************checking for Cloudwatch*******************')
    check_alarm()
    print('*****************Inserting data into mysql for Cloudwatch *******************')
    insert_cloudwatch_data()
    print('*******************checking for Redshift*******************')
    check_redshift()
    print('*****************Inserting data into mysql for Redshift *******************')
    insert_redshift_data()
    print('*******************checking for EBS*******************')
    check_ebs()
    print('*****************Inserting data into mysql for EBS *******************')
    insert_ebs_data()

cost_check()