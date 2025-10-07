"""
Configuration module for the attendance reporting system.
Contains all constants, settings, and configuration variables.
"""

import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

# Log file configuration
LOG_FILE = "attendance_report.log"
LOG_LEVEL_CONSOLE = logging.INFO
LOG_LEVEL_FILE = logging.DEBUG

# Configure logging
def setup_logging():
    """Configure the logging system for the attendance reporting application."""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(LOG_LEVEL_CONSOLE)
    console_handler.setFormatter(console_formatter)

    # File handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(LOG_LEVEL_FILE)
    file_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

# ==============================================================================
# API CONFIGURATION
# ==============================================================================

# Frappe API credentials
API_KEY = os.getenv("ASIATECH_API_KEY")
API_SECRET = os.getenv("ASIATECH_API_SECRET")
API_URL = "https://erp.asiatech.com.mx/api/resource/Employee Checkin"
LEAVE_API_URL = "https://erp.asiatech.com.mx/api/resource/Leave Application"
EMPLOYEE_API_URL = "https://erp.asiatech.com.mx/api/resource/Employee"

# ==============================================================================
# LEAVE POLICY CONFIGURATION
# ==============================================================================

# Leave policy by type - defines how expected hours are handled
POLITICA_PERMISOS = {
    "permiso sin goce de sueldo": "no_ajustar",
    "permiso sin goce": "no_ajustar", 
    "sin goce de sueldo": "no_ajustar",
    "sin goce": "no_ajustar",
    # Space for future policies:
    # "permiso con goce": "ajustar_a_cero",
    # "permiso médico": "prorratear",
}

# ==============================================================================
# BUSINESS RULES CONFIGURATION
# ==============================================================================

# Tardiness forgiveness rule configuration
PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA = False

# Early departure detection configuration
TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS = 15

# Tardiness and absence thresholds (in minutes)
TOLERANCIA_RETARDO_MINUTOS = 15
UMBRAL_FALTA_INJUSTIFICADA_MINUTOS = 60

# Midnight crossing shift grace period (in minutes)
# For shifts that cross midnight (e.g., 18:00 → 02:00), any check-in within this
# grace period after the scheduled exit time will be assigned to the previous day's shift
# instead of the next calendar day. Default: 59 minutes (covers the entire hour)
GRACE_MINUTES = 59
class BusinessRules:
    """Centralized business rules configuration for attendance processing."""
    
    # Tardiness forgiveness rule configuration
    PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA = False
    
    # Early departure detection configuration
    TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS = 15
    
    # Tardiness and absence thresholds (in minutes)
    TOLERANCIA_RETARDO_MINUTOS = 15
    UMBRAL_FALTA_INJUSTIFICADA_MINUTOS = 60
    
    # Midnight crossing shift grace period (in minutes)
    # For shifts that cross midnight (e.g., 18:00 → 02:00), any check-in within this
    # grace period after the scheduled exit time will be assigned to the previous day's shift
    # instead of the next calendar day. Default: 59 minutes (covers the entire hour)
    GRACE_MINUTES = 59
    
    # Break time calculation rules
    MIN_CHECKINS_FOR_BREAK = 4  # Minimum number of check-ins to detect breaks
    DEFAULT_BREAK_DEDUCTION = 1  # Default break time deduction in hours
    
    # Work time validation rules
    MIN_WORK_HOURS_FOR_FORGIVENESS = 0.1  # Minimum hours worked to qualify for tardiness forgiveness
    MAX_WORKED_HOURS_PER_DAY = 16  # Maximum reasonable worked hours per day
    
    # Data quality thresholds
    MAX_CLOCK_IN_DIFFERENCE_MINUTES = 12 * 60  # Maximum reasonable time between consecutive check-ins
    MIN_CLOCK_IN_INTERVAL_MINUTES = 1  # Minimum time between consecutive check-ins
    
    @classmethod
    def validate_tardiness_thresholds(cls) -> None:
        """Validate that tardiness thresholds are logically consistent."""
        if cls.TOLERANCIA_RETARDO_MINUTOS < 0:
            raise ValueError("TOLERANCIA_RETARDO_MINUTOS must be non-negative")
        if cls.UMBRAL_FALTA_INJUSTIFICADA_MINUTOS <= cls.TOLERANCIA_RETARDO_MINUTOS:
            raise ValueError(
                "UMBRAL_FALTA_INJUSTIFICADA_MINUTOS must be greater than TOLERANCIA_RETARDO_MINUTOS"
            )
        if cls.TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS < 0:
            raise ValueError("TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS must be non-negative")
    
    @classmethod
    def validate_grace_period(cls) -> None:
        """Validate grace period configuration."""
        if not (0 <= cls.GRACE_MINUTES <= 120):
            raise ValueError("GRACE_MINUTES must be between 0 and 120 minutes")
    
    @classmethod
    def validate_all(cls) -> None:
        """Validate all business rule configurations."""
        cls.validate_tardiness_thresholds()
        cls.validate_grace_period()

# ==============================================================================
# REPORT CONFIGURATION
# ==============================================================================

# Output file names
OUTPUT_DETAILED_REPORT = "reporte_asistencia_analizado.csv"
OUTPUT_SUMMARY_REPORT = "resumen_periodo.csv" 
OUTPUT_HTML_DASHBOARD = "dashboard_asistencia.html"

# ==============================================================================
# SPANISH DAY NAMES MAPPING
# ==============================================================================

DIAS_ESPANOL = {
    "Monday": "Lunes",
    "Tuesday": "Martes", 
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}

# ==============================================================================
# VALIDATION FUNCTIONS
# ==============================================================================

def validate_api_credentials():
    """Validate that required API credentials are present."""
    if not all([API_KEY, API_SECRET]):
        raise ValueError(
            "Missing API credentials (ASIATECH_API_KEY, ASIATECH_API_SECRET) in .env file"
        )
    return True

def get_api_headers():
    """Get API headers with authentication."""
    validate_api_credentials()
    return {"Authorization": f"token {API_KEY}:{API_SECRET}"}