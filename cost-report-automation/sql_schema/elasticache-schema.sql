CREATE TABLE IF NOT EXISTS elasticache_report(
    cluster_id VARCHAR(100) NOT NULL,
    account_id VARCHAR(50),
    region VARCHAR(20),
    old_gen_cluster VARCHAR(10) DEFAULT 'NO',
    no_graviton VARCHAR(10) DEFAULT 'NO',
    idle_redis_cluster VARCHAR(10) DEFAULT 'NO',
    idle_memcached_cluster VARCHAR(10) DEFAULT 'NO',
    redis_no_read VARCHAR(10) DEFAULT 'NO',
    underutilized_memcached_cluster VARCHAR(10) DEFAULT 'NO',
    underutilized_redis_cluster VARCHAR(10) DEFAULT 'NO',
    replica_redis_cluster VARCHAR(10) DEFAULT 'NO');