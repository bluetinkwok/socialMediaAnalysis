#!/bin/bash

# Docker Security Baseline Generator
# This script generates security baselines for Docker containers

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info &>/dev/null; then
  echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
  exit 1
fi

echo -e "${GREEN}=== Docker Security Baseline Generator ===${NC}"
echo

# Create output directory
BASELINE_DIR="./security-baselines"
mkdir -p "$BASELINE_DIR"

echo "Generating security baselines for running containers..."
echo "Baselines will be saved to $BASELINE_DIR"
echo

# Get list of running containers
containers=$(docker ps --format "{{.Names}}")

if [ -z "$containers" ]; then
  echo -e "${YELLOW}⚠️  No containers are currently running${NC}"
  echo "Please start your containers first, then run this script again."
  exit 1
fi

for container in $containers; do
  echo "Generating baseline for container: $container"
  
  # Create container-specific directory
  container_dir="$BASELINE_DIR/$container"
  mkdir -p "$container_dir"
  
  # Get container details
  echo "  - Getting container configuration..."
  docker inspect "$container" > "$container_dir/container-config.json"
  
  # Get process list
  echo "  - Getting process list..."
  docker exec "$container" ps aux > "$container_dir/processes.txt" 2>/dev/null
  
  # Get network connections
  echo "  - Getting network connections..."
  docker exec "$container" netstat -tulpn > "$container_dir/network-connections.txt" 2>/dev/null
  
  # Get open ports
  echo "  - Getting exposed ports..."
  docker port "$container" > "$container_dir/exposed-ports.txt" 2>/dev/null
  
  # Get mounted volumes
  echo "  - Getting mounted volumes..."
  docker inspect --format='{{range .Mounts}}{{.Source}}:{{.Destination}}:{{.Mode}} {{end}}' "$container" > "$container_dir/mounted-volumes.txt"
  
  # Get environment variables
  echo "  - Getting environment variables (redacted)..."
  docker exec "$container" env | grep -v "PASSWORD\|SECRET\|KEY\|TOKEN" > "$container_dir/environment.txt" 2>/dev/null
  
  # Get user information
  echo "  - Getting user information..."
  docker exec "$container" id > "$container_dir/user-info.txt" 2>/dev/null
  
  # Get capabilities
  echo "  - Getting capabilities..."
  docker exec "$container" capsh --print > "$container_dir/capabilities.txt" 2>/dev/null
  
  # Get installed packages (try different package managers)
  echo "  - Getting installed packages..."
  docker exec "$container" dpkg -l > "$container_dir/packages-dpkg.txt" 2>/dev/null
  docker exec "$container" rpm -qa > "$container_dir/packages-rpm.txt" 2>/dev/null
  docker exec "$container" apk info > "$container_dir/packages-apk.txt" 2>/dev/null
  
  # Get system information
  echo "  - Getting system information..."
  docker exec "$container" uname -a > "$container_dir/system-info.txt" 2>/dev/null
  
  echo "Baseline for $container completed"
  echo "Files saved to $container_dir"
  echo
done

# Generate summary report
echo "Generating summary report..."
summary_file="$BASELINE_DIR/summary.txt"

{
  echo "Docker Security Baseline Summary"
  echo "================================"
  echo "Generated on: $(date)"
  echo
  echo "Container Summary:"
  echo "-----------------"
  for container in $containers; do
    echo "Container: $container"
    echo "  - User: $(cat "$BASELINE_DIR/$container/user-info.txt" 2>/dev/null || echo "N/A")"
    echo "  - Exposed Ports: $(cat "$BASELINE_DIR/$container/exposed-ports.txt" 2>/dev/null || echo "None")"
    echo "  - Process Count: $(wc -l < "$BASELINE_DIR/$container/processes.txt" 2>/dev/null || echo "N/A")"
    echo "  - Network Connections: $(grep -c "LISTEN" "$BASELINE_DIR/$container/network-connections.txt" 2>/dev/null || echo "N/A") listening"
    echo
  done
} > "$summary_file"

echo -e "${GREEN}=== Security Baseline Generation Complete ===${NC}"
echo "Summary report saved to $summary_file"
echo
echo "Review these baselines to understand your containers' security posture."
echo "Use them as a reference point when making security changes."
echo

exit 0
