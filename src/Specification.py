
from IssuesCollection import IssuesCollection
from EpicsCollection import EpicsCollection
from TeamCollection import createTeamCollectionFromFile, TeamCollection
from UsersCollection import UsersCollection

class Specification:
    def __init__(self, projectsFilePath, teamsFilePath, usersFilePath):
        self.projectsFilePath = projectsFilePath
        self.teamsFilePath = teamsFilePath
        self.usersFilePath = usersFilePath
        self.epicsFilePath = None
        self.issuesFilePath = None
        self.usersToGenerateTasksFor = []
        self.teamAllocations = None
        self.epicsCollection = None
        self.issuesCollection = None

    def loadIssues(self):
        if self.issuesFilePath:
            self.issuesCollection = IssuesCollection(self.issuesFilePath)

    def loadEpics(self):
        if self.epicsFilePath:
            self.epicsCollection = EpicsCollection(self.epicsFilePath)

    def loadUsers(self):
        self.users = UsersCollection(self.usersFilePath)

    def loadTeamAllocations(self):
        self.teamAllocations = createTeamCollectionFromFile(self.teamsFilePath, self.users)

    def addTeam(self, key, team:list):
        if self.teamAllocations is None:
            self.teamAllocations = TeamCollection()
        self.teamAllocations.addTeam(key, team)

    def getTeam(self, teamId):
        if self.teamAllocations:
            return self.teamAllocations.get(str(teamId))
        else:
            raise Exception("team allocations not loaded")

    def hasIssues(self):
        return self.epicsFilePath is not None and self.issuesFilePath is not None

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

