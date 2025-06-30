"""
Security Integrator

This module integrates all security components for file processing.
"""

import os
import logging
import asyncio
import json
from typing import Dict, Any, List, Tuple, Optional, Union
from datetime import datetime
from pathlib import Path
import time

from core.config import get_settings
from security.malware_scanner import malware_scanner
from security.pattern_analyzer import pattern_analyzer
from security.metadata_sanitizer import metadata_sanitizer
from security.content_filter import content_filter
from security.quarantine_manager import quarantine_manager

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

# Global security integrator instance
_security_integrator = None

class SecurityIntegrator:
    """
    Integrates all security components to provide a unified security interface.
    
    This class coordinates:
    - Malware scanning (ClamAV)
    - Pattern analysis (YARA rules)
    - Metadata sanitization
    - Content filtering
    - File quarantine management
    """
    
    def __init__(self):
        """Initialize the security integrator"""
        self.initialized = False
        self.components = {
            "malware_scanner": False,
            "pattern_analyzer": False,
            "metadata_sanitizer": False,
            "content_filter": False,
            "quarantine_manager": False
        }
        
    async def initialize(self) -> bool:
        """
        Initialize all security components.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing security integrator...")
            
            # Initialize malware scanner
            malware_scanner_ok = await malware_scanner.initialize()
            self.components["malware_scanner"] = malware_scanner_ok
            logger.info(f"Malware scanner initialized: {malware_scanner_ok}")
            
            # Initialize pattern analyzer
            pattern_analyzer_ok = await pattern_analyzer.initialize()
            self.components["pattern_analyzer"] = pattern_analyzer_ok
            logger.info(f"Pattern analyzer initialized: {pattern_analyzer_ok}")
            
            # Initialize metadata sanitizer
            metadata_sanitizer_ok = await metadata_sanitizer.initialize()
            self.components["metadata_sanitizer"] = metadata_sanitizer_ok
            logger.info(f"Metadata sanitizer initialized: {metadata_sanitizer_ok}")
            
            # Initialize content filter
            content_filter_ok = await content_filter.initialize()
            self.components["content_filter"] = content_filter_ok
            logger.info(f"Content filter initialized: {content_filter_ok}")
            
            # Initialize quarantine manager
            quarantine_manager_ok = quarantine_manager.initialize()
            self.components["quarantine_manager"] = quarantine_manager_ok
            logger.info(f"Quarantine manager initialized: {quarantine_manager_ok}")
            
            # Set initialized flag if at least one component is available
            self.initialized = any(self.components.values())
            
            logger.info(f"Security integrator initialized: {self.initialized}")
            return self.initialized
            
        except Exception as e:
            logger.error(f"Error initializing security integrator: {str(e)}")
            self.initialized = False
            return False
    
    async def scan_file(self, file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Scan a file with all available security components.
        
        Args:
            file_path: Path to the file to scan
            options: Optional configuration for the scan
                - skip_malware: Skip malware scanning
                - skip_patterns: Skip pattern analysis
                - skip_metadata: Skip metadata sanitization
                - skip_content: Skip content filtering
                - quarantine_failed: Automatically quarantine files that fail security checks
                
        Returns:
            Dict[str, Any]: Scan results
        """
        if not self.initialized:
            logger.warning("Security integrator not initialized")
            return {"error": "Security integrator not initialized", "secure": False}
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return {"error": "File not found", "secure": False}
        
        # Default options
        options = options or {}
        skip_malware = options.get("skip_malware", False)
        skip_patterns = options.get("skip_patterns", False)
        skip_metadata = options.get("skip_metadata", False)
        skip_content = options.get("skip_content", False)
        quarantine_failed = options.get("quarantine_failed", True)
        
        # Initialize results
        results = {
            "file_path": file_path,
            "filename": os.path.basename(file_path),
            "file_size": os.path.getsize(file_path),
            "scan_time": time.time(),
            "components": {},
            "secure": True,
            "actions_taken": []
        }
        
        try:
            # Scan with malware scanner
            if self.components["malware_scanner"] and not skip_malware:
                malware_clean, malware_results = await malware_scanner.scan_file(file_path)
                results["components"]["malware_scan"] = {
                    "clean": malware_clean,
                    "results": malware_results
                }
                
                if not malware_clean:
                    results["secure"] = False
                    
                    # Quarantine if requested
                    if quarantine_failed and self.components["quarantine_manager"]:
                        quarantine_success, quarantine_id = await self._quarantine_file(
                            file_path, 
                            "Malware detected", 
                            {"malware_results": malware_results}
                        )
                        if quarantine_success:
                            results["actions_taken"].append({
                                "action": "quarantined",
                                "reason": "malware_detected",
                                "quarantine_id": quarantine_id
                            })
            
            # Scan with pattern analyzer
            if self.components["pattern_analyzer"] and not skip_patterns:
                patterns_clean, patterns_results = await pattern_analyzer.scan_file(file_path)
                results["components"]["pattern_analysis"] = {
                    "clean": patterns_clean,
                    "results": patterns_results
                }
                
                if not patterns_clean:
                    results["secure"] = False
                    
                    # Quarantine if requested and not already quarantined
                    if quarantine_failed and self.components["quarantine_manager"] and not any(action.get("action") == "quarantined" for action in results["actions_taken"]):
                        quarantine_success, quarantine_id = await self._quarantine_file(
                            file_path, 
                            "Suspicious patterns detected", 
                            {"pattern_results": patterns_results}
                        )
                        if quarantine_success:
                            results["actions_taken"].append({
                                "action": "quarantined",
                                "reason": "suspicious_patterns",
                                "quarantine_id": quarantine_id
                            })
            
            # Process with metadata sanitizer
            if self.components["metadata_sanitizer"] and not skip_metadata:
                metadata_clean, metadata_results = await metadata_sanitizer.sanitize_file(file_path)
                results["components"]["metadata_sanitization"] = {
                    "clean": metadata_clean,
                    "results": metadata_results
                }
                
                if not metadata_clean and metadata_results.get("action") != "sanitized":
                    results["secure"] = False
                
                # If metadata was sanitized, record the action
                if metadata_results.get("action") == "sanitized":
                    results["actions_taken"].append({
                        "action": "sanitized",
                        "reason": "metadata_issues",
                        "details": metadata_results.get("issues", [])
                    })
            
            # Scan with content filter
            if self.components["content_filter"] and not skip_content:
                content_appropriate, content_results = await content_filter.filter_file(file_path)
                results["components"]["content_filtering"] = {
                    "appropriate": content_appropriate,
                    "results": content_results
                }
                
                if not content_appropriate:
                    results["secure"] = False
                    
                    # Quarantine if requested and not already quarantined
                    if quarantine_failed and self.components["quarantine_manager"] and not any(action.get("action") == "quarantined" for action in results["actions_taken"]):
                        quarantine_success, quarantine_id = await self._quarantine_file(
                            file_path, 
                            "Inappropriate content detected", 
                            {"content_results": content_results}
                        )
                        if quarantine_success:
                            results["actions_taken"].append({
                                "action": "quarantined",
                                "reason": "inappropriate_content",
                                "quarantine_id": quarantine_id
                            })
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning file: {str(e)}")
            return {
                "error": f"Error scanning file: {str(e)}",
                "secure": False,
                "file_path": file_path,
                "filename": os.path.basename(file_path)
            }
    
    async def _quarantine_file(self, file_path: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Quarantine a file using the quarantine manager.
        
        Args:
            file_path: Path to the file to quarantine
            reason: Reason for quarantining the file
            metadata: Additional metadata about the quarantined file
            
        Returns:
            Tuple[bool, Optional[str]]: (success, quarantine_id)
        """
        try:
            if not self.components["quarantine_manager"]:
                logger.warning("Quarantine manager not available")
                return False, None
            
            # Quarantine the file
            return quarantine_manager.quarantine_file(file_path, reason, metadata)
            
        except Exception as e:
            logger.error(f"Error quarantining file: {str(e)}")
            return False, None
    
    def get_quarantined_files(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of quarantined files.
        
        Args:
            status: Optional status filter ('quarantined', 'restored', 'deleted')
            
        Returns:
            List[Dict[str, Any]]: List of quarantined file information
        """
        if not self.components["quarantine_manager"]:
            logger.warning("Quarantine manager not available")
            return []
        
        return quarantine_manager.list_quarantined_files(status)
    
    def get_quarantined_file_info(self, quarantine_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a quarantined file.
        
        Args:
            quarantine_id: ID of the quarantined file
            
        Returns:
            Optional[Dict[str, Any]]: Information about the quarantined file, or None if not found
        """
        if not self.components["quarantine_manager"]:
            logger.warning("Quarantine manager not available")
            return None
        
        return quarantine_manager.get_quarantined_file_info(quarantine_id)
    
    def restore_quarantined_file(self, quarantine_id: str, restore_path: Optional[str] = None) -> bool:
        """
        Restore a file from quarantine.
        
        Args:
            quarantine_id: ID of the quarantined file
            restore_path: Optional path to restore the file to
            
        Returns:
            bool: True if restore was successful, False otherwise
        """
        if not self.components["quarantine_manager"]:
            logger.warning("Quarantine manager not available")
            return False
        
        return quarantine_manager.restore_file(quarantine_id, restore_path)
    
    def delete_quarantined_file(self, quarantine_id: str, permanent: bool = False) -> bool:
        """
        Delete a quarantined file.
        
        Args:
            quarantine_id: ID of the quarantined file
            permanent: If True, permanently delete the file and its record
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.components["quarantine_manager"]:
            logger.warning("Quarantine manager not available")
            return False
        
        return quarantine_manager.delete_quarantined_file(quarantine_id, permanent)
    
    def clean_quarantine(self, days: int = 30) -> int:
        """
        Clean up old quarantined files.
        
        Args:
            days: Delete files older than this many days
            
        Returns:
            int: Number of files cleaned up
        """
        if not self.components["quarantine_manager"]:
            logger.warning("Quarantine manager not available")
            return 0
        
        return quarantine_manager.clean_quarantine(days)

async def init_security_integrator() -> bool:
    """
    Initialize the global security integrator.
    
    Returns:
        bool: True if initialization was successful, False otherwise
    """
    global _security_integrator
    
    try:
        if _security_integrator is None:
            _security_integrator = SecurityIntegrator()
        
        success = await _security_integrator.initialize()
        return success
    except Exception as e:
        logger.error(f"Error initializing security integrator: {str(e)}")
        return False

def get_security_integrator() -> SecurityIntegrator:
    """
    Get the global security integrator instance.
    
    Returns:
        SecurityIntegrator: The global security integrator instance
    """
    global _security_integrator
    
    if _security_integrator is None:
        _security_integrator = SecurityIntegrator()
        # Note: This doesn't initialize the components, just creates the instance
        logger.warning("Security integrator accessed before initialization")
    
    return _security_integrator
