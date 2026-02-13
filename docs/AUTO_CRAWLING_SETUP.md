# Automated Trend Collection Setup

## Overview

Your trend collection is now fully automated! The system will automatically crawl news sources **every hour** and collect new trends.

## What's Been Set Up

### 1. Automated Collection Script
- **Location**: `/home/tnnd/data/code/trend/scripts/auto_collect_trends.sh`
- **Function**: Runs trend collection via Docker
- **Max posts per category**: 5 (configurable)
- **Logging**: Automatic daily logs

### 2. Cron Job
- **Schedule**: Every hour at minute 0 (e.g., 1:00, 2:00, 3:00, etc.)
- **Command**: `0 * * * * /home/tnnd/data/code/trend/scripts/auto_collect_trends.sh`

### 3. Logging System
- **Log Directory**: `/home/tnnd/data/code/trend/logs/`
- **Log Format**: `auto_collect_YYYYMMDD.log` (one file per day)
- **Retention**: Automatically deletes logs older than 30 days

## Monitoring & Management

### View Current Cron Jobs
```bash
crontab -l
```

### Check Recent Logs
```bash
# View today's log
tail -f /home/tnnd/data/code/trend/logs/auto_collect_$(date +%Y%m%d).log

# View last 50 lines
tail -50 /home/tnnd/data/code/trend/logs/auto_collect_$(date +%Y%m%d).log

# Search for errors
grep -i error /home/tnnd/data/code/trend/logs/auto_collect_*.log
```

### Manual Test
```bash
# Run the script manually to test
/home/tnnd/data/code/trend/scripts/auto_collect_trends.sh
```

### Check Collection Status
```bash
# View web container logs
docker-compose logs -f web

# Check if collections are running
docker-compose exec web python manage.py shell -c "from trends_viewer.models import Trend; print(f'Total trends: {Trend.objects.count()}')"
```

## Customization

### Change Collection Frequency

Edit your crontab:
```bash
crontab -e
```

Then modify the schedule:
- **Every hour**: `0 * * * *` (current)
- **Every 2 hours**: `0 */2 * * *`
- **Every 6 hours**: `0 */6 * * *`
- **Daily at 2 AM**: `0 2 * * *`
- **Twice daily (6 AM, 6 PM)**: `0 6,18 * * *`

### Change Max Posts Per Category

Edit the script:
```bash
nano /home/tnnd/data/code/trend/scripts/auto_collect_trends.sh
```

Change this line:
```bash
MAX_POSTS_PER_CATEGORY=5  # Change to desired number
```

### Enable Email Notifications

Add email to the cron job:
```bash
crontab -e
```

Add at the top:
```bash
MAILTO=your-email@example.com
```

## Troubleshooting

### Cron Job Not Running?

1. **Check cron service status**:
   ```bash
   sudo service cron status
   ```

2. **Verify script is executable**:
   ```bash
   ls -l /home/tnnd/data/code/trend/scripts/auto_collect_trends.sh
   # Should show: -rwxr-xr-x
   ```

3. **Test script manually**:
   ```bash
   /home/tnnd/data/code/trend/scripts/auto_collect_trends.sh
   ```

### Web Container Not Running?

The script will fail if the web container isn't running. Start it with:
```bash
cd /home/tnnd/data/code/trend
./setup.sh  # Then choose option 2 or 3
```

Or directly:
```bash
docker-compose up -d web
```

### Check for Errors

```bash
# View all error messages from logs
grep -i "error\|fail" /home/tnnd/data/code/trend/logs/auto_collect_*.log

# Check latest collection result
tail -20 /home/tnnd/data/code/trend/logs/auto_collect_$(date +%Y%m%d).log
```

## What Happens During Collection

1. Script checks if web container is running
2. Executes `collect_trends` command with max posts setting
3. Collects trends from all configured sources
4. Creates topic clusters (categories)
5. Logs results with timestamp
6. Reports success/failure

## Testing the Setup

Your first automated collection will run at the next hour mark (e.g., if it's 2:30 PM now, it will run at 3:00 PM).

To test immediately:
```bash
# Run manual collection
/home/tnnd/data/code/trend/scripts/auto_collect_trends.sh

# Check the log
cat /home/tnnd/data/code/trend/logs/auto_collect_$(date +%Y%m%d).log
```

## Quick Commands Reference

```bash
# View cron jobs
crontab -l

# Edit cron jobs
crontab -e

# Manual test
/home/tnnd/data/code/trend/scripts/auto_collect_trends.sh

# Check today's logs
tail -f ~/data/code/trend/logs/auto_collect_$(date +%Y%m%d).log

# List all log files
ls -lh ~/data/code/trend/logs/

# View trends in database
docker-compose exec web python manage.py shell -c "from trends_viewer.models import Trend, CollectedTopic; print(f'Trends: {Trend.objects.count()}, Topics: {CollectedTopic.objects.count()}')"
```

## Stopping Automated Collection

To temporarily disable:
```bash
crontab -e
# Add # at the beginning of the auto_collect line to comment it out
```

To permanently remove:
```bash
crontab -e
# Delete the entire auto_collect_trends.sh line
```

---

**Created**: 2026-02-12
**Status**: ✅ Active and tested
**Next Collection**: Every hour at :00
