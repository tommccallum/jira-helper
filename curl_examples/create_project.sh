#!/bin/bash

JSONFILE="$1"

JSON=$(<${JSONFILE})

source ../.env

TOKEN=$(echo -n "${USEREMAIL}:${JIRA_API_KEY}" | base64)

echo "$JSON"

curl \
    --request POST \
    --header "Authorization: Basic ${TOKEN}" \
    --header "Content-Type: application/json" \
    --url "${JIRA_URL}/3/project" \
    --data "$JSON"
