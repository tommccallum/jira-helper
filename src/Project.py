import requests
from requests.auth import HTTPBasicAuth
import json
from dotenv import load_dotenv
import os
import csv
import urllib
import sys
import copy
import Specification
from Strings import convertSnakeCaseToCamelCase
import copy

class Project:
    def __init__(self, specification):
        self.specification = specification
        self.name = "New Project"
        self.key = None
        self.teamId = None
        self.projectDef = None
        self.projectId = None
        self.team = None
        self.projectRoles = {}
        self.template = False

    def __setattr__(self, name, value):
        name = convertSnakeCaseToCamelCase(name)
        if name == "key":
            if value:
                if "%student_initials%" in value:
                    self.template = True
        self.__dict__[name] = value

    def instantiate(self, user):
        newProject = copy.copy(self) # shallow copy only so Specification remains a pointer
        newProject.template = False
        newProject.key = newProject.key.replace("%student_initials%", user.jirakey)
        newProject.name = newProject.name.replace("%student_name%", user.name)
        newProject.teamId = newProject.key
        print("Instantiating project with key {} and name {}".format(newProject.key, newProject.name))
        return newProject

    def toJson(self):
        data = {
            "name": self.name,
            "key": self.key,
            "teamId": self.teamId,
            "projectId": self.projectId,
            "projectDef": self.projectDef
        }
        return data

    def build(self):
        team = self.specification.getTeam(self.teamId)
        # get a default set of values for this project
        projectCreationData = None
        with open(self.projectDef) as inFile:
            projectCreationData = json.load(inFile)
        # override with the current project
        projectCreationData["name"] = self.name
        projectCreationData["key"] = self.key

        self.projectInfo = self.createProject(projectCreationData)
        self.projectRoles = self.getProjectRoles()
        self.projectRoleMembers = {}
        for role in self.projectRoles.keys():
            self.projectRoleMembers[role] = self.getProjectRoleMembers(
                self.projectRoles[role])

        for member in team:
            self.assignRole(member)

        if self.specification.hasIssues():
            self.epicIssueType = None
            for issueType in self.projectInfo['issueTypes']:
                if issueType["name"].upper() == "EPIC":
                    self.epicIssueType = issueType
                if issueType["name"].upper() == "TASK":
                    self.taskIssueType = issueType

            self.issues = self.getAllIssues()
            self.specification.epicsCollection.match(self.issues)
            
            if len(self.specification.usersToGenerateTasksFor) > 0:
                # only create tasks for an individual
                self.specification.issuesCollection.match(self.issues)
                for issue in self.specification.issuesCollection.issues:
                    self.createIssue(issue, team)
            else:
                # try to match the epics
                self.specification.epicsCollection.match(self.issues)
                epicsHaveBeenAddedToBacklog = False
                for k in self.specification.epicsCollection.epics.keys():
                    epic = self.specification.epicsCollection.epics[k]
                    isChanged = self.createEpic(epic)
                    if isChanged:
                        epicsHaveBeenAddedToBacklog = True

                # retrieve all issues again so we get all the new epics if any
                if epicsHaveBeenAddedToBacklog:
                    self.issues = self.getAllIssues()
                    self.specification.epicsCollection.match(self.issues)

                self.specification.issuesCollection.match(self.issues)
                for issue in self.specification.issuesCollection.issues:
                    self.createIssue(issue, team)

    def createIssue(self, issue, team):
        """
        We need to test if the issue is allocated to a team member
        or to be decided by the team
        """
        if issue["assignment_type"].upper() == "TEAM":

            if len(self.specification.usersToGenerateTasksFor) > 0:
                # Do not add team issues if we are assigning only individuals
                return True

            if "issues" not in issue or len(issue["issues"]) == 0:
                self.addIssue(issue)
                return True
            else:
                print("Team issue {} already exists as {}".format(issue["summary"], issue["issues"][0]["id"]))
                return False
        elif issue["assignment_type"].upper() == "INDIVIDUAL":
            # add a new issue per team member
            isChanged = False
            for member in team:
                if len(self.specification.usersToGenerateTasksFor) > 0:
                    if member.name in self.specification.usersToGenerateTasksFor:
                        if "issues" in issue and len(issue["issues"]) > 0:
                            found = False
                            for existingIssue in issue["issues"]:
                                if len(existingIssue["fields"]["assignee"]) > 0:
                                    if existingIssue["fields"]["assignee"]["accountId"] == member.accountId:
                                        found = True
                            if not found:
                                self.addIssue(issue, member)
                                isChanged=True
                            else:
                                print("Individual issue {} already exists as {}".format(issue["summary"], existingIssue["id"]))
                        else:
                            self.addIssue(issue, member)
                            isChanged=True
                else:
                    if "issues" in issue and len(issue["issues"]) > 0:
                        found = False
                        for existingIssue in issue["issues"]:
                            if len(existingIssue["fields"]["assignee"]) > 0:
                                if existingIssue["fields"]["assignee"]["accountId"] == member.accountId:
                                    found = True
                        if not found:
                            self.addIssue(issue, member)
                            isChanged=True
                        else:
                            print("Individual issue {} already exists as {}".format(issue["summary"], existingIssue["id"]))
                    else:
                        self.addIssue(issue, member)
                        isChanged=True
            return isChanged
        else:
            raise Exception("unexpected assignment_type for issue {}".format(issue["summary"]))
        
    def addIssue(self, issue, assignee=None):
        if assignee is None:
            print("[API] Add issue {} to team".format(issue["summary"]))
        else:
            print("[API] Add issue {} to {}".format(issue["summary"], assignee.name))
        
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        headers = {
            "Content-type": "application/json",
            "Accept": "application/json"
        }
        url = os.getenv("JIRA_URL") + "/3/issue"
        data = {
            "update": {},
            "fields": {
                #"customfield_10011": issue["name"],
                "summary": issue["summary"],
                "issuetype": {
                    "id": self.taskIssueType["id"]
                },
                "project": {
                    "id": self.projectInfo["id"]
                }
            }
        }
        
        if "description" in issue:
            # create a field in the "Atlassian Document Format"
            data["fields"]["description"] = {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{
                            "type": "text",
                            "text": issue["description"]
                        }]
                    }
                ]
            }

        if assignee:
            data["fields"]["assignee"] = {}
            data["fields"]["assignee"]["id"] = assignee.accountId
                
        if "epic_id" in issue:
            # set epic if we can find it
            epic = self.specification.epicsCollection.get(issue["epic_id"])
            if epic:
                epicId = epic["issue"]["id"]
                if epicId:
                    # TODO make this Epic Link field a variable as it differs from instance to instance
                    #       I believe the only way to find it is to manually create one and see where the parent key turns up.
                    data["fields"]["customfield_10014"] = epic["issue"]["key"]

        print(data)

        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=json.dumps(data),
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))

        if response.status_code != 201:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        result = json.loads(response.text)
        if "errorMessages" in result:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return True

    def createEpic(self, epic):
        """
        epic is an array of epic_id and summary
        Must be called after getAllIssues
        """
        if "issue" not in epic:
            print("Epic issue not found")
            self.addEpic(epic)
            return True
        else:
            print("Epic {} already exists as {}".format(epic["summary"], epic["issue"]["id"]))
            return False
        
    def addEpic(self, epic):
        print("[API] Add epic {} {}".format(epic["epic_id"], epic["summary"]))
        
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        headers = {
            "Content-type": "application/json",
            "Accept": "application/json"
        }
        url = os.getenv("JIRA_URL") + "/3/issue"
        data = {
            "update": {},
            "fields": {
                "customfield_10011": epic["name"],
                "summary": epic["summary"],
                "issuetype": {
                    "id": self.epicIssueType['id']
                },
                "project": {
                    "id": self.projectInfo["id"]
                }
            }
        }
        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=json.dumps(data),
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))

        if response.status_code != 201:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        result = json.loads(response.text)
        if "errorMessages" in result:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return True



    def getBoards(self):
        # TODO get boards for a project
        print("[API] Get boards {}".format(self.key))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        url = os.getenv("JIRA_URL") + \
            "/3/board"
        response = requests.request(
            "GET",
            url,
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))

        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        result = json.loads(response.text)
        if "errorMessages" in result:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return result

    # TODO get board details, this was from a webpage
    # https://community.atlassian.com/t5/Jira-Software-questions/REST-API-for-Board-Swimlane-Modifications/qaq-p/1288929
    def getBoardDetails(self):
        print("[API] Get board {}".format(self.key))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        url = os.getenv("JIRA_URL") + \
            "/rest/greenhopper/1.0/xboard/work/allData.json?rapidViewId="+1
        response = requests.request(
            "GET",
            url,
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))

        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        result = json.loads(response.text)
        if "errorMessages" in result:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return result

    # change swimlane to Epics
    # https://community.atlassian.com/t5/Jira-Software-questions/REST-API-for-Board-Swimlane-Modifications/qaq-p/1288929
    def changeSwimlaneToEpics(self):
        print("[API] Set swimlane to epics {}".format(self.key))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        headers = {
            "Content-type": "application/json",
            "Accept": "application/json"
        }
        data = {
            "id": 1,
            "swimlaneStrategyId": "Epic"
        }
        url = os.getenv("JIRA_URL") + \
            "/greenhopper/1.0/rapidviewconfig/swimlaneStrategy"
        response = requests.request(
            "PUT",
            url,
            headers=headers,
            data=json.dumps(data),
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))

        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        result = json.loads(response.text)
        if "errorMessages" in result:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return result


    def getAllIssues_helper(self, start=0):
        print("[API] Get all issues {} from {}".format(self.key, start))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        url = os.getenv("JIRA_URL")+"/3/search"
        # can get at most 1000 at once
        # TODO get multiple pages if more than 100
        params = {
            "jql": "project="+self.key,
            "startAt": start,
            "maxResults": -1 
        }
        response = requests.request(
            "GET",
            url,
            auth=auth,
            params=params
        )

        # print("RESPONSE {}: {}".format(response.status_code, response.text))
        with open("tmp_issues.json","w") as outFile:
            json.dump(response.text, outFile, indent=2, sort_keys=True)

        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        issues = json.loads(response.text)
        if "errorMessages" in issues:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return issues

    def getAllIssues(self):
        """
        Iterate over multiple pages of issues
        """
        response = self.getAllIssues_helper(0)
        total = response["total"]
        maxResults = response["maxResults"]
        issues = response["issues"]
        resultsCount = len(issues)
        all_issues = issues
        while resultsCount < total:
            startAt = resultsCount
            response = self.getAllIssues_helper(startAt)
            total = response["total"]
            maxResults = response["maxResults"]
            issues = response["issues"]
            resultsCount += len(issues)
            all_issues = all_issues + issues
        return all_issues


    def getProjectRoles(self):
        print("[API] Get project roles {}".format(self.key))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        url = os.getenv("JIRA_URL")+"/3/project/"+self.key+"/role"
        response = requests.request(
            "GET",
            url,
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))
        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        roles = json.loads(response.text)
        if "errorMessages" in roles:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return roles

    def getProjectRoleMembers(self, url):
        print("[API] Get project roles {} {}".format(self.key, url))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        response = requests.request(
            "GET",
            url,
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))
        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        roleMembers = json.loads(response.text)
        if "errorMessages" in roleMembers:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return roleMembers

    def getRoleId(self, role):
        if not self.projectRoleMembers:
            raise Exception("project role members is not available")
        role = role.title()
        if role not in self.projectRoleMembers:
            raise Exception("project role type {} not found".format(role))
        members = self.projectRoleMembers[role]
        return members['id']

    def isInRole(self, user):
        if not self.projectRoleMembers:
            raise Exception("project role members is not available")
        role = user.role.title()
        if role not in self.projectRoleMembers:
            print(self.projectRoleMembers)
            raise Exception("project role type {} not found".format(role))
        members = self.projectRoleMembers[role]['actors']
        for member in members:
            if member["actorUser"]["accountId"] == user.accountId:
                return True
        return False

    def assignRole(self, user):
        print("[API] Add {} {} {}".format(
            user.name, user.accountId, user.role))
        if self.isInRole(user):
            print("User {} already assigned role {}".format(user.name, user.role))
            return True

        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        headers = {
            "Content-type": "application/json",
            "Accept": "application/json"
        }
        roleId = self.getRoleId(user.role)
        url = os.getenv("JIRA_URL") + "/3/project/" + \
            self.key+"/role/"+str(roleId)
        data = {
            "user": [user.accountId]
        }
        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=json.dumps(data),
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))

        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        result = json.loads(response.text)
        if "errorMessages" in result:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return True

    def createProject(self, data):
        print("[API] Creating project {}".format(data["key"]))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        headers = {
            "Content-type": "application/json",
            "Accept": "application/json"
        }
        url = os.getenv("JIRA_URL") + "/3/project"
        response = requests.request(
            "POST",
            url,
            headers=headers,
            data=json.dumps(data),
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))

        if response.status_code == 400:
            return self.getProject()
        if response.status_code != 201:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        projectDetails = json.loads(response.text)
        if "errorMessages" in projectDetails:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return self.getProject()

    def getProject(self):
        print("[API] Get project {}".format(self.key))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        url = os.getenv("JIRA_URL")+"/3/project/"+self.key
        response = requests.request(
            "GET",
            url,
            auth=auth
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))
        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        projectDetails = json.loads(response.text)
        if "errorMessages" in projectDetails:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return projectDetails

    def save(self):
        """
        Saves a project to file
        """
        data = self.toJson()
        relativePath = os.path.join("projects", self.key + ".json")
        with open(relativePath, 'w') as outFile:
            json.dump(data, outFile, ensure_ascii=False, indent=2)
