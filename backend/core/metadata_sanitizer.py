"""
Metadata sanitization module for removing potentially sensitive information from files.

This module provides functionality to clean metadata from various file types
to prevent information leakage and enhance privacy.
"""

import os
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, BinaryIO
from fastapi import UploadFile, HTTPException, status

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    
# Configure logging
logger = logging.getLogger(__name__)

class MetadataSanitizer:
    """
    Provides capabilities to remove metadata from various file types.
    """
    
    def __init__(self):
        """Initialize the metadata sanitizer."""
        if not HAS_PIL:
            logger.warning("Pillow library not installed. Image metadata sanitization will be limited.")
    
    async def sanitize_image(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        Remove metadata from an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Tuple of (success, message)
        """
        if not HAS_PIL:
            return False, "Pillow library not installed. Cannot sanitize image metadata."
        
        try:
            # Convert to Path object if string
            file_path = Path(file_path) if isinstance(file_path, str) else file_path
            
            # Create a temporary file for the sanitized image
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_path.suffix) as temp_file:
                temp_path = Path(temp_file.name)
            
            # Open the image and save it without metadata
            with Image.open(file_path) as img:
                # Create a new image with the same content but without metadata
                data = list(img.getdata())
                img_without_exif = Image.new(img.mode, img.size)
                img_without_exif.putdata(data)
                
                # Save the new image without metadata
                img_without_exif.save(temp_path)
            
            # Replace the original file with the sanitized one
            shutil.move(temp_path, file_path)
            
            return True, "Image metadata successfully removed"
            
        except Exception as e:
            logger.error(f"Error sanitizing image metadata: {str(e)}")
            return False, f"Failed to sanitize image metadata: {str(e)}"
    
    async def get_image_metadata(self, file_path: Union[str, Path]) -> Dict:
        """
        Extract metadata from an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary of metadata
        """
        if not HAS_PIL:
            return {"error": "Pillow library not installed. Cannot extract image metadata."}
        
        try:
            # Convert to Path object if string
            file_path = Path(file_path) if isinstance(file_path, str) else file_path
            
            # Extract metadata
            metadata = {}
            with Image.open(file_path) as img:
                # Get EXIF data
                exif_data = img._getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag = TAGS.get(tag_id, tag_id)
                        metadata[tag] = str(value)
                
                # Get basic image info
                metadata["format"] = img.format
                metadata["mode"] = img.mode
                metadata["size"] = img.size
                
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting image metadata: {str(e)}")
            return {"error": f"Failed to extract image metadata: {str(e)}"}
    
    async def sanitize_pdf(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        Remove metadata from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # This is a placeholder for PDF metadata sanitization
            # In a real implementation, you would use a library like PyPDF2 or pdfrw
            logger.warning("PDF metadata sanitization not implemented yet")
            return False, "PDF metadata sanitization not implemented yet"
            
        except Exception as e:
            logger.error(f"Error sanitizing PDF metadata: {str(e)}")
            return False, f"Failed to sanitize PDF metadata: {str(e)}"
    
    async def sanitize_office_document(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        Remove metadata from an Office document (Word, Excel, PowerPoint).
        
        Args:
            file_path: Path to the Office document
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # This is a placeholder for Office document metadata sanitization
            # In a real implementation, you would use a library like python-docx or openpyxl
            logger.warning("Office document metadata sanitization not implemented yet")
            return False, "Office document metadata sanitization not implemented yet"
            
        except Exception as e:
            logger.error(f"Error sanitizing Office document metadata: {str(e)}")
            return False, f"Failed to sanitize Office document metadata: {str(e)}"
    
    async def sanitize_upload_file(self, upload_file: UploadFile, save_dir: str) -> Tuple[bool, str, str]:
        """
        Save an uploaded file to disk and sanitize its metadata.
        
        Args:
            upload_file: The uploaded file
            save_dir: Directory to save the file
            
        Returns:
            Tuple of (success, message, saved_path)
        """
        try:
            # Ensure the save directory exists
            os.makedirs(save_dir, exist_ok=True)
            
            # Save the file
            file_path = os.path.join(save_dir, upload_file.filename)
            with open(file_path, "wb") as f:
                content = await upload_file.read()
                f.write(content)
            
            # Reset file position for future reads
            await upload_file.seek(0)
            
            # Determine file type and sanitize accordingly
            file_ext = os.path.splitext(upload_file.filename)[1].lower()
            
            if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']:
                success, message = await self.sanitize_image(file_path)
            elif file_ext == '.pdf':
                success, message = await self.sanitize_pdf(file_path)
            elif file_ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']:
                success, message = await self.sanitize_office_document(file_path)
            else:
                success, message = False, f"Unsupported file type for metadata sanitization: {file_ext}"
            
            return success, message, file_path
            
        except Exception as e:
            logger.error(f"Error sanitizing uploaded file {upload_file.filename}: {str(e)}")
            return False, f"Failed to sanitize uploaded file: {str(e)}", ""

# Create a global instance of the metadata sanitizer
metadata_sanitizer = MetadataSanitizer() 