"""
Nucleus Runtime - Timeout Handler (Reliability Hardening)
==========================================================
Prevents unbounded operations from hanging the MCP server.

RELIABILITY: This module addresses vulnerability C18 identified in
the exhaustive design thinking analysis (Feb 24, 2026).

Attack vector: MCP tool runs indefinitely, hangs server
Defense: Configurable timeouts on all operations

References:
- Evidence: E027
"""

import signal
import threading
import functools
import logging
from typing import Any, Callable, Optional, TypeVar
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

logger = logging.getLogger("nucleus.timeout_handler")

# Type variable for decorated function return type
T = TypeVar('T')

# Default timeouts (seconds)
DEFAULT_TIMEOUT = 30.0
MAX_TIMEOUT = 300.0  # 5 minutes absolute max

# Global thread pool for timeout execution
_executor: Optional[ThreadPoolExecutor] = None


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the global thread pool."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="nucleus-timeout")
    return _executor


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


def with_timeout(
    timeout: float = DEFAULT_TIMEOUT,
    error_message: Optional[str] = None
) -> Callable:
    """
    Decorator to add timeout to a function.
    
    Works on both sync and async functions.
    Uses threading for cross-platform compatibility.
    
    Args:
        timeout: Maximum seconds to allow (default 30)
        error_message: Custom timeout message
        
    Example:
        @with_timeout(10.0)
        def slow_operation():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            actual_timeout = min(timeout, MAX_TIMEOUT)
            executor = _get_executor()
            
            future = executor.submit(func, *args, **kwargs)
            
            try:
                return future.result(timeout=actual_timeout)
            except FutureTimeout:
                msg = error_message or f"Operation timed out after {actual_timeout}s"
                logger.warning(f"Timeout in {func.__name__}: {msg}")
                raise TimeoutError(msg)
        
        return wrapper
    return decorator


def run_with_timeout(
    func: Callable[..., T],
    args: tuple = (),
    kwargs: Optional[dict] = None,
    timeout: float = DEFAULT_TIMEOUT,
    default: Optional[T] = None
) -> T:
    """
    Run a function with a timeout.
    
    Args:
        func: Function to run
        args: Positional arguments
        kwargs: Keyword arguments
        timeout: Maximum seconds
        default: Value to return on timeout (if None, raises TimeoutError)
        
    Returns:
        Function result or default on timeout
    """
    kwargs = kwargs or {}
    executor = _get_executor()
    
    future = executor.submit(func, *args, **kwargs)
    
    try:
        return future.result(timeout=min(timeout, MAX_TIMEOUT))
    except FutureTimeout:
        if default is not None:
            logger.warning(f"Timeout in {func.__name__}, returning default")
            return default
        raise TimeoutError(f"Operation timed out after {timeout}s")


class OperationTimeout:
    """
    Context manager for operations with timeout.
    
    Example:
        with OperationTimeout(30.0, "Reading large file"):
            data = read_file(path)
    """
    
    def __init__(self, timeout: float, operation: str = "operation"):
        self.timeout = min(timeout, MAX_TIMEOUT)
        self.operation = operation
        self._timer: Optional[threading.Timer] = None
        self._timed_out = False
    
    def __enter__(self):
        self._timer = threading.Timer(self.timeout, self._on_timeout)
        self._timer.daemon = True
        self._timer.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._timer:
            self._timer.cancel()
        return False
    
    def _on_timeout(self):
        self._timed_out = True
        logger.warning(f"Timeout in {self.operation} after {self.timeout}s")
    
    @property
    def timed_out(self) -> bool:
        return self._timed_out
    
    def check(self):
        """Check if timeout occurred and raise if so."""
        if self._timed_out:
            raise TimeoutError(f"{self.operation} timed out after {self.timeout}s")


# Specific timeout decorators for different operation types
def tool_timeout(timeout: float = 30.0):
    """Decorator for MCP tool functions."""
    return with_timeout(timeout, "MCP tool operation timed out")


def file_timeout(timeout: float = 10.0):
    """Decorator for file operations."""
    return with_timeout(timeout, "File operation timed out")


def network_timeout(timeout: float = 60.0):
    """Decorator for network operations."""
    return with_timeout(timeout, "Network operation timed out")


def cleanup():
    """Clean up the global executor (call on shutdown)."""
    global _executor
    if _executor:
        _executor.shutdown(wait=False)
        _executor = None
