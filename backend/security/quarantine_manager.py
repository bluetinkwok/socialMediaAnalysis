"""
Quarantine Manager

This module provides functionality to quarantine and manage potentially harmful files.
It implements a secure storage system for isolating files that have been flagged by
security scans or content filtering.
"""

import os
import shutil
import logging
import json
import uuid
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path

from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class QuarantineManager:
    """
    Manages the quarantine system for files that fail security checks.
    
    This class provides functionality to:
    - Quarantine files flagged by security scans
    - Log quarantine events with detailed metadata
    - Retrieve information about quarantined files
    - Restore files from quarantine to original or new locations
    - Permanently delete quarantined files or mark them as deleted
    - Clean up old quarantined files based on age
    """
    
    def __init__(self):
        """Initialize the quarantine manager"""
        self.settings = get_settings()
        self.quarantine_dir = Path(self.settings.quarantine_dir)
        self.quarantine_db_path = self.quarantine_dir / "quarantine_db.json"
        self.initialized = False
        self.quarantine_db = {}
        
    def initialize(self) -> bool:
        """
        Initialize the quarantine manager.
        
        Returns:
            bool: True if initialization was successful, False otherwise
        """
        try:
            # Create quarantine directory if it doesn't exist
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
            
            # Create quarantine database file if it doesn't exist
            if not self.quarantine_db_path.exists():
                self._save_db({
                    "metadata": {
                        "version": "1.0",
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat()
                    },
                    "files": {}
                })
            
            # Load quarantine database
            self.quarantine_db = self._load_db()
            
            # Verify quarantine database structure
            if "metadata" not in self.quarantine_db or "files" not in self.quarantine_db:
                logger.error("Invalid quarantine database structure")
                return False
            
            self.initialized = True
            logger.info(f"Quarantine manager initialized: {self.initialized}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing quarantine manager: {str(e)}")
            self.initialized = False
            return False
    
    def quarantine_file(self, file_path: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, Optional[str]]:
        """
        Quarantine a file that failed security checks.
        
        Args:
            file_path: Path to the file to quarantine
            reason: Reason for quarantining the file
            metadata: Additional metadata about the quarantined file
            
        Returns:
            Tuple[bool, Optional[str]]: (success, quarantine_id)
        """
        if not self.initialized:
            logger.warning("Quarantine manager not initialized")
            return False, None
        
        try:
            # Generate a unique ID for the quarantined file
            quarantine_id = str(uuid.uuid4())
            
            # Create a directory for this quarantined file
            quarantine_file_dir = self.quarantine_dir / quarantine_id
            quarantine_file_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy the file to the quarantine directory
            quarantine_file_path = quarantine_file_dir / Path(file_path).name
            shutil.copy2(file_path, quarantine_file_path)
            
            # Record quarantine event
            quarantine_record = {
                "id": quarantine_id,
                "original_path": str(Path(file_path).absolute()),
                "original_filename": Path(file_path).name,
                "quarantine_path": str(quarantine_file_path),
                "quarantine_time": datetime.now().isoformat(),
                "reason": reason,
                "status": "quarantined",
                "metadata": metadata or {},
                "file_size": os.path.getsize(file_path),
                "history": [
                    {
                        "action": "quarantined",
                        "timestamp": datetime.now().isoformat(),
                        "reason": reason
                    }
                ]
            }
            
            # Update quarantine database
            self.quarantine_db["files"][quarantine_id] = quarantine_record
            self.quarantine_db["metadata"]["last_updated"] = datetime.now().isoformat()
            self._save_db(self.quarantine_db)
            
            logger.info(f"File quarantined: {file_path} -> {quarantine_file_path} (ID: {quarantine_id})")
            return True, quarantine_id
            
        except Exception as e:
            logger.error(f"Error quarantining file: {str(e)}")
            return False, None
    
    def list_quarantined_files(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get a list of quarantined files.
        
        Args:
            status: Optional status filter ('quarantined', 'restored', 'deleted')
            
        Returns:
            List[Dict[str, Any]]: List of quarantined file information
        """
        if not self.initialized:
            logger.warning("Quarantine manager not initialized")
            return []
        
        try:
            # Get all quarantined files
            quarantined_files = list(self.quarantine_db["files"].values())
            
            # Filter by status if provided
            if status:
                quarantined_files = [f for f in quarantined_files if f["status"] == status]
            
            # Sort by quarantine time (newest first)
            quarantined_files.sort(
                key=lambda x: datetime.fromisoformat(x["quarantine_time"]), 
                reverse=True
            )
            
            return quarantined_files
            
        except Exception as e:
            logger.error(f"Error listing quarantined files: {str(e)}")
            return []
    
    def get_quarantined_file_info(self, quarantine_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a quarantined file.
        
        Args:
            quarantine_id: ID of the quarantined file
            
        Returns:
            Optional[Dict[str, Any]]: Information about the quarantined file, or None if not found
        """
        if not self.initialized:
            logger.warning("Quarantine manager not initialized")
            return None
        
        try:
            # Get quarantined file information
            if quarantine_id not in self.quarantine_db["files"]:
                logger.warning(f"Quarantined file not found: {quarantine_id}")
                return None
            
            return self.quarantine_db["files"][quarantine_id]
            
        except Exception as e:
            logger.error(f"Error getting quarantined file info: {str(e)}")
            return None
    
    def restore_file(self, quarantine_id: str, restore_path: Optional[str] = None) -> bool:
        """
        Restore a file from quarantine.
        
        Args:
            quarantine_id: ID of the quarantined file
            restore_path: Optional path to restore the file to
            
        Returns:
            bool: True if restore was successful, False otherwise
        """
        if not self.initialized:
            logger.warning("Quarantine manager not initialized")
            return False
        
        try:
            # Check if quarantined file exists
            if quarantine_id not in self.quarantine_db["files"]:
                logger.warning(f"Quarantined file not found: {quarantine_id}")
                return False
            
            quarantine_record = self.quarantine_db["files"][quarantine_id]
            
            # Check if file is already restored or deleted
            if quarantine_record["status"] != "quarantined":
                logger.warning(f"Cannot restore file with status '{quarantine_record['status']}'")
                return False
            
            # Get quarantined file path
            quarantine_file_path = Path(quarantine_record["quarantine_path"])
            
            # Determine restore path
            if restore_path:
                target_path = Path(restore_path)
            else:
                target_path = Path(quarantine_record["original_path"])
            
            # Create parent directory if it doesn't exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy file from quarantine to target path
            shutil.copy2(quarantine_file_path, target_path)
            
            # Update quarantine record
            quarantine_record["status"] = "restored"
            quarantine_record["restore_path"] = str(target_path)
            quarantine_record["restore_time"] = datetime.now().isoformat()
            quarantine_record["history"].append({
                "action": "restored",
                "timestamp": datetime.now().isoformat(),
                "restore_path": str(target_path)
            })
            
            # Update quarantine database
            self.quarantine_db["files"][quarantine_id] = quarantine_record
            self.quarantine_db["metadata"]["last_updated"] = datetime.now().isoformat()
            self._save_db(self.quarantine_db)
            
            logger.info(f"File restored: {quarantine_file_path} -> {target_path} (ID: {quarantine_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring file: {str(e)}")
            return False
    
    def delete_quarantined_file(self, quarantine_id: str, permanent: bool = False) -> bool:
        """
        Delete a quarantined file.
        
        Args:
            quarantine_id: ID of the quarantined file
            permanent: If True, permanently delete the file and its record
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        if not self.initialized:
            logger.warning("Quarantine manager not initialized")
            return False
        
        try:
            # Check if quarantined file exists
            if quarantine_id not in self.quarantine_db["files"]:
                logger.warning(f"Quarantined file not found: {quarantine_id}")
                return False
            
            quarantine_record = self.quarantine_db["files"][quarantine_id]
            
            # Get quarantined file path
            quarantine_file_path = Path(quarantine_record["quarantine_path"])
            quarantine_dir = quarantine_file_path.parent
            
            if permanent:
                # Permanently delete the file and its directory
                if quarantine_file_path.exists():
                    quarantine_file_path.unlink()
                
                if quarantine_dir.exists():
                    shutil.rmtree(quarantine_dir)
                
                # Remove from quarantine database
                del self.quarantine_db["files"][quarantine_id]
                
                logger.info(f"File permanently deleted: {quarantine_file_path} (ID: {quarantine_id})")
            else:
                # Mark as deleted in the database
                quarantine_record["status"] = "deleted"
                quarantine_record["delete_time"] = datetime.now().isoformat()
                quarantine_record["history"].append({
                    "action": "deleted",
                    "timestamp": datetime.now().isoformat()
                })
                
                # Update quarantine database
                self.quarantine_db["files"][quarantine_id] = quarantine_record
                
                logger.info(f"File marked as deleted: {quarantine_file_path} (ID: {quarantine_id})")
            
            # Update quarantine database
            self.quarantine_db["metadata"]["last_updated"] = datetime.now().isoformat()
            self._save_db(self.quarantine_db)
            
            return True
            
        except Exception as e:
            logger.error(f"Error deleting quarantined file: {str(e)}")
            return False
    
    def clean_quarantine(self, days: int = 30) -> int:
        """
        Clean up old quarantined files.
        
        Args:
            days: Delete files older than this many days
            
        Returns:
            int: Number of files cleaned up
        """
        if not self.initialized:
            logger.warning("Quarantine manager not initialized")
            return 0
        
        try:
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Find old quarantined files
            files_to_clean = []
            for quarantine_id, record in self.quarantine_db["files"].items():
                try:
                    quarantine_time = datetime.fromisoformat(record["quarantine_time"])
                    if quarantine_time < cutoff_date:
                        files_to_clean.append(quarantine_id)
                except (ValueError, KeyError):
                    logger.warning(f"Invalid quarantine record: {quarantine_id}")
            
            # Delete old files
            cleaned_count = 0
            for quarantine_id in files_to_clean:
                if self.delete_quarantined_file(quarantine_id, permanent=True):
                    cleaned_count += 1
            
            logger.info(f"Cleaned {cleaned_count} quarantined files older than {days} days")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning quarantine: {str(e)}")
            return 0
    
    def _load_db(self) -> Dict[str, Any]:
        """
        Load the quarantine database from disk.
        
        Returns:
            Dict[str, Any]: Quarantine database
        """
        try:
            with open(self.quarantine_db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading quarantine database: {str(e)}")
            return {
                "metadata": {
                    "version": "1.0",
                    "created_at": datetime.now().isoformat(),
                    "last_updated": datetime.now().isoformat()
                },
                "files": {}
            }
    
    def _save_db(self, db: Dict[str, Any]) -> bool:
        """
        Save the quarantine database to disk.
        
        Args:
            db: Quarantine database
            
        Returns:
            bool: True if save was successful, False otherwise
        """
        try:
            # Create a backup of the existing database
            if self.quarantine_db_path.exists():
                backup_path = self.quarantine_db_path.with_suffix('.json.bak')
                shutil.copy2(self.quarantine_db_path, backup_path)
            
            # Save the new database
            with open(self.quarantine_db_path, 'w') as f:
                json.dump(db, f, indent=2)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving quarantine database: {str(e)}")
            return False

# Create a global instance of the quarantine manager
quarantine_manager = QuarantineManager() 