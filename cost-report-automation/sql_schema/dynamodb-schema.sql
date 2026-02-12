CREATE TABLE IF NOT EXISTS dynamodb_report(
    table_name VARCHAR(100),
    account_id VARCHAR(50),
    region VARCHAR(20),
    gsi VARCHAR(200),
    inactive_gsi_table VARCHAR(10) DEFAULT 'NO',
    underutilized_gsi_reads_capacity VARCHAR(10) DEFAULT 'NO',
    underutilized_gsi_writes_capacity VARCHAR(10) DEFAULT 'NO',
    underutilized_reads_capacity VARCHAR(10) DEFAULT 'NO',
    underutilized_writes_capacity VARCHAR(10) DEFAULT 'NO',
    underutilized_capacity_tables VARCHAR(10) DEFAULT 'NO'
    );