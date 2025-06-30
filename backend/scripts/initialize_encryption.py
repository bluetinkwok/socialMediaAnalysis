#!/usr/bin/env python3
"""
Encryption System Initialization

This script initializes the encryption system by generating the initial encryption keys
and setting up the necessary directories.
"""

import logging
import os
import sys
from pathlib import Path

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.encryption import key_manager, encryption_service
from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def initialize_encryption():
    """
    Initialize the encryption system.
    
    Returns:
        True if initialization succeeded, False otherwise
    """
    try:
        logger.info("Initializing encryption system...")
        
        # Create key directory if it doesn't exist
        key_dir = Path(".keys")
        if not key_dir.exists():
            logger.info(f"Creating key directory: {key_dir}")
            key_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        elif key_dir.stat().st_mode & 0o777 != 0o700:
            logger.info(f"Fixing permissions on key directory: {key_dir}")
            os.chmod(key_dir, 0o700)
        
        # Initialize key manager
        logger.info("Initializing key manager...")
        key_manager.initialize()
        
        # Get the current key ID
        key_id = key_manager.current_key["id"]
        logger.info(f"Current encryption key ID: {key_id}")
        
        # Test encryption
        logger.info("Testing encryption...")
        test_data = "Encryption test"
        encrypted = encryption_service.encrypt(test_data)
        decrypted = encryption_service.decrypt_to_string(encrypted)
        
        if decrypted == test_data:
            logger.info("Encryption test successful")
        else:
            logger.error("Encryption test failed")
            return False
        
        logger.info("Encryption system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize encryption system: {str(e)}")
        return False


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    success = initialize_encryption()
    sys.exit(0 if success else 1) 