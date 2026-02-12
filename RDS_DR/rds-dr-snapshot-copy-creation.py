import boto3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
 
def lambda_handler(event, context):

    sts = boto3.client('sts')
    source_account_id = sts.get_caller_identity()['Account']
    print("source account_id:",source_account_id)
 
    SOURCE_REGION = "ap-south-1"
    snapshot_id = event["detail"]["SourceIdentifier"]
    print("event details are", event["detail"])
    print("Snapshot id is", snapshot_id)
    rds_source = boto3.client('rds', region_name=SOURCE_REGION)
    kms = boto3.client('kms', region_name=SOURCE_REGION)
    kms_alias_name = "alias/rds-snapshot-key"
 
    # Resolve KMS key for re-encryption
    try:
        alias_info = kms.describe_key(KeyId=kms_alias_name)
        SOURCE_CUSTOMER_KMS_KEY_ID = alias_info["KeyMetadata"]["Arn"]
        print("Source KMS Key:", SOURCE_CUSTOMER_KMS_KEY_ID)
    except Exception as e:
        print(f"Error resolving KMS Alias {kms_alias_name}: {str(e)}")
        raise
 
 
    snap = rds_source.describe_db_snapshots(DBSnapshotIdentifier=snapshot_id)['DBSnapshots'][0]
    snap_status = snap["Status"]
    snap_id = snapshot_id
    snap_arn = snap["DBSnapshotArn"]

    if snap_status == "available":
        is_encrypted = snap.get("Encrypted", False)
        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d-%H-%M-%S')

        if is_encrypted:
            target_snap_name = f"{snap_id}-reencrypted-{timestamp}"
        else:
            target_snap_name = f"{snap_id}-copied-dr-{timestamp}"

        print(f"Copying snapshot as {target_snap_name}")
        if is_encrypted:
            print(f"Snapshot is encrypted. Re-encrypting using {SOURCE_CUSTOMER_KMS_KEY_ID}")
            rds_source.copy_db_snapshot(
                SourceDBSnapshotIdentifier=snap_arn,
                TargetDBSnapshotIdentifier=target_snap_name,
                KmsKeyId=SOURCE_CUSTOMER_KMS_KEY_ID,
                SourceRegion=SOURCE_REGION
            )
            
        else:
            print("Snapshot is not ecnrypted")
            rds_source.copy_db_snapshot(
                SourceDBSnapshotIdentifier=snap_arn,
                TargetDBSnapshotIdentifier=target_snap_name,
                SourceRegion=SOURCE_REGION
            )
    else:
        print("snapshot is not in availaible state")
