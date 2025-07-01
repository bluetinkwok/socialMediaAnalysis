# Security Logging and Monitoring

This document provides an overview of the security logging and monitoring system implemented in the Social Media Analysis Platform.

## Table of Contents

1. [Overview](#overview)
2. [Security Logging](#security-logging)
3. [Security Metrics](#security-metrics)
4. [Intrusion Detection](#intrusion-detection)
5. [Audit Trails](#audit-trails)
6. [Security Monitoring](#security-monitoring)
7. [Integration with Prometheus and Grafana](#integration-with-prometheus-and-grafana)
8. [Security Baselines](#security-baselines)
9. [API Endpoints](#api-endpoints)
10. [Configuration](#configuration)

## Overview

The security logging and monitoring system provides comprehensive tracking and analysis of security-related events in the application. It includes structured logging, metrics collection, intrusion detection, and audit trails to help identify and respond to security incidents.

## Security Logging

The security logging system uses structured logging with consistent fields and formats to make logs easily searchable and analyzable. It is implemented in `core/security_logger.py`.

### Key Features

- **Structured JSON Logging**: All logs are formatted as JSON for easy parsing and analysis.
- **Security-Specific Log Levels**: Custom log levels for different security severities (CRITICAL, HIGH, MEDIUM, LOW, INFO, DEBUG).
- **Contextual Information**: Each log entry includes relevant context such as user IDs, IP addresses, timestamps, and resource identifiers.
- **Specialized Log Methods**: Convenience methods for common security events like authentication failures, permission denials, and suspicious activities.

### Example Usage

```python
from core.security_logger import security_logger

# Log a security event
security_logger.medium(
    "Unusual login pattern detected",
    user_id="user123",
    ip_address="192.168.1.100",
    details={"login_count": 5, "time_window": "10 minutes"}
)

# Log an authentication failure
security_logger.auth_failure(
    username="user@example.com",
    ip_address="192.168.1.100",
    reason="invalid_password"
)
```

## Security Metrics

The security metrics system collects and exposes metrics about security-related events using Prometheus. It is implemented in `models/security.py`.

### Key Metrics

- **Authentication Metrics**: Success/failure counts, latency.
- **Access Control Metrics**: Access denied counts, permission check latency.
- **Rate Limiting Metrics**: Rate limit exceeded counts, current usage.
- **Input Validation Metrics**: Validation failure counts.
- **Suspicious Activity Metrics**: Counts by type and severity.
- **File Scanning Metrics**: Scan counts, rejection counts, latency.
- **Session Metrics**: Active sessions, expired sessions.
- **API Security Metrics**: Missing security headers.
- **Database Security Metrics**: Encryption operations, latency.
- **Privacy Metrics**: Consent changes, data export/deletion requests.

### Example Usage

```python
from models.security import SecurityMetrics

# Track an authentication attempt
SecurityMetrics.track_auth_attempt(
    auth_method="password",
    success=False,
    user_type="standard",
    failure_reason="invalid_credentials"
)

# Track a suspicious activity
SecurityMetrics.track_suspicious_activity(
    event_type="brute_force",
    severity="high"
)
```

## Intrusion Detection

The intrusion detection system identifies potential security threats by analyzing patterns of activity. It is implemented in `core/intrusion_detection.py`.

### Detection Capabilities

- **Brute Force Detection**: Identifies multiple failed login attempts.
- **Unusual Login Detection**: Detects logins at unusual times or from unusual locations.
- **Excessive Requests Detection**: Identifies potential DoS attacks or scraping.
- **Unusual Data Access**: Detects potential data exfiltration.
- **Unusual File Uploads**: Identifies potentially malicious file uploads.
- **Potential Injection Attacks**: Detects SQL injection, command injection, and XSS attempts.

### Example Usage

```python
from core.intrusion_detection import track_security_event, EventType

# Track a security event
track_security_event(
    event_type=EventType.LOGIN_FAILURE,
    user_id="user123",
    ip_address="192.168.1.100",
    details={"reason": "invalid_password"}
)
```

## Audit Trails

The audit trail system tracks all security-relevant actions in the application. It is implemented in `core/audit_trail.py` with database models in `db/audit_models.py`.

### Key Features

- **Comprehensive Tracking**: Records all security-relevant actions including who, what, when, and where.
- **Change Tracking**: Records specific changes made to resources, including old and new values.
- **Immutable Records**: Audit records cannot be modified once created.
- **Sensitive Data Handling**: Automatically identifies and protects sensitive fields.
- **Query Capabilities**: Flexible querying by user, action type, resource type, and time range.
- **Export Capabilities**: Export audit data for compliance reporting.

### Example Usage

```python
from core.audit_trail import create_audit_record, AuditActionType, AuditResourceType

# Create an audit record
create_audit_record(
    action_type=AuditActionType.UPDATE,
    resource_type=AuditResourceType.USER,
    user_id="admin123",
    resource_id="user456",
    ip_address="192.168.1.100",
    status="success",
    changes=[
        {
            "field_name": "role",
            "old_value": "user",
            "new_value": "admin"
        }
    ]
)
```

## Security Monitoring

The security monitoring system provides real-time visibility into security events and alerts. It includes:

- **Security Event Monitoring**: Real-time tracking of security events.
- **Suspicious Activity Alerts**: Alerts for potential security threats.
- **Security Incident Tracking**: Management of security incidents from detection to resolution.
- **Security Dashboards**: Visualization of security metrics and events.

## Integration with Prometheus and Grafana

The security metrics are exposed via a Prometheus endpoint at `/api/v1/metrics` and can be visualized using Grafana.

### Grafana Dashboard

A pre-configured Grafana dashboard is available in `monitoring/grafana/security_dashboard.json`. It includes panels for:

- **Authentication Metrics**: Success/failure rates, latency.
- **Access Control Metrics**: Access denied rates, permission check latency.
- **Rate Limiting Metrics**: Rate limit exceeded events.
- **Suspicious Activity Metrics**: Activity by severity.
- **File Scanning Metrics**: Rejected files by reason.

## Security Baselines

Security baselines provide a reference point for detecting changes in the security posture of the application. The baseline generator is implemented in `backend/scripts/generate_security_baseline.py`.

### Baseline Contents

- **System Information**: Hostname, platform, Python version.
- **Security Settings**: Authentication, rate limiting, encryption, logging, CORS, security headers.
- **Database Security**: Encrypted fields, audit records, security incidents.
- **API Security**: Endpoints, protection, rate limiting.

### Usage

```bash
# Generate a baseline
python backend/scripts/generate_security_baseline.py --output security_baseline.json

# Compare with a previous baseline
python backend/scripts/generate_security_baseline.py --compare previous_baseline.json
```

## API Endpoints

The security monitoring system exposes the following API endpoints:

### Audit API

- `GET /api/v1/audit/records`: Get audit records matching specified criteria.
- `GET /api/v1/audit/records/{record_id}`: Get a specific audit record.
- `GET /api/v1/audit/statistics`: Get statistics about audit records.
- `GET /api/v1/audit/export`: Export audit records to JSON or CSV.

### Security Monitoring API

- `GET /api/v1/security/events`: Get recent security events.
- `GET /api/v1/security/suspicious/ips`: Get suspicious IP addresses.
- `GET /api/v1/security/suspicious/users`: Get suspicious users.
- `GET /api/v1/security/incidents`: Get security incidents.
- `GET /api/v1/security/statistics`: Get security statistics.
- `POST /api/v1/security/incidents/{incident_id}/assign`: Assign a security incident.
- `POST /api/v1/security/incidents/{incident_id}/resolve`: Resolve a security incident.

### Metrics API

- `GET /api/v1/metrics`: Get application metrics in Prometheus format.
- `GET /api/v1/metrics/security`: Get security-specific metrics in Prometheus format.

## Configuration

The security logging and monitoring system can be configured through environment variables and configuration files.

### Environment Variables

- `SECURITY_LOG_DIR`: Directory for security logs (default: "logs/security").
- `PROMETHEUS_MULTIPROC_DIR`: Directory for Prometheus multiprocess mode.
- `ENVIRONMENT`: Application environment (development, production).

### Configuration Files

- `config.py`: Main configuration file for the application.
- `logging.conf`: Configuration for the logging system.

## Best Practices

1. **Regular Monitoring**: Regularly review security logs, metrics, and alerts.
2. **Baseline Comparison**: Compare security baselines to detect changes in the security posture.
3. **Incident Response**: Establish procedures for responding to security incidents.
4. **Log Retention**: Implement appropriate log retention policies.
5. **Access Control**: Restrict access to security logs and metrics to authorized personnel.
6. **Regular Testing**: Test the security monitoring system to ensure it is functioning correctly. 