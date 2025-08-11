# CRUSH.md

## Commands
- **Build / Run**: `uv run main.py` (or `python generar_reporte_optimizado.py` for legacy script)
- **Run GUI**: `uv run run_gui.py`
- **Run all tests**: `uv run pytest`
- **Run a single test file**: `uv run pytest tests/test_<name>.py -v`
- **Run a single test case**: `uv run pytest tests/test_<name>.py::TestClass::test_method -v`
- **Run tests with coverage**: `uv run pytest --cov=. --cov-report=term-missing`
- **Lint / Format**: `uv run ruff check .` and `uv run ruff format .`
- **Type check**: `uv run mypy .`

## Code style
- Use Black line length 88, isort profile `black` (configured in `pyproject.toml`).
- Imports: standard library, then third‑party, then local modules; one blank line between groups.
- Types: all public functions/classes must have type hints; `disallow_untyped_defs` enforced by mypy.
- Naming: `snake_case` for functions/variables, `PascalCase` for classes, constants `UPPER_SNAKE`.
- Errors: raise concrete exceptions, include context; avoid bare `except:`.
- Logging: use `logging` module, log at appropriate level, never print stack traces.
- Docstrings: Google style, first line short description, then args/returns.
- No commented‑out code; remove dead code.
- Avoid mutable default arguments.
- Prefer f‑strings over `%` or `str.format`.
- Keep line length ≤ 88 characters.

## Project specifics
- Tests are in `tests/` following `test_*.py` pattern.
- Use fixtures defined in `tests/conftest_permisos.py` for shared data.
- Mark slow tests with `@pytest.mark.slow` and run with `-m "not slow"` when needed.
- All linting and formatting can be run via the commands above before committing.
