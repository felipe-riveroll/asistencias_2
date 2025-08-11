# Resumen de la Arquitectura del Proyecto *asistencias_2*

## Visión General
El proyecto procesa los registros de asistencia de empleados (check‑ins) provenientes de la API de **Frappe/ERPNext**, los combina con los horarios programados almacenados en PostgreSQL y genera reportes detallados (CSV, HTML y Excel) que incluyen tardanzas, ausencias, permisos y cálculo de horas trabajadas.

## Componentes Principales

| Área | Módulo / Clase | Responsabilidad | Elementos Clave |
|------|----------------|-----------------|-----------------|
| **Entrada de datos** | `api_client.py` | Consulta la API de Frappe para obtener los check‑ins. | Función `obtener_checkins` |
| **Persistencia de horarios** | `db_postgres_connection.py` | Conexión a PostgreSQL y extracción de horarios (función `f_tabla_horarios_multi_quincena`). | `connect_db`, `obtener_tabla_horarios`, `obtener_horarios_multi_quincena`, `mapear_horarios_por_empleado_multi`, `obtener_horario_empleado` |
| **Configuración** | `config.py` | Constantes del sistema: políticas de permisos, umbrales de tardanza/falta, ventana de gracia para turnos nocturnos, rutas de salida, mapeo de nombres de días, etc. | `POLITICA_PERMISOS`, `GRACE_MINUTES`, `DIAS_ESPANOL` |
| **Lógica de negocio** | `data_processor.py` (clase `AttendanceProcessor`) | • Conversión de check‑ins a `DataFrame` base.\n• Enriquecimiento con horarios.\n• Cálculo de descansos.\n• Detección y manejo de turnos que cruzan medianoche (gracia ≈ 59 min).\n• Detección de salidas anticipadas, tardanzas y faltas.\n• Ajuste de horas esperadas según permisos.\n• Regla de “perdón” cuando se cumplen las horas del turno.\n• Re‑clasificación de ausencias con permisos. | Métodos `process_checkins_to_dataframe`, `analizar_asistencia_con_horarios_cache`, `aplicar_calculo_horas_descanso`, `procesar_horarios_con_medianoche`, `ajustar_horas_esperadas_con_permisos`, `aplicar_regla_perdon_retardos`, `clasificar_faltas_con_permisos` |
| **Generación de reportes** | `generar_reporte_optimizado.py` | Orquesta el flujo completo: obtención de check‑ins → carga de horarios → procesamiento con `AttendanceProcessor` → escritura de CSV, HTML y Excel. | Función `main` (script ejecutable) |
| | `report_generator.py` | Construye los CSV de detalle y el resumen de periodo a partir del `DataFrame` final. |
| | `reporte_excel.py` | Crea un archivo XLSX con formato avanzado (colores según estado, múltiples hojas, KPIs). |
| **Interfaz de usuario** | `gui_pyqt6.py` + `run_gui.py` | UI Qt que permite al usuario seleccionar rango de fechas, sucursal y lanzar la generación de reportes sin usar la línea de comandos. |
| **Utilidades auxiliares** | `utils.py` | Funciones auxiliares de manejo de `timedelta` y helpers genéricos. |
| **Pruebas** | `tests/` | Más de 200 pruebas unitarias e integrales que cubren cada capa del sistema. Cada archivo `test_*.py` valida una funcionalidad concreta. |
| **Documentación y configuración** | `Docs/`, `.env.example`, `.gitignore`, `CRUSH.md` | Guías de uso, roadmap, notas de ajuste, variables de entorno y comandos habituales. |

## Flujo de Datos (alto nivel)
```
api_client.py (GET /Employee Checkin)
        │
        ▼
Listado de diccionarios con check‑ins
        │
        ▼
───────────────────────────────────────
│   data_processor.py (process_checkins) │   db_postgres_connection.py (obtener horarios)
───────────────────────────────────────
        │                               │
        ▼                               ▼
  DataFrame base                 Cache de horarios
        │                               │
        └───────────┬───────────────────┘
                    ▼
   Enriquecimiento (horario, cruza medianoche, etc.)
                    │
                    ▼
  Reglas de negocio (tardanzas, descansos, permisos, perdón)
                    │
                    ▼
   DataFrame final con columnas:
   - checado_1..9
   - tipo_retardo, minutos_tarde
   - salida_anticipada, horas_descanso, …
                    │
                    ▼
 ┌─────────────────────────────────────────────────────┐
 │ Generación de reportes (CSV/HTML/Excel)            │
 │   - report_generator.py                             │
 │   - reporte_excel.py                                │
 └─────────────────────┬───────────────────────────────┘
                       ▼
          Archivos de salida en la carpeta de salida
```

## Detalles relevantes
- **Turnos nocturnos**: `procesar_horarios_con_medianoche` separa marcas antes y después de medianoche y asigna, mediante la ventana de gracia (`GRACE_MINUTES = 59`), las marcas que caen justo después de la hora de salida al día de turno anterior.
- **Multi‑quincena**: `obtener_horarios_multi_quincena` devuelve horarios de la primera y/o segunda quincena; `mapear_horarios_por_empleado_multi` crea la estructura `{código: {True/False: {día: horario}}}` que `obtener_horario_empleado` interpreta tanto en modo legacy como multi‑quincena.
- **Permisos**: Se consultan a través de `permisos_dict`; la política se define en `POLITICA_PERMISOS`. Los permisos de medio día descuentan solo la mitad de las horas esperadas.
- **Perdón de tardanza**: Si `horas_trabajadas >= horas_esperadas` se anula la marca de tardanza (y opcionalmente también faltas injustificadas).
- **Formato de fechas y horas**: El código maneja tanto `HH:MM` como `HH:MM:SS`; la conversión se realiza en varios puntos (p. ej. `datetime.strptime`).
- **Generación de Excel**: `reporte_excel.py` utiliza `openpyxl` para aplicar colores y crear múltiples hojas con KPI.

## Puntos críticos / Área de mantenimiento
1. **Ventana de gracia** – lógica central en `map_shift_date`. Cambios futuros deben validar que la asignación a días anteriores sigue siendo correcta.
2. **Cache de horarios** – mantiene dos formatos (legacy y multi‑quincena); cualquier cambio en la estructura debe reflejarse en `obtener_horario_empleado`.
3. **Política de permisos** – cualquier nueva regla requiere actualización de `POLITICA_PERMISOS` y de la lógica en `ajustar_horas_esperadas_con_permisos`.
4. **Formato de horas** – se usan varios parsers; se debe asegurar consistencia al añadir nuevos campos de tiempo.
5. **Generación de Excel** – depende de nombres de columnas del `DataFrame`; cambios en la salida pueden romper el estilo.

## Herramientas de calidad
- **Ruff** (formateo y lint). 
- **MyPy** (type checking, el proyecto requiere tipado completo). 
- **Pytest** con marcadores (`unit`, `integration`, `slow`). 
- **CRUSH.md** contiene los comandos habituales (`uv run pytest`, `uv run ruff check .`, etc.).

---
*Este archivo está pensado como un punto de referencia rápido para nuevos desarrolladores y para documentación del proyecto.*
