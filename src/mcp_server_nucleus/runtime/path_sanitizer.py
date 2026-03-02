"""
Nucleus Runtime - Path Sanitization (Security Hardening)
=========================================================
Prevents path traversal attacks by validating all user-supplied paths.

CRITICAL SECURITY: This module addresses vulnerability C20 identified in
the exhaustive design thinking analysis (Feb 24, 2026).

Attack vector: User supplies task_id="../../../etc/passwd"
Defense: All paths must resolve within the .brain directory.

References:
- OWASP Path Traversal: https://owasp.org/www-community/attacks/Path_Traversal
- Evidence: E029, E030, E031
"""

import re
import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger("nucleus.path_sanitizer")

# Characters forbidden in path components (cross-platform)
FORBIDDEN_CHARS = set('<>:"|?*\x00')

# Patterns that indicate path traversal attempts
TRAVERSAL_PATTERNS = [
    r'\.\.',           # Parent directory
    r'^/',             # Absolute path (Unix)
    r'^[A-Za-z]:',     # Absolute path (Windows)
    r'\\\\',           # UNC path
    r'%2e%2e',         # URL-encoded ..
    r'%252e%252e',     # Double URL-encoded ..
]


class PathTraversalError(Exception):
    """Raised when a path traversal attempt is detected."""
    pass


class InvalidPathError(Exception):
    """Raised when a path contains invalid characters."""
    pass


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing dangerous characters.
    
    Args:
        filename: User-supplied filename
        
    Returns:
        Sanitized filename safe for use in filesystem
        
    Raises:
        InvalidPathError: If filename is empty or only contains forbidden chars
    """
    if not filename:
        raise InvalidPathError("Filename cannot be empty")
    
    # Remove forbidden characters
    sanitized = ''.join(c for c in filename if c not in FORBIDDEN_CHARS)
    
    # Replace path separators with underscores
    sanitized = sanitized.replace('/', '_').replace('\\', '_')
    
    # Remove any remaining .. sequences
    sanitized = sanitized.replace('..', '__')
    
    # Limit length (Windows max is 255)
    sanitized = sanitized[:200]
    
    # Ensure we have something left
    if not sanitized or sanitized.isspace():
        raise InvalidPathError(f"Filename '{filename}' contains only invalid characters")
    
    return sanitized


def validate_path_component(component: str) -> bool:
    """
    Validate a single path component (directory or filename).
    
    Args:
        component: Single path component to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not component:
        return False
    
    # Check for forbidden characters
    if any(c in component for c in FORBIDDEN_CHARS):
        return False
    
    # Check for traversal patterns
    for pattern in TRAVERSAL_PATTERNS:
        if re.search(pattern, component, re.IGNORECASE):
            return False
    
    return True


def sanitize_path(
    user_input: str,
    base_dir: Union[str, Path],
    allow_subdirs: bool = True
) -> Path:
    """
    Sanitize a user-supplied path and ensure it stays within base_dir.
    
    This is the primary security function for preventing path traversal.
    
    Args:
        user_input: User-supplied path string (e.g., task_id, engram_key)
        base_dir: The base directory that paths must stay within
        allow_subdirs: Whether to allow subdirectories within base_dir
        
    Returns:
        Resolved, validated Path object
        
    Raises:
        PathTraversalError: If the path would escape base_dir
        InvalidPathError: If the path contains invalid characters
        
    Example:
        >>> sanitize_path("task_123", "/brain/tasks")
        PosixPath('/brain/tasks/task_123')
        
        >>> sanitize_path("../../../etc/passwd", "/brain/tasks")
        PathTraversalError: Path traversal attempt detected
    """
    if not user_input:
        raise InvalidPathError("Path input cannot be empty")
    
    base = Path(base_dir).resolve()
    
    # First check for obvious traversal patterns
    for pattern in TRAVERSAL_PATTERNS:
        if re.search(pattern, user_input, re.IGNORECASE):
            logger.warning(f"Path traversal attempt detected: {user_input}")
            raise PathTraversalError(f"Path traversal attempt detected")
    
    # Check for null bytes (can bypass some checks)
    if '\x00' in user_input:
        logger.warning(f"Null byte in path: {user_input}")
        raise PathTraversalError("Invalid null byte in path")
    
    # Sanitize the input
    sanitized = sanitize_filename(user_input) if not allow_subdirs else user_input
    
    # If subdirs allowed, sanitize each component
    if allow_subdirs:
        components = sanitized.replace('\\', '/').split('/')
        sanitized_components = []
        for comp in components:
            if comp and comp != '.':
                if not validate_path_component(comp):
                    raise InvalidPathError(f"Invalid path component: {comp}")
                sanitized_components.append(sanitize_filename(comp))
        sanitized = '/'.join(sanitized_components)
    
    # Construct and resolve the full path
    full_path = (base / sanitized).resolve()
    
    # Critical check: ensure path is within base_dir
    try:
        full_path.relative_to(base)
    except ValueError:
        logger.warning(f"Path escape attempt: {user_input} -> {full_path}")
        raise PathTraversalError(f"Path must stay within {base_dir}")
    
    return full_path


def safe_join(base_dir: Union[str, Path], *parts: str) -> Path:
    """
    Safely join path components, preventing traversal.
    
    Args:
        base_dir: Base directory
        *parts: Path components to join
        
    Returns:
        Safe, resolved path
        
    Raises:
        PathTraversalError: If resulting path would escape base_dir
    """
    base = Path(base_dir).resolve()
    
    # Sanitize each part
    sanitized_parts = []
    for part in parts:
        if part:
            sanitized_parts.append(sanitize_filename(part))
    
    # Join and resolve
    full_path = base.joinpath(*sanitized_parts).resolve()
    
    # Verify containment
    try:
        full_path.relative_to(base)
    except ValueError:
        raise PathTraversalError(f"Path escape attempt detected")
    
    return full_path


def is_safe_path(path: Union[str, Path], base_dir: Union[str, Path]) -> bool:
    """
    Check if a path is safe (within base_dir) without raising exceptions.
    
    Args:
        path: Path to check
        base_dir: Base directory that path must be within
        
    Returns:
        True if safe, False otherwise
    """
    try:
        resolved = Path(path).resolve()
        base = Path(base_dir).resolve()
        resolved.relative_to(base)
        return True
    except (ValueError, OSError):
        return False


# Convenience wrapper for common use case
def sanitize_id(user_id: str, base_dir: Union[str, Path]) -> Path:
    """
    Sanitize a user-supplied ID (task_id, engram_key, etc.) for use as filename.
    
    Args:
        user_id: User-supplied identifier
        base_dir: Directory where the file will be created
        
    Returns:
        Safe path for the ID within base_dir
    """
    return sanitize_path(user_id, base_dir, allow_subdirs=False)
