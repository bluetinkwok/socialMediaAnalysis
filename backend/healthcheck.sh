#!/bin/sh
set -e

# Health check for the backend service
# This script is used by Docker to determine if the container is healthy

# API endpoint to check
HEALTH_ENDPOINT="http://localhost:8000/api/v1/health"

# Perform the health check
response=$(curl -s -o /dev/null -w "%{http_code}" $HEALTH_ENDPOINT)

# Check if response is 200 OK
if [ "$response" = "200" ]; then
  echo "Health check passed: API is responding with HTTP 200"
  exit 0
else
  echo "Health check failed: API returned HTTP $response"
  exit 1
fi
