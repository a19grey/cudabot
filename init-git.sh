#!/usr/bin/env bash
set -e
source .env

git init
git config user.name  "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"
git remote add origin "$GITHUB_REMOTE"
git add .
git commit -m "Initial commit"
git push -u origin main