CREATE TABLE IF NOT EXISTS lambda_report(
    function_name VARCHAR(100) NOT NULL,
    account_id VARCHAR(50),
    region VARCHAR(20),
    error_function VARCHAR(10) DEFAULT 'NO',
    unutilized_provision_concurrency VARCHAR(10) DEFAULT 'NO',
    non_graviton_function VARCHAR(10) DEFAULT 'NO',
    underutilized_provision_concurrency_fucntion VARCHAR(10) DEFAULT 'NO',
    underutilized_function VARCHAR(10) DEFAULT 'NO'
    );