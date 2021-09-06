#!/bin/bash

source .env

TOKEN=$(echo -n "${USEREMAIL}:${JIRA_API_KEY}" | base64)

curl -G \
    --request GET \
    --header "Authorization: Basic ${TOKEN}" \
    --header "Content-Type: application/json" \
    --url "${JIRA_URL}/3/groupuserpicker" \
    --data-urlencode "query=$1"
