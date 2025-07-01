# Docker Container Security Hardening

This document provides detailed information about the Docker container security hardening measures implemented in the Social Media Analysis Platform.

## Table of Contents

1. [Overview](#overview)
2. [Container Image Security](#container-image-security)
3. [Network Security](#network-security)
4. [Security Profiles](#security-profiles)
5. [Resource Controls](#resource-controls)
6. [Secrets Management](#secrets-management)
7. [Health and Monitoring](#health-and-monitoring)
8. [Security Best Practices](#security-best-practices)
9. [Security Tools](#security-tools)
10. [References](#references)

## Overview

Container security is a critical aspect of modern application deployment. The Social Media Analysis Platform implements comprehensive security measures to protect against various threats, including:

- Container escape vulnerabilities
- Privilege escalation attacks
- Resource exhaustion (DoS)
- Network-based attacks
- Data exfiltration
- Supply chain attacks

## Container Image Security

### Multi-stage Builds

We use multi-stage builds to separate the build environment from the runtime environment:

```dockerfile
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder
# ... build steps ...

# Stage 2: Runtime
FROM python:3.12-slim
# ... copy only necessary artifacts from builder ...
```

Benefits:
- Reduces attack surface by excluding build tools from runtime
- Smaller final image size
- Separation of concerns

### Minimal Base Images

We use minimal base images to reduce the potential attack surface:

- Backend: `python:3.12-slim`
- Frontend: `node:18-alpine` and `nginx:alpine`

### Non-root Users

All containers run as non-privileged users:

```dockerfile
# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -m appuser
# ...
# Switch to non-root user
USER appuser
```

### File Permissions

We set appropriate permissions for application directories:

```dockerfile
RUN mkdir -p /app/uploads /app/downloads /app/logs \
    && chown -R appuser:appuser /app
```

## Network Security

### Network Isolation

Services are isolated in separate Docker networks:

```yaml
networks:
  frontend-network:
    driver: bridge
  backend-network:
    driver: bridge
  db-network:
    driver: bridge
```

### Limited Exposed Ports

Only necessary ports are exposed:

```yaml
ports:
  - "443:443"  # HTTPS
  - "80:80"    # HTTP (redirects to HTTPS)
```

Internal services use `expose` instead of `ports` to prevent external access:

```yaml
expose:
  - "8000"  # Only accessible within Docker networks
```

### Internal Communication

Services communicate through internal Docker networks:

```yaml
services:
  backend:
    networks:
      - frontend-network  # For frontend communication
      - backend-network   # For database communication
```

## Security Profiles

### Seccomp Profiles

We use a custom seccomp profile to restrict system calls:

```yaml
security_opt:
  - seccomp=./security/seccomp-profile.json
```

The profile is based on Docker's default profile with additional restrictions.

### AppArmor Profiles

We implement an AppArmor profile for container isolation:

```yaml
security_opt:
  - apparmor=social-media-container
```

The profile restricts file access and operations.

### Capability Restrictions

We drop all capabilities by default and only add necessary ones:

```yaml
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE  # Only for services that need to bind to privileged ports
```

### Read-only Filesystems

Production containers use read-only filesystems:

```yaml
read_only: true
tmpfs:
  - /tmp
  - /var/run
  - /var/cache/nginx
```

## Resource Controls

### CPU Limits

We set CPU limits for each container:

```yaml
deploy:
  resources:
    limits:
      cpus: '0.50'  # Limits to 50% of a CPU core
```

### Memory Limits

We configure memory limits to prevent memory-based DoS attacks:

```yaml
deploy:
  resources:
    limits:
      memory: 512M  # Limits to 512 MB of memory
```

## Secrets Management

### Docker Secrets

We use Docker secrets for sensitive information:

```yaml
secrets:
  redis_password:
    file: ./secrets/redis_password_prod.txt
```

And reference them in services:

```yaml
services:
  backend:
    secrets:
      - source: backend_api_key
        target: /app/secrets/api_key
```

### Environment Separation

We maintain separate configurations for development and production:

- `docker-compose.yml` for development
- `docker-compose.prod.yml` for production

## Health and Monitoring

### Container Healthchecks

We implement healthcheck scripts for containers:

```yaml
healthcheck:
  test: ["CMD", "/app/healthcheck.sh"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Security Baseline

We use a baseline generator script to track security configuration:

```bash
./security/generate-baseline.sh
```

### Vulnerability Scanning

We regularly scan Docker images for vulnerabilities:

```bash
./security/scan-vulnerabilities.sh [image_name]
```

## Security Best Practices

1. **Regular Updates**: Keep base images and dependencies updated
2. **Minimal Permissions**: Follow principle of least privilege
3. **Secrets Rotation**: Regularly rotate secrets and credentials
4. **Logging and Monitoring**: Monitor container behavior for anomalies
5. **Security Scanning**: Regularly scan images for vulnerabilities

## Security Tools

The following security tools are provided in the `docker/security/` directory:

- **scan-vulnerabilities.sh**: Scans Docker images for vulnerabilities using Trivy
- **docker-security-check.sh**: Verifies Docker security best practices
- **generate-baseline.sh**: Generates security baselines for running containers
- **load-apparmor.sh**: Loads the AppArmor profile

## References

- [Docker Security Documentation](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [Docker Security Best Practices](https://snyk.io/blog/10-docker-image-security-best-practices/)
- [AppArmor Security Profiles](https://docs.docker.com/engine/security/apparmor/)
- [Seccomp Security Profiles](https://docs.docker.com/engine/security/seccomp/)
