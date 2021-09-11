
class User:
    def __init__(self, jsondata=None):
        self.name = None
        self.type = None
        self.accountId = None
        self.role = None
        self.initials = None
        self.year = None
        self.jirakey = None
        if jsondata is not None:
            for k in jsondata.keys():
                setattr(self, k, jsondata[k])
        if self.name is not None:
            parts = self.name.split(" ")
            self.initials = ""
            for part in parts:
                self.initials += part[0].upper()
            self.jirakey = ""
            for part in parts:
                self.jirakey += part[0:3].upper()

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
            "role": self.role,
            "initials": self.initials,
            "year":self.year,
            "jirakey": self.jirakey
        }
        return data
