# Repository Guidelines

## Project Structure & Module Organization
The Python entry points live at root: `main.py` orchestrates batch runs, `run_gui.py` starts the PyQt6 client, and supporting modules (`api_client.py`, `data_processor.py`, `report_generator.py`, `utils.py`, `validators.py`, `exceptions.py`) split transport, business logic, and formatting duties. Configuration plus logging setup sits in `config.py`, expecting secrets via `.env`. Tests mirror these modules under `tests/`, while reference docs live in `Docs/`; generated outputs and diagnostics are written to `logs/` and the `reporte_*.xlsx` files in the project root.

## Build, Test, and Development Commands
- `uv sync` or `pip install -r requirements.txt` to install dependencies.
- `uv run python main.py --start 2025-01-01 --end 2025-01-31 --sucursal "Complex Branch"` after exporting `ASIATECH_API_KEY` and `ASIATECH_API_SECRET`.
- `uv run python run_gui.py` launches the desktop dashboard.
- `uv run python run_tests.py stable` (happy path), `run_tests.py edge`, or `run_tests.py coverage` for broader suites and HTML coverage reports.

## Coding Style & Naming Conventions
Adopt four-space indentation, 88-character lines, and module/function `snake_case` with `PascalCase` classes. Black, isort, Flake8, and mypy are preconfigured; format and lint with `uv run black .`, `uv run isort .`, `uv run flake8`, and type-check with `uv run mypy .`. Keep filenames descriptive (`attendance_processor.py` style) and co-locate helper modules beside the domain code they serve.

## Testing Guidelines
Pytest discovers files matching `tests/test_*.py`; extend the module-aligned test files when adding behavior. Mark heavy suites with the configured markers (`slow`, `integration`, `api`, `permisos`) so `uv run python run_tests.py fast` stays quick. For permissions and leave scenarios reuse fixtures from `tests/conftest_permisos.py`. Aim to keep coverage steady; `run_tests.py coverage` produces `htmlcov/` for gap inspection.

## Commit & Pull Request Guidelines
Follow the repository’s Conventional Commit history (`feat:`, `fix:`, `docs:`). Keep subjects under 72 characters, add context in the body, and group related changes per commit. Pull requests should outline the problem, solution, and testing performed, reference tickets when applicable, and attach sample output (screenshots or report snippets) for UI/report changes.

## Security & Configuration Tips
Never commit `.env` or credentials; `config.py` loads them at runtime. Scrub generated XLSX/CSV reports before sharing outside the team and rotate keys if exposed. Limit log retention when `attendance_report.log` contains employee identifiers.
