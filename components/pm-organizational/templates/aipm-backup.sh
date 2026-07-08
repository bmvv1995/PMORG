#!/usr/bin/env bash
# Backup-ul bazei de memorie aipm (PLAN-INTEGRARE, datoria operațională 1).
# pg_dump format custom + retenție locală. Copia off-server rămâne responsabilitatea
# ownerului (acest script produce fișierul de luat).
set -euo pipefail

ENVF="${1:?utilizare: aipm-backup.sh <cale către .env-ul aipm> <director backup>}"
DEST="${2:?utilizare: aipm-backup.sh <cale către .env-ul aipm> <director backup>}"
KEEP="${AIPM_BACKUP_KEEP:-14}"

PG_DSN="$(grep '^PG_DSN=' "$ENVF" | head -1 | cut -d= -f2-)"
[ -n "$PG_DSN" ] || { echo "PG_DSN lipsește din $ENVF" >&2; exit 1; }

mkdir -p "$DEST"
chmod 700 "$DEST"
OUT="$DEST/aipm-$(date +%F-%H%M%S).dump"
pg_dump --format=custom --dbname="$PG_DSN" --file="$OUT"

# retenție: păstrează ultimele $KEEP fișiere
ls -1t "$DEST"/aipm-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm --
echo "backup scris: $OUT"
