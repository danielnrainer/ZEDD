"""
File packing utilities for Zenodo uploads
"""

import os
import zipfile
from pathlib import Path
from typing import List, Optional

def create_zip_from_folder(folder_path: str, zip_path: Optional[str] = None) -> str:
    """Create a ZIP file from a folder using LZMA compression
    
    LZMA compression provides better compression ratios than DEFLATE,
    which is beneficial for large scientific datasets.
    
    Args:
        folder_path: Path to the folder to zip
        zip_path: Optional path for the output zip file. If not provided,
                 will use folder_path + '.zip'
    
    Returns:
        str: Path to the created ZIP file
    """
    folder = Path(folder_path)
    if not zip_path:
        zip_path = str(folder.parent / f"{folder.name}.zip")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_LZMA) as zipf:
        for file_path in folder.rglob('*'):
            if file_path.is_file():
                arcname = file_path.relative_to(folder.parent)
                zipf.write(file_path, arcname)
    
    return zip_path

def compute_checksums(files: List[str]) -> dict:
    """Compute MD5 checksums for a list of files
    
    Args:
        files: List of file paths
    
    Returns:
        dict: Mapping of file paths to their MD5 checksums
    """
    import hashlib
    
    checksums = {}
    for file_path in files:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5.update(chunk)
        checksums[file_path] = md5.hexdigest()
    
    return checksums
