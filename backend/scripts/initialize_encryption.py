#!/usr/bin/env python3
"""
Initialize Encryption System

This script initializes the encryption system by generating encryption keys.
"""

import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import encryption modules
from core.encryption import encryption_service, key_manager, EncryptionError


def initialize_encryption():
    """Initialize the encryption system."""
    try:
        logger.info("Initializing encryption system...")
        
        # Initialize key manager
        logger.info("Initializing key manager...")
        key_manager.initialize()
        
        # Get current key ID
        current_key_id = key_manager.current_key["id"]
        logger.info(f"Current encryption key ID: {current_key_id}")
        
        # Test encryption
        logger.info("Testing encryption...")
        test_data = "Test encryption data"
        encrypted = encryption_service.encrypt(test_data)
        decrypted = encryption_service.decrypt_to_string(encrypted)
        
        if decrypted == test_data:
            logger.info("Encryption test successful")
        else:
            raise EncryptionError("Encryption test failed: decrypted data doesn't match original")
        
        logger.info("Encryption system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize encryption system: {str(e)}")
        return False


if __name__ == "__main__":
    success = initialize_encryption()
    sys.exit(0 if success else 1) 