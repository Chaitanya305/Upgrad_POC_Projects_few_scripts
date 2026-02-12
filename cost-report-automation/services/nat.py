import boto3
from datetime import datetime, timedelta, timezone
from common_utils.metrics import metrics_check
from services.ec2 import stopped_instance

ec2 = boto3.client('ec2')

data_loss_nat = []
no_packets_out = []
no_packets_in = []
unused_eip = []
no_outgoing_traffic = []
pub_ips = []
all_nats = []

def check_vpc():
    global data_loss_nat
    global no_packets_out
    global no_packets_in
    global unused_eip
    global no_outgoing_traffic
    global all_nats
    nat_details = ec2.describe_nat_gateways()
    #to check non associated EIP
    eip = ec2.describe_addresses()
    global pub_ips
    for Address in eip['Addresses']:
        public_ip = Address['PublicIp']
        pub_ips.append(public_ip)
        if 'InstanceId' in Address:
            print(f"ip {public_ip} is associated with {Address['InstanceId']}")
            if Address['InstanceId'] in stopped_instance:
                unused_eip.append(public_ip)
            continue
        elif 'NetworkInterfaceId' in Address:
            print(f"ip {public_ip} is associated with {Address['NetworkInterfaceId']}")
            continue
        else:
            unused_eip.append(public_ip)
    count = 0
    for nat in nat_details['NatGateways']:
        nat_id = nat['NatGatewayId']
        all_nats.append(nat_id)
        print('checking for', nat['NatGatewayId'])
        # Fetch the BytesInFromDestination metric
        bytes_in = sum(metrics_check(nat_id, 'BytesInFromDestination', 'Sum', 'Bytes', 900, True, 'AWS/NATGateway', 'NatGatewayId'))
        # Fetch the BytesOutToSource metric
        bytes_out = sum(metrics_check(nat_id, 'BytesOutToSource', 'Sum', 'Bytes', 900, True, 'AWS/NATGateway', 'NatGatewayId'))
        if bytes_in != bytes_out:
            data_loss_nat.append(nat_id)
        #check for Packets Out To Destination
        packets_out = metrics_check(nat_id, 'PacketsOutToDestination', 'Average', 'Count', 900, True, 'AWS/NATGateway', 'NatGatewayId')
        if packets_out:
            avg_packets_out = sum(packets_out)/len(packets_out)
            if avg_packets_out <= 0:
                no_packets_out.append(nat_id)
        #check for Packets in To Destination            
        packets_in = metrics_check(nat_id, 'PacketsInFromSource', 'Average', 'Count', 900, True, 'AWS/NATGateway', 'NatGatewayId')
        if packets_in:
            avg_packets_in = sum(packets_in)/len(packets_in)
            if avg_packets_in <= 0:
                no_packets_in.append(nat_id)
        #There should be no unused Elastic IPs
        for nat_public_ip in nat['NatGatewayAddresses']:
            print('nat pub ip is', nat_public_ip['PublicIp'])
            if nat_public_ip['PublicIp'] in unused_eip:
                print(f"pub ip {nat_public_ip} is associated with nat {nat_id}")
                unused_eip.remove(nat_public_ip)
        #NAT Gateways with no outgoing traffic, BytesOutToDestination= traffic going to the internet from clients that are behind the NAT gateway
        BytesOuttodestination = metrics_check(nat_id, 'BytesOutToDestination', 'Average', 'Bytes', 900, True, 'AWS/NATGateway', 'NatGatewayId')
        if BytesOuttodestination:
            avg_BytesOuttodestination = sum(BytesOuttodestination)/len(BytesOuttodestination)
            if avg_BytesOuttodestination <= 0:
                no_outgoing_traffic.append(nat_id)
        count +=1

    print("********************NAT final output *************************** ")
    print("NAT Gateways with data loss in the past 15 days: ", data_loss_nat)
    print("NAT Gateways with avg of 0 packet out in last 15 days",no_packets_out)
    print("NAT Gateways with avg of 0 packet in from source in last 15 days",no_packets_in)
    print("Unused EIP are: ", unused_eip)
    print("Instance stopped from last 15 days are: ", stopped_instance) 
    print('NAT Gateways with 0 traffic flow in last 15 days:', no_outgoing_traffic)
    print('Total NAT we have are:', count)
