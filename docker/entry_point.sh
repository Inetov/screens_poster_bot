#!/bin/sh

ARGS="--depth=1 --single-branch --branch=main"
COMMAND="git clone $ARGS $REPO_URL /temp_repo"
git config --global safe.directory /app
eval "$(ssh-agent -s)" && ssh-add /app/repo_key
eval "$COMMAND" && cp -R temp_repo/. /app && rm -rf /temp_repo
cd app/ && python main.py
