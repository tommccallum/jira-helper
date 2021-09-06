#!/bin/bash

source ../.env

TOKEN=$(echo -n "${USEREMAIL}:${JIRA_API_KEY}" | base64)

curl \
    --request GET \
    --header "Authorization: Basic ${TOKEN}" \
    --header "Content-Type: application/json" \
    --url "${JIRA_URL}/3/issue/createmeta?expand=projects.issuetypes.fields"
