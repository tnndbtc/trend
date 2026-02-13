#!/bin/bash

################################################################################
# Automated Trend Collection Script
# Runs hourly via cron to collect trends from all configured sources
################################################################################

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/auto_collect_$(date +%Y%m%d).log"
MAX_POSTS_PER_CATEGORY=50

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Determine Docker Compose command
if command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    DOCKER_COMPOSE="docker compose"
fi

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Error handler
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Start collection
log "========================================"
log "Starting automated trend collection"
log "Project Directory: $PROJECT_DIR"
log "Max posts per category: $MAX_POSTS_PER_CATEGORY"
log "========================================"

# Change to project directory
cd "$PROJECT_DIR" || error_exit "Failed to change to project directory: $PROJECT_DIR"

# Check if web container is running
if ! $DOCKER_COMPOSE ps | grep -q "web.*Up"; then
    error_exit "Web container is not running. Please start services first."
fi

log "Web container is running"

# Run trend collection
log "Executing collect_trends command..."
if $DOCKER_COMPOSE exec -T web python manage.py collect_trends --max-posts-per-category "$MAX_POSTS_PER_CATEGORY" >> "$LOG_FILE" 2>&1; then
    log "SUCCESS: Trend collection completed successfully"

    # Optional: Get count of collected trends
    TREND_COUNT=$($DOCKER_COMPOSE exec -T web python manage.py shell -c "from trends_viewer.models import Trend; print(Trend.objects.count())" 2>/dev/null | tail -1)
    if [ -n "$TREND_COUNT" ]; then
        log "Total trends in database: $TREND_COUNT"
    fi
else
    error_exit "Trend collection failed. Check logs for details."
fi

log "========================================"
log "Automated trend collection finished"
log "========================================"
log ""

# Cleanup old logs (keep last 30 days)
find "$LOG_DIR" -name "auto_collect_*.log" -type f -mtime +30 -delete 2>/dev/null

exit 0
