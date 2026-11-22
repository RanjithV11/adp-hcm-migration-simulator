#!/bin/bash
# verify.sh - One-command verification for interviewers

set -e

echo '🔍 Verifying ADP HCM Migration Simulator...'
echo ''

# 1. Check Docker
if ! command -v docker &> /dev/null; then
    echo '❌ Docker not installed. Install Docker Desktop.'
    exit 1
fi
echo '✅ Docker found'

# 2. Clone check
if [ ! -f 'docker-compose.yml' ]; then
    echo '❌ Run from repo root (docker-compose.yml not found)'
    exit 1
fi
echo '✅ Repo structure OK'

# 3. Run pipeline
echo '🚀 Starting pipeline (2-3 min)...'
docker compose down -v > /dev/null 2>&1
docker compose up --build --abort-on-container-exit

# 4. Verify exit code
if [ \True -eq 0 ]; then
    echo ''
    echo '✅ PIPELINE SUCCESS'
    echo ''
    echo '📊 Validation Summary:'
    docker compose run --rm etl python -c \"
import json, glob
latest = max(glob.glob('output/validation_report_*.json'))
with open(latest) as f:
    r = json.load(f)
    print(f'  PASS: {r[\"summary\"][\"pass\"]}')
    print(f'  WARN: {r[\"summary\"][\"warn\"]}')
    print(f'  FAIL: {r[\"summary\"][\"fail\"]}')
\"
    echo ''
    echo '🎯 Ready for interview demo!'
else
    echo '❌ Pipeline failed'
    exit 1
fi
