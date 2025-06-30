"""
Pattern Detector Module

This module provides file type and pattern analysis using YARA rules.
"""

import os
import logging
import asyncio
import yara
from typing import Optional, Tuple, List, Dict, Any
from pathlib import Path

from core.config import get_settings

# Configure logging
logger = logging.getLogger(__name__)
settings = get_settings()

class PatternDetector:
    """
    Pattern detector using YARA rules.
    """
    
    def __init__(self):
        """Initialize YARA rules"""
        self.rules_dir = settings.yara_rules_dir
        self.rules = None
        self.compiled = False
    
    def initialize(self) -> bool:
        """
        Initialize YARA rules.
        
        Returns:
            True if rules were successfully compiled
        """
        try:
            # Check if rules directory exists
            if not os.path.exists(self.rules_dir):
                logger.warning(f"YARA rules directory not found: {self.rules_dir}")
                return False
            
            # Compile all rules in the directory
            filepaths = {}
            for filename in os.listdir(self.rules_dir):
                if filename.endswith('.yar') or filename.endswith('.yara'):
                    filepath = os.path.join(self.rules_dir, filename)
                    filepaths[filename] = filepath
            
            if not filepaths:
                logger.warning(f"No YARA rules found in {self.rules_dir}")
                return False
            
            self.rules = yara.compile(filepaths=filepaths)
            self.compiled = True
            logger.info(f"Successfully compiled {len(filepaths)} YARA rules")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize YARA rules: {str(e)}")
            self.compiled = False
            return False
    
    def create_default_rules(self) -> bool:
        """
        Create default YARA rules if none exist.
        
        Returns:
            True if default rules were created
        """
        try:
            # Create rules directory if it doesn't exist
            if not os.path.exists(self.rules_dir):
                os.makedirs(self.rules_dir, exist_ok=True)
                logger.info(f"Created YARA rules directory: {self.rules_dir}")
            
            # Check if any rules already exist
            existing_rules = [f for f in os.listdir(self.rules_dir) 
                             if f.endswith('.yar') or f.endswith('.yara')]
            if existing_rules:
                logger.info(f"Found {len(existing_rules)} existing YARA rules")
                return True
            
            # Create default rules
            default_rules = {
                "suspicious_js.yar": """
rule SuspiciousJavaScript {
    meta:
        description = "Detects suspicious JavaScript patterns"
        author = "Social Media Analysis Platform"
        severity = "medium"
    
    strings:
        $eval = "eval(" nocase
        $doc_write = "document.write(" nocase
        $fromcharcode = "fromCharCode" nocase
        $encode = "encode" nocase
        $decode = "decode" nocase
        $iframe = "iframe" nocase
        $obfuscated = /var _0x[a-f0-9]{4}/
    
    condition:
        any of them and file.type contains "javascript"
}
""",
                "executable_content.yar": """
rule ExecutableContent {
    meta:
        description = "Detects executable content in non-executable files"
        author = "Social Media Analysis Platform"
        severity = "high"
    
    strings:
        $mz = { 4D 5A }
        $elf = { 7F 45 4C 46 }
        $pe = { 50 45 00 00 }
        $shellcode = { E8 00 00 00 00 }
    
    condition:
        any of them
}
""",
                "suspicious_pdf.yar": """
rule SuspiciousPDF {
    meta:
        description = "Detects suspicious PDF patterns"
        author = "Social Media Analysis Platform"
        severity = "medium"
    
    strings:
        $header = { 25 50 44 46 }
        $js = "/JavaScript" nocase
        $launch = "/Launch" nocase
        $action = "/Action" nocase
        $objstm = "/ObjStm" nocase
        $openaction = "/OpenAction" nocase
        $aa = "/AA" nocase
        $richmedia = "/RichMedia" nocase
        $embedded_file = "/EmbeddedFile" nocase
    
    condition:
        $header at 0 and 3 of ($js, $launch, $action, $objstm, $openaction, $aa, $richmedia, $embedded_file)
}
"""
            }
            
            # Write default rules to files
            for filename, content in default_rules.items():
                filepath = os.path.join(self.rules_dir, filename)
                with open(filepath, 'w') as f:
                    f.write(content)
                logger.info(f"Created default YARA rule: {filename}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create default YARA rules: {str(e)}")
            return False
    
    async def scan_file(self, file_path: str) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Scan a file for suspicious patterns.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            Tuple containing:
            - Boolean indicating if the file is safe
            - List of detected patterns if any
        """
        try:
            # Ensure rules are compiled
            if not self.compiled:
                if not self.initialize():
                    logger.error("YARA rules not compiled, cannot scan file")
                    return False, [{"rule": "error", "description": "YARA rules not compiled"}]
            
            # Ensure file exists
            if not os.path.exists(file_path):
                logger.error(f"File not found: {file_path}")
                return False, [{"rule": "error", "description": "File not found"}]
            
            # Run scan in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._scan_file_sync, file_path)
            
            return result
        except Exception as e:
            logger.error(f"Error scanning file {file_path}: {str(e)}")
            return False, [{"rule": "error", "description": f"Scan error: {str(e)}"}]
    
    def _scan_file_sync(self, file_path: str) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Synchronous version of scan_file.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            Tuple containing:
            - Boolean indicating if the file is safe
            - List of detected patterns if any
        """
        try:
            matches = self.rules.match(file_path)
            
            if not matches:
                return True, None
            
            # Process matches
            findings = []
            for match in matches:
                rule_meta = match.meta if hasattr(match, 'meta') else {}
                finding = {
                    "rule": match.rule,
                    "description": rule_meta.get('description', 'No description'),
                    "severity": rule_meta.get('severity', 'unknown'),
                    "tags": match.tags
                }
                findings.append(finding)
                logger.warning(f"Suspicious pattern found in {file_path}: {match.rule}")
            
            return False, findings
                
        except Exception as e:
            logger.error(f"Error in synchronous scan of {file_path}: {str(e)}")
            return False, [{"rule": "error", "description": f"Scan error: {str(e)}"}]
    
    async def scan_data(self, data: bytes) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Scan binary data for suspicious patterns.
        
        Args:
            data: Binary data to scan
            
        Returns:
            Tuple containing:
            - Boolean indicating if the data is safe
            - List of detected patterns if any
        """
        try:
            # Ensure rules are compiled
            if not self.compiled:
                if not self.initialize():
                    logger.error("YARA rules not compiled, cannot scan data")
                    return False, [{"rule": "error", "description": "YARA rules not compiled"}]
            
            # Run scan in a separate thread to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._scan_data_sync, data)
            
            return result
        except Exception as e:
            logger.error(f"Error scanning data: {str(e)}")
            return False, [{"rule": "error", "description": f"Scan error: {str(e)}"}]
    
    def _scan_data_sync(self, data: bytes) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
        """
        Synchronous version of scan_data.
        
        Args:
            data: Binary data to scan
            
        Returns:
            Tuple containing:
            - Boolean indicating if the data is safe
            - List of detected patterns if any
        """
        try:
            matches = self.rules.match(data=data)
            
            if not matches:
                return True, None
            
            # Process matches
            findings = []
            for match in matches:
                rule_meta = match.meta if hasattr(match, 'meta') else {}
                finding = {
                    "rule": match.rule,
                    "description": rule_meta.get('description', 'No description'),
                    "severity": rule_meta.get('severity', 'unknown'),
                    "tags": match.tags
                }
                findings.append(finding)
                logger.warning(f"Suspicious pattern found in data: {match.rule}")
            
            return False, findings
                
        except Exception as e:
            logger.error(f"Error in synchronous scan of data: {str(e)}")
            return False, [{"rule": "error", "description": f"Scan error: {str(e)}"}] 