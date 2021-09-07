#!/bin/bash

# Wrapper to run the program
python build_project.py -p testproject.csv -t test_teams_after.csv -u users_db.json --epics test_epics.csv --issues test_issues.csv $@
