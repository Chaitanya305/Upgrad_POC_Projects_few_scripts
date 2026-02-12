#!/bin/bash

read -p "Bitbucket user name: " BITBUCKET_USERNAME

read -sp "Bitbucket password: " BITBUCKET_APP_PASSWORD

read -p "Bitbucket Workspace ID: " BITBUCKET_WORKSPACE

read -p "Project key: " PROJECT_KEY

variables=("SES_SMTP_USERNAME=AKIAYJYZJFPTHMQ" "SES_SMTP_PASSWORD=BB4eJy9N4gefaif2zvKo")

#getting all repos name for project
#API URL
url="https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}?q=project.key%3D%22${PROJECT_KEY}%22"
repos_list=()
while [ "$url" ]; do
    response=$(curl -s -u ${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD} --request GET --url "$url")
    repos_list+=($(echo "$response" | jq -r '.values[].name'))
    url=$(echo "$response" | jq -r '.next')
done

FILE_NAME="bitbucket-pipelines.yml"
FILE_PATH=${PWD}/${FILE_NAME}

#all repo names
echo "all repos are: ${repos_list[*]}"

completed_repo=()

for repo in "${repos_list[@]}"; do
    #cloning repo to /tmp dir
    echo "******************************-----------******************************"
    echo "working on repo ${repo} ........ "
    if [[ "${repo}" != "PRISM-frontend" && "${repo}" != "Data_Science" && "${repo}" != "DS_Codes_2" && "${repo}" != "spark-wsm-etl" ]]; then
        completed_repo+="${repo}"
        git clone https://${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}@bitbucket.org/${BITBUCKET_WORKSPACE}/${repo}.git /tmp/${repo}
        cd /tmp/${repo}

        # Fetching all branches
        BRANCHES=$(git branch -r | grep -v '\->' | sed 's/origin\///g')
        completed_branch=()
        for BRANCH_NAME in ${BRANCHES}; do
            if [[ "${BRANCH_NAME}" == "master" || "${BRANCH_NAME}" == "main" || "${BRANCH_NAME}" == "production" || "${BRANCH_NAME}" == "Production" ]]; then
            #if [ "${BRANCH_NAME}" != "tag-check"  ]; then
            continue
            fi
            echo "************* Processing for branch: ${BRANCH_NAME} *************"
            # Switch to the branch
            git checkout ${BRANCH_NAME}
            #copy file
            # if [ -f "$FILE_NAME" ]; then
            # echo 'file already exist skip remaining steps....'
            # continue
            # fi
            cp ${FILE_PATH} /tmp/${repo}/

            git add ${FILE_NAME}
            git commit -m "DO-50 ${FILE_NAME} added"
            git push origin ${BRANCH_NAME} || echo "error permission denied for ${BRANCH_NAME}"
            completed_branch+="${BRANCH_NAME}"
        done
        echo "Actioned perform on branch for repo ${repo} are: ${completed_branch[*]}  "
        #cleaning the repo
        cd ~
        rm -rf /tmp/${repo}
        echo "Cleanup completed... for ${repo}" 
        #set variable and enable pipeline
        API_URL="https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}/${repo}/pipelines_config/variables/"
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
echo "Actioned perform on : ${completed_repo[*]}"
