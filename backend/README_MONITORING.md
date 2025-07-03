# Social Media Analysis - Monitoring System

This document provides an overview of the automated monitoring system for the Social Media Analysis platform.

## Overview

The monitoring system allows users to set up automated, scheduled monitoring of social media platforms. The system will periodically check for new content based on user-defined criteria and frequencies.

## Components

### 1. Database Models

Located in `app/models/monitoring_models.py`:

- **MonitoringFrequency (Enum)**: Defines how often a monitoring job should run (hourly, daily, weekly, monthly, custom)
- **MonitoringStatus (Enum)**: Tracks the status of monitoring jobs (active, paused, completed, failed, deleted)
- **MonitoringJob**: Stores configuration for monitoring tasks
- **MonitoringRun**: Records individual execution instances of monitoring jobs

### 2. API Schemas

Located in `app/schemas/monitoring.py`:

- Request and response models for the monitoring API endpoints
- Validation for monitoring job creation and updates

### 3. API Routes

Located in `app/api/routes/monitoring.py`:

- `POST /api/monitoring/jobs`: Create a new monitoring job
- `GET /api/monitoring/jobs`: List all monitoring jobs
- `GET /api/monitoring/jobs/{job_id}`: Get details for a specific job
- `PUT /api/monitoring/jobs/{job_id}`: Update a monitoring job
- `DELETE /api/monitoring/jobs/{job_id}`: Delete a monitoring job
- `GET /api/monitoring/jobs/{job_id}/runs`: Get execution history for a job
- `POST /api/monitoring/jobs/{job_id}/execute`: Manually trigger a job execution

### 4. Monitoring Service

Located in `app/services/monitoring_service.py`:

- Business logic for creating, updating, and executing monitoring jobs
- Integration with platform-specific services (Twitter, YouTube, etc.)

### 5. Scheduler

Located in `backend/scripts/`:

- `simple_scheduler.py`: Standalone implementation that can run independently
- `monitoring_integration.py`: Example of integration with the main application

## Database Schema

### MonitoringJob

| Field                | Type        | Description                                      |
|----------------------|-------------|--------------------------------------------------|
| id                   | UUID        | Primary key                                      |
| user_id              | UUID        | Foreign key to User                              |
| name                 | String      | Job name                                         |
| platform             | String      | Social media platform (twitter, youtube, etc.)   |
| target_url           | String      | URL to monitor                                   |
| target_type          | String      | Type of target (profile, hashtag, channel, etc.) |
| frequency            | Enum        | How often to run the job                         |
| interval_minutes     | Integer     | Custom interval in minutes (if frequency=CUSTOM) |
| max_items_per_run    | Integer     | Maximum items to process per execution           |
| status               | Enum        | Current job status                               |
| last_run_at          | DateTime    | When the job was last executed                   |
| next_run_at          | DateTime    | When the job is scheduled to run next            |
| total_runs           | Integer     | Total number of executions                       |
| successful_runs      | Integer     | Number of successful executions                  |
| failed_runs          | Integer     | Number of failed executions                      |
| notify_on_new_content| Boolean     | Whether to notify when new content is found      |
| notify_on_failure    | Boolean     | Whether to notify when execution fails           |
| notification_email   | String      | Email address for notifications                  |
| created_at           | DateTime    | When the job was created                         |
| updated_at           | DateTime    | When the job was last updated                    |

### MonitoringRun

| Field                | Type        | Description                                      |
|----------------------|-------------|--------------------------------------------------|
| id                   | UUID        | Primary key                                      |
| monitoring_job_id    | UUID        | Foreign key to MonitoringJob                     |
| start_time           | DateTime    | When the execution started                       |
| end_time             | DateTime    | When the execution completed                     |
| status               | String      | Execution status (in_progress, completed, failed)|
| items_found          | Integer     | Number of items found                            |
| items_processed      | Integer     | Number of items processed                        |
| new_items_downloaded | Integer     | Number of new items downloaded                   |
| error_message        | String      | Error message (if failed)                        |

## Running the Scheduler

### Option 1: Standalone Scheduler

The standalone scheduler (`simple_scheduler.py`) can run independently of the main application:

```bash
# Basic usage (checks every 60 seconds)
python backend/scripts/simple_scheduler.py

# Custom check interval (e.g., every 30 seconds)
python backend/scripts/simple_scheduler.py --interval 30

# Run once and exit
python backend/scripts/simple_scheduler.py --once

# Create a test job and start the scheduler
python backend/scripts/simple_scheduler.py --create-test
```

### Option 2: System Service

For production environments, run the scheduler as a systemd service:

1. Copy `monitoring-scheduler.service` to `/etc/systemd/system/`
2. Edit the file to update paths to match your installation
3. Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable monitoring-scheduler
sudo systemctl start monitoring-scheduler
```

## Integration with Main Application

The `monitoring_integration.py` script demonstrates how to integrate the monitoring system with the main application. It shows:

1. How to import and use the database models
2. How to create and process monitoring jobs
3. How to handle errors and update job statistics

## Development and Testing

1. Make sure the database models are properly set up
2. Use the API endpoints to create and manage monitoring jobs
3. Test the scheduler with the `--once` flag to verify job processing
4. Check the logs for any errors or issues

## Future Enhancements

- Add support for more social media platforms
- Implement notification system for new content and failures
- Add more advanced scheduling options (e.g., specific days of week)
- Create a user interface for managing monitoring jobs
- Add analytics for monitoring job performance and results
