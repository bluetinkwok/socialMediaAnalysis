"""
Input sanitization module for preventing common security vulnerabilities.

This module provides functions to sanitize different types of inputs to prevent:
- XSS (Cross-Site Scripting) attacks
- SQL Injection attacks
- Command Injection attacks
- Path Traversal attacks
"""
import re
import html
import urllib.parse
from typing import Any, Dict, List, Optional, Union

class InputSanitizer:
    """Class for sanitizing user inputs to prevent security vulnerabilities."""
    
    @staticmethod
    def sanitize_string(input_str: Optional[str]) -> str:
        """
        Sanitize a string input to prevent XSS attacks.
        
        Args:
            input_str: The string to sanitize
            
        Returns:
            Sanitized string
        """
        if input_str is None:
            return ""
        
        # HTML escape to prevent XSS
        sanitized = html.escape(input_str)
        return sanitized
    
    @staticmethod
    def sanitize_sql_input(input_str: Optional[str]) -> str:
        """
        Sanitize a string input to prevent SQL injection.
        Note: This is a basic sanitization. Always use parameterized queries.
        
        Args:
            input_str: The string to sanitize
            
        Returns:
            Sanitized string
        """
        if input_str is None:
            return ""
        
        # Remove SQL injection patterns
        dangerous_patterns = [
            "--", ";", "/*", "*/", "@@", "@", "char", "nchar",
            "varchar", "nvarchar", "alter", "begin", "cast",
            "create", "cursor", "declare", "delete", "drop",
            "end", "exec", "execute", "fetch", "insert", "kill",
            "open", "select", "sys", "sysobjects", "syscolumns",
            "table", "update"
        ]
        
        sanitized = input_str
        for pattern in dangerous_patterns:
            # Replace with empty string if the pattern is surrounded by spaces or at the beginning/end
            sanitized = re.sub(r'(?i)(\s+|^)' + re.escape(pattern) + r'(\s+|$)', ' ', sanitized)
        
        return sanitized
    
    @staticmethod
    def sanitize_path(input_path: Optional[str]) -> str:
        """
        Sanitize a file path to prevent path traversal attacks.
        
        Args:
            input_path: The file path to sanitize
            
        Returns:
            Sanitized file path
        """
        if input_path is None:
            return ""
        
        # Remove path traversal sequences
        sanitized = input_path.replace('..', '').replace('\\', '/').replace('//', '/')
        
        # Remove any leading slashes to prevent absolute path references
        sanitized = re.sub(r'^[\/\\]+', '', sanitized)
        
        return sanitized
    
    @staticmethod
    def sanitize_command(input_cmd: Optional[str]) -> str:
        """
        Sanitize a command string to prevent command injection.
        
        Args:
            input_cmd: The command string to sanitize
            
        Returns:
            Sanitized command string
        """
        if input_cmd is None:
            return ""
        
        # Remove shell special characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\\', '"', "'", '\n', '\r']
        sanitized = input_cmd
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
            
        return sanitized
    
    @staticmethod
    def sanitize_url(url: Optional[str]) -> str:
        """
        Sanitize a URL to prevent open redirect and other URL-based attacks.
        
        Args:
            url: The URL to sanitize
            
        Returns:
            Sanitized URL
        """
        if url is None:
            return ""
        
        # URL encode special characters
        sanitized = urllib.parse.quote(url, safe=":/?=&")
        
        return sanitized
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively sanitize all string values in a dictionary.
        
        Args:
            data: Dictionary with values to sanitize
            
        Returns:
            Dictionary with sanitized values
        """
        sanitized_data = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized_data[key] = InputSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized_data[key] = InputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized_data[key] = InputSanitizer.sanitize_list(value)
            else:
                sanitized_data[key] = value
                
        return sanitized_data
    
    @staticmethod
    def sanitize_list(data: List[Any]) -> List[Any]:
        """
        Recursively sanitize all string values in a list.
        
        Args:
            data: List with values to sanitize
            
        Returns:
            List with sanitized values
        """
        sanitized_data = []
        
        for item in data:
            if isinstance(item, str):
                sanitized_data.append(InputSanitizer.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized_data.append(InputSanitizer.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized_data.append(InputSanitizer.sanitize_list(item))
            else:
                sanitized_data.append(item)
                
        return sanitized_data 