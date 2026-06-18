#!/usr/bin/env bash
# Optional local real npm build test — NOT run by pytest.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND="$ROOT/backend"
PROJECT_ID="${1:-}"
if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 <project_id>"
  echo "Example: $0 prj-abc123def0"
  exit 1
fi
EXPORT_DIR="$BACKEND/app/generated_sites/$PROJECT_ID"
if [[ ! -d "$EXPORT_DIR" ]]; then
  echo "Export dir not found: $EXPORT_DIR"
  echo "Run Generate Astro Site from dashboard first."
  exit 1
fi
cd "$EXPORT_DIR"
echo "Running npm install in $EXPORT_DIR"
npm install --no-audit
echo "Running npm run build"
npm run build
if [[ -f dist/index.html ]]; then
  echo "Build OK: dist/index.html exists"
else
  echo "Build finished but dist/index.html missing"
  exit 1
fi
