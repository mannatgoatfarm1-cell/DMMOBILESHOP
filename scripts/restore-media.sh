#!/usr/bin/env bash
set -euo pipefail
ARCHIVE="${1:?Usage: restore-media.sh <media-backup.tar.gz>}"
MEDIA_ROOT="${MEDIA_ROOT:?MEDIA_ROOT is required}"
test -f "$ARCHIVE"
mkdir -p "$MEDIA_ROOT"
tar -xzf "$ARCHIVE" -C "$MEDIA_ROOT"