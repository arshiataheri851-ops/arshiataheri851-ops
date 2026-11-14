#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-./backups}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT="$BACKUP_DIR/atlasrag-$STAMP.dump"

# Credentials are read by Compose from the local .env file; never passed on the command line.
docker compose exec -T atlasrag-db pg_dump -U atlasrag -d atlasrag -Fc > "$OUTPUT"
chmod 600 "$OUTPUT"
sha256sum "$OUTPUT" > "$OUTPUT.sha256"
chmod 600 "$OUTPUT.sha256"
printf 'Backup created: %s\n' "$OUTPUT"
printf 'Verify with: sha256sum -c %s.sha256\n' "$OUTPUT"
