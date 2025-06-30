#!/bin/bash

# Script to load the AppArmor profile for social media containers

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "This script must be run as root"
  exit 1
fi

# Check if AppArmor is available
if ! command -v apparmor_parser &> /dev/null; then
  echo "AppArmor is not installed. Installing now..."
  
  # Detect OS
  if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
  else
    OS="Unknown"
  fi
  
  # Install AppArmor based on OS
  case "$OS" in
    "Ubuntu"|"Debian GNU/Linux")
      apt-get update
      apt-get install -y apparmor apparmor-utils
      ;;
    *)
      echo "Unsupported OS for automatic installation. Please install AppArmor manually."
      exit 1
      ;;
  esac
fi

echo "Loading AppArmor profile for social media containers..."

# Check if the profile exists
if [ ! -f "$(dirname "$0")/apparmor-profile" ]; then
  echo "AppArmor profile not found at $(dirname "$0")/apparmor-profile"
  exit 1
fi

# Load the profile
apparmor_parser -r -W "$(dirname "$0")/apparmor-profile"

if [ $? -eq 0 ]; then
  echo "AppArmor profile loaded successfully"
  
  # Verify the profile is loaded
  if grep -q "social-media-container" /sys/kernel/security/apparmor/profiles 2>/dev/null; then
    echo "Profile verified as loaded"
  else
    echo "Warning: Profile may not be loaded correctly"
  fi
else
  echo "Failed to load AppArmor profile"
  exit 1
fi

echo "To use this profile with Docker, add the following to your docker-compose.yml:"
echo "    security_opt:"
echo "      - apparmor=social-media-container"

exit 0 