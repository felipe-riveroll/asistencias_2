"""
Retry utilities for handling transient failures in external operations.

This module provides retry patterns with exponential backoff, jitter,
and configurable strategies for handling network operations, database connections,
and other external service calls that may fail intermittently.
"""

import time
import random
import logging
from typing import TypeVar, Callable, Any, Optional, Type, List, Union, Dict
from functools import wraps
from dataclasses import dataclass, field
from enum import Enum

from exceptions import RetryExhaustedError, AttendanceSystemError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BackoffStrategy(Enum):
    """Enumeration of backoff strategies for retry attempts."""
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"
    FIXED = "fixed"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True  # Add randomness to prevent thundering herd
    exponential_base: float = 2.0  # Base for exponential backoff
    retry_on: Optional[List[Type[Exception]]] = None  # Specific exceptions to retry on
    retry_condition: Optional[Callable[[Exception], bool]] = None  # Custom retry condition
    on_retry_callback: Optional[Callable[[Exception, int], None]] = None  # Callback for each retry
    log_retries: bool = True  # Whether to log retry attempts
    
    def __post_init__(self) -> None:
        """Post-initialization validation."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay <= 0:
            raise ValueError("max_delay must be positive")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be greater than 1")


class RetryState:
    """Tracks the state of a retry operation."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self.start_time = time.time()
        self.retry_history: List[Dict[str, Any]] = []
    
    def should_retry(self, exception: Exception) -> bool:
        """Determine if the operation should be retried based on the exception."""
        self.attempt += 1
        self.last_exception = exception
        
        # Check if we've exceeded max attempts
        if self.attempt >= self.config.max_attempts:
            return False
        
        # Check specific exception types
        if self.config.retry_on:
            return any(isinstance(exception, exc_type) for exc_type in self.config.retry_on)
        
        # Check custom retry condition
        if self.config.retry_condition:
            return self.config.retry_condition(exception)
        
        # Default: retry on most exceptions except some specific ones
        non_retryable_exceptions = (
            ValueError, TypeError, KeyError, IndexError, 
            AttributeError, ImportError, SyntaxError
        )
        return not isinstance(exception, non_retryable_exceptions)
    
    def record_attempt(self, exception: Exception) -> None:
        """Record information about a retry attempt."""
        attempt_info = {
            'attempt': self.attempt,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'timestamp': time.time(),
            'elapsed_time': time.time() - self.start_time
        }
        self.retry_history.append(attempt_info)
    
    def calculate_delay(self) -> float:
        """Calculate the delay before the next retry attempt."""
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.base_delay
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay * self.attempt
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.exponential_base ** (self.attempt - 1))
        elif self.config.backoff_strategy == BackoffStrategy.FIBONACCI:
            delay = self.config.base_delay * self._fibonacci(self.attempt)
        else:
            delay = self.config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, self.config.max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)
        
        # Ensure delay is not negative
        return max(0, delay)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate the nth Fibonacci number."""
        if n <= 0:
            return 0
        elif n == 1:
            return 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            return b


class RetryEngine:
    """Engine for executing operations with retry logic."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a function with retry logic."""
        state = RetryState(self.config)
        
        while True:
            try:
                return func(*args, **kwargs)
            
            except Exception as exception:
                state.record_attempt(exception)
                
                if not state.should_retry(exception):
                    # Retry exhausted, raise custom exception
                    raise RetryExhaustedError(
                        f"Operation failed after {state.attempt} attempts: {str(exception)}",
                        max_attempts=self.config.max_attempts,
                        last_error=exception,
                        context={
                            'function': func.__name__,
                            'total_time': time.time() - state.start_time,
                            'retry_history': state.retry_history
                        }
                    )
                
                # Calculate delay and wait
                delay = state.calculate_delay()
                
                # Log retry attempt
                if self.config.log_retries:
                    logger.warning(
                        f"Retry attempt {state.attempt}/{self.config.max_attempts} for {func.__name__} "
                        f"after {delay:.2f}s delay. Error: {str(exception)}"
                    )
                
                # Call retry callback if provided
                if self.config.on_retry_callback:
                    try:
                        self.config.on_retry_callback(exception, state.attempt)
                    except Exception as callback_error:
                        logger.error(f"Retry callback failed: {callback_error}")
                
                # Wait before retry
                if delay > 0:
                    time.sleep(delay)


# Decorator for easy function retry decoration
def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    jitter: bool = True,
    retry_on: Optional[List[Type[Exception]]] = None,
    retry_condition: Optional[Callable[[Exception], bool]] = None,
    on_retry_callback: Optional[Callable[[Exception, int], None]] = None,
    log_retries: bool = True
) -> Callable:
    """Decorator to add retry functionality to a function."""
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            backoff_strategy=backoff_strategy,
            jitter=jitter,
            retry_on=retry_on,
            retry_condition=retry_condition,
            on_retry_callback=on_retry_callback,
            log_retries=log_retries
        )
        engine = RetryEngine(config)
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return engine.execute(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# Predefined retry configurations for common use cases
class RetryPresets:
    """Predefined retry configurations for common scenarios."""
    
    @staticmethod
    def network_operations() -> RetryConfig:
        """Retry configuration for network operations."""
        return RetryConfig(
            max_attempts=5,
            base_delay=0.5,
            max_delay=30.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=True,
            retry_on=[ConnectionError, TimeoutError, OSError]
        )
    
    @staticmethod
    def database_operations() -> RetryConfig:
        """Retry configuration for database operations."""
        return RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            max_delay=10.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter=False,
            retry_on=[ConnectionError, TimeoutError]
        )
    
    @staticmethod
    def api_calls() -> RetryConfig:
        """Retry configuration for API calls."""
        return RetryConfig(
            max_attempts=4,
            base_delay=2.0,
            max_delay=60.0,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            jitter=True,
            retry_condition=lambda exc: isinstance(exc, (ConnectionError, TimeoutError)) or 
                                   (hasattr(exc, 'status_code') and getattr(exc, 'status_code') in [429, 502, 503, 504])
        )
    
    @staticmethod
    def file_operations() -> RetryConfig:
        """Retry configuration for file operations."""
        return RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            max_delay=5.0,
            backoff_strategy=BackoffStrategy.FIXED,
            jitter=True,
            retry_on=[IOError, OSError, PermissionError]
        )


# Utility functions for common retry scenarios
def with_network_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that applies network retry configuration to a function."""
    return retry(**RetryPresets.network_operations().__dict__)(func)


def with_database_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that applies database retry configuration to a function."""
    return retry(**RetryPresets.database_operations().__dict__)(func)


def with_api_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that applies API retry configuration to a function."""
    return retry(**RetryPresets.api_calls().__dict__)(func)


def with_file_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator that applies file operation retry configuration to a function."""
    return retry(**RetryPresets.file_operations().__dict__)(func)


# Context manager for retry operations
class RetryContext:
    """Context manager for retry operations."""
    
    def __init__(self, config: RetryConfig):
        self.config = config
        self.engine = RetryEngine(config)
    
    def __enter__(self) -> 'RetryContext':
        return self
    
    def __exit__(self, exc_type: Optional[Type[BaseException]], 
                 exc_val: Optional[BaseException], 
                 exc_tb: Optional[Any]) -> bool:
        # Context manager doesn't suppress exceptions
        return False
    
    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute a function within this retry context."""
        return self.engine.execute(func, *args, **kwargs)


# Utility function to create retry contexts
def retry_context(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    jitter: bool = True,
    **kwargs
) -> RetryContext:
    """Create a retry context with the specified configuration."""
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        backoff_strategy=backoff_strategy,
        jitter=jitter,
        **kwargs
    )
    return RetryContext(config)