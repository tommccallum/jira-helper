import requests
from requests.auth import HTTPBasicAuth
import json
from dotenv import load_dotenv
import os
import csv
import urllib
import sys
import copy

load_dotenv()
print(os.getenv("JIRA_URL"))

# url = "https://uhi.atlassian.net/rest/api/3/issue"


# data = {}


# response = requests.request(
#     "POST",
#     url,
#     headers=headers,
#     data=data,
#     auth=auth
# )

# resp = json.loads(response.text)


class ProjectCollection:
    """
    Container for a set of projects
    """

    def __init__(self, specification):
        self.projects = []
        with open(specification.projectsFilePath, "r") as inFile:
            row = 1
            for projectDef in inFile:
                projectDef = projectDef.strip()
                x = list(csv.reader([projectDef],
                                    delimiter=',', quotechar='"'))[0]
                if row == 1:
                    headers = x
                    row += 1
                    continue
                if len(x) > 0:
                    project = Project(specification)
                    for index, header in enumerate(headers):
                        setattr(project, header, x[index])
                    self.projects.append(project)

    def build(self):
        for project in self.projects:
            project.build()

    def save(self):
        for project in self.projects:
            project.save()


def convertSnakeCaseToCamelCase(name):
    if "_" in name:
        name = ''.join(word.title() for word in name.split('_'))
        name = name[:1].lower() + name[1:]
    return name


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

    def __setattr__(self, name, value):
        name = convertSnakeCaseToCamelCase(name)
        self.__dict__[name] = value

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
        team = self.specification.getTeam(int(self.teamId))
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

        self.epicIssueType = None
        for issueType in self.projectInfo['issueTypes']:
            if issueType["name"].upper() == "EPIC":
                self.epicIssueType = issueType
            if issueType["name"].upper() == "TASK":
                self.taskIssueType = issueType

        self.issues = self.getAllIssues()

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

    def getAllIssues(self):
        print("[API] Get all issues {}".format(self.key))
        auth = HTTPBasicAuth(os.getenv('USEREMAIL'), os.getenv('JIRA_API_KEY'))
        url = os.getenv("JIRA_URL")+"/3/search"
        # can get at most 1000 at once
        # TODO get multiple pages if more than 100
        params = {
            "jql": "project="+self.key,
            "maxResults": -1
        }
        response = requests.request(
            "GET",
            url,
            auth=auth,
            params=params
        )
        print("RESPONSE {}: {}".format(response.status_code, response.text))
        if response.status_code != 200:
            raise Exception("Received {} from {}".format(
                response.status_code, url))
        issues = json.loads(response.text)
        if "errorMessages" in issues:
            raise Exception(
                "REST API call incurred errors: {}".format(response.text))
        return issues["issues"]

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


class TeamCollection:
    def __init__(self, teamsFilePath, users):
        print("Loading team allocations from {}".format(teamsFilePath))
        self.teams = {}

        mapUserStringToTeam = []
        with open(teamsFilePath, "r") as inFile:
            row = 1
            for userToTeamMapping in inFile:
                userToTeamMapping = userToTeamMapping.strip()
                x = list(csv.reader([userToTeamMapping],
                                    delimiter=',', quotechar='"'))[0]
                if row == 1:
                    headers = x
                    row += 1
                    continue
                if len(x) > 0:
                    rowData = {}
                    for index, header in enumerate(headers):
                        rowData[header] = x[index]
                    mapUserStringToTeam.append(rowData)

        for m in mapUserStringToTeam:
            if "team_id" not in m:
                raise Exception("team id is missing")
            teamId = int(m["team_id"])
            roleInTeam = m["role"]
            if teamId not in self.teams:
                self.teams[teamId] = []
            u = users.find(m["name"])
            u.setRole(roleInTeam)
            self.teams[teamId].append(u)

    def get(self, teamId):
        if teamId not in self.teams:
            raise Exception(
                "team {} not found in team collection".format(teamId))
        return self.teams[teamId]

    def save(self):
        data = {}
        for k in self.teams.keys():
            data[k] = []
            members = self.teams[k]
            for m in members:
                data[k].append(m.accountId)
        return data


class User:
    def __init__(self, jsondata=None):
        self.name = None
        self.type = None
        self.accountId = None
        self.role = None

        if jsondata is not None:
            for k in jsondata.keys():
                setattr(self, k, jsondata[k])

    def isStudent(self):
        return self.type.upper() == "STUDENT"

    def isStaff(self):
        return self.type.upper() == "ADMIN"

    def __setattr__(self, name, value):
        self.__dict__[name] = value

    def setRole(self, role):
        self.role = role.title()

    def save(self):
        data = {
            "name": self.name,
            "type": self.type,
            "accountId": self.accountId,
            "role": self.role
        }
        return data


class UsersCollection:
    def __init__(self, usersFilePath):
        print("Loading users from {}".format(usersFilePath))
        base, ext = os.path.splitext(usersFilePath)
        self.users = []
        if ext == ".json":
            with open(usersFilePath) as inFile:
                userdata = json.load(inFile)
                for userjson in userdata:
                    u = User(userjson)
                    self.users.append(u)
        elif ext == ".csv":
            raise Exception("TODO use find_users.py code to complete")
        else:
            raise Exception("unexpected file extension found '{}'".format(ext))

    def find(self, name):
        for u in self.users:
            if u.name.upper() == name.upper():
                return u
        raise Exception("could not find {} in users collection".format(name))

    def save(self):
        data = []
        for u in self.users:
            data.append(u.save())
        return data

    def getStaff(self):
        staff = []
        for u in self.users:
            if u.isStaff():
                staff.append(u)
        return staff

class EpicsCollection:
    def __init__(self, epicsFilePath):
        self.epicsFilePath = epicsFilePath
        print("Loading Epics from {}".format(epicsFilePath))
        self.epics = {}

        with open(epicsFilePath, "r") as inFile:
            row = 1
            for epicRowData in inFile:
                epicRowData = epicRowData.strip()
                x = list(csv.reader([epicRowData],
                                    delimiter=',', quotechar='"'))[0]
                if row == 1:
                    headers = x
                    row += 1
                    continue
                if len(x) > 0:
                    rowData = {}
                    for index, header in enumerate(headers):
                        rowData[header] = x[index]
                    self.epics[rowData["epic_id"]] = rowData

    def get(self, id):
        id = str(id)
        if id not in self.epics:
            raise Exception("Epic with index {} was not found".format(id))
        return self.epics[id]

    def match(self, issues):
        for issue in issues:
            if "fields" not in issue:
                continue
            if "issuetype" not in issue["fields"]:
                continue
            if issue["fields"]["issuetype"]["name"].upper() == "EPIC":
                for k in self.epics.keys():
                    if self.epics[k]["summary"].upper() == issue["fields"]["summary"].upper():
                        self.epics[k]["issue"] = issue

    def save(self):
        return self.epics

class IssuesCollection:
    def __init__(self, issuesFilePath):
        self.issuesFilePath = issuesFilePath
        print("Loading Issues from {}".format(issuesFilePath))
        self.issues = []

        with open(issuesFilePath, "r") as inFile:
            row = 1
            for issueRowData in inFile:
                issueRowData = issueRowData.strip()
                x = list(csv.reader([issueRowData],
                                    delimiter=',', quotechar='"'))[0]
                if row == 1:
                    headers = x
                    row += 1
                    continue
                if len(x) > 0:
                    rowData = {}
                    for index, header in enumerate(headers):
                        rowData[header] = x[index]
                    self.issues.append(rowData)

    def match(self, issues):
        """
        Must match summary and assignee
        """
        for issue in issues:
            if "fields" not in issue:
                continue
            if "issuetype" not in issue["fields"]:
                continue
            if issue["fields"]["issuetype"]["name"].upper() == "TASK":
                for index, task in enumerate(self.issues):
                    if task["summary"].upper() == issue["fields"]["summary"].upper():
                        if "issues" not in self.issues[index]:
                            self.issues[index]["issues"] = []
                        else:
                            self.issues[index]["issues"].append(issue)

    def save(self):
        return self.issues

class Specification:
    def __init__(self, projectsFilePath, teamsFilePath, usersFilePath):
        self.projectsFilePath = projectsFilePath
        self.teamsFilePath = teamsFilePath
        self.usersFilePath = usersFilePath
        self.epicsFilePath = None
        self.issuesFilePath = None

    def loadIssues(self):
        if self.issuesFilePath:
            self.issuesCollection = IssuesCollection(self.issuesFilePath)

    def loadEpics(self):
        if self.epicsFilePath:
            self.epicsCollection = EpicsCollection(self.epicsFilePath)

    def loadUsers(self):
        self.users = UsersCollection(self.usersFilePath)

    def loadTeamAllocations(self):
        self.teamAllocations = TeamCollection(self.teamsFilePath, self.users)

    def getTeam(self, teamId):
        if self.teamAllocations:
            return self.teamAllocations.get(teamId)
        else:
            raise Exception("team allocations not loaded")

    def save(self):
        data = {}
        if self.users:
            data["users"] = self.users.save()
        if self.teamAllocations:
            data["teamAllocations"] = self.teamAllocations.save()
        if self.epicsCollection:
            data["epics"] = self.epicsCollection.save()
        if self.issuesCollection:
            data["issues"] = self.issuesCollection.save()
        return data


if __name__ == "__main__":
    # local variables to main
    projectsFilePath = None                      # the projects.csv file
    issuesFilePath = None
    epicsFilePath = None
    teamsFilePath = None
    usersFilePath = None

    # parse all our arguments from command line
    argCount = len(sys.argv)
    argIndex = 1
    while argIndex < argCount:
        if sys.argv[argIndex] == "-p":
            projectsFilePath = sys.argv[argIndex + 1]
            argIndex += 2
            continue
        if sys.argv[argIndex] == "-t":
            teamsFilePath = sys.argv[argIndex + 1]
            argIndex += 2
            continue
        if sys.argv[argIndex] == "-u":
            usersFilePath = sys.argv[argIndex + 1]
            argIndex += 2
            continue
        if sys.argv[argIndex] == "--epics":
            epicsFilePath = sys.argv[argIndex + 1]
            argIndex += 2
            continue
        if sys.argv[argIndex] == "--issues":
            issuesFilePath = sys.argv[argIndex + 1]
            argIndex += 2
            continue
        argIndex += 1

    if not projectsFilePath:
        raise Exception("No project path specified")

    if not teamsFilePath:
        raise Exception("No teams path specified")

    if not usersFilePath:
        raise Exception("No users path specified")

    specification = Specification(
        projectsFilePath, teamsFilePath, usersFilePath)
    specification.epicsFilePath = epicsFilePath
    specification.issuesFilePath = issuesFilePath

    # build project
    specification.loadUsers()
    specification.loadTeamAllocations()
    specification.loadEpics()
    specification.loadIssues()
    data = specification.save()
    with open("specification.json", "w") as outFile:
        json.dump(data, outFile, ensure_ascii=False, indent=2)

    projectCollection = ProjectCollection(specification)
    projectCollection.build()
    # projectCollection.save()
