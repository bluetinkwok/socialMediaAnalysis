# Monitoring Scheduler

This directory contains scripts for automated scheduling and execution of monitoring jobs.

## Simple Scheduler

The `simple_scheduler.py` script provides a standalone implementation of the monitoring scheduler
that can run independently of the main application. It uses SQLite for storage and the Python
`schedule` library for scheduling.

### Features

- Periodic checking for pending monitoring jobs
- Processing of due jobs based on their frequency settings
- Tracking of job execution history and statistics
- Standalone operation with minimal dependencies

### Requirements

- Python 3.8+
- `schedule` library (`pip install schedule`)

### Usage

```bash
# Basic usage (checks every 60 seconds)
python simple_scheduler.py

# Custom check interval (e.g., every 30 seconds)
python simple_scheduler.py --interval 30

# Run once and exit
python simple_scheduler.py --once

# Create a test job and start the scheduler
python simple_scheduler.py --create-test
```

### Database

The scheduler uses SQLite and creates a database file at `../data/social_media_analysis.db`.
It manages two tables:

1. `monitoring_jobs` - Stores job configurations and statistics
2. `monitoring_runs` - Stores individual run history and results

### Running as a Service

For production use, you can set up the scheduler as a systemd service:

1. Copy the `monitoring-scheduler.service` file to `/etc/systemd/system/`
2. Edit the file to update the paths to match your installation
3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable monitoring-scheduler
sudo systemctl start monitoring-scheduler
```

4. Check the status:

```bash
sudo systemctl status monitoring-scheduler
```

### Logs

Logs are written to `../logs/simple_scheduler.log` and to the console.

## Integration with Main Application

For full integration with the main application:

1. Ensure the application's database models are properly set up with the required tables
2. Use the monitoring service API to create and manage monitoring jobs
3. Set up the scheduler to run periodically using the system's cron or a dedicated service
