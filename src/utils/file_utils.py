"""
File utility functions for document processing.
"""

import hashlib
import mimetypes
import os
from pathlib import Path
from typing import Optional


def get_file_hash(file_path: str | Path, algorithm: str = "sha256") -> str:
    """
    Calculate hash of a file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (md5, sha256, etc.)
        
    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)
    
    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for chunk in iter(lambda: f.read(8192), b""):
            hash_obj.update(chunk)
    
    return hash_obj.hexdigest()


def get_mime_type(file_path: str | Path) -> Optional[str]:
    """
    Detect MIME type of a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string or None if unknown
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type


def ensure_directory(directory: str | Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory
        
    Returns:
        Path object for the directory
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_file_size(file_path: str | Path) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(file_path)


def get_file_extension(file_path: str | Path) -> str:
    """
    Get the file extension (lowercase, without dot).
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension string
    """
    return Path(file_path).suffix.lower().lstrip(".")


def safe_filename(filename: str) -> str:
    """
    Sanitize a filename to be safe for filesystem use.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove any path components
    filename = os.path.basename(filename)
    
    # Replace problematic characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, "_")
    
    # Limit length
    max_length = 200
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext
    
    return filename


def cleanup_old_files(directory: str | Path, max_age_days: int = 30) -> list[Path]:
    """
    Remove files older than specified age.
    
    Args:
        directory: Directory to clean up
        max_age_days: Maximum file age in days
        
    Returns:
        List of removed file paths
    """
    import time
    
    directory = Path(directory)
    if not directory.exists():
        return []
    
    max_age_seconds = max_age_days * 24 * 60 * 60
    current_time = time.time()
    removed = []
    
    for file_path in directory.rglob("*"):
        if file_path.is_file():
            file_age = current_time - file_path.stat().st_mtime
            if file_age > max_age_seconds:
                file_path.unlink()
                removed.append(file_path)
    
    return removed
