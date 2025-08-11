# CRUSH.md

## Commands
- **Build / Run**: `uv run main.py` (or `python generar_reporte_optimizado.py` for legacy script)
- **Run GUI**: `uv run run_gui.py`
- **Run all tests**: `uv run pytest`
- **Run a single test file**: `uv run pytest tests/test_<name>.py -v`
- **Run a single test case**: `uv run pytest tests/test_<name>.py::TestClass::test_method -v`
- **Run tests with coverage**: `uv run pytest --cov=. --cov-report=term-missing`
- **Run tests in parallel**: `uv run pytest -n auto`
- **Lint / Format**: `uv run ruff format .` and `uv run ruff check .`
- **Type check**: `uv run mypy .`

## Testing (from CLAUDE.md)
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=. --cov-report=term-missing --cov-report=html

# Run specific categories
uv run pytest -m unit          # unit tests only
uv run pytest -m integration   # integration tests only
uv run pytest -m "not slow"   # skip slow tests
uv run pytest tests/test_perdon_retardos.py -v  # single test file

# Parallel execution (if pytest-xdist available)
uv run pytest -n auto
```

## Code Quality (from CLAUDE.md)
```bash
# Format and lint with Ruff (preferred)
uv run ruff format .
uv run ruff check .
uv run ruff check --fix .   # auto‑fix issues

# Alternative: Black formatting
uv run black .

# Lint with flake8
uv run flake8 .

# Type checking with mypy
uv run mypy generar_reporte_optimizado.py db_postgres_connection.py
```

## Main Application (from CLAUDE.md)
```bash
# Legacy script
python generar_reporte_optimizado.py

# Modular version
python main.py
uv run python main.py

# PyQt6 GUI
python gui_pyqt6.py
uv run python gui_pyqt6.py

# Launcher script
python run_gui.py
uv run python run_gui.py
```

## Code style
- Black line length 88, isort profile `black` (configured in `pyproject.toml`).
- Imports: std lib, third‑party, local modules; one blank line between groups.
- Types: all public functions/classes must have type hints; `disallow_untyped_defs` enforced.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, constants `UPPER_SNAKE`.
- Errors: raise concrete exceptions, include context; avoid bare `except:`.
- Logging: use `logging` module, appropriate level, no stack traces.
- Docstrings: Google style, short description then args/returns.
- No commented‑out code; remove dead code.
- Avoid mutable default arguments.
- Prefer f‑strings over `%` or `str.format`.
- Keep line length ≤ 88 characters.

## Project specifics
- Tests reside in `tests/` following `test_*.py` naming.
- Shared fixtures in `tests/conftest_permisos.py`.
- Mark slow tests with `@pytest.mark.slow`; run `-m "not slow"` to skip.
- Run lint/format before committing using commands above.
