import json
import os
import sys
import datetime
import boto3
import urllib.request
import pymysql
import time

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
    secret = get_secret_value("db-credentials", region_name="us-east-1")
    db_user_name = secret.get("username")
    db_password = secret.get("password")
    connection = pymysql.connect(
        host='zeroops-db.upgrad.com', 
        user=db_user_name,
        password=db_password,
        database='aws',
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

    var = event['detail']['userIdentity']['arn']
    type = event['detail']['userIdentity']['type']

    x = var.split("/")
    
    # Send to Teams
    user = x[2] if len(x) > 2 else "Unknown"
    role = x[1] if len(x) > 1 else "Unknown"
    if type == "IAMUser":
        user = role
        role = "N/A"

    # Determine event type
    detail_type = event.get("detail-type", "")
    account_id = event.get('account', 'Unknown')
    region = event['detail'].get('awsRegion', 'Unknown')
    webhook_url = "https://ueducation.webhook.office.com/webhookb2/bac08e4c-3a42-4df5-8eae-f3a30701063c@2e08a381-ba90-42a8-a03d-e078b350caaa/JenkinsCI/474b89efe14c4093ade45427404d1c14/c16d2a5d-953b-4df6-ad9a-312bbd4f9127/V2O6tlyDNy1ycia6Swztck2ALfemaPQfS1XK2sbe8oFWU1"

    #account name selection
    account_map = {'954772230024': 'Degrees - Jnu', '122610519847': 'Degrees - Bharathidasan', '861276124837': 'Degrees - Centurion', '535002871556': 'Degrees - Chandigarh', '717279695343': 'Degrees - Drmgr', '202533495773': 'Degrees - Dypatil', '039612850873': 'Degrees - Andhra', '890742599999': 'Degrees - Kiit', '491085420150': 'Degrees - Kuk', '345594584986': 'Degrees - Vgu', '597088024596': 'Degrees - Jain', '050451378467': 'Degrees - Niu', '443370702768': 'Degrees - Common', '833192497705': 'Degrees - Vistas', '097085170336': 'POC'}
    account_name = account_map.get(account_id, 'N/A')
    if detail_type == "AWS Console Sign In via CloudTrail":
        print(x)
        message = "User: {} logged in with Role: {} at {}".format(x[2],x[1],str(now))
        print(message)
        teams_message = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": "AWS Login Alert",
            "sections": [{
                "activityTitle": "🚨 AWS Federated Login Alert",
                "facts": [
                    {"name": "User", "value": user},
                    {"name": "Role", "value": role},
                    {"name": "Account ID", "value": account_id},
                    {"name": "Account Name", "value": account_name},
                    {"name": "Region", "value": region},
                    {"name": "Time (IST)", "value": now}
                ],
                "markdown": True
            }]
        }
        sql = """
            INSERT INTO aws_login (
                user, role, account_id, account_name, region, time
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """
        values = (user, role, account_id, account_name, region, now)
    elif detail_type == "AWS API Call via CloudTrail":
        # WRITE OPERATION EVENT
        # Only human users trigger this (IAMUser / AssumedRole)
        identity_type = event['detail']['userIdentity'].get('type')
        read_only = event['detail'].get('readOnly', True)
        print("event details are:- ",event['detail'])
        if identity_type in ["IAMUser", "AssumedRole"] and read_only is False:
            request_params = event['detail'].get('requestParameters', {})
            response_elements = event['detail'].get('responseElements', {})
            event_name = event['detail'].get('eventName', 'Unknown')
            if not response_elements:
                response_elements = request_params
            teams_message = {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": "AWS Write Operation Alert",
                "sections": [{
                    "activityTitle": "🚨 AWS Write Operation Detected",
                    "facts": [
                        {"name": "User", "value": user},
                        {"name": "Role", "value": role},
                        {"name": "Account ID", "value": account_id},
                        {"name": "Account Name", "value": account_name},
                        {"name": "Region", "value": region},
                        {"name": "Action", "value": event_name},
                        {"name": "Action Performed", "value": json.dumps(response_elements)},
                        {"name": "Time (IST)", "value": now}
                    ],
                    "markdown": True
                }]
            }
            sql = """
            INSERT INTO aws_activity (
                user, role, account_id, account_name, region, action, action_performed, time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (user, role, account_id, account_name, region, event_name, json.dumps(response_elements), now)
        else:
            # Not a human write operation, ignore
            return {"statusCode": 200, "body": "Ignored AWS service operation"}
    else:
        # Ignore other events
        return {"statusCode": 200, "body": "Event type ignored"}


    #send message to teams
    if "sso" in role or type == "IAMUser":
        data = json.dumps(teams_message).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        time.sleep(5)
        with urllib.request.urlopen(req) as resp:
            print("Teams Status:", resp.status)
            print("Teams Response:", resp.read().decode())
        #save this data to db
        insert_data(sql, values)

    else:
        print("As it's not done by sso user or iam user, so skip teams alert")



