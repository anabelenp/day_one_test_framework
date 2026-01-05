#!/usr/bin/env bash
set -euo pipefail

BRANCH=${1:-feature/dlp-jmeter-ci}
MSG=${2:-"Add DLP JMeter tests, runner updates and CI workflow"}

echo "Creating branch: $BRANCH"
git checkout -b "$BRANCH"

echo "Staging changes..."
git add -A

echo "Committing..."
git commit -m "$MSG" || echo "No changes to commit"

echo "Pushing branch to origin..."
git push -u origin "$BRANCH"

if command -v gh &>/dev/null; then
  echo "Creating PR using gh..."
  gh pr create --title "$MSG" --body "This PR adds DLP JMeter tests, updates the performance runner and Jenkinsfile, and adds a GitHub Actions workflow for JMeter-based performance testing." --base main || true
else
  echo "gh CLI not found. To create a PR, run:"
  echo "  gh pr create --title \"$MSG\" --body \"This PR adds DLP JMeter tests...\" --base main"
fi

echo "Done."
