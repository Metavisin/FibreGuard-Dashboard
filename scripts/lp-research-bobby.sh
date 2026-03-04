#!/bin/bash
# LP CRM Research Cron Job
# Runs hourly from 18:00-08:00 CET (outside office hours)
# Uses Python script for research and CRM updates

cd /Users/metavision/.openclaw/workspace

LOG_FILE="memory/lp-cron.log"

# Check time - only run if after 18:00 CET or before 08:00
HOUR=$(date +%H)
CURRENT_TIME=$(date "+%a %b %d %H:%M:%S %Z %Y")

if [ "$HOUR" -lt 8 ] || [ "$HOUR" -ge 18 ]; then
    echo "$CURRENT_TIME: === Starting LP research cycle (hour: $HOUR) ===" >> "$LOG_FILE"
    python3 scripts/lp-research-bobby.py >> "$LOG_FILE" 2>&1
else
    echo "$CURRENT_TIME: Skipping - inside office hours (hour: $HOUR)" >> "$LOG_FILE"
    exit 0
fi
