"""
Nucleus Runtime - Error Sanitization (Security Hardening)
==========================================================
Prevents information leakage through error messages.

SECURITY: This module addresses vulnerability C33 identified in
the exhaustive design thinking analysis (Feb 24, 2026).

Attack vector: Error messages reveal internal paths, stack traces, system info
Defense: Log detailed errors internally, return generic messages to clients

References:
- OWASP Error Handling: https://owasp.org/www-community/Improper_Error_Handling
- Evidence: E053, E054, E055
"""

import uuid
import logging
import traceback
from typing import Any, Dict, Optional, Callable
from functools import wraps
from datetime import datetime, timezone

logger = logging.getLogger("nucleus.error_sanitizer")

# Error categories with user-safe messages
ERROR_MESSAGES = {
    "file_not_found": "The requested resource was not found.",
    "permission_denied": "Access to the requested resource was denied.",
    "invalid_input": "The provided input was invalid.",
    "timeout": "The operation timed out. Please try again.",
    "rate_limited": "Too many requests. Please wait before trying again.",
    "internal_error": "An internal error occurred. Error ID: {error_id}",
    "path_traversal": "Invalid path specified.",
    "lock_error": "Resource is temporarily unavailable. Please try again.",
    "validation_error": "Input validation failed: {details}",
    "not_implemented": "This feature is not yet available.",
}


class SanitizedError(Exception):
    """
    Exception that carries both internal and sanitized messages.
    
    Use this when you need to provide specific error context to logs
    while returning safe messages to users.
    """
    
    def __init__(
        self,
        category: str,
        internal_message: str,
        details: Optional[str] = None,
        error_id: Optional[str] = None
    ):
        self.category = category
        self.internal_message = internal_message
        self.details = details
        self.error_id = error_id or str(uuid.uuid4())[:8]
        
        # Log the detailed error
        logger.error(
            f"[{self.error_id}] {category}: {internal_message}",
            extra={"error_id": self.error_id, "category": category}
        )
        
        # Create user-safe message
        template = ERROR_MESSAGES.get(category, ERROR_MESSAGES["internal_error"])
        self.user_message = template.format(error_id=self.error_id, details=details or "")
        
        super().__init__(self.user_message)


def sanitize_error(
    error: Exception,
    category: str = "internal_error",
    context: Optional[str] = None
) -> str:
    """
    Convert any exception to a sanitized error message.
    
    Logs the full error internally and returns a safe message.
    
    Args:
        error: The original exception
        category: Error category for user message
        context: Additional context for logging
        
    Returns:
        User-safe error message
    """
    error_id = str(uuid.uuid4())[:8]
    
    # Log full details internally
    logger.error(
        f"[{error_id}] {category}: {str(error)}"
        + (f" | Context: {context}" if context else ""),
        exc_info=True,
        extra={
            "error_id": error_id,
            "category": category,
            "error_type": type(error).__name__,
        }
    )
    
    # Return sanitized message
    template = ERROR_MESSAGES.get(category, ERROR_MESSAGES["internal_error"])
    return template.format(error_id=error_id, details="")


def safe_error_handler(category: str = "internal_error"):
    """
    Decorator that catches exceptions and returns sanitized errors.
    
    Args:
        category: Default error category
        
    Example:
        @safe_error_handler("file_not_found")
        def read_file(path):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SanitizedError:
                raise  # Already sanitized
            except FileNotFoundError as e:
                raise SanitizedError("file_not_found", str(e)) from e
            except PermissionError as e:
                raise SanitizedError("permission_denied", str(e)) from e
            except ValueError as e:
                raise SanitizedError("invalid_input", str(e)) from e
            except TimeoutError as e:
                raise SanitizedError("timeout", str(e)) from e
            except Exception as e:
                raise SanitizedError(category, str(e)) from e
        return wrapper
    return decorator


def format_safe_response(
    success: bool,
    data: Optional[Any] = None,
    error: Optional[str] = None,
    error_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format a response with sanitized error information.
    
    Args:
        success: Whether the operation succeeded
        data: Response data (if success)
        error: Sanitized error message (if failure)
        error_id: Error tracking ID
        
    Returns:
        Formatted response dict
    """
    response = {"success": success}
    
    if success:
        if data is not None:
            response["data"] = data
    else:
        response["error"] = error or "An error occurred"
        if error_id:
            response["error_id"] = error_id
            response["message"] = (
                f"If this persists, please report error ID: {error_id}"
            )
    
    return response


def log_operation(
    operation: str,
    user_id: Optional[str] = None,
    resource: Optional[str] = None,
    result: Optional[str] = None,
    **extra
) -> str:
    """
    Log an operation for audit trail.
    
    Args:
        operation: Name of the operation
        user_id: User/agent identifier
        resource: Resource being accessed
        result: Operation result (success/failure)
        **extra: Additional context
        
    Returns:
        Operation ID for tracking
    """
    op_id = str(uuid.uuid4())[:12]
    
    logger.info(
        f"[AUDIT] {op_id} | {operation} | user={user_id} | resource={resource} | result={result}",
        extra={
            "operation_id": op_id,
            "operation": operation,
            "user_id": user_id,
            "resource": resource,
            "result": result,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            **extra
        }
    )
    
    return op_id


class ErrorContext:
    """
    Context manager for safe error handling with automatic logging.
    
    Example:
        with ErrorContext("reading config", category="file_not_found") as ctx:
            data = read_file(path)
            ctx.success(data)
    """
    
    def __init__(self, operation: str, category: str = "internal_error"):
        self.operation = operation
        self.category = category
        self.error_id = str(uuid.uuid4())[:8]
        self._result = None
        self._error = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            # Log and sanitize the error
            logger.error(
                f"[{self.error_id}] {self.operation} failed: {exc_val}",
                exc_info=True,
                extra={"error_id": self.error_id, "operation": self.operation}
            )
            self._error = sanitize_error(exc_val, self.category, self.operation)
            # Don't suppress the exception
            return False
        return False
    
    def success(self, result: Any = None):
        """Mark operation as successful."""
        self._result = result
        log_operation(self.operation, result="success")
    
    @property
    def result(self) -> Any:
        return self._result
    
    @property
    def error(self) -> Optional[str]:
        return self._error
