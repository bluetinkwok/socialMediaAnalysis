# Social Media Analysis Platform - Deployment Guide

This document provides comprehensive instructions for deploying the Social Media Analysis Platform using Docker Compose.

## Prerequisites

- Docker Engine (version 20.10.0+)
- Docker Compose (version 2.0.0+)
- Git
- At least 4GB of RAM and 2 CPU cores for the host machine

## Configuration

### Environment Variables

1. Copy the example environment file to create a production environment file:

```bash
cd docker
cp env.example .env.production
```

2. Edit the `.env.production` file to set appropriate values for your environment:

```bash
# Required changes:
# - Set secure passwords for Redis and PostgreSQL
# - Configure JWT_SECRET_KEY and ENCRYPTION_KEY with strong, random values
# - Set proper API URLs for frontend configuration
# - Add any required API keys for external services
```

### Volume Configuration

The following Docker volumes are used for persistent storage:

- `postgres_data`: PostgreSQL database files
- `redis_data`: Redis cache data
- `uploads`: User-uploaded files
- `downloads`: Downloaded content from social media platforms
- `sqlite_data`: SQLite database files (used by the monitoring scheduler)

These volumes are automatically created by Docker Compose, but you can customize their configuration in the `docker-compose.yml` file if needed.

## Deployment Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-organization/social-media-analysis.git
cd social-media-analysis
```

### 2. Build the Docker Images

```bash
cd docker
docker-compose build
```

### 3. Start the Services

```bash
docker-compose up -d
```

This command starts all services defined in the `docker-compose.yml` file in detached mode.

### 4. Verify Deployment

Check that all containers are running:

```bash
docker-compose ps
```

All services should show a status of "Up" with no restart counts.

### 5. Access the Application

- Frontend: http://localhost:80
- Backend API: http://localhost:8000

## Service Architecture

The deployment consists of the following services:

1. **Frontend**: Nginx-based web server serving the React application
2. **Backend**: Python FastAPI application providing the REST API
3. **PostgreSQL**: Database for structured data storage
4. **Redis**: Cache for session management and temporary data
5. **Monitoring Scheduler**: Service that periodically checks for and processes monitoring jobs

## Resource Limits

Each service has resource limits configured to prevent resource monopolization:

- Frontend: 0.5 CPU cores, 512MB memory
- Backend: 1.0 CPU core, 1GB memory
- PostgreSQL: 0.75 CPU cores, 1GB memory
- Redis: 0.25 CPU cores, 256MB memory
- Monitoring Scheduler: 0.25 CPU cores, 256MB memory

These limits can be adjusted in the `docker-compose.yml` file if needed.

## Health Checks

All services have health checks configured to detect and recover from failures:

- Frontend: Checks if Nginx is serving content
- Backend: Verifies API endpoint availability
- PostgreSQL: Confirms database connectivity
- Redis: Tests cache responsiveness
- Monitoring Scheduler: Ensures the scheduler process is running

## Maintenance

### Viewing Logs

```bash
# View logs for all services
docker-compose logs

# View logs for a specific service
docker-compose logs backend

# Follow logs in real-time
docker-compose logs -f
```

### Updating the Application

```bash
# Pull the latest changes
git pull

# Rebuild the containers
docker-compose build

# Restart the services
docker-compose down
docker-compose up -d
```

### Backup and Restore

#### Database Backup

```bash
# PostgreSQL backup
docker exec social-media-postgres pg_dump -U postgres social_media > backup.sql

# SQLite backup
docker cp social-media-monitoring-scheduler:/app/data/social_media_analysis.db ./backup.db
```

#### Database Restore

```bash
# PostgreSQL restore
cat backup.sql | docker exec -i social-media-postgres psql -U postgres social_media

# SQLite restore
docker cp ./backup.db social-media-monitoring-scheduler:/app/data/social_media_analysis.db
```

## Troubleshooting

### Container Fails to Start

Check the logs for the failing container:

```bash
docker-compose logs <service-name>
```

### Database Connection Issues

Verify that the database container is running and healthy:

```bash
docker-compose ps postgres
```

### Performance Problems

Monitor resource usage to identify bottlenecks:

```bash
docker stats
```

## Security Considerations

- All containers run with non-root users
- Security options like `no-new-privileges` are enabled
- Frontend container runs in read-only mode
- Sensitive data is managed through environment variables
- Regular security updates should be applied to base images

## Production Considerations

For a production deployment, consider the following additional steps:

1. Use a reverse proxy like Traefik or Nginx for SSL termination
2. Set up proper DNS records for your domain
3. Configure automated backups
4. Implement monitoring and alerting
5. Consider using Docker Swarm or Kubernetes for high-availability deployments
