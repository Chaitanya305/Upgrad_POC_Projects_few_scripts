#!/bin/bash

read -p "Bitbucket user name: " BITBUCKET_USERNAME

read -sp "Bitbucket password: " BITBUCKET_APP_PASSWORD

read -p "Bitbucket Workspace ID: " BITBUCKET_WORKSPACE

read -p "Project key: " PROJECT_KEY

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

checked_repo=()
checked_branch=()

add_entry() {
  checked_repo+=("$1")
  checked_branch+=("$2")
}

for repo in "${repos_list[@]}"; do
    if [[ "${repo}" != "PRISM-frontend" && "${repo}" != "pedagogy-mobile" && "${repo}" != "DS_Codes_2" && "${repo}" != "spark-wsm-etl" ]]; then
        echo "******************************-----------******************************"
        echo "working on repo ${repo} ........ "
        completed_repo+="${repo}"
        git clone https://${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}@bitbucket.org/${BITBUCKET_WORKSPACE}/${repo}.git /tmp/${repo}
        cd /tmp/${repo}

        # Fetching all branches
        BRANCHES=$(git branch -r | grep -v '\->' | sed 's/origin\///g')

    # BRANCHES=$(curl -s -u "${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}" \
    #     "https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}/${repo}/refs/branches?pagelen=1000" \
    #     | jq -r '.values[].name')
    # url="https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}/${repo}/refs/branches"
    # BRANCHES=()
    # while [ "$url" ]; do
    #     response=$(curl -s -u "${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}" "$url")
    #     BRANCHES+=($(echo "$response" | jq -r '.values[].name'))
    #     # Get the next URL if it exists, or set to empty to exit the loop
    #     url=$(echo "$response" | jq -r '.next')
    # done

        for BRANCH_NAME in ${BRANCHES}; do
            if [[ "${BRANCH_NAME}" == "master" || "${BRANCH_NAME}" == "main" || "${BRANCH_NAME}" == "production" || "${BRANCH_NAME}" == "Production" ]]; then
            #if [ "${BRANCH_NAME}" != "tag-check"  ]; then
            continue
            fi
            echo "************* Processing for branch: ${BRANCH_NAME} *************"
            git checkout ${BRANCH_NAME}
            #  # Build the URL to check the file in the specific branch.
            # encoded_branch="${BRANCH_NAME//\//%2F}"
            # file_url="https://api.bitbucket.org/2.0/repositories/${BITBUCKET_WORKSPACE}/${repo}/src/${encoded_branch}/${FILE_NAME}"
            # # Get the HTTP status code. 404 indicates the file is not found.
            # http_code=$(curl -s -o /dev/null -w "%{http_code}" -u "${BITBUCKET_USERNAME}:${BITBUCKET_APP_PASSWORD}" "$file_url")
            if [ -f "$FILE_NAME" ]; then
                echo "File '${FILE_NAME}' exists in repo: ${repo} on branch: ${BRANCH_NAME}"
                # echo 'file already exist skip remaining steps....'
                # continue
                # fi
            # if [ "$http_code" -eq 404 ]; then
            else
                echo "File '${FILE_NAME}' does NOT exist in repo: ${repo} on branch: ${BRANCH_NAME}"
                # Append branch to the dictionary. If multiple branches are missing the file, join them with commas.
                add_entry $repo $BRANCH_NAME
            fi
        done
        #cleaning the repo
        cd ~
        rm -rf /tmp/${repo}
        echo "Cleanup completed... for ${repo}"
    fi
done

# Print out the final dictionary with repositories and branches missing the file.
echo "Repositories and branches where '${FILE_NAME}' is missing:"
for i in "${!checked_repo[@]}"; do
    echo "${checked_repo[i]}: ${checked_branch[i]}"
done