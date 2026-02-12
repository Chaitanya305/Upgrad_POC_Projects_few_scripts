-- Create Table 
CREATE TABLE ec2_report (
    instance_id VARCHAR(50) PRIMARY KEY NOT NULL,
    instance_name VARCHAR(100),
    account_id VARCHAR(50) NOT NULL,
    region VARCHAR(20) NOT NULL, 
    previous_gen_instances VARCHAR(10) default 'NO',
    cpu_less_than_5 VARCHAR(10) default 'NO',
    network_IO_less_100_KB VARCHAR(10) default 'NO',
    windows_instance_T_family VARCHAR(10) default 'NO',
    dedicated_tenancy VARCHAR(10) default 'NO',
    no_graviton VARCHAR(10) default 'NO',
    network_io_less_100_kb_3hrs VARCHAR(10) default 'NO',
    no_amd VARCHAR(10) default 'NO',
    failed_health_check VARCHAR(10) default 'NO',
    stopped_instances_last_15Days VARCHAR(10) default 'NO'
);
