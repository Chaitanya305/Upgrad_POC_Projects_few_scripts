import json
import gzip
import base64
import boto3
import pymysql
import time
import datetime

def get_secret_value(secret_name, region_name='ap-south-1'):
    try:
        client = boto3.client('secretsmanager', region_name=region_name)

        response = client.get_secret_value(SecretId=secret_name)

        if 'SecretString' in response:
            secret = response['SecretString']
        else:
            secret = response['SecretBinary'].decode('utf-8')

        # Convert JSON string to dictionary
        try:
            return json.loads(secret)
        except json.JSONDecodeError:
            return secret  # Return raw string if not JSON

    except Exception as e:
        print(f"Error retrieving secret: {e}")
        return None

def insert_data(sql_query, values):
    secret = get_secret_value("prod", region_name="ap-south-1")
    db_user_name = secret.get("PUBLIC_MYSQL_USER_NAME")
    db_password = secret.get("PUBLIC_MYSQL_PASSWORD")
    connection = pymysql.connect(
        host='zeroops-db.upgrad.com', 
        user=db_user_name,
        password=db_password,
        database='k8s',
        cursorclass=pymysql.cursors.DictCursor
    )
    try:
        with connection.cursor() as cursor:
            #insert query
            sql = sql_query
            cursor.execute(sql, values)
        # Commit the transaction
        connection.commit()
        print("Inserted values in db successfully")
    except Exception as e:
        print(f"Error inserting data: {e}")
    finally:
        connection.close()


def lambda_handler(event, context):
    timec = datetime.datetime.now()
    timei = timec + datetime.timedelta(0,19800)
    now = timei.strftime("%d/%m/%Y %H:%M")
    # Decode the base64 data
    compressed_payload = base64.b64decode(event['awslogs']['data'])
    
    # Decompress the gzipped payload
    decompressed_payload = gzip.decompress(compressed_payload)
    
    # Parse the JSON data
    log_data = json.loads(decompressed_payload)
    
    # Optional: Access each log event
    for log_event in log_data['logEvents']:
        message_data = json.loads(log_event['message'])
        username = message_data['user']['username']
        sts_client = boto3.client("sts")
        account_id = sts_client.get_caller_identity()["Account"]
        print("account_id:",account_id)

        #get_account_name
        account_map = {'954772230024': 'Degrees - Jnu', '122610519847': 'Degrees - Bharathidasan', '861276124837': 'Degrees - Centurion', '535002871556': 'Degrees - Chandigarh', '717279695343': 'Degrees - Drmgr', '202533495773': 'Degrees - Dypatil', '039612850873': 'Degrees - Andhra', '890742599999': 'Degrees - Kiit', '491085420150': 'Degrees - Kuk', '345594584986': 'Degrees - Vgu', '597088024596': 'Degrees - Jain', '050451378467': 'Degrees - Niu', '443370702768': 'Degrees - Common', '833192497705': 'Degrees - Vistas', '097085170336': 'POC', '216989121040': 'Degrees - Atlas', '557690605483': 'Degrees - Alagappa', '290945445801': 'Degrees - Periyar', '518474287165': 'Degrees - Gradr'}
        account_name = account_map.get(account_id, 'N/A')

        if "upgrad-46com" in username:
            #print("Log Message:", log_event['message'])
            print("user name is:", username)
            print("Action performed:",message_data['verb'])
            action = message_data['verb']
            print("retion is perfosource on which acrmed:", message_data['requestURI'])
            resource = message_data['requestURI']
            
            username = message_data['user']['username'].split(':')
            username = username[3]
            username = username.replace("46", ".")
            username = username.replace("64", "@")
            username = username.replace("-", "")
            print("final username is", username)

            if "dev" in resource and "venus" in resource and "loadtest" in resource:
                cluster = "Degrees-Common-dev"
            else:
                cluster = f"{account_name}-Prod"

            #insert data in db
            sql = """
            INSERT INTO k8s_activity (
                username, cluster, account_name, account_id, action, resource, time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (username, cluster, account_name, account_id, action, resource, now)

            insert_data(sql, values)