#!/usr/bin/env bash
# Helper to update the repository secret ELEVENLABS_API_KEY using the GitHub CLI `gh`.
# Usage:
#   ./scripts/update_github_secret.sh <new-key>
# or
#   ELEVENLABS_API_KEY=<new-key> ./scripts/update_github_secret.sh

set -euo pipefail

if ! command -v gh >/dev/null 2>&1; then
  echo "Error: GitHub CLI 'gh' not found. Install it: https://cli.github.com/" >&2
  exit 2
fi

KEY="${1:-${ELEVENLABS_API_KEY:-}}"
if [ -z "$KEY" ]; then
  echo "Usage: $0 <new-key>  (or set ELEVENLABS_API_KEY env var)" >&2
  exit 2
fi

# Ensure gh is authenticated (will prompt if not)
if ! gh auth status >/dev/null 2>&1; then
  echo "Please authenticate GitHub CLI (run: gh auth login)" >&2
  exit 2
fi

# Set repository secret
# This command will set the secret for the current repo (must run in repo root or pass --repo)
gh secret set ELEVENLABS_API_KEY --body "$KEY"

echo "Repository secret ELEVENLABS_API_KEY updated. Make sure to protect branches as needed."
