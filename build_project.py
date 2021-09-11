import requests
from requests.auth import HTTPBasicAuth
import json
from dotenv import load_dotenv
import os
import csv
import urllib
import sys
import copy
from Specification import Specification
from ProjectCollection import ProjectCollection
from FindUsers import findAllUsersFromFile

load_dotenv()

if __name__ == "__main__":
    # local variables to main
    projectsFilePath = None                      # the projects.csv file
    issuesFilePath = None
    epicsFilePath = None
    teamsFilePath = None
    usersFilePath = None
    usersToGenerateTasksFor = []
    projectHasIssues = True

    # parse all our arguments from command line
    argCount = len(sys.argv)
    argIndex = 1
    actionUpdateUsersList = False
    actionCreateProjects = False
    actionCreateBoardForEachIndividual = False

    saveUsersToFile = "users_db.json"
    usersList = "jira_users.csv"
    while argIndex < argCount:
        if sys.argv[argIndex] == "--save-users-to-file":
            saveUsersToFile = sys.argv[argIndex+1]
            argIndex += 2
            continue
        if sys.argv[argIndex] == "--users-list-file":
            usersList = sys.argv[argIndex+1]
            argIndex += 2
            continue
        if sys.argv[argIndex] == "--update-users-list":
            actionUpdateUsersList = True
            argIndex += 1
            continue
        if sys.argv[argIndex] == "--individual-boards":
            actionCreateBoardForEachIndividual = True
            argIndex += 1
            continue
        if sys.argv[argIndex] == "--create-team-projects":
            actionCreateProjects = True
            argIndex += 1
            continue
        
        if sys.argv[argIndex] == "--empty":
            projectHasIssues = False
            argIndex += 1
            continue
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
        if sys.argv[argIndex] == "--users" or sys.argv[argIndex] == "--user":
            usersToGenerateTasksFor.append(sys.argv[argIndex+1])
            argIndex += 2
            continue
        argIndex += 1

    if actionUpdateUsersList:
        findAllUsersFromFile(usersList, saveUsersToFile)
        usersFilePath = saveUsersToFile


    if actionCreateProjects:
        if not projectsFilePath:
            raise Exception("No project path specified")

        if not teamsFilePath:
            raise Exception("No teams path specified")

        if not usersFilePath:
            raise Exception("No users path specified")

        if projectHasIssues:
            if not epicsFilePath:
                raise Exception("No epics path specified")

            if not issuesFilePath:
                raise Exception("No issues path specified")

        specification = Specification(
            projectsFilePath, teamsFilePath, usersFilePath)
        specification.epicsFilePath = epicsFilePath
        specification.issuesFilePath = issuesFilePath
        specification.usersToGenerateTasksFor = usersToGenerateTasksFor

        # build project
        specification.loadUsers()
        specification.loadTeamAllocations()
        if projectHasIssues:
            specification.loadEpics()
            specification.loadIssues()
        data = specification.save()
        with open("specification.json", "w") as outFile:
            json.dump(data, outFile, ensure_ascii=False, indent=2)

        projectCollection = ProjectCollection(specification)
        projectCollection.build()
        # projectCollection.save()

    elif actionCreateBoardForEachIndividual:
        if not projectsFilePath:
            raise Exception("No project path specified")

        if not usersFilePath:
            raise Exception("No users path specified")

        if not epicsFilePath:
            raise Exception("No epics path specified")

        if not issuesFilePath:
            raise Exception("No issues path specified")

        specification = Specification(projectsFilePath, teamsFilePath, usersFilePath)
        specification.loadUsers()
        specification.epicsFilePath = epicsFilePath
        specification.issuesFilePath = issuesFilePath
        specification.loadEpics()
        specification.loadIssues()

        data = specification.save()
        with open("specification.json", "w") as outFile:
            json.dump(data, outFile, ensure_ascii=False, indent=2)

        projectCollection = ProjectCollection(specification)
        if projectCollection.size() != 1:
            raise Exception("Expected only once parameterised project name")
        

        for user in usersToGenerateTasksFor:
            userObject = specification.users.find(user)
            print("Creating individual board for {} ({})".format(user, userObject.jirakey))
            projectCollection.generateProjectsForUser(userObject)

        projectCollection.build()
    else:
        print("No action specified, nothing to do.")
