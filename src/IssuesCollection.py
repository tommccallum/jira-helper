
import csv

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
                        if index < len(x):
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
