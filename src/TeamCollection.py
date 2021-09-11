import csv

def createTeamCollectionFromFile(teamsFilePath, users):
    teamCollection = TeamCollection()
    print("Loading team allocations from {}".format(teamsFilePath))
    
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
        teamId = str(m["team_id"])
        roleInTeam = m["role"]
        u = users.find(m["name"])
        u.setRole(roleInTeam)
        teamCollection.addTeamMember(teamId,u)
    return teamCollection

class TeamCollection:
    def __init__(self):
        self.teams = {}

    def addTeamMember(self, key, member):
        if key not in self.teams:
            print("Creating new team '{}'".format(key))
            self.teams[key] = []
        self.teams[key].append(member)

    def addTeam(self, key, team:list = []):
        if key in self.teams:
            raise Exception("Duplicate team key '{}'".format(key))
        print("Adding team {}".format(key))
        self.teams[key] = team

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

