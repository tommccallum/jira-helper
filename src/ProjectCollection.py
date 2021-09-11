from Project import Project
import csv

class ProjectCollection:
    """
    Container for a set of projects
    """

    def __init__(self, specification):
        self.projects = []
        self.specification = specification
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
            if not project.template:
                project.build()

    def save(self):
        for project in self.projects:
            project.save()
    
    def size(self):
        return len(self.projects)

    def generateProjectsForUser(self, user):
        for project in self.projects:
            if project.template:
                newProject = project.instantiate(user)
                # check current projects for name clash
                print("Creating new project {} ({})".format(newProject.name,newProject.key))
                self.projects.append(newProject)

                # we need to create a new team and add it to the 
                # specification
                user.setRole("Administrators")
                self.specification.addTeam(newProject.key, [user])
            

