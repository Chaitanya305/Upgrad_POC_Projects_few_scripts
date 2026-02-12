-- Create Table

CREATE TABLE IF NOT EXISTS s3_report(
    bucket_name VARCHAR(200),
    upload_key VARCHAR(200),
    account_id VARCHAR(50),
    incomplete_object_buckets VARCHAR(10) DEFAULT 'NO'
    );
