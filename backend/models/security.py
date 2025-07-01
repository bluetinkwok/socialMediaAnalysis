"""
Security Metrics Module

This module provides metrics collection for security-related events using Prometheus.
It tracks various security metrics that can be exposed via an HTTP endpoint and
monitored by Prometheus or other compatible monitoring systems.
"""

import time
from typing import Dict, List, Optional, Set

from prometheus_client import Counter, Gauge, Histogram, Summary

# Authentication metrics
AUTH_SUCCESS = Counter(
    'security_auth_success_total',
    'Total number of successful authentication attempts',
    ['user_type', 'auth_method']
)

AUTH_FAILURE = Counter(
    'security_auth_failure_total',
    'Total number of failed authentication attempts',
    ['reason', 'auth_method']
)

AUTH_LATENCY = Histogram(
    'security_auth_latency_seconds',
    'Authentication request latency in seconds',
    ['auth_method', 'success'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10)
)

# Access control metrics
ACCESS_DENIED = Counter(
    'security_access_denied_total',
    'Total number of access denied events',
    ['resource_type', 'action']
)

PERMISSION_CHECK_LATENCY = Histogram(
    'security_permission_check_latency_seconds',
    'Permission check latency in seconds',
    ['resource_type', 'action'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5)
)

# Rate limiting metrics
RATE_LIMIT_EXCEEDED = Counter(
    'security_rate_limit_exceeded_total',
    'Total number of rate limit exceeded events',
    ['endpoint', 'limit_type']
)

RATE_LIMIT_CURRENT = Gauge(
    'security_rate_limit_current',
    'Current rate limit usage',
    ['endpoint', 'limit_type']
)

# Input validation metrics
INPUT_VALIDATION_FAILURE = Counter(
    'security_input_validation_failure_total',
    'Total number of input validation failures',
    ['validation_type', 'endpoint']
)

# Suspicious activity metrics
SUSPICIOUS_ACTIVITY = Counter(
    'security_suspicious_activity_total',
    'Total number of suspicious activity events',
    ['event_type', 'severity']
)

# File scanning metrics
FILE_SCAN_TOTAL = Counter(
    'security_file_scan_total',
    'Total number of file scans performed',
    ['file_type', 'scan_type']
)

FILE_SCAN_REJECTED = Counter(
    'security_file_scan_rejected_total',
    'Total number of files rejected by security scans',
    ['file_type', 'rejection_reason']
)

FILE_SCAN_LATENCY = Histogram(
    'security_file_scan_latency_seconds',
    'File scanning latency in seconds',
    ['file_type', 'scan_type'],
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120)
)

# Session metrics
ACTIVE_SESSIONS = Gauge(
    'security_active_sessions',
    'Number of currently active sessions',
    ['user_type']
)

SESSION_EXPIRED = Counter(
    'security_session_expired_total',
    'Total number of expired sessions',
    ['expiry_reason']
)

# API security metrics
API_SECURITY_HEADERS_MISSING = Counter(
    'security_api_headers_missing_total',
    'Total number of requests with missing security headers',
    ['header_name']
)

# Database security metrics
DB_ENCRYPTION_OPERATIONS = Counter(
    'security_db_encryption_operations_total',
    'Total number of database encryption/decryption operations',
    ['operation_type']
)

DB_ENCRYPTION_LATENCY = Histogram(
    'security_db_encryption_latency_seconds',
    'Database encryption/decryption latency in seconds',
    ['operation_type'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5)
)

# Privacy metrics
PRIVACY_CONSENT_CHANGES = Counter(
    'security_privacy_consent_changes_total',
    'Total number of privacy consent changes',
    ['consent_type', 'change_type']
)

DATA_EXPORT_REQUESTS = Counter(
    'security_data_export_requests_total',
    'Total number of data export requests',
    ['request_type']
)

DATA_DELETION_REQUESTS = Counter(
    'security_data_deletion_requests_total',
    'Total number of data deletion requests',
    ['request_type']
)


class SecurityMetrics:
    """
    Helper class for tracking security metrics in the application.
    Provides convenience methods for common security metric operations.
    """

    @staticmethod
    def track_auth_attempt(auth_method: str, success: bool, user_type: str = "standard", 
                          failure_reason: Optional[str] = None) -> None:
        """
        Track an authentication attempt.
        
        Args:
            auth_method: Authentication method used (password, oauth, token, etc.)
            success: Whether authentication was successful
            user_type: Type of user (standard, admin, api, etc.)
            failure_reason: Reason for failure if authentication failed
        """
        start_time = time.time()
        
        if success:
            AUTH_SUCCESS.labels(user_type=user_type, auth_method=auth_method).inc()
        else:
            reason = failure_reason or "unknown"
            AUTH_FAILURE.labels(reason=reason, auth_method=auth_method).inc()
        
        # Track latency
        latency = time.time() - start_time
        AUTH_LATENCY.labels(auth_method=auth_method, success=str(success)).observe(latency)

    @staticmethod
    def track_access_control(resource_type: str, action: str, allowed: bool, 
                            latency: Optional[float] = None) -> None:
        """
        Track an access control decision.
        
        Args:
            resource_type: Type of resource being accessed
            action: Action being performed (read, write, delete, etc.)
            allowed: Whether access was allowed
            latency: Optional pre-calculated latency
        """
        if not allowed:
            ACCESS_DENIED.labels(resource_type=resource_type, action=action).inc()
        
        if latency is not None:
            PERMISSION_CHECK_LATENCY.labels(resource_type=resource_type, action=action).observe(latency)

    @staticmethod
    def track_rate_limit(endpoint: str, limit_type: str, exceeded: bool, current_usage: float) -> None:
        """
        Track rate limit metrics.
        
        Args:
            endpoint: API endpoint or resource being rate limited
            limit_type: Type of rate limit (requests_per_minute, etc.)
            exceeded: Whether the rate limit was exceeded
            current_usage: Current usage as a percentage of the limit
        """
        if exceeded:
            RATE_LIMIT_EXCEEDED.labels(endpoint=endpoint, limit_type=limit_type).inc()
        
        RATE_LIMIT_CURRENT.labels(endpoint=endpoint, limit_type=limit_type).set(current_usage)

    @staticmethod
    def track_input_validation(validation_type: str, endpoint: str, passed: bool) -> None:
        """
        Track input validation results.
        
        Args:
            validation_type: Type of validation (schema, sanitization, etc.)
            endpoint: API endpoint where validation occurred
            passed: Whether validation passed
        """
        if not passed:
            INPUT_VALIDATION_FAILURE.labels(validation_type=validation_type, endpoint=endpoint).inc()

    @staticmethod
    def track_suspicious_activity(event_type: str, severity: str) -> None:
        """
        Track suspicious activity detection.
        
        Args:
            event_type: Type of suspicious activity
            severity: Severity level (low, medium, high, critical)
        """
        SUSPICIOUS_ACTIVITY.labels(event_type=event_type, severity=severity).inc()

    @staticmethod
    def track_file_scan(file_type: str, scan_type: str, rejected: bool, 
                       rejection_reason: Optional[str] = None, latency: Optional[float] = None) -> None:
        """
        Track file security scanning.
        
        Args:
            file_type: Type of file being scanned
            scan_type: Type of scan performed
            rejected: Whether the file was rejected
            rejection_reason: Reason for rejection if rejected
            latency: Optional pre-calculated latency
        """
        FILE_SCAN_TOTAL.labels(file_type=file_type, scan_type=scan_type).inc()
        
        if rejected and rejection_reason:
            FILE_SCAN_REJECTED.labels(file_type=file_type, rejection_reason=rejection_reason).inc()
        
        if latency is not None:
            FILE_SCAN_LATENCY.labels(file_type=file_type, scan_type=scan_type).observe(latency)

    @staticmethod
    def update_session_count(user_type: str, count: int) -> None:
        """
        Update the count of active sessions.
        
        Args:
            user_type: Type of user (standard, admin, api, etc.)
            count: Current count of active sessions
        """
        ACTIVE_SESSIONS.labels(user_type=user_type).set(count)

    @staticmethod
    def track_session_expired(reason: str) -> None:
        """
        Track a session expiration event.
        
        Args:
            reason: Reason for session expiration (timeout, logout, revoked, etc.)
        """
        SESSION_EXPIRED.labels(expiry_reason=reason).inc()

    @staticmethod
    def track_missing_security_header(header_name: str) -> None:
        """
        Track a missing security header in an API request.
        
        Args:
            header_name: Name of the missing security header
        """
        API_SECURITY_HEADERS_MISSING.labels(header_name=header_name).inc()

    @staticmethod
    def track_db_encryption_operation(operation_type: str, latency: Optional[float] = None) -> None:
        """
        Track a database encryption operation.
        
        Args:
            operation_type: Type of operation (encrypt, decrypt)
            latency: Optional pre-calculated latency
        """
        DB_ENCRYPTION_OPERATIONS.labels(operation_type=operation_type).inc()
        
        if latency is not None:
            DB_ENCRYPTION_LATENCY.labels(operation_type=operation_type).observe(latency)

    @staticmethod
    def track_privacy_consent_change(consent_type: str, change_type: str) -> None:
        """
        Track a privacy consent change.
        
        Args:
            consent_type: Type of consent (marketing, analytics, etc.)
            change_type: Type of change (granted, revoked, updated)
        """
        PRIVACY_CONSENT_CHANGES.labels(consent_type=consent_type, change_type=change_type).inc()

    @staticmethod
    def track_data_export_request(request_type: str) -> None:
        """
        Track a data export request.
        
        Args:
            request_type: Type of export request (gdpr, download, etc.)
        """
        DATA_EXPORT_REQUESTS.labels(request_type=request_type).inc()

    @staticmethod
    def track_data_deletion_request(request_type: str) -> None:
        """
        Track a data deletion request.
        
        Args:
            request_type: Type of deletion request (gdpr, account_closure, etc.)
        """
        DATA_DELETION_REQUESTS.labels(request_type=request_type).inc() 