#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not inside a git repository: $repo_root" >&2
  exit 1
fi

git config --unset core.hooksPath >/dev/null 2>&1 || true

precommit_cmd=""
if [ -x "venv/bin/pre-commit" ]; then
  precommit_cmd="venv/bin/pre-commit"
elif command -v pre-commit >/dev/null 2>&1; then
  precommit_cmd="pre-commit"
else
  echo "ERROR: pre-commit is not installed. Install it with:" >&2
  echo "  venv/bin/pip install -r requirements.txt" >&2
  echo "Then run:" >&2
  echo "  venv/bin/pre-commit install" >&2
  exit 1
fi

"$precommit_cmd" install

echo "Installed pre-commit hook via: $precommit_cmd install"
echo "Hooks path: (default .git/hooks)"

