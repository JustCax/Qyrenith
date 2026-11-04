#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if [[ "$#" -gt 1 ]]; then
  echo "usage: release.sh [output-directory]" >&2
  exit 2
fi
exec python3 "$ROOT/scripts/release.py" "$@"
