-- Create Table

CREATE TABLE IF NOT EXISTS rds_report (
    DBInstance_id VARCHAR(100),
    account_id VARCHAR(50),
    region VARCHAR(20),
    previous_gen_rds_instances VARCHAR(10) DEFAULT 'NO',
    idle_rds_instances VARCHAR(10) DEFAULT 'NO',
    read_replica_rp_more_than_20 VARCHAR(10) DEFAULT'NO',
    rds_rp_more_than_20 VARCHAR(10) DEFAULT 'NO',
    rds_no_graviton VARCHAR(10) DEFAULT 'NO');