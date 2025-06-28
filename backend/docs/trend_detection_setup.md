# Trend Detection Setup Guide

This guide explains how to set up and use the scheduled trend detection system for the Social Media Analysis platform.

## Overview

The trend detection system automatically analyzes social media content at regular intervals to identify:

- High-performing content (performance trends)
- Viral content (viral trends)
- Rising engagement (rising trends)
- High-quality content (quality trends)
- Trending hashtags (hashtag trends)
- Successful content patterns (pattern trends)

## Setup Options

There are three ways to set up the trend detection system:

1. **Systemd Service** (recommended for production Linux servers)
2. **Docker Container** (recommended for containerized environments)
3. **Manual Execution** (for development or testing)

## 1. Systemd Service Setup

### Prerequisites

- Linux system with systemd
- Python 3.8+ installed
- Project dependencies installed (`pip install -r requirements.txt`)

### Installation

1. Navigate to the deployment directory:
   ```bash
   cd backend/deployment
   ```

2. Make the installation script executable:
   ```bash
   chmod +x install_trend_service.sh
   ```

3. Run the installation script as root:
   ```bash
   sudo ./install_trend_service.sh
   ```

### Managing the Service

- **Check status**:
  ```bash
  sudo systemctl status trend-detection
  ```

- **Start the service**:
  ```bash
  sudo systemctl start trend-detection
  ```

- **Stop the service**:
  ```bash
  sudo systemctl stop trend-detection
  ```

- **Restart the service**:
  ```bash
  sudo systemctl restart trend-detection
  ```

- **View logs**:
  ```bash
  sudo journalctl -u trend-detection
  ```

## 2. Docker Container Setup

### Prerequisites

- Docker and Docker Compose installed
- Database connection configured

### Installation

1. Navigate to the deployment directory:
   ```bash
   cd backend/deployment
   ```

2. Start the trend detection service:
   ```bash
   docker-compose -f docker-compose.trend.yml up -d
   ```

### Managing the Container

- **Check status**:
  ```bash
  docker ps -f name=social-media-analysis-trend-detection
  ```

- **View logs**:
  ```bash
  docker logs social-media-analysis-trend-detection
  ```

- **Stop the container**:
  ```bash
  docker-compose -f docker-compose.trend.yml down
  ```

## 3. Manual Execution

### One-time Execution

To run trend detection once:

```bash
cd backend
python scripts/run_trend_detection.py --window all
```

Options:
- `--window`: Specify time window (`realtime`, `short`, `medium`, `long`, or `all`)
- `--platform`: Filter by platform (`youtube`, `instagram`, `threads`, `rednote`, or `all`)
- `--dry-run`: Run without saving to database

### Manual Scheduling

To run the scheduler manually:

```bash
cd backend
python scripts/schedule_trend_detection.py
```

Options:
- `--realtime`: Interval in minutes for realtime window (default: 5)
- `--short`: Interval in minutes for short window (default: 30)
- `--medium`: Interval in minutes for medium window (default: 120)
- `--long`: Interval in minutes for long window (default: 360)
- `--initial-run`: Run all trend detection immediately on startup

## Customizing Trend Detection

### Time Windows

The system uses four time windows for analysis:

1. **Realtime**: Last 24 hours (default interval: every 5 minutes)
2. **Short**: Last 7 days (default interval: every 30 minutes)
3. **Medium**: Last 30 days (default interval: every 2 hours)
4. **Long**: Last 90 days (default interval: every 6 hours)

To customize these intervals, modify the parameters when running the scheduler or edit the systemd service file.

### Accessing Trend Data

Trend data is stored in the `trend_data` table and can be accessed via the following API endpoints:

- `/trends/performance` - High-performing content
- `/trends/viral` - Viral content identification
- `/trends/rising` - Rising engagement trends
- `/trends/quality` - High-quality content trends
- `/trends/hashtags` - Trending hashtags
- `/trends/patterns` - Successful content patterns
- `/trends/all` - Combined trends across categories

Each endpoint supports filtering by time window and platform.

## Troubleshooting

### Common Issues

1. **No trends detected**:
   - Ensure there's enough content in the database
   - Check minimum data requirements in `TrendWindow` configuration
   - Verify content has been properly analyzed with `is_analyzed=True`

2. **Service fails to start**:
   - Check logs with `journalctl -u trend-detection`
   - Verify permissions on script files
   - Ensure database connection is properly configured

3. **High CPU usage**:
   - Increase intervals between trend detection runs
   - Consider reducing the scope of analysis (e.g., focus on specific platforms) 