#!/bin/bash

read -p "Bitbucket user name: " BITBUCKET_USERNAME
read -sp "Bitbucket APP Password: " BITBUCKET_APP_PASSWORD
read -p "Bitbucket Workspace ID: " BITBUCKET_WORKSPACE
read -p "Project key: " PROJECT_KEY
#read -p "Provide the bitbucket repo name: " REPO_NAME

variables=("SES_SMTP_USERNAME=AKIAYJYZJFLLZDYPTHMQ" "SES_SMTP_PASSWORD=BB4eJy9oazT37j4JvdUgzUiNNAzdisjN4gefaif2zvKo")

# Initial API URL
url="https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}?q=project.key%3D%22${PROJECT_KEY}%22"
#url="https://api.bitbucket.org/2.0/repositories/upgrad_dev?q=project.key%3D%22TE%22"
# Initialize an empty list to store repository names
repos_list=()
# Loop through all pages of results
while [ "$url" ]; do
    response=$(curl -s -u ${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD} --request GET --url "$url")
    repos_list+=($(echo "$response" | jq -r '.values[].name'))
    url=$(echo "$response" | jq -r '.next')
done

#all repo names
echo "all repos are: ${repos_list[*]}"
completed_repo=()

for repo in "${repos_list[@]}"; do
    echo "******************************-----------******************************"
    echo "working on repo ${repo} ........ "
    # API endpoint for repository variables
    API_URL="https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}/${repo}/pipelines_config/variables/"
    if [ "${repo}" != "PRISM-frontend" ]; then
        completed_repo+="${repo}"
        for variable in "${variables[@]}"; do
            key="${variable%%=*}"
            value="${variable#*=}"
            curl -u ${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD} \
                -X POST ${API_URL} \
                -H "Content-Type: application/json" \
                -d '{
                        "key": "'"${key}"'",
                        "value": "'"${value}"'",
                        "secured": true
                    }'
        done
        #to enabel pipeline for all repos
        PIPELINE_API_URL="https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}/${repo}/pipelines_config"
        curl -u ${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD} \
                -X PUT ${PIPELINE_API_URL} \
                -H "Content-Type: application/json" \
                -d '{"enabled": true}'
    fi
done
echo "Actioned perform on: ${completed_repo[*]}"
