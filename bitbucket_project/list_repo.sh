#!/bin/bash
  
# Initial API URL
url="https://api.bitbucket.org/2.0/repositories/upgrad_dev?q=project.key%3D%22TE%22"

# Initialize an empty list to store repository names
repos_list=()

# Loop through all pages of results
while [ "$url" ]; do
  # Make the API request and process the response
  response=$(curl -s -u chaitanyagolhar:ATBBkvGz9v9ETSK7tgUcjzBR4NdZA4EAD8A4 --request GET --url "$url")

  # Extract repository names and append them to the list
  repos_list+=($(echo "$response" | jq -r '.values[].name'))

  # Check if there is a next page and update the URL
  url=$(echo "$response" | jq -r '.next')
done

# Print the list of repositories
echo "Repositories List: ${repos_list[@]}"