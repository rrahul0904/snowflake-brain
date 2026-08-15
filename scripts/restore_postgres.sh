#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL must point to the PostgreSQL restore target}"
BACKUP="${1:-}"
if [[ -z "$BACKUP" || ! -f "$BACKUP" ]]; then
  echo "Usage: CONFIRM_RESTORE=1 DATABASE_URL=... $0 <backup.dump>" >&2
  exit 2
fi
if [[ "${CONFIRM_RESTORE:-0}" != "1" ]]; then
  echo "Refusing destructive restore. Set CONFIRM_RESTORE=1 after verifying the target DATABASE_URL." >&2
  exit 3
fi

if [[ -f "$BACKUP.sha256" ]]; then
  sha256sum --check "$BACKUP.sha256"
fi
pg_restore --list "$BACKUP" >/dev/null
pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  --exit-on-error \
  --dbname="$DATABASE_URL" \
  "$BACKUP"

printf 'PostgreSQL restore completed from: %s\n' "$BACKUP"
