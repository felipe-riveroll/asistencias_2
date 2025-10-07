"""
Reusable validation utilities for the attendance reporting system.

This module provides common validation functions that can be used across
different components to ensure data consistency and proper error handling.
"""

import re
from datetime import datetime, date, time
from typing import Any, Optional, Union, Dict, List, Pattern
from dataclasses import dataclass

from exceptions import ValidationError, DataValidationError
from config import BusinessRules


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    context: Dict[str, Any]
    
    def add_error(self, message: str) -> None:
        """Add an error message to the result."""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning message to the result."""
        self.warnings.append(message)


class BaseValidator:
    """Base class for all validators."""
    
    @staticmethod
    def validate_required(value: Any, field_name: str = "field") -> ValidationResult:
        """Validate that a value is not None or empty."""
        result = ValidationResult(True, [], [], {"field": field_name})
        
        if value is None:
            result.add_error(f"{field_name} is required")
        elif isinstance(value, str) and not value.strip():
            result.add_error(f"{field_name} cannot be empty")
        elif isinstance(value, (list, dict)) and len(value) == 0:
            result.add_error(f"{field_name} cannot be empty")
        
        return result
    
    @staticmethod
    def validate_type(value: Any, expected_type: type, field_name: str = "field") -> ValidationResult:
        """Validate that a value matches the expected type."""
        result = ValidationResult(True, [], [], {"field": field_name, "expected_type": expected_type.__name__})
        
        if not isinstance(value, expected_type):
            result.add_error(f"{field_name} must be of type {expected_type.__name__}, got {type(value).__name__}")
        
        return result
    
    @staticmethod
    def validate_range(value: Union[int, float], min_val: Optional[float] = None, 
                      max_val: Optional[float] = None, field_name: str = "field") -> ValidationResult:
        """Validate that a numeric value is within the specified range."""
        result = ValidationResult(True, [], [], {"field": field_name, "value": value})
        
        if min_val is not None and value < min_val:
            result.add_error(f"{field_name} must be at least {min_val}, got {value}")
        
        if max_val is not None and value > max_val:
            result.add_error(f"{field_name} must be at most {max_val}, got {value}")
        
        return result
    
    @staticmethod
    def validate_length(value: str, min_length: Optional[int] = None, 
                       max_length: Optional[int] = None, field_name: str = "field") -> ValidationResult:
        """Validate that a string length is within the specified range."""
        result = ValidationResult(True, [], [], {"field": field_name, "length": len(value)})
        
        if min_length is not None and len(value) < min_length:
            result.add_error(f"{field_name} must be at least {min_length} characters, got {len(value)}")
        
        if max_length is not None and len(value) > max_length:
            result.add_error(f"{field_name} must be at most {max_length} characters, got {len(value)}")
        
        return result
    
    @staticmethod
    def validate_pattern(value: str, pattern: Union[str, Pattern], field_name: str = "field") -> ValidationResult:
        """Validate that a string matches the specified regex pattern."""
        result = ValidationResult(True, [], [], {"field": field_name, "pattern": str(pattern)})
        
        if isinstance(pattern, str):
            pattern = re.compile(pattern)
        
        if not pattern.match(value):
            result.add_error(f"{field_name} does not match required pattern")
        
        return result


class EmployeeValidator(BaseValidator):
    """Validator for employee-related data."""
    
    @staticmethod
    def validate_employee_id(employee_id: str) -> ValidationResult:
        """Validate employee ID format."""
        result = EmployeeValidator.validate_required(employee_id, "employee_id")
        if not result.is_valid:
            return result
        
        # Check type
        type_result = EmployeeValidator.validate_type(employee_id, str, "employee_id")
        if not type_result.is_valid:
            return type_result
        
        # Check length
        length_result = EmployeeValidator.validate_length(employee_id, min_length=1, max_length=50, field_name="employee_id")
        if not length_result.is_valid:
            return length_result
        
        # Check pattern (alphanumeric with optional special characters)
        pattern_result = EmployeeValidator.validate_pattern(employee_id, r'^[a-zA-Z0-9\-_\.]+$', "employee_id")
        if not pattern_result.is_valid:
            return pattern_result
        
        return result
    
    @staticmethod
    def validate_employee_name(name: str) -> ValidationResult:
        """Validate employee name format."""
        result = EmployeeValidator.validate_required(name, "name")
        if not result.is_valid:
            return result
        
        # Check type
        type_result = EmployeeValidator.validate_type(name, str, "name")
        if not type_result.is_valid:
            return type_result
        
        # Check length
        length_result = EmployeeValidator.validate_length(name, min_length=2, max_length=100, field_name="name")
        if not length_result.is_valid:
            return length_result
        
        # Check pattern (letters, spaces, and common name characters)
        pattern_result = EmployeeValidator.validate_pattern(name, r'^[a-zA-ZáéíóúñÁÉÍÓÚÑ\s\-\']+$', "name")
        if not pattern_result.is_valid:
            return pattern_result
        
        return result


class DateValidator(BaseValidator):
    """Validator for date and time data."""
    
    @staticmethod
    def validate_date_string(date_str: str, formats: Optional[List[str]] = None) -> ValidationResult:
        """Validate date string format."""
        if formats is None:
            formats = ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]
        
        result = DateValidator.validate_required(date_str, "date")
        if not result.is_valid:
            return result
        
        # Try each format
        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                return ValidationResult(True, [], [], {"format": fmt})
            except ValueError:
                continue
        
        result.add_error(f"Date '{date_str}' does not match any of the expected formats: {formats}")
        return result
    
    @staticmethod
    def validate_time_range(start_time: time, end_time: time) -> ValidationResult:
        """Validate that start_time is before end_time (accounting for overnight shifts)."""
        result = ValidationResult(True, [], [], {"start_time": str(start_time), "end_time": str(end_time)})
        
        # Check types
        start_type_result = DateValidator.validate_type(start_time, time, "start_time")
        if not start_type_result.is_valid:
            return start_type_result
        
        end_type_result = DateValidator.validate_type(end_time, time, "end_time")
        if not end_type_result.is_valid:
            return end_type_result
        
        # For overnight shifts, end_time can be earlier than start_time
        # This is valid and should be handled by the processing logic
        
        return result
    
    @staticmethod
    def validate_business_hours(start_time: time, end_time: time) -> ValidationResult:
        """Validate that business hours are reasonable."""
        result = DateValidator.validate_time_range(start_time, end_time)
        if not result.is_valid:
            return result
        
        # Check that work duration is reasonable (1-16 hours)
        start_minutes = start_time.hour * 60 + start_time.minute
        end_minutes = end_time.hour * 60 + end_time.minute
        
        if end_minutes > start_minutes:
            duration = end_minutes - start_minutes
        else:
            # Overnight shift
            duration = (24 * 60 - start_minutes) + end_minutes
        
        duration_result = DateValidator.validate_range(
            duration, 
            min_val=60,  # 1 hour minimum
            max_val=16 * 60,  # 16 hours maximum
            field_name="work_duration_minutes"
        )
        
        if not duration_result.is_valid:
            result.errors.extend(duration_result.errors)
            result.is_valid = False
        
        return result


class AttendanceValidator(BaseValidator):
    """Validator for attendance-specific data."""
    
    @staticmethod
    def validate_check_in_times(check_in_times: List[datetime]) -> ValidationResult:
        """Validate a list of check-in times."""
        result = AttendanceValidator.validate_required(check_in_times, "check_in_times")
        if not result.is_valid:
            return result
        
        # Check type
        type_result = AttendanceValidator.validate_type(check_in_times, list, "check_in_times")
        if not type_result.is_valid:
            return type_result
        
        # Check that list is not empty
        if len(check_in_times) == 0:
            result.add_error("check_in_times cannot be empty")
            return result
        
        # Validate each check-in time
        for i, check_in in enumerate(check_in_times):
            if not isinstance(check_in, datetime):
                result.add_error(f"check_in_times[{i}] must be a datetime object")
        
        # Check chronological order
        for i in range(1, len(check_in_times)):
            if check_in_times[i] <= check_in_times[i-1]:
                result.add_error(f"check_in_times[{i}] must be after check_in_times[{i-1}]")
        
        return result
    
    @staticmethod
    def validate_worked_hours(worked_hours: float, scheduled_hours: float) -> ValidationResult:
        """Validate worked hours against scheduled hours."""
        result = ValidationResult(True, [], [], {"worked_hours": worked_hours, "scheduled_hours": scheduled_hours})
        
        # Check types
        worked_type_result = AttendanceValidator.validate_type(worked_hours, (int, float), "worked_hours")
        if not worked_type_result.is_valid:
            return worked_type_result
        
        scheduled_type_result = AttendanceValidator.validate_type(scheduled_hours, (int, float), "scheduled_hours")
        if not scheduled_type_result.is_valid:
            return scheduled_type_result
        
        # Check ranges
        worked_range_result = AttendanceValidator.validate_range(
            worked_hours, 
            min_val=0, 
            max_val=BusinessRules.MAX_WORKED_HOURS_PER_DAY,
            field_name="worked_hours"
        )
        if not worked_range_result.is_valid:
            result.errors.extend(worked_range_result.errors)
            result.is_valid = False
        
        scheduled_range_result = AttendanceValidator.validate_range(
            scheduled_hours, 
            min_val=0, 
            max_val=24,
            field_name="scheduled_hours"
        )
        if not scheduled_range_result.is_valid:
            result.errors.extend(scheduled_range_result.errors)
            result.is_valid = False
        
        # Add warning if worked hours significantly exceed scheduled hours
        if worked_hours > scheduled_hours * 1.5:
            result.add_warning(f"Worked hours ({worked_hours}) significantly exceed scheduled hours ({scheduled_hours})")
        
        return result


class APIValidator(BaseValidator):
    """Validator for API-related data."""
    
    @staticmethod
    def validate_api_url(url: str) -> ValidationResult:
        """Validate API URL format."""
        result = APIValidator.validate_required(url, "url")
        if not result.is_valid:
            return result
        
        # Check type
        type_result = APIValidator.validate_type(url, str, "url")
        if not type_result.is_valid:
            return type_result
        
        # Check pattern
        pattern_result = APIValidator.validate_pattern(
            url, 
            r'^https?://[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(/.*)?$', 
            "url"
        )
        if not pattern_result.is_valid:
            return pattern_result
        
        return result
    
    @staticmethod
    def validate_api_key(api_key: str) -> ValidationResult:
        """Validate API key format."""
        result = APIValidator.validate_required(api_key, "api_key")
        if not result.is_valid:
            return result
        
        # Check type
        type_result = APIValidator.validate_type(api_key, str, "api_key")
        if not type_result.is_valid:
            return type_result
        
        # Check length (API keys are typically long strings)
        length_result = APIValidator.validate_length(api_key, min_length=10, max_length=500, field_name="api_key")
        if not length_result.is_valid:
            return length_result
        
        return result


class CompositeValidator:
    """Combines multiple validators for complex validation scenarios."""
    
    @staticmethod
    def validate_attendance_record(
        employee_id: str,
        date_str: str,
        check_in_times: List[datetime],
        scheduled_hours: float
    ) -> ValidationResult:
        """Validate a complete attendance record."""
        combined_result = ValidationResult(True, [], [], {})
        
        # Validate employee ID
        employee_result = EmployeeValidator.validate_employee_id(employee_id)
        combined_result.errors.extend(employee_result.errors)
        combined_result.warnings.extend(employee_result.warnings)
        
        # Validate date
        date_result = DateValidator.validate_date_string(date_str)
        combined_result.errors.extend(date_result.errors)
        combined_result.warnings.extend(date_result.warnings)
        
        # Validate check-in times
        checkin_result = AttendanceValidator.validate_check_in_times(check_in_times)
        combined_result.errors.extend(checkin_result.errors)
        combined_result.warnings.extend(checkin_result.warnings)
        
        # Validate scheduled hours
        scheduled_result = AttendanceValidator.validate_range(
            scheduled_hours, 
            min_val=0, 
            max_val=24, 
            field_name="scheduled_hours"
        )
        combined_result.errors.extend(scheduled_result.errors)
        combined_result.warnings.extend(scheduled_result.warnings)
        
        # Update overall validity
        combined_result.is_valid = len(combined_result.errors) == 0
        
        return combined_result
    
    @staticmethod
    def validate_configuration(config_dict: Dict[str, Any]) -> ValidationResult:
        """Validate application configuration."""
        result = ValidationResult(True, [], [], {})
        
        # Validate required configuration keys
        required_keys = [
            'API_KEY', 'API_SECRET', 'API_URL', 
            'TOLERANCIA_RETARDO_MINUTOS', 'UMBRAL_FALTA_INJUSTIFICADA_MINUTOS'
        ]
        
        for key in required_keys:
            if key not in config_dict:
                result.add_error(f"Missing required configuration key: {key}")
        
        # Validate business rules if present
        if all(key in config_dict for key in ['TOLERANCIA_RETARDO_MINUTOS', 'UMBRAL_FALTA_INJUSTIFICADA_MINUTOS']):
            try:
                BusinessRules.validate_tardiness_thresholds()
            except ValueError as e:
                result.add_error(f"Invalid business rule configuration: {str(e)}")
        
        result.is_valid = len(result.errors) == 0
        return result


def validate_and_raise(validator_result: ValidationResult, error_type: type = ValidationError) -> None:
    """Raise an exception if validation fails."""
    if not validator_result.is_valid:
        error_message = "; ".join(validator_result.errors)
        if validator_result.warnings:
            error_message += f" (Warnings: {'; '.join(validator_result.warnings)})"
        raise error_type(error_message, context=validator_result.context)