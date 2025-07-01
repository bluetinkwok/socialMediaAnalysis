#!/usr/bin/env python3
"""
Security Baseline Generator Script

This script generates a security baseline for the application, including
security settings, configurations, and metrics. The baseline can be used
for comparison during security audits or monitoring.
"""

import argparse
import datetime
import json
import os
import platform
import socket
import sys
from typing import Dict, List, Optional

# Add the parent directory to the path to import application modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.security_logger import security_logger
from db.database import get_db


def get_system_info() -> Dict:
    """
    Get system information.
    
    Returns:
        Dictionary of system information
    """
    return {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }


def get_security_settings() -> Dict:
    """
    Get security settings from the application configuration.
    
    Returns:
        Dictionary of security settings
    """
    # In a real implementation, this would read from the application config
    # For now, we'll return placeholder settings
    return {
        "auth": {
            "token_expiration": 3600,  # seconds
            "refresh_token_expiration": 86400,  # seconds
            "password_min_length": 8,
            "password_complexity": True,
            "two_factor_auth": False
        },
        "rate_limiting": {
            "enabled": True,
            "default_limit": 100,  # requests per minute
            "login_limit": 10  # requests per minute
        },
        "encryption": {
            "algorithm": "AES-256-GCM",
            "key_rotation_days": 90
        },
        "logging": {
            "security_log_level": "INFO",
            "audit_enabled": True
        },
        "cors": {
            "allowed_origins": ["https://example.com"],
            "allow_credentials": True
        },
        "security_headers": {
            "content_security_policy": "default-src 'self'",
            "x_content_type_options": "nosniff",
            "x_frame_options": "DENY",
            "strict_transport_security": "max-age=31536000; includeSubDomains"
        }
    }


def get_database_security_info() -> Dict:
    """
    Get security information about the database.
    
    Returns:
        Dictionary of database security information
    """
    try:
        db = next(get_db())
        
        # In a real implementation, this would query the database for security info
        # For now, we'll return placeholder info
        return {
            "encrypted_fields": 10,
            "audit_records_count": 1000,
            "security_incidents_count": 5
        }
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return {
            "error": str(e)
        }


def get_api_security_info() -> Dict:
    """
    Get security information about the API.
    
    Returns:
        Dictionary of API security information
    """
    # In a real implementation, this would analyze the API endpoints
    # For now, we'll return placeholder info
    return {
        "endpoints_count": 50,
        "protected_endpoints_count": 40,
        "rate_limited_endpoints_count": 30
    }


def generate_baseline(output_file: Optional[str] = None) -> Dict:
    """
    Generate a security baseline.
    
    Args:
        output_file: Path to the output file (optional)
        
    Returns:
        Dictionary containing the security baseline
    """
    # Collect baseline information
    baseline = {
        "system_info": get_system_info(),
        "security_settings": get_security_settings(),
        "database_security": get_database_security_info(),
        "api_security": get_api_security_info()
    }
    
    # Write to file if specified
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(baseline, f, indent=2)
        print(f"Security baseline written to {output_file}")
    
    return baseline


def compare_baselines(baseline1: Dict, baseline2: Dict) -> Dict:
    """
    Compare two security baselines.
    
    Args:
        baseline1: First baseline
        baseline2: Second baseline
        
    Returns:
        Dictionary containing differences between the baselines
    """
    differences = {}
    
    # Compare security settings
    settings1 = baseline1.get("security_settings", {})
    settings2 = baseline2.get("security_settings", {})
    settings_diff = {}
    
    for category, values1 in settings1.items():
        if category in settings2:
            values2 = settings2[category]
            category_diff = {}
            
            for key, value1 in values1.items():
                if key in values2:
                    if value1 != values2[key]:
                        category_diff[key] = {
                            "baseline1": value1,
                            "baseline2": values2[key]
                        }
                else:
                    category_diff[key] = {
                        "baseline1": value1,
                        "baseline2": None
                    }
            
            for key, value2 in values2.items():
                if key not in values1:
                    category_diff[key] = {
                        "baseline1": None,
                        "baseline2": value2
                    }
            
            if category_diff:
                settings_diff[category] = category_diff
    
    if settings_diff:
        differences["security_settings"] = settings_diff
    
    # Compare database security
    db1 = baseline1.get("database_security", {})
    db2 = baseline2.get("database_security", {})
    db_diff = {}
    
    for key, value1 in db1.items():
        if key in db2:
            if value1 != db2[key]:
                db_diff[key] = {
                    "baseline1": value1,
                    "baseline2": db2[key]
                }
        else:
            db_diff[key] = {
                "baseline1": value1,
                "baseline2": None
            }
    
    for key, value2 in db2.items():
        if key not in db1:
            db_diff[key] = {
                "baseline1": None,
                "baseline2": value2
            }
    
    if db_diff:
        differences["database_security"] = db_diff
    
    # Compare API security
    api1 = baseline1.get("api_security", {})
    api2 = baseline2.get("api_security", {})
    api_diff = {}
    
    for key, value1 in api1.items():
        if key in api2:
            if value1 != api2[key]:
                api_diff[key] = {
                    "baseline1": value1,
                    "baseline2": api2[key]
                }
        else:
            api_diff[key] = {
                "baseline1": value1,
                "baseline2": None
            }
    
    for key, value2 in api2.items():
        if key not in api1:
            api_diff[key] = {
                "baseline1": None,
                "baseline2": value2
            }
    
    if api_diff:
        differences["api_security"] = api_diff
    
    return differences


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Generate a security baseline")
    parser.add_argument(
        "--output", "-o",
        help="Path to the output file",
        default="security_baseline.json"
    )
    parser.add_argument(
        "--compare", "-c",
        help="Path to a baseline file to compare with"
    )
    
    args = parser.parse_args()
    
    # Generate baseline
    baseline = generate_baseline(args.output)
    
    # Compare with existing baseline if specified
    if args.compare:
        try:
            with open(args.compare, "r") as f:
                compare_baseline = json.load(f)
            
            differences = compare_baselines(compare_baseline, baseline)
            
            if differences:
                print("\nDifferences found between baselines:")
                print(json.dumps(differences, indent=2))
                
                # Write differences to file
                diff_file = f"baseline_diff_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                with open(diff_file, "w") as f:
                    json.dump(differences, f, indent=2)
                print(f"\nDifferences written to {diff_file}")
            else:
                print("\nNo differences found between baselines.")
        except Exception as e:
            print(f"Error comparing baselines: {e}")


if __name__ == "__main__":
    main() 