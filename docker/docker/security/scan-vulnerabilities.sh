#!/bin/bash

# Docker Container Vulnerability Scanner
# This script scans Docker images for vulnerabilities using Trivy

# Check if Trivy is installed
if ! command -v trivy &> /dev/null; then
    echo "Trivy is not installed. Installing now..."
    
    # Detect OS
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
    elif [ "$(uname)" == "Darwin" ]; then
        OS="macOS"
    else
        OS="Unknown"
    fi
    
    # Install Trivy based on OS
    case "$OS" in
        "Ubuntu"|"Debian GNU/Linux")
            sudo apt-get update
            sudo apt-get install -y wget apt-transport-https gnupg lsb-release
            wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | sudo apt-key add -
            echo deb https://aquasecurity.github.io/trivy-repo/deb $(lsb_release -sc) main | sudo tee -a /etc/apt/sources.list.d/trivy.list
            sudo apt-get update
            sudo apt-get install -y trivy
            ;;
        "macOS")
            brew install trivy
            ;;
        *)
            echo "Unsupported OS for automatic installation. Please install Trivy manually:"
            echo "https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
            exit 1
            ;;
    esac
fi

echo "=== Docker Container Vulnerability Scanner ==="
echo

# Check if Docker is running
if ! docker info &>/dev/null; then
  echo "❌ Docker is not running. Please start Docker and try again."
  exit 1
fi

echo "✅ Docker is running"

# Create output directory
SCAN_DIR="./vulnerability-reports"
mkdir -p "$SCAN_DIR"

echo "Scanning Docker images for vulnerabilities..."
echo "Reports will be saved to $SCAN_DIR"
echo

# Get list of images used in docker-compose files
IMAGES=$(grep -h "image:" ../docker-compose*.yml | awk '{print $2}' | sort -u)

# Add built images
BUILT_IMAGES="social-media-backend social-media-frontend"

# Scan each image
for IMAGE in $IMAGES $BUILT_IMAGES; do
    echo "Scanning image: $IMAGE"
    
    # Clean image name for filename
    FILENAME=$(echo "$IMAGE" | tr ':/' '_')
    
    # Scan image with Trivy
    trivy image --format json --output "$SCAN_DIR/${FILENAME}_report.json" "$IMAGE"
    
    # Generate human-readable report
    trivy image --severity HIGH,CRITICAL "$IMAGE" > "$SCAN_DIR/${FILENAME}_critical.txt"
    
    echo "Completed scan of $IMAGE"
    echo "Report saved to $SCAN_DIR/${FILENAME}_report.json"
    echo "Critical vulnerabilities saved to $SCAN_DIR/${FILENAME}_critical.txt"
    echo
done

echo "=== Vulnerability Scanning Complete ==="
echo "Review the reports in $SCAN_DIR to address any critical vulnerabilities."
echo

# Summary of critical vulnerabilities
echo "=== Critical Vulnerabilities Summary ==="
grep -r "Critical" "$SCAN_DIR"/*_critical.txt | wc -l | xargs echo "Total Critical Vulnerabilities:"
echo

exit 0
