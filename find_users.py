import requests
from requests.auth import HTTPBasicAuth
import json
from dotenv import load_dotenv
import os
import csv
import urllib

load_dotenv()
print(os.getenv("JIRA_URL"))

url = "https://uhi.atlassian.net/rest/api/3/groupuserpicker"

auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))

headers = {
    "Accept": "application/json"
}

row = 0
users = []
with open("jira_users.csv") as users_csv:
    for u in users_csv:
        if row > 0:
            u = u.strip()
            x = list(csv.reader([u], delimiter=',', quotechar='"'))[0]
            o = {"name": x[0], "type": x[1]}
            users.append(o)
        row += 1

print(users)

for index, user in enumerate(users):
    query = {
        'query': urllib.parse.quote(user['name'])
    }
    print(query)

    response = requests.request(
        "GET",
        url,
        headers=headers,
        params=query,
        auth=auth
    )

    resp = json.loads(response.text)
    print(json.dumps(json.loads(response.text),
                     sort_keys=True, indent=4, separators=(",", ": ")))
    matching_users_count = resp["users"]["total"]
    validUser = None
    if matching_users_count > 1:
        for potentialUser in resp["users"]["users"]:
            if potentialUser['displayName'].lower() == user['name'].lower():
                validUser = potentialUser
                break
        if not validUser:
            raise Exception(
                "More than one user found for string {}".format(user['name']))
    elif matching_users_count == 0:
        raise Exception("No users found for string {}".format(user['name']))
    else:
        validUser = resp["users"]["users"][0]
    if not validUser:
        raise Exception("validUser not found")
    accountId = validUser["accountId"]
    users[index]['accountId'] = accountId

with open('users_db.json', 'w') as outFile:
    json.dump(users, outFile, ensure_ascii=False, indent=2)
