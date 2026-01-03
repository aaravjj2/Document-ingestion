"""
Validation utilities for document processing.
"""

from typing import Optional

from ..core.config import get_settings


# Allowed MIME types for document upload
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
    "image/gif",
    "image/webp",
}

# File extensions mapped to MIME types
EXTENSION_MIME_MAP = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "tiff": "image/tiff",
    "tif": "image/tiff",
    "bmp": "image/bmp",
    "gif": "image/gif",
    "webp": "image/webp",
}


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


def validate_file_size(file_size: int, max_size_mb: Optional[float] = None) -> bool:
    """
    Validate that a file is within the allowed size limit.
    
    Args:
        file_size: File size in bytes
        max_size_mb: Maximum allowed size in MB (uses config default if None)
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If file exceeds size limit
    """
    if max_size_mb is None:
        settings = get_settings()
        max_size_mb = settings.max_upload_size_mb
    
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        raise ValidationError(
            f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds "
            f"maximum allowed size ({max_size_mb} MB)"
        )
    
    return True


def validate_file_type(
    mime_type: Optional[str] = None,
    filename: Optional[str] = None,
    allowed_types: Optional[set[str]] = None
) -> bool:
    """
    Validate that a file type is allowed.
    
    Args:
        mime_type: MIME type of the file
        filename: Filename to extract extension from
        allowed_types: Set of allowed MIME types (uses default if None)
        
    Returns:
        True if valid
        
    Raises:
        ValidationError: If file type is not allowed
    """
    if allowed_types is None:
        allowed_types = ALLOWED_MIME_TYPES
    
    # Check MIME type directly if provided
    if mime_type and mime_type in allowed_types:
        return True
    
    # Check by file extension
    if filename:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if extension in EXTENSION_MIME_MAP:
            mapped_mime = EXTENSION_MIME_MAP[extension]
            if mapped_mime in allowed_types:
                return True
    
    # Build error message
    error_msg = "File type not allowed."
    if mime_type:
        error_msg += f" Got: {mime_type}."
    if filename:
        error_msg += f" Filename: {filename}."
    error_msg += f" Allowed types: {', '.join(sorted(allowed_types))}"
    
    raise ValidationError(error_msg)


def validate_document_upload(
    filename: str,
    file_size: int,
    mime_type: Optional[str] = None
) -> dict:
    """
    Perform full validation for document upload.
    
    Args:
        filename: Name of the uploaded file
        file_size: Size of the file in bytes
        mime_type: MIME type if known
        
    Returns:
        Dictionary with validation results and detected info
        
    Raises:
        ValidationError: If validation fails
    """
    # Validate file size
    validate_file_size(file_size)
    
    # Validate and detect file type
    validate_file_type(mime_type=mime_type, filename=filename)
    
    # Determine final MIME type
    final_mime_type = mime_type
    if not final_mime_type:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        final_mime_type = EXTENSION_MIME_MAP.get(extension, "application/octet-stream")
    
    # Determine if it's a PDF or image
    is_pdf = final_mime_type == "application/pdf"
    is_image = final_mime_type.startswith("image/")
    
    return {
        "valid": True,
        "filename": filename,
        "file_size": file_size,
        "mime_type": final_mime_type,
        "is_pdf": is_pdf,
        "is_image": is_image,
    }


def validate_page_range(
    start_page: int,
    end_page: int,
    total_pages: int
) -> tuple[int, int]:
    """
    Validate and normalize page range.
    
    Args:
        start_page: Starting page (1-indexed)
        end_page: Ending page (1-indexed, -1 for last page)
        total_pages: Total number of pages in document
        
    Returns:
        Tuple of (start_page, end_page) normalized values
        
    Raises:
        ValidationError: If page range is invalid
    """
    if total_pages <= 0:
        raise ValidationError("Document has no pages")
    
    # Normalize start page
    if start_page < 1:
        start_page = 1
    if start_page > total_pages:
        raise ValidationError(
            f"Start page ({start_page}) exceeds total pages ({total_pages})"
        )
    
    # Normalize end page (-1 means last page)
    if end_page == -1 or end_page > total_pages:
        end_page = total_pages
    if end_page < start_page:
        raise ValidationError(
            f"End page ({end_page}) cannot be less than start page ({start_page})"
        )
    
    return start_page, end_page
