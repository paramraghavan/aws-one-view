#!/bin/bash
# AWS Monitor - Backup Script
# Backs up configuration files and recent output data

# Configuration
INSTALL_DIR="/opt/aws-monitor"
BACKUP_DIR="/opt/aws-monitor-backups"
RETENTION_DAYS=30

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/aws-monitor-backup-$TIMESTAMP.tar.gz"

echo "AWS Monitor - Backup Script"
echo "==========================="
echo ""
echo "Backup location: $BACKUP_FILE"
echo ""

# Items to backup
echo "Creating backup..."
cd "$INSTALL_DIR" || exit 1

tar -czf "$BACKUP_FILE" \
    --exclude='venv' \
    --exclude='*.pyc' \
    --exclude='__pycache__' \
    --exclude='logs/*.log' \
    configs/ \
    output/ \
    deployment/ \
    *.py \
    requirements.txt \
    2>/dev/null

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    echo "  File: $BACKUP_FILE"
    echo "  Size: $BACKUP_SIZE"
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

echo ""

# Clean old backups
echo "Cleaning old backups (older than $RETENTION_DAYS days)..."
OLD_BACKUPS=$(find "$BACKUP_DIR" -name "aws-monitor-backup-*.tar.gz" -type f -mtime +$RETENTION_DAYS 2>/dev/null)

if [ -z "$OLD_BACKUPS" ]; then
    echo "  No old backups to remove"
else
    REMOVED_COUNT=0
    echo "$OLD_BACKUPS" | while read file; do
        rm -f "$file"
        echo "  Removed: $(basename $file)"
        ((REMOVED_COUNT++))
    done
    echo -e "${GREEN}✓ Cleaned $REMOVED_COUNT old backup(s)${NC}"
fi

echo ""

# Show all backups
echo "Available backups:"
ls -lh "$BACKUP_DIR"/aws-monitor-backup-*.tar.gz 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'

echo ""
echo "Total backup space: $(du -sh $BACKUP_DIR | cut -f1)"
echo ""
echo -e "${GREEN}Backup complete!${NC}"
echo ""
echo "To restore from backup:"
echo "  tar -xzf $BACKUP_FILE -C /opt/aws-monitor"
