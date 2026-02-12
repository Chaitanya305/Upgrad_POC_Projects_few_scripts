#!/bin/bash

read -p "Bitbucket user name: " BITBUCKET_USERNAME

read -sp "Bitbucket password: " BITBUCKET_APP_PASSWORD

read -p "Bitbucket Workspace ID: " BITBUCKET_WORKSPACE

repos_list=("te-app-scripts" "kuk-campus-portal" "niuonline_website" "atlas-university-website" "aspire-be" "bdu-campus-portal" "aspire-frontend")

# brew install jq || true

# sudo apt-get install jq -y || true

FILE_NAME="bitbucket-pipelines.yml"
FILE_PATH=${PWD}/${FILE_NAME}

#all repo names
echo "all repos are: ${repos_list[*]}"

completed_repo=()

for repo in "${repos_list[@]}"; do
    #cloning repo to /tmp dir
    echo "******************************-----------******************************"
    echo "working on repo ${repo} ........ "
    if [[ "${repo}" != "PRISM-frontend" && "${repo}" != "pedagogy-mobile" && "${repo}" != "DS_Codes_2" && "${repo}" != "spark-wsm-etl" ]]; then
        completed_repo+=("${repo}")
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
            # if [ -f "$FILE_NAME" ]; then
            # echo 'file already exist skip remaining steps....'
            # continue
            # fi
            #copy file
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
    fi
done
echo "Actioned perform on : ${completed_repo[*]}"
