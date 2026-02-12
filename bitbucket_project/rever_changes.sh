#!/bin/bash

read -p "Bitbucket user name: " BITBUCKET_USERNAME

read -sp "Bitbucket password: " BITBUCKET_APP_PASSWORD

read -p "Bitbucket Workspace ID: " BITBUCKET_WORKSPACE

read -p "repo name: " repo

FILE_NAME="bitbucket-pipelines.yml"
FILE_PATH=${PWD}/${FILE_NAME}

echo "******************************-----------******************************"
echo "working on repo ${repo} ........ "
git clone https://${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}@bitbucket.org/${BITBUCKET_WORKSPACE}/${repo}.git /tmp/${repo}
cd /tmp/${repo}

# Fetching all branches
BRANCHES=$(git branch -r | grep -v '\->' | sed 's/origin\///g')
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
done