import os
import csv
import json
from requests.auth import HTTPBasicAuth
import requests
import urllib

def getListOfJiraUsersFromCsv(jiraUsersToSearchFor="jira_users.csv"):
    """
    Gets list of jira users expected to find.
    The csv should contain their name in the format "FIRSTNAME LASTNAME"
    and the type "STUDENT" or "ADMIN".
    Expects first row to be a header so ignores it.
    Ignores blank lines or those starting with a #
    """
    row = 0
    users = []
    with open(jiraUsersToSearchFor) as users_csv:
        for u in users_csv:
            if row > 0:
                u = u.strip()
                if len(u) > 0 or u[0] != '#':
                    x = list(csv.reader([u], delimiter=',', quotechar='"'))[0]
                    o = {"name": x[1], "type": x[2], "year": x[0]}
                    users.append(o)
            row += 1
    return users

def getAccountIdForUsersList(jiraUsersToSearchFor):
    """
    Downloads the users list from Jira and save the JSON response to a file
    Returns the JSON response
    """
    url = "https://uhi.atlassian.net/rest/api/3/groupuserpicker"
    auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))

    headers = {
        "Accept": "application/json"
    }

    for index, user in enumerate(jiraUsersToSearchFor):
        query = {
            'query': urllib.parse.quote(user['name'])
        }

        response = requests.request(
            "GET",
            url,
            headers=headers,
            params=query,
            auth=auth
        )

        resp = json.loads(response.text)
        # print(json.dumps(json.loads(response.text),
        #                 sort_keys=True, indent=4, separators=(",", ": ")))
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
        jiraUsersToSearchFor[index]['accountId'] = accountId

    
    return jiraUsersToSearchFor

def saveUsersListToFile(usersList, fileToSaveUsersIn):
    print("Writing users to {}".format(fileToSaveUsersIn))
    with open(fileToSaveUsersIn, 'w') as outFile:
        json.dump(usersList, outFile, ensure_ascii=False, indent=2, separators=(",", ": "), sort_keys=True)

def findAllUsersFromFile(expectedJiraUsersFile, userListFile):
    users = getListOfJiraUsersFromCsv(expectedJiraUsersFile)
    users = getAccountIdForUsersList(users)
    saveUsersListToFile(users, userListFile)
    return users