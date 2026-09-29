"""
Shared Validators
=================
Authoritative validation utilities for uploads, videos, documents, and inputs.
"""

import os
from django.core.exceptions import ValidationError

ALLOWED_DOCUMENT_EXTENSIONS = {'.pptx', '.ppt', '.pdf', '.docx', '.txt'}
ALLOWED_VIDEO_EXTENSIONS = {'.mp4', '.webm', '.avi', '.mov'}
MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
MAX_VIDEO_SIZE_BYTES = 20 * 1024 * 1024     # 20 MB (as specified in concept assessment / upload requirements)


def validate_document_file(file_obj, max_size=MAX_DOCUMENT_SIZE_BYTES):
    """
    Validates uploaded document extension and size.
    Returns (is_valid, error_message).
    """
    if not file_obj:
        return False, "No file was uploaded."

    filename = getattr(file_obj, 'name', '')
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        return False, f"Unsupported file format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_DOCUMENT_EXTENSIONS))}"

    size = getattr(file_obj, 'size', 0)
    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"File size exceeds maximum limit of {max_mb:.0f} MB."

    return True, ""


def validate_video_file(file_obj, max_size=MAX_VIDEO_SIZE_BYTES):
    """
    Validates uploaded video extension and size.
    Returns (is_valid, error_message).
    """
    if not file_obj:
        return False, "No video file was uploaded."

    filename = getattr(file_obj, 'name', '')
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        return False, f"Unsupported video format '{ext}'. Allowed formats: {', '.join(sorted(ALLOWED_VIDEO_EXTENSIONS))}"

    size = getattr(file_obj, 'size', 0)
    if size > max_size:
        max_mb = max_size / (1024 * 1024)
        return False, f"Video size exceeds limit of {max_mb:.0f} MB."

    return True, ""
