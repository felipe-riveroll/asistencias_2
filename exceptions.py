"""
Custom exception classes for the attendance reporting system.

This module defines a hierarchy of custom exceptions that provide clear,
specific error handling throughout the application. Each exception is
designed to handle specific error scenarios with appropriate context.
"""

from typing import Optional, Any, Dict
import logging

logger = logging.getLogger(__name__)


class AttendanceSystemError(Exception):
    """Base exception for all attendance system errors.
    
    Attributes:
        message: Human-readable error description
        error_code: Unique error identifier for logging/tracking
        context: Additional context information
        original_error: The original exception that caused this error
    """
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        self.original_error = original_error
        
        # Log the exception with structured information
        logger.error(
            f"{self.error_code}: {message}",
            extra={
                "error_code": self.error_code,
                "context": self.context,
                "original_error": str(original_error) if original_error else None
            }
        )
    
    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} (Context: {context_str})"
        return self.message


class ConfigurationError(AttendanceSystemError):
    """Raised when there's an error in system configuration."""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if config_key:
            context['config_key'] = config_key
        if config_value is not None:
            context['config_value'] = config_value
        kwargs['context'] = context
        
        super().__init__(message, error_code="CONFIG_ERROR", **kwargs)


class DataValidationError(AttendanceSystemError):
    """Raised when data validation fails during processing."""
    
    def __init__(
        self, 
        message: str, 
        field_name: Optional[str] = None,
        field_value: Optional[Any] = None,
        validation_rule: Optional[str] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if field_name:
            context['field_name'] = field_name
        if field_value is not None:
            context['field_value'] = field_value
        if validation_rule:
            context['validation_rule'] = validation_rule
        kwargs['context'] = context
        
        super().__init__(message, error_code="DATA_VALIDATION_ERROR", **kwargs)


class APIConnectionError(AttendanceSystemError):
    """Raised when API connectivity or authentication fails."""
    
    def __init__(
        self, 
        message: str, 
        api_endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        response_text: Optional[str] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if api_endpoint:
            context['api_endpoint'] = api_endpoint
        if status_code:
            context['status_code'] = status_code
        if response_text:
            context['response_text'] = response_text[:500]  # Truncate long responses
        kwargs['context'] = context
        
        super().__init__(message, error_code="API_CONNECTION_ERROR", **kwargs)


class DatabaseConnectionError(AttendanceSystemError):
    """Raised when database operations fail."""
    
    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None,
        database: Optional[str] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if query:
            context['query'] = query[:200]  # Truncate long queries
        if database:
            context['database'] = database
        kwargs['context'] = context
        
        super().__init__(message, error_code="DATABASE_CONNECTION_ERROR", **kwargs)


class DataProcessingError(AttendanceSystemError):
    """Raised when data processing logic encounters an error."""
    
    def __init__(
        self, 
        message: str, 
        employee_id: Optional[str] = None,
        date: Optional[str] = None,
        processing_step: Optional[str] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if employee_id:
            context['employee_id'] = employee_id
        if date:
            context['date'] = date
        if processing_step:
            context['processing_step'] = processing_step
        kwargs['context'] = context
        
        super().__init__(message, error_code="DATA_PROCESSING_ERROR", **kwargs)


class ReportGenerationError(AttendanceSystemError):
    """Raised when report generation fails."""
    
    def __init__(
        self, 
        message: str, 
        report_type: Optional[str] = None,
        output_file: Optional[str] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if report_type:
            context['report_type'] = report_type
        if output_file:
            context['output_file'] = output_file
        kwargs['context'] = context
        
        super().__init__(message, error_code="REPORT_GENERATION_ERROR", **kwargs)


class ValidationError(AttendanceSystemError):
    """Raised when input validation fails."""
    
    def __init__(
        self, 
        message: str, 
        input_value: Optional[Any] = None,
        validation_type: Optional[str] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if input_value is not None:
            context['input_value'] = str(input_value)[:100]
        if validation_type:
            context['validation_type'] = validation_type
        kwargs['context'] = context
        
        super().__init__(message, error_code="VALIDATION_ERROR", **kwargs)


class RetryExhaustedError(AttendanceSystemError):
    """Raised when retry attempts are exhausted."""
    
    def __init__(
        self, 
        message: str, 
        max_attempts: Optional[int] = None,
        last_error: Optional[Exception] = None,
        **kwargs
    ) -> None:
        context = kwargs.get('context', {})
        if max_attempts:
            context['max_attempts'] = max_attempts
        if last_error:
            context['last_error'] = str(last_error)
        kwargs['context'] = context
        kwargs['original_error'] = last_error
        
        super().__init__(message, error_code="RETRY_EXHAUSTED_ERROR", **kwargs)


# Exception handling utilities
def handle_exception(
    exception: Exception,
    context: Optional[Dict[str, Any]] = None,
    reraise: bool = True
) -> Optional[AttendanceSystemError]:
    """
    Convert generic exceptions to appropriate custom exceptions.
    
    Args:
        exception: The original exception to handle
        context: Additional context information
        reraise: Whether to reraise the custom exception
        
    Returns:
        Custom exception instance if reraise=False, None if reraise=True
        
    Raises:
        AttendanceSystemError: Always raised if reraise=True
    """
    context = context or {}
    
    # Map common exceptions to custom exceptions
    if isinstance(exception, (ConnectionError, TimeoutError)):
        custom_error = APIConnectionError(
            f"Network connectivity error: {str(exception)}",
            context=context,
            original_error=exception
        )
    elif isinstance(exception, ValueError):
        custom_error = DataValidationError(
            f"Data validation error: {str(exception)}",
            context=context,
            original_error=exception
        )
    elif isinstance(exception, KeyError):
        custom_error = DataProcessingError(
            f"Missing required data: {str(exception)}",
            context=context,
            original_error=exception
        )
    elif isinstance(exception, PermissionError):
        custom_error = AttendanceSystemError(
            f"Permission denied: {str(exception)}",
            error_code="PERMISSION_ERROR",
            context=context,
            original_error=exception
        )
    else:
        custom_error = AttendanceSystemError(
            f"Unexpected error: {str(exception)}",
            error_code="UNEXPECTED_ERROR",
            context=context,
            original_error=exception
        )
    
    if reraise:
        raise custom_error
    
    return custom_error


def safe_execute(
    func,
    *args,
    error_message: Optional[str] = None,
    error_type: type = AttendanceSystemError,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
) -> Any:
    """
    Safely execute a function with consistent error handling.
    
    Args:
        func: Function to execute
        *args: Function arguments
        error_message: Custom error message if execution fails
        error_type: Type of custom exception to raise
        context: Additional context information
        **kwargs: Function keyword arguments
        
    Returns:
        Function return value
        
    Raises:
        error_type: Custom exception if function execution fails
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        message = error_message or f"Failed to execute {func.__name__}: {str(e)}"
        context = context or {}
        context['function'] = func.__name__
        
        if error_type == AttendanceSystemError:
            raise handle_exception(e, context=context)
        else:
            raise error_type(message, context=context, original_error=e)