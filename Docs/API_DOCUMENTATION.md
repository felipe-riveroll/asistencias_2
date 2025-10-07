# API Documentation - Attendance Reporting System

This document provides comprehensive documentation for the APIs, data structures, and interfaces used throughout the attendance reporting system.

## Table of Contents
- [Core APIs](#core-apis)
- [Data Models](#data-models)
- [Configuration](#configuration)
- [External APIs](#external-apis)
- [Error Handling](#error-handling)
- [Usage Examples](#usage-examples)

---

## Core APIs

### AttendanceProcessor Class

The main class responsible for processing attendance data and applying business rules.

#### Methods

##### `__init__() -> None`
Initialize the attendance processor.

##### `process_checkins_to_dataframe(checkin_data: List[Dict[str, Any]], start_date: str, end_date: str) -> pd.DataFrame`
Creates a base DataFrame with one row per employee and day.

**Parameters:**
- `checkin_data`: List of check-in records from the API
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format

**Returns:** DataFrame with structured attendance data

**Example:**
```python
processor = AttendanceProcessor()
df = processor.process_checkins_to_dataframe(
    checkin_data=[{'employee': 'EMP001', 'time': '2025-01-01T09:00:00', 'employee_name': 'John Doe'}],
    start_date='2025-01-01',
    end_date='2025-01-31'
)
```

##### `calcular_horas_descanso(df_dia: Union[pd.DataFrame, pd.Series]) -> timedelta`
Calculates break hours based on check-ins for the day.

**Parameters:**
- `df_dia`: DataFrame or Series containing check-in data for a single day

**Returns:** Calculated break time as timedelta

##### `aplicar_calculo_horas_descanso(df: pd.DataFrame) -> pd.DataFrame`
Applies break hours calculation to the entire DataFrame.

##### `procesar_horarios_con_medianoche(df: pd.DataFrame, cache_horarios: Dict[str, Any]) -> pd.DataFrame`
Reorganizes check-in/out records for shifts that cross midnight.

##### `analizar_asistencia_con_horarios_cache(df: pd.DataFrame, cache_horarios: Dict[str, Any]) -> pd.DataFrame`
Enriches the DataFrame with schedule and tardiness analysis using the schedule cache.

##### `ajustar_horas_esperadas_con_permisos(df: pd.DataFrame, permisos_dict: Dict[str, Any], cache_horarios: Dict[str, Any]) -> pd.DataFrame`
Adjusts expected hours considering approved leaves.

##### `aplicar_regla_perdon_retardos(df: pd.DataFrame) -> pd.DataFrame`
Applies the tardiness forgiveness rule when an employee fulfills their shift hours.

##### `clasificar_faltas_con_permisos(df: pd.DataFrame) -> pd.DataFrame`
Updates absence classification considering approved leaves.

##### `marcar_dias_no_contratado(df: pd.DataFrame, joining_dates_dict: Dict[str, date]) -> pd.DataFrame`
Marks days before an employee's joining date as 'No Contratado'.

### APIClient Class

Handles communication with external APIs for fetching attendance and leave data.

#### Methods

##### `__init__(api_key: str, api_secret: str, base_url: str) -> None`
Initialize the API client with authentication credentials.

##### `fetch_checkins(start_date: str, end_date: str, device_filter: Optional[str] = None) -> List[Dict[str, Any]]`
Fetch check-in records within the specified date range.

##### `fetch_leave_applications(start_date: str, end_date: str) -> List[Dict[str, Any]]`
Fetch leave applications within the specified date range.

##### `fetch_employee_details(employee_id: str) -> Dict[str, Any]`
Fetch detailed information for a specific employee.

### ReportGenerator Class

Generates various types of attendance reports.

#### Methods

##### `generate_detailed_report(df: pd.DataFrame, output_file: str) -> None`
Generate detailed CSV report with all attendance data.

##### `generate_summary_report(df: pd.DataFrame, output_file: str) -> None`
Generate summary report with aggregated metrics.

##### `generate_html_dashboard(df: pd.DataFrame, output_file: str) -> None`
Generate interactive HTML dashboard with visualizations.

---

## Data Models

### Check-in Record

```python
{
    "employee": str,           # Employee ID
    "employee_name": str,      # Employee full name
    "time": str,               # ISO datetime format (YYYY-MM-DDTHH:MM:SS)
    "device_id": Optional[str] # Device identifier (optional)
}
```

### Schedule Record

```python
{
    "employee_id": str,
    "dia_iso": int,                    # ISO weekday (1=Monday, 7=Sunday)
    "es_primera_quincena": bool,       # First half of month flag
    "hora_entrada": str,               # Entry time (HH:MM)
    "hora_salida": str,                # Exit time (HH:MM)
    "cruza_medianoche": bool,          # Crosses midnight flag
    "horas_totales": float             # Total scheduled hours
}
```

### Leave Application Record

```python
{
    "employee": str,
    "leave_type": str,
    "leave_type_normalized": str,      # Normalized leave type for business rules
    "from_date": date,
    "to_date": date,
    "is_half_day": bool,
    "status": str                      # "Approved", "Rejected", "Pending"
}
```

### Processed Attendance Record

```python
{
    "employee": str,
    "dia": date,
    "dia_semana": str,                 # Spanish day name
    "dia_iso": int,                    # ISO weekday
    "Nombre": str,                     # Employee name
    "checado_1": Optional[str],        # First check-in
    "checado_2": Optional[str],        # Second check-in
    # ... checado_3 through checado_9
    "duration": Optional[timedelta],   # Total worked time
    "horas_trabajadas": str,           # Worked hours as string (HH:MM:SS)
    "hora_entrada_programada": Optional[str],
    "hora_salida_programada": Optional[str],
    "cruza_medianoche": bool,
    "horas_esperadas": str,
    "tipo_retardo": str,               # "A Tiempo", "Retardo", "Falta", "Falta Injustificada"
    "minutos_tarde": int,
    "es_retardo_acumulable": bool,
    "retardos_acumulados": int,
    "descuento_por_3_retardos": str,
    "salida_anticipada": bool,
    "tiene_permiso": bool,
    "tipo_permiso": Optional[str],
    "es_permiso_sin_goce": bool,
    "es_permiso_medio_dia": bool,
    "horas_descontadas_permiso": str,
    "tipo_falta_ajustada": str,
    "falta_justificada": bool,
    "retardo_perdonado": bool,
    "cumplio_horas_turno": bool,
    "horas_descanso": str,
    "observaciones": Optional[str]
}
```

---

## Configuration

### BusinessRules Class

Centralized business rules configuration.

#### Attributes

- `TOLERANCIA_RETARDO_MINUTOS`: int (default: 15)
- `UMBRAL_FALTA_INJUSTIFICADA_MINUTOS`: int (default: 60)
- `TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS`: int (default: 15)
- `PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA`: bool (default: False)
- `GRACE_MINUTES`: int (default: 59)
- `MIN_CHECKINS_FOR_BREAK`: int (default: 4)
- `DEFAULT_BREAK_DEDUCTION`: int (default: 1)

#### Methods

##### `validate_tardiness_thresholds() -> None`
Validates that tardiness thresholds are logically consistent.

##### `validate_grace_period() -> None`
Validates grace period configuration.

##### `validate_all() -> None`
Validates all business rule configurations.

### Environment Variables

```bash
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=attendance_db
DB_USER=username
DB_PASSWORD=password

# API Configuration
ASIATECH_API_KEY=your_api_key
ASIATECH_API_SECRET=your_api_secret
LEAVE_API_URL=https://erp.asiatech.com.mx/api/resource/Leave Application
EMPLOYEE_API_URL=https://erp.asiatech.com.mx/api/resource/Employee

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=attendance_report.log
```

---

## External APIs

### Frappe ERPNext API

#### Base URL
```
https://erp.asiatech.com.mx/api/resource/
```

#### Endpoints

##### Employee Checkin
```
GET /api/resource/Employee Checkin
```

**Headers:**
```
Authorization: token {API_KEY}:{API_SECRET}
```

**Query Parameters:**
- `filters`: JSON-encoded filter criteria
- `fields`: Comma-separated list of fields to return

**Response Format:**
```json
{
    "data": [
        {
            "name": "CHK-2025-001",
            "employee": "EMP001",
            "time": "2025-01-01 09:00:00",
            "log_type": "IN",
            "device_id": "DEVICE001"
        }
    ]
}
```

##### Leave Application
```
GET /api/resource/Leave Application
```

**Response Format:**
```json
{
    "data": [
        {
            "name": "LEAVE-2025-001",
            "employee": "EMP001",
            "leave_type": "Leave Without Pay",
            "from_date": "2025-01-15",
            "to_date": "2025-01-15",
            "status": "Approved",
            "half_day": 0
        }
    ]
}
```

##### Employee Details
```
GET /api/resource/Employee/{employee_id}
```

**Response Format:**
```json
{
    "data": {
        "name": "EMP001",
        "employee_name": "John Doe",
        "date_of_joining": "2024-01-01",
        "status": "Active"
    }
}
```

---

## Error Handling

### Exception Hierarchy

```python
AttendanceSystemError
├── ConfigurationError
├── DataValidationError
├── APIConnectionError
├── DatabaseConnectionError
├── DataProcessingError
├── ReportGenerationError
├── ValidationError
└── RetryExhaustedError
```

### Error Response Format

All exceptions include structured information for debugging:

```python
{
    "message": str,           # Human-readable error description
    "error_code": str,        # Unique error identifier
    "context": Dict[str, Any], # Additional context information
    "original_error": Optional[Exception] # Original exception if applicable
}
```

### Common Error Scenarios

#### API Connection Errors
```python
try:
    api_client = APIClient(api_key, api_secret, base_url)
    data = api_client.fetch_checkins(start_date, end_date)
except APIConnectionError as e:
    logger.error(f"API connection failed: {e}")
    logger.error(f"Context: {e.context}")
```

#### Data Validation Errors
```python
try:
    validator = EmployeeValidator()
    result = validator.validate_employee_id(employee_id)
    validate_and_raise(result)
except DataValidationError as e:
    logger.error(f"Validation failed: {e}")
```

#### Retry Exhausted Errors
```python
from retry_utils import with_api_retry

@with_api_retry
def fetch_data_with_retry():
    return api_client.fetch_checkins(start_date, end_date)

try:
    data = fetch_data_with_retry()
except RetryExhaustedError as e:
    logger.error(f"All retry attempts failed: {e}")
```

---

## Usage Examples

### Basic Data Processing

```python
from data_processor import AttendanceProcessor
from config import setup_logging

# Initialize logging
logger = setup_logging()

# Create processor instance
processor = AttendanceProcessor()

# Process check-in data
checkin_data = [
    {
        "employee": "EMP001",
        "time": "2025-01-01T09:00:00",
        "employee_name": "John Doe"
    }
]

df = processor.process_checkins_to_dataframe(
    checkin_data=checkin_data,
    start_date="2025-01-01",
    end_date="2025-01-31"
)

# Apply business rules
cache_horarios = load_schedule_cache()  # Your cache loading function
df = processor.analizar_asistencia_con_horarios_cache(df, cache_horarios)
```

### Error Handling

```python
from exceptions import APIConnectionError, DataProcessingError
from retry_utils import RetryConfig, RetryEngine

# Configure retry for API calls
retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    backoff_strategy=BackoffStrategy.EXPONENTIAL
)

retry_engine = RetryEngine(retry_config)

try:
    data = retry_engine.execute(
        api_client.fetch_checkins,
        start_date="2025-01-01",
        end_date="2025-01-31"
    )
except RetryExhaustedError as e:
    logger.error(f"Failed to fetch data after retries: {e}")
    # Handle fallback logic
```

### Validation

```python
from validators import EmployeeValidator, DateValidator, validate_and_raise

# Validate employee data
employee_validator = EmployeeValidator()
result = employee_validator.validate_employee_id("EMP001")

if not result.is_valid:
    print(f"Validation errors: {result.errors}")
    print(f"Validation warnings: {result.warnings}")

# Or raise exceptions automatically
try:
    validate_and_raise(result)
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Report Generation

```python
from report_generator import ReportGenerator

# Generate reports
generator = ReportGenerator()

# Detailed CSV report
generator.generate_detailed_report(
    df=df,
    output_file="detailed_report.csv"
)

# HTML Dashboard
generator.generate_html_dashboard(
    df=df,
    output_file="dashboard.html"
)
```

### Configuration Management

```python
from config import BusinessRules

# Validate business rules
try:
    BusinessRules.validate_all()
    print("All business rules are valid")
except ValueError as e:
    print(f"Invalid business rule configuration: {e}")

# Access business rules
print(f"Tardiness tolerance: {BusinessRules.TOLERANCIA_RETARDO_MINUTOS} minutes")
print(f"Unjustified absence threshold: {BusinessRules.UMBRAL_FALTA_INJUSTIFICADA_MINUTOS} minutes")
```

---

## Testing

### API Testing

```python
import pytest
from unittest.mock import Mock, patch
from api_client import APIClient

@pytest.fixture
def mock_api_client():
    return APIClient("test_key", "test_secret", "https://test.api.com")

@patch('requests.get')
def test_fetch_checkins(mock_get, mock_api_client):
    # Mock API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "data": [
            {
                "employee": "EMP001",
                "time": "2025-01-01 09:00:00",
                "employee_name": "Test Employee"
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    # Test the method
    result = mock_api_client.fetch_checkins("2025-01-01", "2025-01-31")
    
    assert len(result) == 1
    assert result[0]["employee"] == "EMP001"
```

### Data Processing Testing

```python
import pytest
import pandas as pd
from data_processor import AttendanceProcessor

@pytest.fixture
def sample_processor():
    return AttendanceProcessor()

@pytest.fixture
def sample_checkin_data():
    return [
        {
            "employee": "EMP001",
            "time": "2025-01-01T09:00:00",
            "employee_name": "John Doe"
        },
        {
            "employee": "EMP001", 
            "time": "2025-01-01T18:00:00",
            "employee_name": "John Doe"
        }
    ]

def test_process_checkins_to_dataframe(sample_processor, sample_checkin_data):
    df = sample_processor.process_checkins_to_dataframe(
        checkin_data=sample_checkin_data,
        start_date="2025-01-01",
        end_date="2025-01-01"
    )
    
    assert len(df) == 1
    assert df.iloc[0]["employee"] == "EMP001"
    assert df.iloc[0]["Nombre"] == "John Doe"
    assert "checado_1" in df.columns
    assert "checado_2" in df.columns
```

---

## Performance Considerations

### Data Processing

- Use vectorized pandas operations instead of loops when possible
- Cache schedule data to avoid repeated database queries
- Process data in chunks for large datasets
- Use appropriate data types to reduce memory usage

### API Calls

- Implement retry logic with exponential backoff
- Cache API responses when appropriate
- Use connection pooling for HTTP requests
- Monitor API rate limits and implement throttling

### Memory Management

- Use generators for large data processing pipelines
- Clear intermediate DataFrames when no longer needed
- Use appropriate data types (category, int32 vs int64)
- Monitor memory usage during processing

---

## Security Considerations

### API Keys

- Store API keys in environment variables, not in code
- Rotate API keys regularly
- Use secure transmission (HTTPS) for all API calls
- Implement proper error handling to avoid exposing keys in logs

### Data Privacy

- Minimize data collection to only what's necessary
- Implement proper access controls
- Use secure data storage and transmission
- Follow data retention policies

### Input Validation

- Validate all external inputs
- Sanitize data before processing
- Implement proper error handling
- Use parameterized queries for database operations