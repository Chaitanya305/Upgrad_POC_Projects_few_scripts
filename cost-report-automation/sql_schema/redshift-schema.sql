CREATE TABLE IF NOT EXISTS redshift_report(
    redshift_clusters VARCHAR(100),
    account_id VARCHAR(50),
    region VARCHAR(20),
    idle_redshift VARCHAR(10) DEFAULT 'NO'
    );