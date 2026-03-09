#!/bin/bash
# FibreGuard Dashboard — Daily Refresh
# Runs at 8:30 AM CET, fetches fresh TikTok data and deploys to GitHub Pages
# Logs to: /Users/metavision/FibreGuard-Dashboard/logs/refresh.log

set -euo pipefail

REPO="/Users/metavision/FibreGuard-Dashboard"
LOG_DIR="$REPO/logs"
LOG="$LOG_DIR/refresh.log"
SCRIPT="$REPO/scripts/fetch-tiktok-v5.py"
ENV_FILE="$REPO/.env"

mkdir -p "$LOG_DIR"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S CET')] $1" | tee -a "$LOG"
}

log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "🔄 Starting FibreGuard daily refresh"

# Load APIFY_TOKEN from .env file
if [ -f "$ENV_FILE" ]; then
  export $(grep -v '^#' "$ENV_FILE" | xargs)
  log "✅ Loaded env from .env"
else
  log "❌ .env file not found at $ENV_FILE — aborting"
  exit 1
fi

if [ -z "${APIFY_TOKEN:-}" ]; then
  log "❌ APIFY_TOKEN not set — aborting"
  exit 1
fi

# Pull latest from GitHub first
log "📥 Pulling latest from GitHub..."
cd "$REPO"
git pull origin main --quiet >> "$LOG" 2>&1

# Run the Apify fetch (all 7 countries)
log "📡 Fetching TikTok data for US, FR, DE, IT, ES, NL, GB..."
APIFY_TOKEN="$APIFY_TOKEN" python3 "$SCRIPT" >> "$LOG" 2>&1
log "✅ Data fetch complete"

# Commit and push
log "📤 Committing and pushing to GitHub..."
cd "$REPO"
git add fibreguard-v5-data.json
TIMESTAMP=$(date '+%Y-%m-%d %H:%M CET')
git commit -m "data: daily refresh — $TIMESTAMP" >> "$LOG" 2>&1 || {
  log "ℹ️  No changes to commit (data unchanged)"
  exit 0
}
git push origin main >> "$LOG" 2>&1
log "✅ Pushed — GitHub Pages will update in ~1 min"
log "🌐 Dashboard: https://metavisin.github.io/FibreGuard-Dashboard/"
log "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
