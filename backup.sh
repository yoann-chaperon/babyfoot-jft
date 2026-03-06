#!/bin/bash

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB_FILE="$PROJECT_DIR/instance/babyfoot.db"
BACKUP_DIR="$PROJECT_DIR/backups"

DATE=$(date +"%Y-%m-%d_%H-%M")

mkdir -p "$BACKUP_DIR"

if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_DIR/babyfoot_$DATE.db"
    echo "Sauvegarde créée : $BACKUP_DIR/babyfoot_$DATE.db"
else
    echo "Base introuvable"
fi