import boto3
from datetime import datetime, timedelta, timezone, time
from zoneinfo import ZoneInfo

def lambda_handler(event, context):
    rds = boto3.client('rds')

    # Delete snapshots older than 2 days
    days_old = 2
    cutoff_time = datetime.now(ZoneInfo("Asia/Kolkata")) - timedelta(days=days_old)

    print(f"Deleting manual snapshots older than {days_old} days...")

    try:
        snapshots = rds.describe_db_snapshots(SnapshotType='manual')['DBSnapshots']
    except Exception as e:
        print("Error describing snapshots:", str(e))
        return

    for snap in snapshots:
        snap_id = snap['DBSnapshotIdentifier']
        snap_create_time = snap['SnapshotCreateTime'].astimezone(ZoneInfo("Asia/Kolkata"))
        is_encrypted = snap.get('Encrypted', False)

        # Skip automated snapshots
        if snap.get("SnapshotType") != "manual":
            continue

        # Delete manual snapshots older than 2 days
        if snap_create_time < cutoff_time and (all(s in snap_id for s in ('-reencrypted-', 'account-')) or 'common-' in snap_id):
            try:
                print(f"Deleting old snapshot: {snap_id}, created at: {snap_create_time}")
                rds.delete_db_snapshot(DBSnapshotIdentifier=snap_id)
            except Exception as e:
                print(f"Error deleting snapshot {snap_id}: {str(e)}")
        elif snap_create_time < cutoff_time and '-copied-dr-' in snap_id:
                try:
                    print(f"Deleting old snapshot: {snap_id}, created at {snap_create_time}")
                    rds.delete_db_snapshot(DBSnapshotIdentifier=snap_id)
                except Exception as e:
                    print(f"Error deleting snapshot {snap_id}: {str(e)}")

    print("Snapshot cleanup completed.")
