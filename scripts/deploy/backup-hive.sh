#!/usr/bin/env bash
# Daily backup — cron: 0 3 * * * /opt/hive/scripts/deploy/backup-hive.sh
set -euo pipefail

HIVE_ROOT="${HIVE_ROOT:-/opt/hive}"
BACKUP_DIR="$HIVE_ROOT/backups"
STAMP=$(date +%Y-%m-%d)
ARCHIVE="$BACKUP_DIR/hive-$STAMP.tar.gz"
TMP=$(mktemp -d)

mkdir -p "$BACKUP_DIR"

cp "$HIVE_ROOT/backend/.env" "$TMP/.env" 2>/dev/null || true
mkdir -p "$TMP/state"
cp "$HIVE_ROOT/backend/app/"*_state.json "$TMP/state/" 2>/dev/null || true
[[ -d "$HIVE_ROOT/backend/talon_data" ]] && cp -a "$HIVE_ROOT/backend/talon_data" "$TMP/"
[[ -d "$HIVE_ROOT/backend/reports" ]] && cp -a "$HIVE_ROOT/backend/reports" "$TMP/"
[[ -d "$HIVE_ROOT/backend/browser_profiles" ]] && cp -a "$HIVE_ROOT/backend/browser_profiles" "$TMP/"

tar -czf "$ARCHIVE" -C "$TMP" .
rm -rf "$TMP"

find "$BACKUP_DIR" -name 'hive-*.tar.gz' -mtime +14 -delete

echo "Backup: $ARCHIVE"
