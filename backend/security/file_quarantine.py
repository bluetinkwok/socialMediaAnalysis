"""
File Quarantine System

This module provides functionality to safely quarantine files that have failed
security checks, such as malware detection or inappropriate content filtering.
"""

import os
import shutil
import logging
import json
import uuid
import datetime
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import hashlib

from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class QuarantineReason:
    """Reasons for file quarantine"""
    MALWARE = "malware"
    INAPPROPRIATE_CONTENT = "inappropriate_content"
    SUSPICIOUS_PATTERN = "suspicious_pattern"
    METADATA_RISK = "metadata_risk"
    MANUAL = "manual"
    UNKNOWN = "unknown"

class FileQuarantine:
    """
    File Quarantine System
    
    Provides functionality to:
    - Safely quarantine files that fail security checks
    - Store quarantined files in a secure location
    - Maintain metadata about quarantined files
    - Provide methods to manage quarantined files
    """
    
    def __init__(self):
        """Initialize the file quarantine system"""
        self.initialized = False
        self.quarantine_dir = None
        self.metadata_file = None
        self.quarantine_data = {}
        self.settings = get_settings()
    
    def initialize(self, base_dir: str = None) -> bool:
        """
        Initialize the file quarantine system.
        
        Args:
            base_dir: Base directory for quarantine storage
            
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            logger.info("Initializing file quarantine system")
            
            # Use provided base dir or default to 'data/quarantine'
            if not base_dir:
                base_dir = os.path.join("data", "quarantine")
            
            # Create quarantine directory structure
            self.quarantine_dir = os.path.abspath(base_dir)
            self.files_dir = os.path.join(self.quarantine_dir, "files")
            self.metadata_file = os.path.join(self.quarantine_dir, "quarantine_metadata.json")
            
            # Create directories if they don't exist
            os.makedirs(self.quarantine_dir, exist_ok=True)
            os.makedirs(self.files_dir, exist_ok=True)
            
            # Set secure permissions (0o700 = rwx------)
            os.chmod(self.quarantine_dir, 0o700)
            os.chmod(self.files_dir, 0o700)
            
            # Load existing metadata if available
            if os.path.exists(self.metadata_file):
                try:
                    with open(self.metadata_file, 'r') as f:
                        self.quarantine_data = json.load(f)
                except json.JSONDecodeError:
                    logger.warning("Invalid quarantine metadata file, creating new one")
                    self.quarantine_data = {}
            
            self.initialized = True
            logger.info(f"File quarantine system initialized at {self.quarantine_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing file quarantine system: {str(e)}")
            return False
    
    def quarantine_file(self, file_path: str, reason: str = QuarantineReason.UNKNOWN, 
                       details: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Move a file to quarantine.
        
        Args:
            file_path: Path to the file to quarantine
            reason: Reason for quarantine (use QuarantineReason constants)
            details: Additional details about the quarantine reason
            
        Returns:
            Tuple[bool, str]: (success, quarantine_id or error message)
        """
        if not self.initialized:
            logger.warning("File quarantine system not initialized")
            return False, "File quarantine system not initialized"
        
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False, "File not found"
            
            # Generate a unique ID for the quarantined file
            quarantine_id = str(uuid.uuid4())
            
            # Calculate file hash for integrity verification
            file_hash = self._calculate_file_hash(file_path)
            
            # Create quarantine file path with a unique name
            quarantine_file_path = os.path.join(self.files_dir, f"{quarantine_id}{os.path.splitext(file_path)[1]}")
            
            # Move the file to quarantine
            shutil.copy2(file_path, quarantine_file_path)
            
            # Set secure permissions (0o400 = r--------)
            os.chmod(quarantine_file_path, 0o400)
            
            # Record metadata
            metadata = {
                "quarantine_id": quarantine_id,
                "original_path": os.path.abspath(file_path),
                "original_filename": os.path.basename(file_path),
                "quarantine_path": quarantine_file_path,
                "quarantine_date": datetime.datetime.now().isoformat(),
                "reason": reason,
                "details": details or {},
                "file_size": os.path.getsize(file_path),
                "file_hash": file_hash,
                "status": "quarantined"
            }
            
            # Add to quarantine data
            self.quarantine_data[quarantine_id] = metadata
            
            # Save metadata
            self._save_metadata()
            
            logger.info(f"File quarantined: {file_path} -> {quarantine_file_path} (ID: {quarantine_id})")
            return True, quarantine_id
            
        except Exception as e:
            logger.error(f"Error quarantining file: {str(e)}")
            return False, f"Error quarantining file: {str(e)}"
    
    def get_quarantined_file_info(self, quarantine_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a quarantined file.
        
        Args:
            quarantine_id: ID of the quarantined file
            
        Returns:
            Optional[Dict[str, Any]]: Metadata about the quarantined file or None if not found
        """
        if not self.initialized:
            logger.warning("File quarantine system not initialized")
            return None
        
        return self.quarantine_data.get(quarantine_id)
    
    def list_quarantined_files(self, filter_reason: str = None) -> List[Dict[str, Any]]:
        """
        List all quarantined files, optionally filtered by reason.
        
        Args:
            filter_reason: Filter by quarantine reason
            
        Returns:
            List[Dict[str, Any]]: List of quarantined file metadata
        """
        if not self.initialized:
            logger.warning("File quarantine system not initialized")
            return []
        
        if filter_reason:
            return [data for data in self.quarantine_data.values() if data.get("reason") == filter_reason]
        else:
            return list(self.quarantine_data.values())
    
    def release_file(self, quarantine_id: str, destination_path: str) -> bool:
        """
        Release a file from quarantine to a specified destination.
        
        Args:
            quarantine_id: ID of the quarantined file
            destination_path: Path where the file should be released
            
        Returns:
            bool: True if the file was successfully released, False otherwise
        """
        if not self.initialized:
            logger.warning("File quarantine system not initialized")
            return False
        
        try:
            # Get file metadata
            metadata = self.quarantine_data.get(quarantine_id)
            if not metadata:
                logger.error(f"Quarantined file not found: {quarantine_id}")
                return False
            
            # Check if file exists in quarantine
            quarantine_path = metadata.get("quarantine_path")
            if not os.path.exists(quarantine_path):
                logger.error(f"Quarantined file missing: {quarantine_path}")
                return False
            
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            
            # Copy file to destination
            shutil.copy2(quarantine_path, destination_path)
            
            # Update metadata
            metadata["release_date"] = datetime.datetime.now().isoformat()
            metadata["release_path"] = destination_path
            metadata["status"] = "released"
            
            # Save metadata
            self._save_metadata()
            
            logger.info(f"File released from quarantine: {quarantine_path} -> {destination_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing file from quarantine: {str(e)}")
            return False
    
    def delete_file(self, quarantine_id: str) -> bool:
        """
        Permanently delete a file from quarantine.
        
        Args:
            quarantine_id: ID of the quarantined file
            
        Returns:
            bool: True if the file was successfully deleted, False otherwise
        """
        if not self.initialized:
            logger.warning("File quarantine system not initialized")
            return False
        
        try:
            # Get file metadata
            metadata = self.quarantine_data.get(quarantine_id)
            if not metadata:
                logger.error(f"Quarantined file not found: {quarantine_id}")
                return False
            
            # Check if file exists in quarantine
            quarantine_path = metadata.get("quarantine_path")
            if os.path.exists(quarantine_path):
                # Delete the file
                os.remove(quarantine_path)
            
            # Update metadata
            metadata["deletion_date"] = datetime.datetime.now().isoformat()
            metadata["status"] = "deleted"
            
            # Save metadata
            self._save_metadata()
            
            logger.info(f"File deleted from quarantine: {quarantine_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from quarantine: {str(e)}")
            return False
    
    def verify_file_integrity(self, quarantine_id: str) -> bool:
        """
        Verify the integrity of a quarantined file by checking its hash.
        
        Args:
            quarantine_id: ID of the quarantined file
            
        Returns:
            bool: True if the file integrity is verified, False otherwise
        """
        if not self.initialized:
            logger.warning("File quarantine system not initialized")
            return False
        
        try:
            # Get file metadata
            metadata = self.quarantine_data.get(quarantine_id)
            if not metadata:
                logger.error(f"Quarantined file not found: {quarantine_id}")
                return False
            
            # Check if file exists in quarantine
            quarantine_path = metadata.get("quarantine_path")
            if not os.path.exists(quarantine_path):
                logger.error(f"Quarantined file missing: {quarantine_path}")
                return False
            
            # Get stored hash
            stored_hash = metadata.get("file_hash")
            if not stored_hash:
                logger.warning(f"No hash available for quarantined file: {quarantine_id}")
                return False
            
            # Calculate current hash
            current_hash = self._calculate_file_hash(quarantine_path)
            
            # Compare hashes
            integrity_verified = stored_hash == current_hash
            
            if not integrity_verified:
                logger.warning(f"Integrity check failed for quarantined file: {quarantine_id}")
                
                # Update metadata
                metadata["integrity_check"] = {
                    "date": datetime.datetime.now().isoformat(),
                    "result": "failed",
                    "expected_hash": stored_hash,
                    "actual_hash": current_hash
                }
                
                # Save metadata
                self._save_metadata()
            
            return integrity_verified
            
        except Exception as e:
            logger.error(f"Error verifying file integrity: {str(e)}")
            return False
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            str: SHA-256 hash of the file
        """
        sha256_hash = hashlib.sha256()
        
        with open(file_path, "rb") as f:
            # Read and update hash in chunks for memory efficiency
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()
    
    def _save_metadata(self) -> bool:
        """
        Save quarantine metadata to file.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.quarantine_data, f, indent=2)
            
            # Set secure permissions (0o600 = rw-------)
            os.chmod(self.metadata_file, 0o600)
            
            return True
        except Exception as e:
            logger.error(f"Error saving quarantine metadata: {str(e)}")
            return False 