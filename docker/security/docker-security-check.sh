#!/bin/bash

# Docker Security Best Practices Check Script
# This script checks for common Docker security issues in the project

echo "=== Docker Security Best Practices Check ==="
echo

# Check if Docker is running
if ! docker info &>/dev/null; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

echo "✅ Docker is running"

# Check Dockerfile for best practices
check_dockerfile() {
  local dockerfile=$1
  echo
  echo "Checking $dockerfile..."
  
  # Check for USER instruction (non-root user)
  if grep -q "^USER " "$dockerfile"; then
    echo "✅ Non-root USER directive found"
  else
    echo "❌ No USER directive found. Containers may be running as root"
  fi
  
  # Check for multi-stage builds
  if grep -q "^FROM.*AS.*" "$dockerfile"; then
    echo "✅ Multi-stage build detected"
  else
    echo "⚠️ No multi-stage build detected"
  fi
  
  # Check for HEALTHCHECK
  if grep -q "^HEALTHCHECK " "$dockerfile" || grep -q "healthcheck.sh" "$dockerfile"; then
    echo "✅ HEALTHCHECK directive found"
  else
    echo "⚠️ No HEALTHCHECK directive found"
  fi
  
  # Check for latest tag
  if grep -q "FROM.*:latest" "$dockerfile"; then
    echo "❌ ':latest' tag used. Consider using specific version tags"
  else
    echo "✅ No 'latest' tags detected"
  fi
  
  # Check for ADD vs COPY
  if grep -q "^ADD " "$dockerfile"; then
    echo "⚠️ ADD instruction found. COPY is generally preferred for security"
  else
    echo "✅ No ADD instructions found (COPY preferred)"
  fi
}

# Check docker-compose files for best practices
check_compose() {
  local composefile=$1
  echo
  echo "Checking $composefile..."
  
  # Check for privileged mode
  if grep -q "privileged: true" "$composefile"; then
    echo "❌ Container(s) running in privileged mode detected"
  else
    echo "✅ No containers running in privileged mode"
  fi
  
  # Check for network mode: host
  if grep -q "network_mode: host" "$composefile"; then
    echo "⚠️ Container(s) using host network mode detected"
  else
    echo "✅ No containers using host network mode"
  fi
  
  # Check for read-only root filesystem
  if grep -q "read_only: true" "$composefile"; then
    echo "✅ Read-only root filesystem detected"
  else
    echo "⚠️ No read-only root filesystem configured"
  fi
  
  # Check for resource limits
  if grep -q "cpus:" "$composefile" || grep -q "memory:" "$composefile"; then
    echo "✅ Resource limits defined"
  else
    echo "⚠️ No resource limits defined"
  fi
  
  # Check for healthcheck
  if grep -q "healthcheck:" "$composefile"; then
    echo "✅ Healthcheck configuration found"
  else
    echo "⚠️ No healthcheck configuration found"
  fi
  
  # Check for security options
  if grep -q "security_opt:" "$composefile"; then
    echo "✅ Security options configured"
  else
    echo "⚠️ No security options configured"
  fi
}

# Check Dockerfiles
for dockerfile in $(find .. -name "Dockerfile*" -not -path "*/\.*"); do
  check_dockerfile "$dockerfile"
done

# Check docker-compose files
for composefile in $(find . -name "docker-compose*.yml"); do
  check_compose "$composefile"
done

echo
echo "=== Security Check Complete ==="
echo "Review any warnings or errors and address them according to your security requirements."
echo
