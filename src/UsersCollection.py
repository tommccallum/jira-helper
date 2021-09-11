import json
import os
from User import User

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

