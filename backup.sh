#!/bin/bash

PROJECT_DIR="$HOME/babyfoot-jft"
DB_FILE="$PROJECT_DIR/babyfoot.db"
BACKUP_DIR="$PROJECT_DIR/backups"

DATE=$(date +"%Y-%m-%d")

mkdir -p "$BACKUP_DIR"

cp "$DB_FILE" "$BACKUP_DIR/babyfoot_$DATE.db"

echo "Sauvegarde effectuée : $BACKUP_DIR/babyfoot_$DATE.db"
