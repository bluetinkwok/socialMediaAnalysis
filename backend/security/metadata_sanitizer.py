"""
Metadata Sanitizer

This module provides functionality to remove sensitive metadata from files.
"""

import os
import logging
import asyncio
import tempfile
import shutil
from typing import Tuple, Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not installed. Image metadata sanitization will be limited.")

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not installed. PDF metadata sanitization will be limited.")

class MetadataSanitizer:
    """Metadata sanitizer for various file types"""
    
    def __init__(self):
        """Initialize the metadata sanitizer"""
        self.handlers = {
            ".jpg": self._sanitize_image,
            ".jpeg": self._sanitize_image,
            ".png": self._sanitize_image,
            ".gif": self._sanitize_image,
            ".bmp": self._sanitize_image,
            ".webp": self._sanitize_image,
            ".pdf": self._sanitize_pdf,
            ".doc": self._sanitize_office_document,
            ".docx": self._sanitize_office_document,
            ".xls": self._sanitize_office_document,
            ".xlsx": self._sanitize_office_document,
        }
    
    async def sanitize_file(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Remove sensitive metadata from a file.
        
        Args:
            file_path: Path to the file to sanitize
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (success, results)
        """
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return False, {"error": "File not found"}
        
        try:
            # Get file extension
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()
            
            # Check if we have a handler for this file type
            if ext not in self.handlers:
                logger.info(f"No metadata handler for file type: {ext}")
                return True, {"status": "SKIPPED", "details": f"No metadata handler for file type: {ext}"}
            
            # Call the appropriate handler
            handler = self.handlers[ext]
            success, results = await handler(file_path)
            
            return success, results
            
        except Exception as e:
            logger.error(f"Error sanitizing file metadata: {str(e)}")
            return False, {"error": f"Metadata sanitization failed: {str(e)}"}
    
    async def _sanitize_image(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Remove metadata from an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (success, results)
        """
        if not PIL_AVAILABLE:
            return True, {"status": "SKIPPED", "details": "PIL not available for image metadata sanitization"}
        
        try:
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_path)[1])
            temp_file.close()
            
            # Extract metadata before sanitizing
            metadata_before = self._extract_image_metadata(file_path)
            
            # Open the image and save it without metadata
            with Image.open(file_path) as img:
                # Save without EXIF data
                img.save(temp_file.name, exif=b"")
            
            # Replace the original file with the sanitized one
            shutil.move(temp_file.name, file_path)
            
            # Extract metadata after sanitizing to verify
            metadata_after = self._extract_image_metadata(file_path)
            
            return True, {
                "status": "OK",
                "details": "Image metadata removed",
                "metadata_removed": metadata_before,
                "metadata_remaining": metadata_after
            }
            
        except Exception as e:
            logger.error(f"Error sanitizing image metadata: {str(e)}")
            
            # Clean up temp file if it exists
            if 'temp_file' in locals() and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
            return False, {"error": f"Image metadata sanitization failed: {str(e)}"}
    
    def _extract_image_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dict[str, Any]: Extracted metadata
        """
        if not PIL_AVAILABLE:
            return {}
        
        try:
            with Image.open(file_path) as img:
                # Extract EXIF data if available
                exif_data = {}
                if hasattr(img, '_getexif') and img._getexif():
                    for tag, value in img._getexif().items():
                        if tag in TAGS:
                            exif_data[TAGS[tag]] = str(value)
                
                # Extract basic image info
                basic_info = {
                    "format": img.format,
                    "mode": img.mode,
                    "size": img.size,
                }
                
                return {
                    "basic_info": basic_info,
                    "exif_data": exif_data
                }
                
        except Exception as e:
            logger.error(f"Error extracting image metadata: {str(e)}")
            return {}
    
    async def _sanitize_pdf(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Remove metadata from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (success, results)
        """
        if not PYPDF2_AVAILABLE:
            return True, {"status": "SKIPPED", "details": "PyPDF2 not available for PDF metadata sanitization"}
        
        try:
            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            temp_file.close()
            
            # Extract metadata before sanitizing
            metadata_before = self._extract_pdf_metadata(file_path)
            
            # Open the PDF and create a new one without metadata
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                pdf_writer = PyPDF2.PdfWriter()
                
                # Copy pages without metadata
                for page_num in range(len(pdf_reader.pages)):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Write the sanitized PDF to the temporary file
                with open(temp_file.name, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            # Replace the original file with the sanitized one
            shutil.move(temp_file.name, file_path)
            
            # Extract metadata after sanitizing to verify
            metadata_after = self._extract_pdf_metadata(file_path)
            
            return True, {
                "status": "OK",
                "details": "PDF metadata removed",
                "metadata_removed": metadata_before,
                "metadata_remaining": metadata_after
            }
            
        except Exception as e:
            logger.error(f"Error sanitizing PDF metadata: {str(e)}")
            
            # Clean up temp file if it exists
            if 'temp_file' in locals() and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
            return False, {"error": f"PDF metadata sanitization failed: {str(e)}"}
    
    def _extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Extract metadata from a PDF file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dict[str, Any]: Extracted metadata
        """
        if not PYPDF2_AVAILABLE:
            return {}
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                metadata = pdf_reader.metadata
                
                # Convert metadata to a dictionary
                if metadata:
                    return {k: str(v) for k, v in metadata.items()}
                else:
                    return {}
                    
        except Exception as e:
            logger.error(f"Error extracting PDF metadata: {str(e)}")
            return {}
    
    async def _sanitize_office_document(self, file_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Remove metadata from an Office document.
        
        Args:
            file_path: Path to the Office document
            
        Returns:
            Tuple[bool, Dict[str, Any]]: (success, results)
        """
        # Office document sanitization is more complex and would require additional libraries
        # For now, we'll just return a message indicating it's not implemented
        return True, {
            "status": "SKIPPED", 
            "details": "Office document metadata sanitization not implemented"
        }
