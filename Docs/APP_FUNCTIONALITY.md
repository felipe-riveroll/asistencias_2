# Visión General de la Funcionalidad de la Aplicación

## `main.py`
- Proporciona un **punto de entrada CLI** que crea un `AttendanceReportManager`.
- Los parámetros configurables (rango de fechas, sucursal y filtro de dispositivos) están definidos directamente en la función `main()`; pueden modificarse antes de ejecutar el script.
- Pasos del flujo de trabajo:
  1. Validar credenciales de la API (`config.validate_api_credentials`).
  2. Obtener los registros de entradas/salidas mediante `APIClient.fetch_checkins`.
  3. Extraer los códigos de empleados (`utils.obtener_codigos_empleados_api`).
  4. Obtener las solicitudes de permisos (`APIClient.fetch_leave_applications`) y procesarlas con `api_client.procesar_permisos_empleados`.
  5. Recuperar los horarios de la base de datos PostgreSQL (`db_postgres_connection`).
  6. Procesar los datos usando `AttendanceProcessor`: convertir a DataFrame, manejar turnos nocturnos, analizar asistencia, aplicar deducción de descansos, aplicar permisos, regla de perdón de retardos y clasificar ausencias.
  7. Generar los reportes con `ReportGenerator`: CSV detallado, CSV resumen, dashboard HTML y archivo Excel.
- Devuelve un diccionario con el estado, nombres de los archivos generados y contadores de empleados y días procesados.
- Los errores son capturados y mostrados; el script finaliza con código de salida 1 en caso de fallo.

## `run_gui.py`
- Lanza la **interfaz gráfica de escritorio PyQt6** (`gui_pyqt6.py`).
- Instancia la clase `App` (ventana principal) y arranca el bucle de eventos de Qt.
- La GUI reproduce el mismo flujo que la CLI, pero permite al usuario seleccionar de forma interactiva el rango de fechas y la sucursal, muestra una barra de progreso y abre automáticamente los reportes generados.
- Callbacks principales:
  * `run_report` – crea un `AttendanceReportManager` con los parámetros ingresados por el usuario y muestra diálogos de éxito o error.
  * Validación de los datos de entrada (formato de fecha y sucursal no vacía) antes de invocar el manager.

## Suite de pruebas (`tests/`)
- Todos los test siguen la convención `test_*.py` y son descubiertos por pytest.
- **Fixtures clave** en `tests/conftest_permisos.py` proveen respuestas simuladas de la API, conexiones a base de datos y datos de ejemplo utilizados en varios módulos de pruebas.
- Puntos destacados de cobertura:
  * `test_api_client.py` – valida el comportamiento del cliente API y el procesamiento de permisos.
  * `test_data_processor.py` – pruebas unitarias para cada paso de procesamiento (manejo de turnos nocturnos, deducción de descansos, regla de perdón, etc.).
  * `test_report_generator.py` – asegura que se crean correctamente los archivos CSV, HTML y Excel con el contenido esperado.
  * `test_main.py` – prueba end‑to‑end que ejecuta `main.main()` con dependencias simuladas, confirmando que todo el pipeline funciona.
  * `test_gui.py` – verifica que la ventana principal se carga y responde a acciones del usuario sin lanzar el proceso completo de generación de reportes.
- Las pruebas están marcadas (`@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`, `@pytest.mark.edge`) para permitir ejecuciones selectivas mediante la opción `-m`.
- Ejemplo para ejecutar un caso de prueba específico:
  ```bash
  uv run pytest tests/test_data_processor.py::TestAttendanceProcessor::test_procesar_horarios_con_medianoche
  ```

## Uso de la documentación
- Este archivo puede ser consultado por desarrolladores o agentes de IA para comprender rápidamente el flujo de trabajo de alto nivel, los puntos de entrada y la cobertura de pruebas.
- Para obtener información detallada del código, revise los docstrings de cada módulo y la extensa suite de pruebas bajo `tests/`.
