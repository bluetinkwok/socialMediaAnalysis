#!/bin/bash
# Trend Detection Service Installation Script

set -e

# Check if running as root
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root or with sudo"
  exit 1
fi

# Set variables
INSTALL_DIR="/opt/socialMediaAnalysis"
SERVICE_NAME="trend-detection"
SERVICE_FILE="trend_detection.service"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo "Installing Trend Detection Service..."

# Create log directory if it doesn't exist
mkdir -p ${INSTALL_DIR}/backend/logs
touch ${INSTALL_DIR}/backend/logs/scheduled_trends.log
touch ${INSTALL_DIR}/backend/logs/trend_detection.log

# Set permissions
chown -R www-data:www-data ${INSTALL_DIR}/backend/logs
chmod 755 ${INSTALL_DIR}/backend/scripts/schedule_trend_detection.py
chmod 755 ${INSTALL_DIR}/backend/scripts/run_trend_detection.py

# Copy service file to systemd directory
cp ${SCRIPT_DIR}/${SERVICE_FILE} /etc/systemd/system/

# Reload systemd to recognize the new service
systemctl daemon-reload

# Enable and start the service
systemctl enable ${SERVICE_NAME}
systemctl start ${SERVICE_NAME}

echo "Trend Detection Service installed and started successfully."
echo "Check status with: systemctl status ${SERVICE_NAME}"
echo "View logs with: journalctl -u ${SERVICE_NAME}" 