#!/bin/sh

# Health check script for frontend container
# This script performs various checks to ensure the frontend is healthy

# Check if the web server is responding
WEB_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:80/ || echo "failed")

if [ "$WEB_STATUS" = "200" ] || [ "$WEB_STATUS" = "301" ] || [ "$WEB_STATUS" = "302" ]; then
  echo "Web server is responding with status $WEB_STATUS"
else
  echo "Web server is not responding properly. Status: $WEB_STATUS"
  exit 1
fi

# Check if critical files exist
if [ ! -f "/usr/share/nginx/html/index.html" ]; then
  echo "Critical file missing: index.html"
  exit 1
fi

# Check disk space
DISK_SPACE=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_SPACE" -gt 90 ]; then
  echo "Disk space critical: $DISK_SPACE%"
  exit 1
fi

# Check memory usage
MEM_AVAILABLE=$(free -m | awk 'NR==2 {print $7}')
if [ "$MEM_AVAILABLE" -lt 50 ]; then
  echo "Available memory critical: $MEM_AVAILABLE MB"
  exit 1
fi

# All checks passed
echo "Frontend health check passed"
exit 0 