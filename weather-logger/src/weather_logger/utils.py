"""
Utility functions for Weather Logger.
"""
import logging
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Tuple, Type


def setup_logging(log_file: str, log_level: str = "INFO", log_format: str = None) -> None:
    """
    Setup logging configuration with file and console handlers.

    Args:
        log_file: Path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log message format string
    """
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Create logs directory if it doesn't exist
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Remove existing handlers
    logger.handlers.clear()

    # File handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    console_formatter = logging.Formatter(log_format)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential: If True, use exponential backoff; otherwise use constant delay
        exceptions: Tuple of exception types to catch and retry

    Returns:
        Decorated function

    Example:
        @retry(max_attempts=3, base_delay=1, exceptions=(requests.RequestException,))
        def fetch_data():
            return requests.get("https://api.example.com/data")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger(func.__module__)

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    # Calculate delay
                    if exponential:
                        delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    else:
                        delay = base_delay

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}), "
                        f"retrying in {delay:.1f}s: {e}"
                    )
                    time.sleep(delay)

            return None  # Should never reach here

        return wrapper
    return decorator


def validate_mac_address(mac: str) -> bool:
    """
    Validate MAC address format.

    Accepts formats:
    - XX:XX:XX:XX:XX:XX
    - XXXXXXXXXXXX

    Args:
        mac: MAC address string

    Returns:
        True if valid, False otherwise
    """
    import re

    # Pattern with colons
    pattern1 = re.compile(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$')
    # Pattern without colons
    pattern2 = re.compile(r'^[0-9A-Fa-f]{12}$')

    return bool(pattern1.match(mac) or pattern2.match(mac))


def sanitize_for_logging(data: Any) -> Any:
    """
    Sanitize data for logging by redacting sensitive information.

    Args:
        data: Data to sanitize (str, dict, etc.)

    Returns:
        Sanitized data
    """
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = {"api_key", "application_key", "password", "secret", "token"}

        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = sanitize_for_logging(value)
            else:
                sanitized[key] = value

        return sanitized
    elif isinstance(data, str):
        # Don't log long strings that might contain keys
        if len(data) > 100:
            return data[:50] + "...[truncated]"
        return data
    else:
        return data


def ensure_directory(path: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path
    """
    Path(path).mkdir(parents=True, exist_ok=True)
