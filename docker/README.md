# Docker Configuration

This directory contains Docker and Docker Compose configurations for the Social Media Analysis Platform.

## Quick Start

### Development Environment

1. **Copy environment file:**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

2. **Start development environment:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
   ```

3. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Production Environment

1. **Start production environment:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
   ```

2. **Access through nginx reverse proxy:**
   - Application: http://localhost

## Services

### Core Services

- **backend**: FastAPI Python 3.12 backend
- **frontend**: React TypeScript frontend
- **redis**: Redis for caching and task queues
- **clamav**: ClamAV for malware scanning

### Optional Services

- **nginx**: Reverse proxy (production only)

## Configuration Files

### docker-compose.yml
Main Docker Compose configuration with all services defined.

### docker-compose.dev.yml
Development overrides:
- Hot reload enabled
- Debug logging
- Source code volumes mounted
- Development commands

### docker-compose.prod.yml
Production overrides:
- Optimized builds
- Production commands (gunicorn, serve)
- No source code volumes
- Nginx enabled

### Dockerfiles

#### backend/Dockerfile
Multi-stage Python 3.12 Dockerfile:
- **Development stage**: Hot reload, dev dependencies
- **Production stage**: Optimized, minimal dependencies

#### frontend/Dockerfile
Multi-stage Node.js Dockerfile:
- **Builder stage**: Build React app
- **Production stage**: Serve static files
- **Development stage**: Hot reload

## Environment Variables

Copy `env.example` to `.env` and configure:

### Required Variables
```bash
REDIS_PASSWORD=your_secure_password
JWT_SECRET_KEY=your_jwt_secret
ENCRYPTION_KEY=your_encryption_key
```

### Optional Variables
```bash
# API Keys
YOUTUBE_API_KEY=your_key
INSTAGRAM_SESSION_ID=your_session

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
```

## Volumes

### Persistent Data
- `redis_data`: Redis persistence
- `clamav_data`: ClamAV virus definitions
- `backend_data`: SQLite database
- `downloads_data`: Downloaded content
- `logs_data`: Application logs

### Development Volumes
- Source code mounted for hot reload
- Anonymous volumes for node_modules

## Networking

### Internal Network
- Custom bridge network: `172.20.0.0/16`
- Service discovery via service names
- Isolated from host network

### Port Mapping
- **3000**: Frontend (development)
- **8000**: Backend API
- **6379**: Redis (optional external access)
- **3310**: ClamAV (optional external access)
- **80/443**: Nginx (production)

## Health Checks

All services include health checks:
- **Backend**: HTTP health endpoint
- **Frontend**: HTTP availability
- **Redis**: Connection test
- **ClamAV**: Service status

## Security Features

### Container Security
- Non-root users in all containers
- Minimal base images (Alpine/Slim)
- Security headers in nginx
- Rate limiting

### Network Security
- Isolated container network
- Internal service communication
- Firewall-friendly port mapping

### Data Security
- Encrypted environment variables
- Secure volume permissions
- Malware scanning integration

## Development Workflow

### Starting Development
```bash
# Start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Start specific services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up backend frontend

# Rebuild and start
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Debugging
```bash
# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Execute commands in containers
docker-compose exec backend bash
docker-compose exec frontend sh

# Check service status
docker-compose ps
```

### Database Management
```bash
# Access SQLite database
docker-compose exec backend sqlite3 /app/data/app.db

# Backup database
docker-compose exec backend cp /app/data/app.db /app/data/backup.db
```

## Production Deployment

### Pre-deployment Checklist
- [ ] Update environment variables in `.env`
- [ ] Configure SSL certificates (if using HTTPS)
- [ ] Set up external monitoring
- [ ] Configure log rotation
- [ ] Set up backup procedures

### Deployment Commands
```bash
# Pull latest images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Deploy with zero downtime
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build backend
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --build frontend

# Full deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Monitoring
```bash
# Check resource usage
docker stats

# View production logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# Health check all services
curl http://localhost/health
```

## Troubleshooting

### Common Issues

1. **Port conflicts**
   ```bash
   # Check what's using ports
   netstat -tulpn | grep :3000
   netstat -tulpn | grep :8000
   ```

2. **Permission issues**
   ```bash
   # Fix volume permissions
   sudo chown -R $USER:$USER backend/downloads
   ```

3. **Build failures**
   ```bash
   # Clean build
   docker-compose down -v
   docker system prune -f
   docker-compose build --no-cache
   ```

4. **Database issues**
   ```bash
   # Reset database
   docker-compose down
   docker volume rm social-media-analysis_backend_data
   docker-compose up
   ```

### Performance Tuning

1. **Resource limits** (add to docker-compose.yml):
   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 1G
             cpus: '0.5'
   ```

2. **Redis optimization**:
   ```bash
   # Monitor Redis
   docker-compose exec redis redis-cli monitor
   ```

## Maintenance

### Regular Tasks
- Update base images monthly
- Rotate logs weekly
- Backup database daily
- Update virus definitions (automatic)

### Updates
```bash
# Update Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Update images
docker-compose pull
docker-compose up -d
``` 