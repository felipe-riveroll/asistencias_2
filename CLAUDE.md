# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=. --cov-report=term-missing --cov-report=html

# Run specific test categories
uv run pytest -m unit                    # Unit tests only
uv run pytest -m integration            # Integration tests only
uv run pytest -m "not slow"             # Skip slow tests
uv run pytest tests/test_perdon_retardos.py -v  # Specific test file

# Run tests in parallel (if pytest-xdist is available)
uv run pytest -n auto
```

### Code Quality
```bash
# Format and lint with Ruff (preferred)
uv run ruff format .
uv run ruff check .
uv run ruff check --fix .        # Auto-fix issues

# Format code with Black (alternative)
uv run black .

# Lint with flake8
uv run flake8 .

# Type checking with mypy
uv run mypy generar_reporte_optimizado.py db_postgres_connection.py

# Run specific test file (for new modules)
uv run python test_reporte_excel.py
```

### Main Application
```bash
# Run the attendance report generator (legacy script)
python generar_reporte_optimizado.py

# Run the modular version
python main.py
uv run python main.py

# Run the PyQt6 Desktop GUI
python gui_pyqt6.py
uv run python gui_pyqt6.py

# Or use the launcher script
python run_gui.py
uv run python run_gui.py
```

## Project Architecture

### Core System
This is a Python-based attendance reporting system that processes employee check-ins/check-outs and generates comprehensive attendance reports. The system integrates with PostgreSQL for scheduled hours and ERPNext API for leave applications.

### Key Components

**`generar_reporte_optimizado.py`** - Main script containing the core processing logic:
- Fetches check-in data from Frappe API
- Processes attendance against scheduled hours from PostgreSQL 
- Integrates leave/permission data from ERPNext
- Generates detailed CSV reports and interactive HTML dashboard
- Handles complex scenarios: night shifts, break time calculation, forgiveness rules

**`db_postgres_connection.py`** - Database connection and query management:
- PostgreSQL connection handling with caching
- Functions to retrieve scheduled hours by employee
- Optimized queries for multi-period processing

**`tests/`** - Comprehensive test suite (209+ tests):
- Unit tests for core functionality
- Integration tests with external APIs
- Edge case testing for complex scenarios
- Performance and validation tests

**`reporte_excel.py`** - Excel report generator with advanced formatting:
- Generates detailed Excel reports with multiple sheets
- Advanced coloring for attendance status (on-time, late, absent)
- Statistical analysis and KPI calculations
- Integration with existing data processing pipeline

**`test_reporte_excel.py`** - Unit tests for Excel report generation:
- Tests for attendance coloring logic
- Validation of different tardiness scenarios
- Mock-based testing for Excel formatting features

**`gui_pyqt6.py`** - PyQt6 Desktop GUI Application:
- User-friendly interface for report generation
- Date range selection with validation
- Branch selection (31 PTE, VILLAS, NAVE)
- Real-time status updates and progress indication
- Automatic Excel file opening functionality
- Error handling with detailed dialog messages

**`run_gui.py`** - GUI launcher script for easy application startup

**`test_gui.py`** - GUI component testing without full report execution

### Data Flow Architecture

1. **Data Collection**: Fetch check-ins from Frappe API and leave applications from ERPNext
2. **Data Processing**: Match check-ins with scheduled hours, calculate worked hours, apply business rules
3. **Policy Application**: Apply forgiveness rules, handle half-day leaves, classify absences
4. **Report Generation**: Generate detailed CSV and interactive HTML dashboard

### Business Logic Features

**Break Time Calculation**: Automatically calculates break hours based on multiple check-ins (minimum 4 required)

**Tardiness Forgiveness**: Pardons tardiness when employee completes their scheduled hours

**Night Shift Handling**: Correctly processes shifts that cross midnight

**Early Departure Detection**: Identifies when employees leave before scheduled end time

**Half-Day Leave Support**: Handles both full-day (0.5 day deduction) and half-day leaves proportionally

**Leave Integration**: Automatically justifies absences with approved leave applications

### Configuration

**Environment Variables** (`.env` file):
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` - PostgreSQL connection
- `ASIATECH_API_KEY`, `ASIATECH_API_SECRET` - Frappe API credentials
- `LEAVE_API_URL` - ERPNext leave applications endpoint

**Execution Configuration** (in `generar_reporte_optimizado.py`):
```python
start_date = "2025-01-01"      # Period start date
end_date = "2025-01-15"        # Period end date  
sucursal = "Villas"            # Branch to analyze
device_filter = "%villas%"     # Device filter for database query
```

### Output Files

- `reporte_asistencia_analizado.csv` - Detailed daily attendance analysis
- `resumen_periodo.csv` - Period summary with aggregated metrics
- `dashboard_asistencia.html` - Interactive dashboard with DataTables.net and D3.js visualizations
- `reporte_asistencia_[branch]_[dates].xlsx` - Advanced Excel report with multiple sheets, KPIs, and colored formatting

### Testing Strategy

The project uses pytest with comprehensive test coverage:
- Markers for test categorization (unit, integration, slow, edge, api, database)
- Mock objects for external API testing
- Fixtures for consistent test data
- Coverage reporting with HTML output

### Key Business Rules

- **Tardiness Threshold**: 15 minutes tolerance, 60 minutes becomes unjustified absence
- **Break Deduction**: 1 hour deducted from expected hours when breaks are detected
- **Leave Policies**: Configurable per leave type (currently "no adjustment" for unpaid leave)
- **Forgiveness Rule**: Tardiness pardoned when scheduled hours are completed
- **Excel Report Coloring**: Automatic color coding for attendance status (yellow for late, red for excessive tardiness)
- **Data Processing**: Supports both modular architecture (main.py) and legacy monolithic script (generar_reporte_optimizado.py)