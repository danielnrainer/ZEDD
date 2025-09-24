"""
File validation services

Provides validation for files before upload to catch issues early
and provide better user feedback.
"""

import os
from pathlib import Path
from typing import Optional, Tuple

from ..core.interfaces import FileValidator, ValidationError


class ZenodoFileValidator(FileValidator):
    """File validator for Zenodo uploads"""
    
    # Zenodo limits
    MAX_FILE_SIZE = 50 * 1024 * 1024 * 1024  # 50GB in bytes
    MAX_FILES_PER_RECORD = 100
    
    def validate(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file for Zenodo upload
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            path = Path(file_path)
            
            # Check if file exists
            if not path.exists():
                return False, f"File not found: {file_path}"
            
            # Check if it's actually a file
            if not path.is_file():
                return False, f"Path is not a file: {file_path}"
            
            # Check if file is readable
            try:
                with open(file_path, 'rb') as f:
                    f.read(1)  # Try to read first byte
            except PermissionError:
                return False, f"File is not readable (permission denied): {file_path}"
            except OSError as e:
                return False, f"Cannot read file: {e}"
            
            # Check file size
            file_size = path.stat().st_size
            if file_size > self.MAX_FILE_SIZE:
                size_gb = file_size / (1024**3)
                max_gb = self.MAX_FILE_SIZE / (1024**3)
                return False, f"File too large: {size_gb:.2f}GB. Maximum allowed: {max_gb}GB"
            
            # Check for empty files
            if file_size == 0:
                return False, f"File is empty: {file_path}"
            
            # File is valid
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def get_file_info(self, file_path: str) -> dict:
        """
        Get detailed file information
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file information
        """
        try:
            path = Path(file_path)
            stat = path.stat()
            
            return {
                'path': str(path.absolute()),
                'name': path.name,
                'size_bytes': stat.st_size,
                'size_mb': stat.st_size / (1024 * 1024),
                'size_gb': stat.st_size / (1024**3),
                'exists': path.exists(),
                'is_file': path.is_file(),
                'readable': os.access(path, os.R_OK),
                'extension': path.suffix.lower(),
                'within_size_limit': stat.st_size <= self.MAX_FILE_SIZE
            }
        except Exception as e:
            return {
                'path': file_path,
                'error': str(e)
            }


class BatchFileValidator:
    """Validator for multiple files"""
    
    def __init__(self, file_validator: FileValidator):
        self.file_validator = file_validator
    
    def validate_multiple(self, file_paths: list[str]) -> Tuple[bool, list[str], dict]:
        """
        Validate multiple files
        
        Args:
            file_paths: List of file paths to validate
            
        Returns:
            Tuple of (all_valid, error_messages, validation_results)
        """
        results = {}
        error_messages = []
        all_valid = True
        
        if len(file_paths) > ZenodoFileValidator.MAX_FILES_PER_RECORD:
            error_messages.append(
                f"Too many files: {len(file_paths)}. "
                f"Maximum allowed: {ZenodoFileValidator.MAX_FILES_PER_RECORD}"
            )
            all_valid = False
        
        for file_path in file_paths:
            is_valid, error_msg = self.file_validator.validate(file_path)
            results[file_path] = {
                'valid': is_valid,
                'error': error_msg
            }
            
            if not is_valid:
                all_valid = False
                error_messages.append(f"{Path(file_path).name}: {error_msg}")
        
        return all_valid, error_messages, results