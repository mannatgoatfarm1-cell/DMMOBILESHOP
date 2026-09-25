#!/usr/bin/env bash
set -euo pipefail
MEDIA_ROOT="${MEDIA_ROOT:?MEDIA_ROOT is required}"
BACKUP_TARGET="${BACKUP_TARGET:?BACKUP_TARGET is required}"
STATUS_FILE="${BACKUP_STATUS_FILE:?BACKUP_STATUS_FILE is required}"
mkdir -p "$(dirname "$STATUS_FILE")"
tar -C "$MEDIA_ROOT" -czf "$BACKUP_TARGET/media-$(date -u +%Y%m%dT%H%M%SZ).tar.gz" .
printf 'ok %s\n' "$(date -u +%FT%TZ)" > "$STATUS_FILE"