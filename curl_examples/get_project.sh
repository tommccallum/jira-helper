#!/bin/bash

source .env

TOKEN=$(echo -n "${USEREMAIL}:${JIRA_API_KEY}" | base64)
echo "TOKEN: ${TOKEN}"

curl --request GET \
    --url "${JIRA_URL}/3/project/$1" \
    --header "Authorization: Basic ${TOKEN}" \
    --header 'Accept: application/json'
