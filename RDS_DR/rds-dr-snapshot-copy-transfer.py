import boto3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
 
def lambda_handler(event, context):
    sts = boto3.client('sts')
    source_account_id = sts.get_caller_identity()['Account']
    snapshot_id = event["detail"]["SourceIdentifier"]
    print("Event is:", event["detail"])

    rds_source = boto3.client('rds')
    DESTINATION_ACCOUNT_ID = "443370702768"
    DESTINATION_REGION = "ap-south-1"
    SOURCE_REGION = "ap-south-1"

    # share snapshot in destination account
    rds_source.modify_db_snapshot_attribute(
            DBSnapshotIdentifier=snapshot_id,
            AttributeName="restore",
            ValuesToAdd=[DESTINATION_ACCOUNT_ID]
        )
    
    sts_client = boto3.client('sts')

    # copy snapshot in destination account
    assumed_role = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{DESTINATION_ACCOUNT_ID}:role/CrossAccountSnapshotCopyRole",
        RoleSessionName="rds-copy" 
    )

    creds = assumed_role['Credentials']

    kms = boto3.client('kms', region_name=DESTINATION_REGION, aws_access_key_id=creds["AccessKeyId"], aws_secret_access_key=creds["SecretAccessKey"], aws_session_token=creds["SessionToken"])
    kms_alias_name = "alias/rds-dr-key"
 
    # Resolve KMS key for copy snapshot into destination account
    try:
        alias_info = kms.describe_key(KeyId=kms_alias_name)
        DESTINATION_CUSTOMER_KMS_KEY_ID = alias_info["KeyMetadata"]["Arn"]
        print("Destination KMS Key:", DESTINATION_CUSTOMER_KMS_KEY_ID)
    except Exception as e:
        print(f"Error resolving KMS Alias {kms_alias_name}: {str(e)}")
        raise

    # Update destination KMS key policy
    kms_dest = boto3.client('kms', region_name=DESTINATION_REGION, aws_access_key_id=creds["AccessKeyId"], aws_secret_access_key=creds["SecretAccessKey"], aws_session_token=creds["SessionToken"])

    # Get existing key policy
    policy = kms_dest.get_key_policy(KeyId=DESTINATION_CUSTOMER_KMS_KEY_ID, PolicyName='default')['Policy']
    policy_json = json.loads(policy)

    # Create statement for the source account
    new_statement = {
        "Sid": source_account_id,  
        "Effect": "Allow",
        "Principal": {
            "AWS": f"arn:aws:iam::{source_account_id}:role/lambda-snap-share-role"
        },
        "Action": [
            "kms:Encrypt",
            "kms:Decrypt",
            "kms:ReEncrypt*",
            "kms:GenerateDataKey*",
            "kms:DescribeKey",
            "kms:CreateGrant",
            "kms:GetKeyPolicy",
            "kms:PutKeyPolicy"
        ],
        "Resource": "*"
    }

    # Add only if not already present
    if not any(s.get("Sid") == source_account_id for s in policy_json.get("Statement", [])):
        policy_json["Statement"].append(new_statement)
        kms_dest.put_key_policy(
            KeyId=DESTINATION_CUSTOMER_KMS_KEY_ID,
            PolicyName='default',
            Policy=json.dumps(policy_json)
        )
        print(f"Added new KMS policy statement for source account {source_account_id}")
    else:
        print(f"KMS policy for source account {source_account_id} already exists")

    rds_dest = boto3.client(
        "rds",
        region_name=DESTINATION_REGION,
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"]
    )
    dest_snap = f"account-{source_account_id}-{snapshot_id}"
    final_snap_arn = f"arn:aws:rds:{SOURCE_REGION}:{source_account_id}:snapshot:{snapshot_id}"
    print("Final snapshot ARN being copied:", final_snap_arn)
    try:
        rds_dest.copy_db_snapshot(
            SourceDBSnapshotIdentifier=final_snap_arn,
            TargetDBSnapshotIdentifier=dest_snap,
            KmsKeyId=DESTINATION_CUSTOMER_KMS_KEY_ID,
            SourceRegion=SOURCE_REGION
        )
        print(f"Snapshot copy to destination for {snapshot_id} succeeded")

        message = event["detail"]["Message"]
        parts = message.split()
        original_snapshot = parts[4]
        print("Original snapshot name:", original_snapshot)

        if "Finished copy of snapshot" in message:
            # Delete original snapshot only if older than 1 day
            delete_origsnap_older_than_days = 1
            retention_cutoff_time = datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(days=delete_origsnap_older_than_days)

            try:
                orig_snap_info = rds_source.describe_db_snapshots(DBSnapshotIdentifier=original_snapshot)['DBSnapshots'][0]
                snap_taken_time = orig_snap_info['SnapshotCreateTime'].astimezone(ZoneInfo("Asia/Kolkata"))
                
                if snap_taken_time < retention_cutoff_time:
                    rds_source.delete_db_snapshot(DBSnapshotIdentifier=original_snapshot)
                    print(f"Deleted original snapshot {original_snapshot}, created at {snap_taken_time}")
                else:
                    print(f"Original snapshot {original_snapshot} is not older than {delete_origsnap_older_than_days} day(s), so skipping deletion")
            except Exception as e:
                print("Error deleting original snapshot:", str(e))

        #delete one day older copied snapshots (non-encrypted and encrypted both)
        print("Checking for old copied snapshots in source account...")
        delete_older_than_days = 1
        cutoff_time = datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(days=delete_older_than_days)
        snapshots = rds_source.describe_db_snapshots(SnapshotType='manual')['DBSnapshots']
        for snap in snapshots:
            snap_id = snap['DBSnapshotIdentifier']
            snap_time = snap['SnapshotCreateTime'].astimezone(ZoneInfo("Asia/Kolkata"))
            is_encrypted = snap.get('Encrypted', False)
        
            # Delete only re-encrypted snapshots older than 1 day
            if is_encrypted and '-reencrypted-' in snap_id and snap_time < cutoff_time:
                try:
                    print(f"Deleting old snapshot: {snap_id}, created at {snap_time}")
                    rds_source.delete_db_snapshot(DBSnapshotIdentifier=snap_id)
                except Exception as e:
                    print(f"Error deleting snapshot {snap_id}: {str(e)}")
            # Delete only re-encrypted snapshots older than 1 day
            elif is_encrypted == False and '-copied-dr-' in snap_id and snap_time < cutoff_time:
                try:
                    print(f"Deleting old snapshot: {snap_id}, created at {snap_time}")
                    rds_source.delete_db_snapshot(DBSnapshotIdentifier=snap_id)
                except Exception as e:
                    print(f"Error deleting snapshot {snap_id}: {str(e)}")


    finally:
        # Remove temporary KMS permission
        # Get latest policy
        policy = kms_dest.get_key_policy(KeyId=DESTINATION_CUSTOMER_KMS_KEY_ID, PolicyName='default')['Policy']
        policy_json = json.loads(policy)
        # Remove statement for source account
        statements = [s for s in policy_json.get("Statement", []) if s.get("Sid") != source_account_id]
        policy_json["Statement"] = statements
        kms_dest.put_key_policy(
            KeyId=DESTINATION_CUSTOMER_KMS_KEY_ID,
            PolicyName='default',
            Policy=json.dumps(policy_json)
        )
        print(f"Removed KMS policy statement for source account {source_account_id}")