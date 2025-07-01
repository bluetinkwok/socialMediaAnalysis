# Docker Security Measures

This directory contains security-related files and scripts for hardening Docker containers in the Social Media Analysis Platform.

## Security Files

- **apparmor-profile**: AppArmor profile that restricts container processes to only necessary operations
- **seccomp-profile.json**: Custom seccomp profile to restrict system calls for containers
- **docker-security-check.sh**: Script to verify Docker security best practices in your environment
- **generate-baseline.sh**: Generates security baselines for running containers
- **load-apparmor.sh**: Helper script to load the AppArmor profile
- **scan-vulnerabilities.sh**: Script to scan Docker images for vulnerabilities using Trivy

## Usage

1. **Load AppArmor Profile**:
   ```
   sudo ./load-apparmor.sh
   ```

2. **Scan for Vulnerabilities**:
   ```
   ./scan-vulnerabilities.sh [image_name]
   ```

3. **Check Security Best Practices**:
   ```
   ./docker-security-check.sh
   ```

4. **Generate Security Baseline**:
   ```
   ./generate-baseline.sh
   ```

## Security Best Practices

- Run containers as non-root users
- Use read-only file systems where possible
- Implement resource limits (CPU, memory)
- Use network isolation between services
- Apply seccomp and AppArmor profiles
- Regularly scan for vulnerabilities
- Use Docker secrets for sensitive information
- Implement container health checks

## Additional Resources

- [Docker Security Documentation](https://docs.docker.com/engine/security/)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [OWASP Docker Security](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html) 