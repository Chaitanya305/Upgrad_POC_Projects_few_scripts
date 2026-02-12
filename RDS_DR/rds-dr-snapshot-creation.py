import boto3
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def lambda_handler(event, context):

    # getting account ids
    sts = boto3.client('sts')
    source_account_id = sts.get_caller_identity()['Account']
    print("source account_id:",source_account_id)

    SOURCE_REGION = "ap-south-1"

    rds_source = boto3.client('rds', region_name=SOURCE_REGION)
    sts_client = boto3.client('sts')

    instances = rds_source.describe_db_instances()['DBInstances']
    if not instances:
        return {"status": "error", "message": "No RDS instances found"}

    responses = []

    # loop through all DB instances
    for db in instances:
        db_identifier = db['DBInstanceIdentifier']
        print("Processing RDS instance:",db_identifier)

        timestamp = datetime.now(ZoneInfo("Asia/Kolkata")).strftime('%Y-%m-%d-%H-%M-%S')
        take_snap = f"{db_identifier}-snap-{timestamp}"

        # create snapshot
        print("Creating snapshot:",take_snap)
        rds_source.create_db_snapshot(
            DBSnapshotIdentifier=take_snap,
            DBInstanceIdentifier=db_identifier,
        )
        print("snapshot taken.")

        responses.append({
            "db_instance": db_identifier,
            "snapshot": take_snap
        })

    return {
        "status": "success",
        "sourceAccount": source_account_id,
        "results": responses
    }
