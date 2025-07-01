"""
Intrusion Detection System Module

This module provides intrusion detection capabilities for identifying potential
security threats and suspicious activities in the application. It includes
rules for detecting unusual patterns and a mechanism to track and correlate
events across different parts of the application.
"""

import datetime
import ipaddress
import time
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Union

from core.security_logger import security_logger
from models.security import SecurityMetrics


class SuspiciousActivityType(str, Enum):
    """Types of suspicious activities that can be detected."""
    BRUTE_FORCE = "brute_force"
    UNUSUAL_LOGIN_TIME = "unusual_login_time"
    UNUSUAL_LOCATION = "unusual_location"
    EXCESSIVE_REQUESTS = "excessive_requests"
    UNUSUAL_ACCESS_PATTERN = "unusual_access_pattern"
    POTENTIAL_DATA_EXFILTRATION = "potential_data_exfiltration"
    POTENTIAL_INJECTION = "potential_injection"
    POTENTIAL_XSS = "potential_xss"
    POTENTIAL_CSRF = "potential_csrf"
    UNUSUAL_FILE_UPLOAD = "unusual_file_upload"
    UNUSUAL_API_USAGE = "unusual_api_usage"


class SeverityLevel(str, Enum):
    """Severity levels for suspicious activities."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Types of security events that can be tracked."""
    LOGIN_ATTEMPT = "login_attempt"
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    PASSWORD_CHANGE = "password_change"
    PERMISSION_CHANGE = "permission_change"
    ACCESS_SENSITIVE_RESOURCE = "access_sensitive_resource"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"
    API_REQUEST = "api_request"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INPUT_VALIDATION_FAILURE = "input_validation_failure"
    SECURITY_CONFIG_CHANGE = "security_config_change"


class SecurityEvent:
    """
    Represents a security event in the application.
    
    This class stores information about security events that can be
    analyzed for potential intrusions or suspicious activities.
    """
    
    def __init__(
        self,
        event_type: EventType,
        user_id: Optional[str],
        ip_address: str,
        timestamp: Optional[datetime.datetime] = None,
        details: Optional[Dict] = None
    ):
        """
        Initialize a security event.
        
        Args:
            event_type: Type of security event
            user_id: ID of the user associated with the event (if any)
            ip_address: IP address associated with the event
            timestamp: Time when the event occurred (defaults to now)
            details: Additional details about the event
        """
        self.event_type = event_type
        self.user_id = user_id
        self.ip_address = ip_address
        self.timestamp = timestamp or datetime.datetime.utcnow()
        self.details = details or {}
    
    def to_dict(self) -> Dict:
        """
        Convert the event to a dictionary.
        
        Returns:
            Dictionary representation of the event
        """
        return {
            "event_type": self.event_type,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "timestamp": self.timestamp.isoformat(),
            "details": self.details
        }


class IntrusionDetectionSystem:
    """
    Intrusion Detection System for identifying suspicious activities.
    
    This class provides methods for tracking security events and
    detecting potential intrusions based on predefined rules.
    """
    
    def __init__(
        self,
        login_failure_threshold: int = 5,
        login_failure_window: int = 300,  # 5 minutes
        request_rate_threshold: int = 100,
        request_rate_window: int = 60,  # 1 minute
        sensitive_data_threshold: int = 10,
        sensitive_data_window: int = 60  # 1 minute
    ):
        """
        Initialize the intrusion detection system.
        
        Args:
            login_failure_threshold: Number of login failures to trigger an alert
            login_failure_window: Time window for login failures in seconds
            request_rate_threshold: Number of requests to trigger an alert
            request_rate_window: Time window for request rate in seconds
            sensitive_data_threshold: Number of sensitive data accesses to trigger an alert
            sensitive_data_window: Time window for sensitive data accesses in seconds
        """
        self.login_failure_threshold = login_failure_threshold
        self.login_failure_window = login_failure_window
        self.request_rate_threshold = request_rate_threshold
        self.request_rate_window = request_rate_window
        self.sensitive_data_threshold = sensitive_data_threshold
        self.sensitive_data_window = sensitive_data_window
        
        # Event storage
        self.events: List[SecurityEvent] = []
        self.max_events = 10000  # Maximum number of events to store
        
        # Tracking dictionaries
        self.login_failures: Dict[str, List[datetime.datetime]] = {}  # IP -> timestamps
        self.requests: Dict[str, List[datetime.datetime]] = {}  # IP -> timestamps
        self.sensitive_data_accesses: Dict[str, List[datetime.datetime]] = {}  # User ID -> timestamps
        self.blocked_ips: Set[str] = set()
        self.suspicious_ips: Dict[str, int] = {}  # IP -> suspicion score
        self.suspicious_users: Dict[str, int] = {}  # User ID -> suspicion score
        
        # Known patterns
        self.normal_login_hours = set(range(7, 20))  # 7 AM to 8 PM
        self.known_locations: Dict[str, Set[str]] = {}  # User ID -> set of IP subnets
    
    def track_event(self, event: SecurityEvent) -> None:
        """
        Track a security event and check for suspicious activities.
        
        Args:
            event: Security event to track
        """
        # Store the event
        self.events.append(event)
        
        # Trim events if necessary
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Check for suspicious activities based on the event type
        if event.event_type == EventType.LOGIN_FAILURE:
            self._check_login_failures(event)
        elif event.event_type == EventType.LOGIN_SUCCESS:
            self._check_unusual_login(event)
        elif event.event_type == EventType.API_REQUEST:
            self._check_request_rate(event)
        elif event.event_type == EventType.ACCESS_SENSITIVE_RESOURCE:
            self._check_sensitive_data_access(event)
        elif event.event_type == EventType.FILE_UPLOAD:
            self._check_unusual_file_upload(event)
        elif event.event_type == EventType.INPUT_VALIDATION_FAILURE:
            self._check_potential_injection(event)
    
    def _check_login_failures(self, event: SecurityEvent) -> None:
        """
        Check for brute force login attempts.
        
        Args:
            event: Login failure event
        """
        ip = event.ip_address
        now = event.timestamp
        
        # Initialize if needed
        if ip not in self.login_failures:
            self.login_failures[ip] = []
        
        # Add the current timestamp
        self.login_failures[ip].append(now)
        
        # Remove old timestamps
        window_start = now - datetime.timedelta(seconds=self.login_failure_window)
        self.login_failures[ip] = [ts for ts in self.login_failures[ip] if ts >= window_start]
        
        # Check if threshold is exceeded
        if len(self.login_failures[ip]) >= self.login_failure_threshold:
            self._report_suspicious_activity(
                SuspiciousActivityType.BRUTE_FORCE,
                SeverityLevel.HIGH,
                ip=ip,
                user_id=event.user_id,
                details={
                    "login_failures": len(self.login_failures[ip]),
                    "window_seconds": self.login_failure_window
                }
            )
            
            # Block the IP
            self.blocked_ips.add(ip)
            
            # Increase suspicion score
            self.suspicious_ips[ip] = self.suspicious_ips.get(ip, 0) + 10
    
    def _check_unusual_login(self, event: SecurityEvent) -> None:
        """
        Check for unusual login patterns.
        
        Args:
            event: Login success event
        """
        ip = event.ip_address
        user_id = event.user_id
        now = event.timestamp
        
        if not user_id:
            return
        
        # Check login time
        hour = now.hour
        if hour not in self.normal_login_hours:
            self._report_suspicious_activity(
                SuspiciousActivityType.UNUSUAL_LOGIN_TIME,
                SeverityLevel.MEDIUM,
                ip=ip,
                user_id=user_id,
                details={
                    "login_hour": hour,
                    "normal_hours": f"{min(self.normal_login_hours)}-{max(self.normal_login_hours)}"
                }
            )
            
            # Increase suspicion score
            self.suspicious_users[user_id] = self.suspicious_users.get(user_id, 0) + 5
        
        # Check login location
        if user_id in self.known_locations:
            ip_obj = ipaddress.ip_address(ip)
            known_subnets = self.known_locations[user_id]
            
            if not any(ip_obj in ipaddress.ip_network(subnet) for subnet in known_subnets):
                self._report_suspicious_activity(
                    SuspiciousActivityType.UNUSUAL_LOCATION,
                    SeverityLevel.HIGH,
                    ip=ip,
                    user_id=user_id,
                    details={
                        "ip": ip,
                        "known_subnets": list(known_subnets)
                    }
                )
                
                # Increase suspicion score
                self.suspicious_users[user_id] = self.suspicious_users.get(user_id, 0) + 8
    
    def _check_request_rate(self, event: SecurityEvent) -> None:
        """
        Check for excessive request rates.
        
        Args:
            event: API request event
        """
        ip = event.ip_address
        now = event.timestamp
        
        # Initialize if needed
        if ip not in self.requests:
            self.requests[ip] = []
        
        # Add the current timestamp
        self.requests[ip].append(now)
        
        # Remove old timestamps
        window_start = now - datetime.timedelta(seconds=self.request_rate_window)
        self.requests[ip] = [ts for ts in self.requests[ip] if ts >= window_start]
        
        # Check if threshold is exceeded
        if len(self.requests[ip]) >= self.request_rate_threshold:
            self._report_suspicious_activity(
                SuspiciousActivityType.EXCESSIVE_REQUESTS,
                SeverityLevel.MEDIUM,
                ip=ip,
                user_id=event.user_id,
                details={
                    "request_count": len(self.requests[ip]),
                    "window_seconds": self.request_rate_window,
                    "endpoint": event.details.get("endpoint", "unknown")
                }
            )
            
            # Increase suspicion score
            self.suspicious_ips[ip] = self.suspicious_ips.get(ip, 0) + 6
    
    def _check_sensitive_data_access(self, event: SecurityEvent) -> None:
        """
        Check for unusual sensitive data access patterns.
        
        Args:
            event: Sensitive data access event
        """
        user_id = event.user_id
        now = event.timestamp
        
        if not user_id:
            return
        
        # Initialize if needed
        if user_id not in self.sensitive_data_accesses:
            self.sensitive_data_accesses[user_id] = []
        
        # Add the current timestamp
        self.sensitive_data_accesses[user_id].append(now)
        
        # Remove old timestamps
        window_start = now - datetime.timedelta(seconds=self.sensitive_data_window)
        self.sensitive_data_accesses[user_id] = [
            ts for ts in self.sensitive_data_accesses[user_id] if ts >= window_start
        ]
        
        # Check if threshold is exceeded
        if len(self.sensitive_data_accesses[user_id]) >= self.sensitive_data_threshold:
            self._report_suspicious_activity(
                SuspiciousActivityType.POTENTIAL_DATA_EXFILTRATION,
                SeverityLevel.HIGH,
                ip=event.ip_address,
                user_id=user_id,
                details={
                    "access_count": len(self.sensitive_data_accesses[user_id]),
                    "window_seconds": self.sensitive_data_window,
                    "resource": event.details.get("resource", "unknown")
                }
            )
            
            # Increase suspicion score
            self.suspicious_users[user_id] = self.suspicious_users.get(user_id, 0) + 8
    
    def _check_unusual_file_upload(self, event: SecurityEvent) -> None:
        """
        Check for unusual file upload patterns.
        
        Args:
            event: File upload event
        """
        file_type = event.details.get("file_type", "unknown")
        file_size = event.details.get("file_size", 0)
        
        # Check for unusually large files
        if file_size > 10 * 1024 * 1024:  # 10 MB
            self._report_suspicious_activity(
                SuspiciousActivityType.UNUSUAL_FILE_UPLOAD,
                SeverityLevel.MEDIUM,
                ip=event.ip_address,
                user_id=event.user_id,
                details={
                    "file_type": file_type,
                    "file_size": file_size,
                    "file_name": event.details.get("file_name", "unknown")
                }
            )
            
            # Increase suspicion score
            if event.user_id:
                self.suspicious_users[event.user_id] = self.suspicious_users.get(event.user_id, 0) + 4
            self.suspicious_ips[event.ip_address] = self.suspicious_ips.get(event.ip_address, 0) + 4
    
    def _check_potential_injection(self, event: SecurityEvent) -> None:
        """
        Check for potential injection attacks.
        
        Args:
            event: Input validation failure event
        """
        validation_type = event.details.get("validation_type", "unknown")
        input_value = event.details.get("input_value", "")
        
        if validation_type in ["sql_injection", "command_injection", "xss"]:
            activity_type = {
                "sql_injection": SuspiciousActivityType.POTENTIAL_INJECTION,
                "command_injection": SuspiciousActivityType.POTENTIAL_INJECTION,
                "xss": SuspiciousActivityType.POTENTIAL_XSS
            }.get(validation_type, SuspiciousActivityType.POTENTIAL_INJECTION)
            
            self._report_suspicious_activity(
                activity_type,
                SeverityLevel.HIGH,
                ip=event.ip_address,
                user_id=event.user_id,
                details={
                    "validation_type": validation_type,
                    "input_value": input_value[:100],  # Truncate for safety
                    "endpoint": event.details.get("endpoint", "unknown")
                }
            )
            
            # Increase suspicion score
            self.suspicious_ips[event.ip_address] = self.suspicious_ips.get(event.ip_address, 0) + 9
            if event.user_id:
                self.suspicious_users[event.user_id] = self.suspicious_users.get(event.user_id, 0) + 9
    
    def _report_suspicious_activity(
        self,
        activity_type: SuspiciousActivityType,
        severity: SeverityLevel,
        ip: str,
        user_id: Optional[str] = None,
        details: Optional[Dict] = None
    ) -> None:
        """
        Report a suspicious activity.
        
        Args:
            activity_type: Type of suspicious activity
            severity: Severity level
            ip: IP address associated with the activity
            user_id: User ID associated with the activity (if any)
            details: Additional details about the activity
        """
        # Prepare details
        activity_details = details or {}
        activity_details.update({
            "activity_type": activity_type,
            "severity": severity,
            "ip_address": ip,
            "user_id": user_id,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })
        
        # Log the suspicious activity
        security_logger.suspicious_activity(
            activity_type,
            severity,
            activity_details
        )
        
        # Track metrics
        SecurityMetrics.track_suspicious_activity(
            event_type=activity_type,
            severity=severity
        )
    
    def is_ip_blocked(self, ip: str) -> bool:
        """
        Check if an IP address is blocked.
        
        Args:
            ip: IP address to check
            
        Returns:
            True if the IP is blocked, False otherwise
        """
        return ip in self.blocked_ips
    
    def get_user_suspicion_level(self, user_id: str) -> int:
        """
        Get the suspicion level for a user.
        
        Args:
            user_id: User ID to check
            
        Returns:
            Suspicion score (0-100)
        """
        return min(self.suspicious_users.get(user_id, 0), 100)
    
    def get_ip_suspicion_level(self, ip: str) -> int:
        """
        Get the suspicion level for an IP address.
        
        Args:
            ip: IP address to check
            
        Returns:
            Suspicion score (0-100)
        """
        return min(self.suspicious_ips.get(ip, 0), 100)
    
    def add_known_location(self, user_id: str, subnet: str) -> None:
        """
        Add a known location for a user.
        
        Args:
            user_id: User ID
            subnet: IP subnet in CIDR notation (e.g., "192.168.1.0/24")
        """
        if user_id not in self.known_locations:
            self.known_locations[user_id] = set()
        
        self.known_locations[user_id].add(subnet)
    
    def set_normal_login_hours(self, start_hour: int, end_hour: int) -> None:
        """
        Set the normal login hours.
        
        Args:
            start_hour: Start hour (0-23)
            end_hour: End hour (0-23)
        """
        self.normal_login_hours = set(range(start_hour, end_hour + 1))
    
    def get_recent_events(self, limit: int = 100) -> List[Dict]:
        """
        Get recent security events.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent events as dictionaries
        """
        return [event.to_dict() for event in self.events[-limit:]]
    
    def get_suspicious_ips(self, threshold: int = 5) -> Dict[str, int]:
        """
        Get suspicious IP addresses.
        
        Args:
            threshold: Minimum suspicion score to include
            
        Returns:
            Dictionary of suspicious IPs and their scores
        """
        return {ip: score for ip, score in self.suspicious_ips.items() if score >= threshold}
    
    def get_suspicious_users(self, threshold: int = 5) -> Dict[str, int]:
        """
        Get suspicious users.
        
        Args:
            threshold: Minimum suspicion score to include
            
        Returns:
            Dictionary of suspicious users and their scores
        """
        return {user: score for user, score in self.suspicious_users.items() if score >= threshold}


# Create a global instance of the intrusion detection system
intrusion_detection = IntrusionDetectionSystem()


def track_security_event(
    event_type: Union[EventType, str],
    user_id: Optional[str],
    ip_address: str,
    details: Optional[Dict] = None
) -> None:
    """
    Track a security event.
    
    Args:
        event_type: Type of security event
        user_id: ID of the user associated with the event (if any)
        ip_address: IP address associated with the event
        details: Additional details about the event
    """
    # Convert string to enum if needed
    if isinstance(event_type, str):
        event_type = EventType(event_type)
    
    # Create and track the event
    event = SecurityEvent(
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        details=details
    )
    
    intrusion_detection.track_event(event)


def is_ip_blocked(ip: str) -> bool:
    """
    Check if an IP address is blocked.
    
    Args:
        ip: IP address to check
        
    Returns:
        True if the IP is blocked, False otherwise
    """
    return intrusion_detection.is_ip_blocked(ip)


def get_user_suspicion_level(user_id: str) -> int:
    """
    Get the suspicion level for a user.
    
    Args:
        user_id: User ID to check
        
    Returns:
        Suspicion score (0-100)
    """
    return intrusion_detection.get_user_suspicion_level(user_id)


def get_ip_suspicion_level(ip: str) -> int:
    """
    Get the suspicion level for an IP address.
    
    Args:
        ip: IP address to check
        
    Returns:
        Suspicion score (0-100)
    """
    return intrusion_detection.get_ip_suspicion_level(ip)


def add_known_location(user_id: str, subnet: str) -> None:
    """
    Add a known location for a user.
    
    Args:
        user_id: User ID
        subnet: IP subnet in CIDR notation (e.g., "192.168.1.0/24")
    """
    intrusion_detection.add_known_location(user_id, subnet)


def set_normal_login_hours(start_hour: int, end_hour: int) -> None:
    """
    Set the normal login hours.
    
    Args:
        start_hour: Start hour (0-23)
        end_hour: End hour (0-23)
    """
    intrusion_detection.set_normal_login_hours(start_hour, end_hour)


def get_recent_events(limit: int = 100) -> List[Dict]:
    """
    Get recent security events.
    
    Args:
        limit: Maximum number of events to return
        
    Returns:
        List of recent events as dictionaries
    """
    return intrusion_detection.get_recent_events(limit)


def get_suspicious_ips(threshold: int = 5) -> Dict[str, int]:
    """
    Get suspicious IP addresses.
    
    Args:
        threshold: Minimum suspicion score to include
        
    Returns:
        Dictionary of suspicious IPs and their scores
    """
    return intrusion_detection.get_suspicious_ips(threshold)


def get_suspicious_users(threshold: int = 5) -> Dict[str, int]:
    """
    Get suspicious users.
    
    Args:
        threshold: Minimum suspicion score to include
        
    Returns:
        Dictionary of suspicious users and their scores
    """
    return intrusion_detection.get_suspicious_users(threshold) 