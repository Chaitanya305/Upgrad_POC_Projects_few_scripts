CREATE TABLE IF NOT EXISTS ebs_report(
    EBS_volume_id VARCHAR(100),
    account_id VARCHAR(50),
    region VARCHAR(20),
    available_volume VARCHAR(10) DEFAULT 'NO',
    not_gp3_volume VARCHAR(10) DEFAULT 'NO',
    unused_attached_ebs VARCHAR(10) DEFAULT 'NO'
    );