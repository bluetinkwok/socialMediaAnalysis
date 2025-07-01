"""
Security Logger Module

This module provides a structured logging system for security-related events
in the application. It uses structlog and python-json-logger to create
consistent, structured logs that can be easily parsed and analyzed.
"""

import logging
import logging.config
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, Optional, Union

import structlog
from pythonjsonlogger import jsonlogger

# Configure log directory
LOG_DIR = os.environ.get("SECURITY_LOG_DIR", "logs/security")
os.makedirs(LOG_DIR, exist_ok=True)

# Security log levels
SECURITY_LEVELS = {
    "CRITICAL": 50,  # Security breach or attack detected
    "HIGH": 45,      # Serious security concern
    "MEDIUM": 35,    # Notable security event
    "LOW": 25,       # Minor security event
    "INFO": 20,      # Informational security event
    "DEBUG": 10      # Debug information
}

# Add custom log levels to logging
for level_name, level_value in SECURITY_LEVELS.items():
    if not hasattr(logging, level_name):
        logging.addLevelName(level_value, level_name)


class SecurityLogger:
    """
    Security logger for tracking security-related events in the application.
    Provides structured logging with consistent fields and formats.
    """

    def __init__(self, app_name: str = "social-media-analyzer"):
        """
        Initialize the security logger.
        
        Args:
            app_name: Name of the application for log identification
        """
        self.app_name = app_name
        self._configure_logging()
        self.logger = structlog.get_logger(app_name)

    def _configure_logging(self) -> None:
        """Configure structured logging with JSON formatting"""
        # Create formatters
        json_formatter = jsonlogger.JsonFormatter(
            fmt="%(timestamp)s %(level)s %(name)s %(message)s",
            timestamp=True
        )
        
        # Configure handlers
        file_handler = logging.FileHandler(
            os.path.join(LOG_DIR, f"security_{datetime.now().strftime('%Y-%m-%d')}.log")
        )
        file_handler.setFormatter(json_formatter)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        
        # Only add console handler in development
        if os.environ.get("ENVIRONMENT", "development") == "development":
            root_logger.addHandler(console_handler)
        
        # Configure structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    def _log(self, level: int, event: str, **kwargs) -> None:
        """
        Log a security event with the specified level and additional context.
        
        Args:
            level: Log level (use SECURITY_LEVELS constants)
            event: Event name or description
            **kwargs: Additional context fields to include in the log
        """
        # Add standard fields
        context = {
            "timestamp": datetime.utcnow().isoformat(),
            "app": self.app_name,
            "event_type": "security",
        }
        
        # Add custom fields
        context.update(kwargs)
        
        # Log the event
        self.logger.log(level, event, **context)

    def critical(self, event: str, **kwargs) -> None:
        """
        Log a critical security event (security breach or attack).
        
        Args:
            event: Event description
            **kwargs: Additional context
        """
        self._log(SECURITY_LEVELS["CRITICAL"], event, **kwargs)

    def high(self, event: str, **kwargs) -> None:
        """
        Log a high-severity security event.
        
        Args:
            event: Event description
            **kwargs: Additional context
        """
        self._log(SECURITY_LEVELS["HIGH"], event, **kwargs)

    def medium(self, event: str, **kwargs) -> None:
        """
        Log a medium-severity security event.
        
        Args:
            event: Event description
            **kwargs: Additional context
        """
        self._log(SECURITY_LEVELS["MEDIUM"], event, **kwargs)

    def low(self, event: str, **kwargs) -> None:
        """
        Log a low-severity security event.
        
        Args:
            event: Event description
            **kwargs: Additional context
        """
        self._log(SECURITY_LEVELS["LOW"], event, **kwargs)

    def info(self, event: str, **kwargs) -> None:
        """
        Log an informational security event.
        
        Args:
            event: Event description
            **kwargs: Additional context
        """
        self._log(SECURITY_LEVELS["INFO"], event, **kwargs)

    def debug(self, event: str, **kwargs) -> None:
        """
        Log a debug-level security event.
        
        Args:
            event: Event description
            **kwargs: Additional context
        """
        self._log(SECURITY_LEVELS["DEBUG"], event, **kwargs)

    def auth_success(self, user_id: str, ip_address: str, **kwargs) -> None:
        """
        Log a successful authentication event.
        
        Args:
            user_id: ID of the authenticated user
            ip_address: IP address of the client
            **kwargs: Additional context
        """
        self._log(
            SECURITY_LEVELS["INFO"],
            "Authentication successful",
            user_id=user_id,
            ip_address=ip_address,
            auth_event="success",
            **kwargs
        )

    def auth_failure(self, username: str, ip_address: str, reason: str, **kwargs) -> None:
        """
        Log a failed authentication event.
        
        Args:
            username: Username that failed authentication
            ip_address: IP address of the client
            reason: Reason for authentication failure
            **kwargs: Additional context
        """
        self._log(
            SECURITY_LEVELS["MEDIUM"],
            "Authentication failed",
            username=username,
            ip_address=ip_address,
            auth_event="failure",
            reason=reason,
            **kwargs
        )

    def permission_denied(self, user_id: str, resource: str, action: str, ip_address: str, **kwargs) -> None:
        """
        Log a permission denied event.
        
        Args:
            user_id: ID of the user
            resource: Resource that was accessed
            action: Action that was attempted
            ip_address: IP address of the client
            **kwargs: Additional context
        """
        self._log(
            SECURITY_LEVELS["MEDIUM"],
            "Permission denied",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            **kwargs
        )

    def resource_access(self, user_id: str, resource: str, action: str, ip_address: str, **kwargs) -> None:
        """
        Log a resource access event.
        
        Args:
            user_id: ID of the user
            resource: Resource that was accessed
            action: Action that was performed
            ip_address: IP address of the client
            **kwargs: Additional context
        """
        self._log(
            SECURITY_LEVELS["INFO"],
            "Resource accessed",
            user_id=user_id,
            resource=resource,
            action=action,
            ip_address=ip_address,
            **kwargs
        )

    def security_config_change(self, user_id: str, setting: str, old_value: Any, new_value: Any, **kwargs) -> None:
        """
        Log a security configuration change event.
        
        Args:
            user_id: ID of the user making the change
            setting: Setting that was changed
            old_value: Previous value
            new_value: New value
            **kwargs: Additional context
        """
        self._log(
            SECURITY_LEVELS["HIGH"],
            "Security configuration changed",
            user_id=user_id,
            setting=setting,
            old_value=str(old_value),
            new_value=str(new_value),
            **kwargs
        )

    def suspicious_activity(self, event_type: str, severity: str, details: Dict[str, Any], **kwargs) -> None:
        """
        Log a suspicious activity event.
        
        Args:
            event_type: Type of suspicious activity
            severity: Severity level (low, medium, high, critical)
            details: Details about the suspicious activity
            **kwargs: Additional context
        """
        level = SECURITY_LEVELS.get(severity.upper(), SECURITY_LEVELS["MEDIUM"])
        self._log(
            level,
            f"Suspicious activity: {event_type}",
            event_type=event_type,
            severity=severity,
            details=details,
            **kwargs
        )


# Create a global instance of the security logger
security_logger = SecurityLogger()


# Add convenience methods to access the global logger
def critical(event: str, **kwargs) -> None:
    """Log a critical security event"""
    security_logger.critical(event, **kwargs)


def high(event: str, **kwargs) -> None:
    """Log a high-severity security event"""
    security_logger.high(event, **kwargs)


def medium(event: str, **kwargs) -> None:
    """Log a medium-severity security event"""
    security_logger.medium(event, **kwargs)


def low(event: str, **kwargs) -> None:
    """Log a low-severity security event"""
    security_logger.low(event, **kwargs)


def info(event: str, **kwargs) -> None:
    """Log an informational security event"""
    security_logger.info(event, **kwargs)


def debug(event: str, **kwargs) -> None:
    """Log a debug-level security event"""
    security_logger.debug(event, **kwargs)


def auth_success(user_id: str, ip_address: str, **kwargs) -> None:
    """Log a successful authentication event"""
    security_logger.auth_success(user_id, ip_address, **kwargs)


def auth_failure(username: str, ip_address: str, reason: str, **kwargs) -> None:
    """Log a failed authentication event"""
    security_logger.auth_failure(username, ip_address, reason, **kwargs)


def permission_denied(user_id: str, resource: str, action: str, ip_address: str, **kwargs) -> None:
    """Log a permission denied event"""
    security_logger.permission_denied(user_id, resource, action, ip_address, **kwargs)


def resource_access(user_id: str, resource: str, action: str, ip_address: str, **kwargs) -> None:
    """Log a resource access event"""
    security_logger.resource_access(user_id, resource, action, ip_address, **kwargs)


def security_config_change(user_id: str, setting: str, old_value: Any, new_value: Any, **kwargs) -> None:
    """Log a security configuration change event"""
    security_logger.security_config_change(user_id, setting, old_value, new_value, **kwargs)


def suspicious_activity(event_type: str, severity: str, details: Dict[str, Any], **kwargs) -> None:
    """Log a suspicious activity event"""
    security_logger.suspicious_activity(event_type, severity, details, **kwargs) 