import csv

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
