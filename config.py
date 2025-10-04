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