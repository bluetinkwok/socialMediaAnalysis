"""
Security Logger

This module provides security logging functionality.
"""

import os
import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SecurityLogger:
    """Security event logger"""
    
    def __init__(self, log_path: str):
        """
        Initialize the security logger.
        
        Args:
            log_path: Path to the security log file
        """
        self.log_path = log_path
        
        # Ensure log directory exists
        log_dir = os.path.dirname(log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    async def log_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """
        Log a security event.
        
        Args:
            event_type: Type of security event
            event_data: Event data
        """
        try:
            # Create log entry
            timestamp = datetime.now().isoformat()
            log_entry = {
                "timestamp": timestamp,
                "event_type": event_type,
                "data": event_data
            }
            
            # Convert to JSON string
            log_json = json.dumps(log_entry)
            
            # Append to log file
            async with asyncio.Lock():
                with open(self.log_path, "a") as f:
                    f.write(log_json + "\n")
                    
            # Also log to application logger
            logger.info(f"Security event: {event_type} - {timestamp}")
            
        except Exception as e:
            logger.error(f"Error logging security event: {str(e)}")
    
    async def get_events(self, event_type: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent security events from the log file.
        
        Args:
            event_type: Optional filter for event type
            limit: Maximum number of events to return
            
        Returns:
            List of security events
        """
        try:
            events = []
            
            # Check if log file exists
            if not os.path.exists(self.log_path):
                return []
            
            # Read log file
            with open(self.log_path, "r") as f:
                # Read from the end of the file to get the most recent events
                lines = f.readlines()
                
                # Process lines from newest to oldest
                for line in reversed(lines):
                    if not line.strip():
                        continue
                    
                    try:
                        event = json.loads(line)
                        
                        # Filter by event type if specified
                        if event_type and event.get("event_type") != event_type:
                            continue
                        
                        events.append(event)
                        
                        # Check limit
                        if len(events) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in security log: {line}")
            
            return events
            
        except Exception as e:
            logger.error(f"Error reading security events: {str(e)}")
            return []
