# Docker Security Hardening

This directory contains security configurations and profiles for hardening Docker containers in the Social Media Analysis platform.

## Security Measures Implemented

### 1. Container Security

- **Multi-stage builds**: Separate build and runtime environments to reduce attack surface
- **Non-root users**: Containers run as non-privileged users
- **Read-only file systems**: Production containers use read-only file systems
- **Minimal base images**: Using slim variants of official images
- **Dropped capabilities**: Only essential Linux capabilities are enabled
- **Resource limits**: CPU and memory limits prevent resource exhaustion attacks

### 2. Network Security

- **Network isolation**: Services are isolated in separate networks
- **Exposed ports**: Only necessary ports are exposed
- **Internal communication**: Services communicate through internal Docker networks

### 3. Advanced Security Controls

- **Seccomp profiles**: System call filtering (seccomp-profile.json)
- **AppArmor profiles**: Mandatory access control (apparmor-profile)
- **Security scanning**: Integration with vulnerability scanning
- **Secrets management**: Sensitive data stored as Docker secrets

## Usage

### Loading AppArmor Profile

```bash
# Make the script executable
chmod +x security/load-apparmor.sh

# Load the profile
./security/load-apparmor.sh
```

### Using Seccomp Profile

The seccomp profile is automatically applied to containers via the `security_opt` setting in docker-compose.prod.yml.

## Security Best Practices

1. **Regular updates**: Keep base images and dependencies updated
2. **Vulnerability scanning**: Regularly scan images for vulnerabilities
3. **Minimal permissions**: Follow principle of least privilege
4. **Secrets rotation**: Regularly rotate secrets and credentials
5. **Logging and monitoring**: Monitor container behavior for anomalies

## References

- [Docker Security Documentation](https://docs.docker.com/engine/security/)
- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
