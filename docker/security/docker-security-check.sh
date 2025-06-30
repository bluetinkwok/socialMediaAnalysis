#!/bin/bash

# Docker Security Best Practices Checker
# This script checks for common Docker security best practices in your configuration

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Function to check if Docker is running
check_docker_running() {
  if ! docker info &>/dev/null; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
  fi
  echo -e "${GREEN}✅ Docker is running${NC}"
}

# Function to check if a container is running as non-root
check_non_root_user() {
  local container=$1
  local user=$(docker exec "$container" id -u 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Container $container is not running${NC}"
    return
  fi
  
  if [ "$user" = "0" ]; then
    echo -e "${RED}❌ Container $container is running as root (UID 0)${NC}"
  else
    echo -e "${GREEN}✅ Container $container is running as non-root (UID $user)${NC}"
  fi
}

# Function to check if a container has privileged mode enabled
check_privileged_mode() {
  local container=$1
  local privileged=$(docker inspect --format='{{.HostConfig.Privileged}}' "$container" 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Container $container does not exist${NC}"
    return
  fi
  
  if [ "$privileged" = "true" ]; then
    echo -e "${RED}❌ Container $container is running in privileged mode${NC}"
  else
    echo -e "${GREEN}✅ Container $container is not running in privileged mode${NC}"
  fi
}

# Function to check if a container has limited capabilities
check_capabilities() {
  local container=$1
  local caps=$(docker inspect --format='{{range $cap := .HostConfig.CapAdd}}{{$cap}} {{end}}' "$container" 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Container $container does not exist${NC}"
    return
  fi
  
  if [ -z "$caps" ]; then
    echo -e "${GREEN}✅ Container $container has no additional capabilities${NC}"
  else
    echo -e "${YELLOW}⚠️  Container $container has additional capabilities: $caps${NC}"
  fi
}

# Function to check if a container has resource limits
check_resource_limits() {
  local container=$1
  local memory_limit=$(docker inspect --format='{{.HostConfig.Memory}}' "$container" 2>/dev/null)
  local cpu_limit=$(docker inspect --format='{{.HostConfig.NanoCpus}}' "$container" 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Container $container does not exist${NC}"
    return
  fi
  
  if [ "$memory_limit" = "0" ]; then
    echo -e "${YELLOW}⚠️  Container $container has no memory limit set${NC}"
  else
    echo -e "${GREEN}✅ Container $container has memory limit: $(($memory_limit/1024/1024))MB${NC}"
  fi
  
  if [ "$cpu_limit" = "0" ]; then
    echo -e "${YELLOW}⚠️  Container $container has no CPU limit set${NC}"
  else
    echo -e "${GREEN}✅ Container $container has CPU limit: $(($cpu_limit/1000000000)) cores${NC}"
  fi
}

# Function to check if a container has a read-only filesystem
check_readonly_filesystem() {
  local container=$1
  local readonly=$(docker inspect --format='{{.HostConfig.ReadonlyRootfs}}' "$container" 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Container $container does not exist${NC}"
    return
  fi
  
  if [ "$readonly" = "true" ]; then
    echo -e "${GREEN}✅ Container $container has a read-only root filesystem${NC}"
  else
    echo -e "${YELLOW}⚠️  Container $container does not have a read-only root filesystem${NC}"
  fi
}

# Function to check if a container has a healthcheck
check_healthcheck() {
  local container=$1
  local healthcheck=$(docker inspect --format='{{.Config.Healthcheck}}' "$container" 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Container $container does not exist${NC}"
    return
  fi
  
  if [ "$healthcheck" = "<nil>" ] || [ -z "$healthcheck" ]; then
    echo -e "${YELLOW}⚠️  Container $container does not have a healthcheck defined${NC}"
  else
    echo -e "${GREEN}✅ Container $container has a healthcheck defined${NC}"
  fi
}

# Function to check Docker network configuration
check_network_configuration() {
  local networks=$(docker network ls --format "{{.Name}}" | grep -v "bridge\|host\|none")
  
  if [ -z "$networks" ]; then
    echo -e "${YELLOW}⚠️  No custom Docker networks found. Using custom networks is recommended for container isolation.${NC}"
  else
    echo -e "${GREEN}✅ Custom Docker networks found: $networks${NC}"
  fi
}

# Function to check Docker secrets
check_secrets() {
  local secrets=$(docker secret ls --format "{{.Name}}" 2>/dev/null)
  
  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Docker secrets are not available (not running in swarm mode)${NC}"
    return
  fi
  
  if [ -z "$secrets" ]; then
    echo -e "${YELLOW}⚠️  No Docker secrets found. Using Docker secrets is recommended for sensitive data.${NC}"
  else
    echo -e "${GREEN}✅ Docker secrets found: $secrets${NC}"
  fi
}

# Function to check Docker version
check_docker_version() {
  local version=$(docker version --format '{{.Server.Version}}')
  echo -e "${GREEN}ℹ️  Docker version: $version${NC}"
  
  # Check if version is recent (arbitrary cutoff at 20.10)
  if [[ "$version" < "20.10" ]]; then
    echo -e "${YELLOW}⚠️  Docker version is older than 20.10. Consider upgrading for latest security features.${NC}"
  else
    echo -e "${GREEN}✅ Docker version is recent${NC}"
  fi
}

# Function to check if images are scanned for vulnerabilities
check_vulnerability_scanning() {
  if [ -d "../vulnerability-reports" ] || [ -d "./vulnerability-reports" ]; then
    echo -e "${GREEN}✅ Vulnerability scanning reports directory exists${NC}"
  else
    echo -e "${YELLOW}⚠️  No vulnerability scanning reports found. Consider running scan-vulnerabilities.sh${NC}"
  fi
}

# Main function
main() {
  echo -e "${GREEN}=== Docker Security Best Practices Checker ===${NC}"
  echo
  
  check_docker_running
  check_docker_version
  
  echo
  echo -e "${GREEN}=== Checking Network Configuration ===${NC}"
  check_network_configuration
  
  echo
  echo -e "${GREEN}=== Checking Docker Secrets ===${NC}"
  check_secrets
  
  echo
  echo -e "${GREEN}=== Checking Vulnerability Scanning ===${NC}"
  check_vulnerability_scanning
  
  echo
  echo -e "${GREEN}=== Checking Running Containers ===${NC}"
  
  # Get list of running containers
  containers=$(docker ps --format "{{.Names}}")
  
  if [ -z "$containers" ]; then
    echo -e "${YELLOW}⚠️  No containers are currently running${NC}"
  else
    for container in $containers; do
      echo
      echo -e "${GREEN}Container: $container${NC}"
      check_non_root_user "$container"
      check_privileged_mode "$container"
      check_capabilities "$container"
      check_resource_limits "$container"
      check_readonly_filesystem "$container"
      check_healthcheck "$container"
    done
  fi
  
  echo
  echo -e "${GREEN}=== Security Check Complete ===${NC}"
}

# Run the main function
main
