# Jira Utilities

## Getting started

```
cd jira-helper
python -m venv venv
source venv/bin/activate
pip install requests
pip install python-dotenv
```

### Setup environment

```
cp .env.template .env
```

Then modify the file by adding the Jira API key and the email address of the user who is using the API.

### Downloading list of Jira Users

A comma separated value (csv) file with:

* name, which is the name of each person as show in Jira.
* type, either STUDENT or ADMIN.

Run the following to generate the users_db.json file.

```
python find_users.py
```

### Create teams csv

This file will place each user into a team and mark them as 'Developers' or 'Administrators' which are 2 user types that should be available by default.

```
"name","team_id","role"
"Person 1",1,"Developers"
"Person 2",1,"Administrators"
```

### Create project definition

Here is an example project definition:

```
{
  "name": "Basic Test Rest API Board",
  "key": "BASICREST",
  "projectTypeKey": "software",
  "assigneeType": "UNASSIGNED",
  "leadAccountId": "<jira account id of user>",
  "projectTemplateKey": "com.pyxis.greenhopper.jira:gh-simplified-kanban-classic"
}
```

### Create Projects CSV

Create a line for each project we want to create.

```
"project_id","key","name","team_id","project_def"
1,"FIR","First project",1,"simple_project.json"
2,"SEC","Second project",2,"simple_project.json"
```

### Create Epics CSV

Create a csv with our epics that we want to create.

```
"epic_id","name","summary"
1,"Epic1","Epic1 summary"
2,"Epic2","Epic2 summary"
```

### Create Issues CSV

Create a csv with our issues.

* assignment_type, this can be either 'team' which means it will unassigned and left to the team to decide, or 'individual' where each team member will get their own task assigned to them.

```
"epic_id","summary","assignment_type"
1,"Issue 1","team"
1,"Issue 2","team"
2,"Issue 3","team"
```

### Build the projects

The build.sh script wraps the command to create the projects.  You will need to download the users list first so that we can get the user ids.

```
./build.sh
```
