CREATE TABLE IF NOT EXISTS vpc_report(
    eip VARCHAR(50),
    nat_id VARCHAR(100),
    account_id VARCHAR(50),
    region VARCHAR(20),
    data_loss_nats VARCHAR(10) DEFAULT 'NO',
    no_packet_out VARCHAR(10) DEFAULT 'NO',
    no_packet_in VARCHAR(10) DEFAULT 'NO',
    unused_eips VARCHAR(10) DEFAULT 'NO',
    no_outgoing_traffic_nat VARCHAR(10) DEFAULT 'NO'
    );