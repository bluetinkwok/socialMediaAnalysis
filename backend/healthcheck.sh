#!/bin/sh

# Health check script for backend container
# This script performs various checks to ensure the backend is healthy

# Check if the API is responding
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health || echo "failed")

# Check if the database connection is working
DB_STATUS=$(python -c "
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
    print('ok')
except Exception as e:
    print(f'failed: {e}')
    sys.exit(1)
" || echo "failed")

# Check if Redis is available (if used)
REDIS_STATUS=$(python -c "
import os
import sys
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
try:
    from django.core.cache import cache
    cache.set('healthcheck', 'ok', 10)
    result = cache.get('healthcheck')
    if result == 'ok':
        print('ok')
    else:
        print('failed: cache not working')
        sys.exit(1)
except Exception as e:
    print(f'failed: {e}')
    sys.exit(1)
" || echo "failed")

# Check disk space
DISK_SPACE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_SPACE" -gt 90 ]; then
    DISK_STATUS="critical: $DISK_SPACE% used"
else
    DISK_STATUS="ok: $DISK_SPACE% used"
fi

# Check memory usage
if command -v free >/dev/null 2>&1; then
    MEMORY_USAGE=$(free | awk '/Mem:/ {printf "%.0f", $3/$2 * 100}')
    if [ "$MEMORY_USAGE" -gt 90 ]; then
        MEMORY_STATUS="critical: $MEMORY_USAGE% used"
    else
        MEMORY_STATUS="ok: $MEMORY_USAGE% used"
    fi
else
    MEMORY_STATUS="unknown"
fi

# Output results
echo "API Status: $API_STATUS"
echo "Database Status: $DB_STATUS"
echo "Cache Status: $REDIS_STATUS"
echo "Disk Status: $DISK_STATUS"
echo "Memory Status: $MEMORY_STATUS"

# Determine overall health
if [ "$API_STATUS" = "200" ] && [ "$DB_STATUS" = "ok" ] && [ "$DISK_SPACE" -lt 90 ]; then
    echo "Overall health: OK"
    exit 0
else
    echo "Overall health: FAIL"
    exit 1
fi
