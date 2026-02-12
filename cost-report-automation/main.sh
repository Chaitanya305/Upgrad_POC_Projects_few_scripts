#!/bin/bash
accountId=$1
region=$2

echo "Starting with the script"
date=$(date +'%d-%m-%y')

echo "Starting $accountId"

if [ "$accountId" = "635145294553" ]; then
    echo "Running for upGrad NonProd account"
    aws configure set region "$region"
    python3 ./miscellaneous/cost-report-automation/main.py
else
    role="arn:aws:iam::$accountId:role/aws-security-reports"
    role_output=$(aws sts assume-role --role-arn "$role" --role-session-name AWSCLI-session)
    access_key_id=$(echo "$role_output" | jq -r '.Credentials.AccessKeyId')
    secret_access_key=$(echo "$role_output" | jq -r '.Credentials.SecretAccessKey')
    session_token=$(echo "$role_output" | jq -r '.Credentials.SessionToken')

    aws configure set aws_access_key_id "$access_key_id" --profile "$accountId"
    aws configure set aws_secret_access_key "$secret_access_key" --profile "$accountId"
    aws configure set aws_session_token "$session_token" --profile "$accountId"
    aws configure set region "$region" --profile "$accountId"

    echo "AWS_ACCESS_KEY_ID: $access_key_id"
    echo "AWS_SECRET_ACCESS_KEY: $secret_access_key"
    echo "AWS_SESSION_TOKEN: $session_token"
    echo "AWS REGION: $region"
    AWS_PROFILE=$accountId python3 ./miscellaneous/cost-report-automation/main.py
fi

