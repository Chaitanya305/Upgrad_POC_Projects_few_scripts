CREATE TABLE IF NOT EXISTS opensearch_report(
    cluster_name VARCHAR(100),
    node_id VARCHAR(100),
    account_id VARCHAR(50),
    region VARCHAR(20),
    red_cluster VARCHAR(10) DEFAULT 'NO',
    idle_cluster VARCHAR(10) DEFAULT 'NO',
    no_gp3_ebs VARCHAR(10) DEFAULT 'NO',
    idle_master_nodes VARCHAR(10) DEFAULT 'NO',
    node_with_previous_generation VARCHAR(10) DEFAULT 'NO',
    node_without_graviton VARCHAR(10) DEFAULT 'NO'
    );