import boto3
import requests
from requests_aws4auth import AWS4Auth

host = 'https://vpc-ug-nonprod-application-ancqfmmt2364owa2fvv3onhjie.ap-south-1.es.amazonaws.com' # domain endpoint
region = 'ap-south-1' # e.g. us-west-1
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

# Register repository

path = '/_snapshot/stage-snapshot-repo' # the OpenSearch API endpoint
url = host + path

payload = {
  "type": "s3",
  "settings": {
    "bucket": "upgrad-elasticsearch-nv-mumbai-migration",
    "base_path": "stage",
    "region": "us-east-1",
    "role_arn": "arn:aws:iam::635145294553:role/ESSnapshotRole",
    "endpoint": "s3.amazonaws.com"
  }
}

headers = {"Content-Type": "application/json"}

r = requests.put(url, auth=awsauth, json=payload, headers=headers)

print(r.status_code)
print(r.text)