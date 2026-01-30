#!/bin/bash
# AWS Monitor - Log Cleanup Script
# Removes old logs to prevent disk space issues

# Configuration
LOG_DIR="/opt/aws-monitor/logs"
OUTPUT_DIR="/opt/aws-monitor/output"
DAYS_TO_KEEP=30
DRY_RUN=0

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "AWS Monitor - Log Cleanup"
echo "========================="
echo ""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --days)
            DAYS_TO_KEEP="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--dry-run] [--days N]"
            exit 1
            ;;
    esac
done

if [ $DRY_RUN -eq 1 ]; then
    echo -e "${YELLOW}DRY RUN MODE - No files will be deleted${NC}\n"
fi

echo "Configuration:"
echo "  Log directory: $LOG_DIR"
echo "  Output directory: $OUTPUT_DIR"
echo "  Keep files newer than: $DAYS_TO_KEEP days"
echo ""

# Function to clean directory
clean_directory() {
    local dir=$1
    local pattern=$2
    local description=$3
    
    echo "Cleaning $description..."
    
    if [ ! -d "$dir" ]; then
        echo "  Directory not found: $dir"
        return
    fi
    
    # Find old files
    old_files=$(find "$dir" -name "$pattern" -type f -mtime +$DAYS_TO_KEEP 2>/dev/null)
    file_count=$(echo "$old_files" | grep -c . || echo 0)
    
    if [ $file_count -eq 0 ]; then
        echo "  No old files found"
        return
    fi
    
    echo "  Found $file_count old file(s)"
    
    if [ $DRY_RUN -eq 1 ]; then
        echo "  Would delete:"
        echo "$old_files" | while read file; do
            echo "    - $file"
        done
    else
        echo "$old_files" | while read file; do
            rm -f "$file"
            echo "    Deleted: $(basename $file)"
        done
        echo -e "  ${GREEN}Cleaned $file_count file(s)${NC}"
    fi
    
    echo ""
}

# Clean log files
clean_directory "$LOG_DIR" "*.log" "application logs"

# Clean old JSON outputs
clean_directory "$OUTPUT_DIR" "*.json" "JSON output files"

# Compress remaining logs (older than 7 days but within retention)
echo "Compressing old logs..."
if [ -d "$LOG_DIR" ]; then
    old_logs=$(find "$LOG_DIR" -name "*.log" -type f -mtime +7 ! -name "*.gz" 2>/dev/null)
    
    if [ -z "$old_logs" ]; then
        echo "  No logs to compress"
    else
        log_count=$(echo "$old_logs" | grep -c .)
        echo "  Found $log_count log(s) to compress"
        
        if [ $DRY_RUN -eq 1 ]; then
            echo "  Would compress:"
            echo "$old_logs" | while read file; do
                echo "    - $file"
            done
        else
            echo "$old_logs" | while read file; do
                gzip "$file"
                echo "    Compressed: $(basename $file)"
            done
            echo -e "  ${GREEN}Compressed $log_count log(s)${NC}"
        fi
    fi
fi

echo ""

# Show disk usage
echo "Disk usage:"
if [ -d "$LOG_DIR" ]; then
    echo "  Logs: $(du -sh $LOG_DIR 2>/dev/null | cut -f1)"
fi
if [ -d "$OUTPUT_DIR" ]; then
    echo "  Output: $(du -sh $OUTPUT_DIR 2>/dev/null | cut -f1)"
fi

echo ""
if [ $DRY_RUN -eq 1 ]; then
    echo "Dry run complete. Run without --dry-run to actually delete files."
else
    echo -e "${GREEN}Cleanup complete!${NC}"
fi
