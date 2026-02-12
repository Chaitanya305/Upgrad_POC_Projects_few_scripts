CREATE TABLE IF NOT EXISTS cloudwatch_report(
    alarm_name VARCHAR(100),
    log_groups VARCHAR(100),
    account_id VARCHAR(50),
    region VARCHAR(20),
    insufficient_alarm VARCHAR(10) DEFAULT 'NO',
    inappropriate_log_groups VARCHAR(10) DEFAULT 'NO',
    no_retention_period VARCHAR(10) DEFAULT 'NO'
    );