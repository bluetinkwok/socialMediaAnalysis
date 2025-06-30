"""
Pattern detection module for identifying suspicious patterns in files.

This module uses YARA rules to scan files for suspicious patterns that may
indicate malicious content.
"""

import os
import logging
import yara
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from fastapi import UploadFile, HTTPException, status

from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class PatternDetector:
    """
    Provides pattern detection capabilities using YARA rules.
    """
    
    def __init__(self, rules_dir: str = None):
        """
        Initialize the pattern detector.
        
        Args:
            rules_dir: Directory containing YARA rule files (default: ./data/security/yara_rules)
        """
        self.rules_dir = rules_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                                                "data", "security", "yara_rules")
        self._rules = None
        
    @property
    def rules(self):
        """Get or initialize the YARA rules."""
        if self._rules is None:
            try:
                # Ensure the rules directory exists
                os.makedirs(self.rules_dir, exist_ok=True)
                
                # Compile all .yar files in the rules directory
                filepaths = {}
                for file in os.listdir(self.rules_dir):
                    if file.endswith('.yar') or file.endswith('.yara'):
                        filepath = os.path.join(self.rules_dir, file)
                        filepaths[file] = filepath
                
                if filepaths:
                    self._rules = yara.compile(filepaths=filepaths)
                    logger.info(f"Compiled YARA rules from {len(filepaths)} files")
                else:
                    logger.warning(f"No YARA rule files found in {self.rules_dir}")
                    
            except Exception as e:
                logger.error(f"Error compiling YARA rules: {str(e)}")
                self._rules = None
        
        return self._rules
    
    async def scan_file(self, file_path: Union[str, Path]) -> List[Dict]:
        """
        Scan a file for suspicious patterns using YARA rules.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            List of matches, each containing rule name and metadata
        """
        if not self.rules:
            logger.warning("YARA rules not available, skipping pattern scan")
            return []
        
        try:
            # Convert to string if Path object
            file_path_str = str(file_path)
            
            # Scan the file
            matches = self.rules.match(file_path_str)
            
            # Format the results
            results = []
            for match in matches:
                results.append({
                    "rule": match.rule,
                    "tags": match.tags,
                    "meta": match.meta,
                    "strings": [(s[0], s[1], s[2].decode('utf-8', errors='replace')) for s in match.strings]
                })
            
            if results:
                logger.warning(f"Found {len(results)} suspicious patterns in {file_path_str}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning file {file_path} for patterns: {str(e)}")
            return []
    
    async def scan_bytes(self, content: bytes) -> List[Dict]:
        """
        Scan binary content for suspicious patterns using YARA rules.
        
        Args:
            content: Binary content to scan
            
        Returns:
            List of matches, each containing rule name and metadata
        """
        if not self.rules:
            logger.warning("YARA rules not available, skipping pattern scan")
            return []
        
        try:
            # Scan the content
            matches = self.rules.match(data=content)
            
            # Format the results
            results = []
            for match in matches:
                results.append({
                    "rule": match.rule,
                    "tags": match.tags,
                    "meta": match.meta,
                    "strings": [(s[0], s[1], s[2].decode('utf-8', errors='replace')) for s in match.strings]
                })
            
            if results:
                logger.warning(f"Found {len(results)} suspicious patterns in binary content")
            
            return results
            
        except Exception as e:
            logger.error(f"Error scanning binary content for patterns: {str(e)}")
            return []
    
    async def scan_upload_file(self, upload_file: UploadFile) -> List[Dict]:
        """
        Scan an uploaded file for suspicious patterns using YARA rules.
        
        Args:
            upload_file: The uploaded file
            
        Returns:
            List of matches, each containing rule name and metadata
        """
        if not self.rules:
            logger.warning("YARA rules not available, skipping pattern scan")
            return []
        
        try:
            # Read the file content
            content = await upload_file.read()
            
            # Reset the file position for future reads
            await upload_file.seek(0)
            
            # Scan the file content
            return await self.scan_bytes(content)
            
        except Exception as e:
            logger.error(f"Error scanning uploaded file {upload_file.filename} for patterns: {str(e)}")
            return []
    
    def get_available_rules(self) -> List[Dict]:
        """
        Get information about available YARA rules.
        
        Returns:
            List of rule information, each containing rule name and metadata
        """
        if not self.rules:
            logger.warning("YARA rules not available")
            return []
        
        try:
            # Get rule information by scanning an empty string
            # This will not match any rules, but allows us to enumerate them
            rule_info = []
            
            # List all .yar files in the rules directory
            for file in os.listdir(self.rules_dir):
                if file.endswith('.yar') or file.endswith('.yara'):
                    filepath = os.path.join(self.rules_dir, file)
                    try:
                        # Compile individual file to get its rules
                        rules = yara.compile(filepath=filepath)
                        
                        # Get rule names and metadata
                        # This is a bit of a hack, but YARA doesn't provide a direct way to list rules
                        matches = rules.match(data=b"")
                        for match in matches:
                            rule_info.append({
                                "file": file,
                                "rule": match.rule,
                                "tags": match.tags,
                                "meta": match.meta
                            })
                    except Exception as e:
                        logger.error(f"Error getting rule information from {file}: {str(e)}")
            
            return rule_info
            
        except Exception as e:
            logger.error(f"Error getting available rules: {str(e)}")
            return []


# Create a global instance of the pattern detector
pattern_detector = PatternDetector() 