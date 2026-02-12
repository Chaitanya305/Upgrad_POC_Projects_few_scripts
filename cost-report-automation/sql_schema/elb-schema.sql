CREATE TABLE IF NOT EXISTS elb_report (
    elb_name VARCHAR(100) NOT NULL,
    account_id VARCHAR(50),
    region VARCHAR(20),
    inactive_alb VARCHAR(10) DEFAULT 'NO',
    inactive_nlb VARCHAR(10) DEFAULT 'NO',
    inactive_gtw VARCHAR(10) DEFAULT 'NO'
    );