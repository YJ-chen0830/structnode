#!/usr/bin/env bash
set -euo pipefail
: "${1:?Usage: scripts/ship.sh <commit-message>}"

branch="$(git branch --show-current)"
if [[ "$branch" == "main" || "$branch" == "master" || -z "$branch" ]]; then
  echo 'ERROR: shipping from protected/default branch is forbidden' >&2
  exit 1
fi

if ! git remote get-url origin >/dev/null 2>&1; then
  echo 'ERROR: origin not configured; NOT PUSHED' >&2
  exit 1
fi

bash scripts/preflight.sh

git add -A

if git diff --cached --quiet; then
  echo 'No staged changes'
  exit 0
fi

# --- Staged-file / secret safeguard (S0 minimum bar; not a full DLP scanner) ---
# Forbidden filename patterns: dotenv, credential stores, key material.
forbidden_name_pattern='(^|/)(\.env(\..*)?|.*credentials.*\.json|.*secrets.*\.(json|ya?ml)|id_(rsa|ed25519)|.*\.pem|.*\.key)$'
staged_files="$(git diff --cached --name-only)"
bad_names="$(printf '%s\n' "$staged_files" | grep -Ei "$forbidden_name_pattern" || true)"
if [[ -n "$bad_names" ]]; then
  echo "ERROR: refusing to commit files matching forbidden secret/credential patterns:" >&2
  printf '  %s\n' "$bad_names" >&2
  git reset >/dev/null
  exit 1
fi

# Content scan over the staged diff for common secret shapes.
secret_pattern='(AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[0-9A-Za-z-]{10,}|(api|secret)[_-]?key["'\'']?\s*[:=]\s*["'\''][A-Za-z0-9/+=_-]{16,}["'\''])'
if git diff --cached | grep -Ei "$secret_pattern" >/dev/null; then
  echo "ERROR: staged diff matches a likely-secret pattern; refusing to commit." >&2
  echo "       Review with: git diff --cached | grep -Ei '$secret_pattern'" >&2
  git reset >/dev/null
  exit 1
fi

git commit -m "$1"
git push --set-upstream origin "$branch"

# `gh` CLI must be authenticated; failures must be reported, not swallowed.
if ! gh pr view --json url >/dev/null 2>&1; then
  gh pr create --fill --base main
fi

printf 'PUSHED branch=%s commit=%s\n' "$branch" "$(git rev-parse HEAD)"
