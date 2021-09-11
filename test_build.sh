#!/bin/bash

export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/src"
# Wrapper to run the program
python build_project.py -p testproject.csv -t test_teams_before.csv -u users_db.json --epics test_epics.csv --issues test_issues.csv
