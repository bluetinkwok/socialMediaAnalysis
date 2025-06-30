#!/bin/bash

# Docker Security Baseline Generator
# This script creates a security baseline for Docker containers

echo "=== Docker Security Baseline Generator ==="
echo

# Check if Docker is running
if ! docker info &>/dev/null; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

echo "✅ Docker is running"

# Create output directory
BASELINE_DIR="./security/baseline"
mkdir -p "$BASELINE_DIR"

echo "Creating Docker security baseline in $BASELINE_DIR"

# Generate Docker info baseline
echo "Generating Docker info baseline..."
docker info > "$BASELINE_DIR/docker-info.txt"

# Generate Docker version baseline
echo "Generating Docker version baseline..."
docker version > "$BASELINE_DIR/docker-version.txt"

# Generate system info
echo "Generating system info baseline..."
{
  echo "=== System Information ==="
  echo "Date: $(date)"
  echo "Hostname: $(hostname)"
  echo "Kernel: $(uname -r)"
  echo "OS: $(uname -s)"
  echo "Architecture: $(uname -m)"
  echo
  echo "=== CPU Information ==="
  if [ "$(uname)" == "Darwin" ]; then
    sysctl -n machdep.cpu.brand_string
    sysctl -n hw.ncpu
  else
    grep "model name" /proc/cpuinfo | head -1
    grep -c processor /proc/cpuinfo
  fi
  echo
  echo "=== Memory Information ==="
  if [ "$(uname)" == "Darwin" ]; then
    sysctl hw.memsize | awk '{print $2/1024/1024/1024 " GB"}'
  else
    grep MemTotal /proc/meminfo
  fi
} > "$BASELINE_DIR/system-info.txt"

# Generate Docker network baseline
echo "Generating Docker network baseline..."
docker network ls > "$BASELINE_DIR/docker-networks.txt"

# Generate Docker security options
echo "Generating Docker security options baseline..."
{
  echo "=== Docker Security Options ==="
  echo "Docker Root Dir: $(docker info | grep "Docker Root Dir" | awk '{print $4}')"
  echo "Security Options:"
  docker info | grep -A 10 "Security Options:" | grep -v "Security Options:"
} > "$BASELINE_DIR/docker-security.txt"

# Generate Docker daemon configuration
echo "Generating Docker daemon configuration baseline..."
if [ -f "/etc/docker/daemon.json" ]; then
  cp "/etc/docker/daemon.json" "$BASELINE_DIR/daemon.json"
else
  echo "{}" > "$BASELINE_DIR/daemon.json"
  echo "No Docker daemon configuration found, created empty file"
fi

# Generate container security baseline for running containers
echo "Generating container security baseline for running containers..."
{
  echo "=== Running Containers ==="
  docker ps -a --format "table {{.ID}}\t{{.Image}}\t{{.Command}}\t{{.Status}}\t{{.Names}}"
  echo
  echo "=== Container Security Details ==="
  for container in $(docker ps -q); do
    echo "Container: $(docker inspect --format '{{.Name}}' "$container" | sed 's/^\///')"
    echo "  Image: $(docker inspect --format '{{.Config.Image}}' "$container")"
    echo "  User: $(docker inspect --format '{{.Config.User}}' "$container")"
    echo "  Privileged: $(docker inspect --format '{{.HostConfig.Privileged}}' "$container")"
    echo "  Read-only Root FS: $(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$container")"
    echo "  Security Opts: $(docker inspect --format '{{.HostConfig.SecurityOpt}}' "$container")"
    echo "  Cap Add: $(docker inspect --format '{{.HostConfig.CapAdd}}' "$container")"
    echo "  Cap Drop: $(docker inspect --format '{{.HostConfig.CapDrop}}' "$container")"
    echo
  done
} > "$BASELINE_DIR/container-security.txt"

echo
echo "=== Security Baseline Generation Complete ==="
echo "Baseline files have been saved to $BASELINE_DIR"
echo "Use these files as a reference for security auditing and compliance checks."
echo
