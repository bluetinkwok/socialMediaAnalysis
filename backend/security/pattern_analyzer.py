"""
Pattern Analyzer

This module provides suspicious pattern detection using YARA rules.
"""

import os
import logging
from typing import Tuple, Dict, Any, List, Optional

# Import yara if available
try:
    import yara
    YARA_AVAILABLE = True
except ImportError:
    YARA_AVAILABLE = False
    logging.warning("YARA not installed. Pattern analysis will be unavailable.")

logger = logging.getLogger(__name__)

class YaraScanner:
    """YARA pattern scanner"""
    
    def __init__(self, rules_path: str):
        """
        Initialize the YARA scanner.
        
        Args:
            rules_path: Path to the YARA rules directory
        """
        self.rules_path = rules_path
        self.rules = None
        self.available = YARA_AVAILABLE
    
    def load_rules(self) -> bool:
        """
        Load YARA rules from the rules directory.
        
        Returns:
            bool: True if rules were loaded successfully, False otherwise
        """
        if not self.available:
            logger.warning("YARA not available. Skipping rule loading.")
            return False
        
        try:
            # Check if rules directory exists
            if not os.path.exists(self.rules_path):
                logger.warning(f"YARA rules directory not found: {self.rules_path}")
                return False
            
            # Compile all .yar files in the directory
            rule_files = {}
            for filename in os.listdir(self.rules_path):
                if filename.endswith(".yar") or filename.endswith(".yara"):
                    filepath = os.path.join(self.rules_path, filename)
                    namespace = os.path.splitext(filename)[0]
                    rule_files[namespace] = filepath
            
            if not rule_files:
                logger.warning(f"No YARA rule files found in {self.rules_path}")
                return False
            
            # Compile the rules
            self.rules = yara.compile(filepaths=rule_files)
            logger.info(f"Loaded YARA rules from {len(rule_files)} files")
            return True
            
        except Exception as e:
            logger.error(f"Error loading YARA rules: {str(e)}")
            self.rules = None
            return False
    
    def scan_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Scan a file for suspicious patterns.
        
        Args:
            file_path: Path to the file to scan
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (is_safe, scan_results)
        """
        if not self.available:
            logger.warning("YARA not available. Skipping pattern analysis.")
            return True, {"warning": "YARA not available. Pattern analysis skipped."}
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False, {"error": "File not found"}
        
        if self.rules is None:
            logger.warning("YARA rules not loaded. Skipping pattern analysis.")
            return True, {"warning": "YARA rules not loaded. Pattern analysis skipped."}
        
        try:
            # Scan the file with YARA rules
            matches = self.rules.match(file_path)
            
            # Process matches
            if matches:
                match_details = []
                for match in matches:
                    match_details.append({
                        "rule": match.rule,
                        "namespace": match.namespace,
                        "tags": match.tags,
                        "meta": match.meta
                    })
                
                return False, {
                    "status": "SUSPICIOUS",
                    "matches": match_details,
                    "count": len(matches)
                }
            else:
                return True, {
                    "status": "OK",
                    "details": "No suspicious patterns found"
                }
                
        except Exception as e:
            logger.error(f"Error scanning file with YARA: {str(e)}")
            return False, {"error": f"Pattern analysis failed: {str(e)}"}
