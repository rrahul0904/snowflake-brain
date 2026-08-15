#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must point to the PostgreSQL production database}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${1:-$BACKUP_DIR/snowflake-certification-$STAMP.dump}"

pg_dump \
  --format=custom \
  --compress=9 \
  --no-owner \
  --no-acl \
  --file="$OUT" \
  "$DATABASE_URL"

# Verify the archive is readable before reporting success.
pg_restore --list "$OUT" >/dev/null
sha256sum "$OUT" > "$OUT.sha256"
printf 'PostgreSQL backup verified: %s\n' "$OUT"
