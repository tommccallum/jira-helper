#!/bin/bash

export PYTHONPATH="${PYTHONPATH}:$(pwd):$(pwd)/src"

# Wrapper to run the program
python build_project.py -p projects.csv -t teams.csv -u users_db.json --epics week1_epics.csv --issues week1_issues.csv
