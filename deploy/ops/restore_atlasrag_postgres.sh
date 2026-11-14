#!/usr/bin/env bash
set -euo pipefail

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Refusing destructive restore. Set CONFIRM_RESTORE=YES to continue." >&2
  exit 2
fi
BACKUP_FILE="${1:?Usage: CONFIRM_RESTORE=YES $0 path/to/atlasrag.dump}"
if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE" >&2
  exit 2
fi
if [[ -f "$BACKUP_FILE.sha256" ]]; then
  sha256sum -c "$BACKUP_FILE.sha256"
fi

echo "Stopping AtlasRAG API before restore..."
docker compose stop atlasrag
echo "Restoring PostgreSQL archive in one transaction..."
docker compose exec -T atlasrag-db pg_restore \
  --clean --if-exists --no-owner --single-transaction --exit-on-error \
  -U atlasrag -d atlasrag < "$BACKUP_FILE"
echo "Starting AtlasRAG API..."
docker compose start atlasrag
echo "Restore completed. Verify /health and tenant-scoped smoke tests."
