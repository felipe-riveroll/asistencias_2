# 🏢 Sistema de Reportes de Asistencia - Arquitectura Modular

Sistema completo para generar reportes de asistencia, retardos y horas trabajadas, integrando datos de marcaciones de empleados con horarios programados desde PostgreSQL.

## 🏗️ **Nueva Arquitectura Modular**

El sistema ha sido refactorizado completamente en una **arquitectura modular** que mantiene toda la funcionalidad original pero con mejor organización, mantenibilidad y escalabilidad.

### **🌟 Ventajas de la Arquitectura Modular:**

- **📦 Separación de Responsabilidades**: Cada módulo tiene una función específica y bien definida
- **🔧 Mantenibilidad**: Código más fácil de entender, modificar y depurar
- **🧪 Testabilidad**: Módulos independientes facilitan las pruebas unitarias
- **🚀 Escalabilidad**: Fácil agregar nuevas funcionalidades sin afectar el código existente
- **🔄 Reutilización**: Componentes reutilizables entre diferentes partes del sistema
- **🛠️ Configuración Centralizada**: Todas las constantes y configuraciones en un solo lugar
- **🌐 Interfaz en Español**: Mensajes de consola completamente traducidos al español
- **🐛 Corrección de Errores**: Se corrigió un error crítico de JavaScript que impedía el funcionamiento del dashboard HTML

### **🔧 Proceso de Refactorización:**

El script monolítico original de **1844 líneas** fue dividido en **6 módulos especializados**:
1. **`main.py`** (205 líneas) - Orquestación principal
2. **`config.py`** (89 líneas) - Configuración y constantes
3. **`utils.py`** (263 líneas) - Utilidades compartidas
4. **`api_client.py`** (215 líneas) - Cliente de APIs
5. **`data_processor.py`** (694 líneas) - Procesamiento de datos
6. **`report_generator.py`** (634 líneas) - Generación de reportes

**Total modular**: ~2100 líneas distribuidas vs **1844 líneas** monolíticas
**Funcionalidad**: 100% equivalente, con correcciones de errores críticos

## 🚀 **Características Principales**

- **🏗️ Arquitectura Modular**: **NUEVO** - Sistema refactorizado en 6 módulos especializados para mejor mantenibilidad
- **🌐 Interfaz en Español**: **NUEVO** - Mensajes de consola completamente traducidos al español
- **🐛 Dashboard Corregido**: **NUEVO** - Corregido error crítico de JavaScript que impedía el funcionamiento del dashboard
- **📊 Análisis Automático**: Procesa checadas y las compara con horarios programados
- **⏰ Gestión de Retardos**: Clasifica asistencias (A Tiempo, Retardo, Falta)
- **🚪 Detección de Salidas Anticipadas**: **NUEVO** - Detecta cuando empleados se retiran antes del horario programado
- **🎯 Regla de Perdón de Retardos**: Perdona retardos cuando se cumplen las horas del turno
- **📋 Integración de Permisos**: Conecta con ERPNext para obtener permisos aprobados
- **✅ Faltas Justificadas**: Reclasifica automáticamente faltas con permisos válidos
- **🆕 Permisos de Medio Día**: **NUEVO** - Maneja permisos de medio día (0.5 días) con cálculo proporcional de horas
- **🌙 Turnos Nocturnos**: Maneja correctamente horarios que cruzan medianoche
- **💾 Caché Inteligente**: Optimiza consultas a base de datos con sistema de caché
- **📈 Reportes Detallados**: Genera CSV con análisis completo y resúmenes
- **🌐 Dashboard HTML Interactivo**: **CORREGIDO** - Dashboard con DataTables.net funcionando correctamente
- **🧪 Pruebas Unitarias**: 209+ pruebas automatizadas con pytest
- **🔧 Configuración Centralizada**: Todas las constantes y configuraciones en un módulo dedicado

## 📋 **Requisitos del Sistema**

### **Software Requerido:**
- Python 3.8+
- PostgreSQL 12+
- Acceso a API de registros de asistencia

### **Dependencias Python:**
```bash
pandas>=1.5.0
numpy>=1.21.0
requests>=2.28.0
python-dotenv>=0.19.0
psycopg2-binary>=2.9.0
pytz>=2022.1
pytest>=7.0.0
pytest-cov>=4.0.0
pytest-mock>=3.10.0
responses>=0.22.0
freezegun>=1.2.0
```

## ⚙️ **Configuración Inicial**

### **1. Variables de Entorno**
Copia `.env.example` a `.env` y configura:

```bash
# Base de Datos PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=asistencias_db
DB_USER=usuario
DB_PASSWORD=contraseña

# API de Asistencia
ASIATECH_API_KEY=tu_api_key
ASIATECH_API_SECRET=tu_api_secret

# API de Permisos ERPNext  
LEAVE_API_URL=https://erp.asiatech.com.mx/api/resource/Leave%20Application
```

### **2. Instalación de Dependencias**
```bash
# Usando uv (recomendado)
uv sync

# O usando pip
pip install -r requirements.txt
```

## 🏗️ **Estructura del Proyecto - Arquitectura Modular**

```
nuevo_asistencias/
├── 📁 tests/                                    # Pruebas unitarias
│   ├── test_generar_reporte_optimizado.py      # Pruebas básicas del sistema
│   ├── test_casos_edge.py                      # Casos límite y validaciones
│   ├── test_permisos_integration.py            # Integración con ERPNext
│   ├── test_permisos_performance.py            # Pruebas de rendimiento
│   ├── test_permisos_sin_goce.py               # Permisos sin goce de sueldo
│   ├── test_quincenas.py                       # Pruebas de quincenas
│   ├── test_normalizacion_permisos.py          # Normalización de tipos de permiso
│   ├── test_cruce_medianoche.py                # Turnos nocturnos
│   ├── test_resumen_periodo.py                 # Generación de resúmenes
│   ├── test_umbral_falta_injustificada.py      # Umbral de 60 minutos
│   ├── test_perdon_retardos.py                 # Regla de perdón de retardos
│   ├── conftest_permisos.py                    # Fixtures para pruebas
│   └── run_tests.py                            # Ejecutor interno
├── 📄 main.py                                   # **NUEVO** - Script principal modular (punto de entrada)
├── 📄 config.py                                 # **NUEVO** - Configuración centralizada y constantes
├── 📄 utils.py                                  # **NUEVO** - Funciones de utilidad compartidas
├── 📄 api_client.py                             # **NUEVO** - Cliente para APIs externas (checadas y permisos)
├── 📄 data_processor.py                         # **NUEVO** - Lógica de procesamiento de datos de asistencia
├── 📄 report_generator.py                       # **NUEVO** - Generación de reportes CSV y HTML
├── 📄 generar_reporte_optimizado.py            # Script original (monolítico, mantenido para referencia)
├── 📄 db_postgres_connection.py                # Conexión BD
├── 📄 db_postgres.sql                          # Estructura BD
├── 📄 pyproject.toml                           # Configuración proyecto
├── 📄 pytest.ini                               # Configuración pytest
├── 📄 run_tests.py                             # Ejecutor pruebas
├── 📄 README_PYTEST.md                         # Documentación pruebas
├── 📄 README_PERMISOS_TESTS.md                 # Documentación pruebas permisos
├── 📄 INTEGRACION_PERMISOS.md                  # Documentación integración permisos
├── 📄 PERMISOS_SIN_GOCE_DOCS.md                # Documentación permisos sin goce
├── 📄 RESUMEN_IMPLEMENTACION_PERDON_RETARDOS.md # Documentación regla de perdón
└── 📄 INFORME_ESTABILIZACION_TESTS.md          # Informe de estabilización
```

## 🔧 **Componentes de la Arquitectura Modular**

### **`main.py` - Script Principal Modular**
**Punto de entrada del sistema** que orquesta todos los módulos:

**Clase Principal:**
- `AttendanceReportManager`: Coordina todo el proceso de generación de reportes
- `generate_attendance_report()`: Método principal que ejecuta todo el flujo
- **Mensajes en español**: Toda la interfaz de consola en español

**Configuración de Ejecución:**
```python
# En la sección de configuración del archivo:
start_date = "2025-07-01"      # Fecha inicio
end_date = "2025-07-31"        # Fecha fin
sucursal = "Villas"            # Sucursal a analizar
device_filter = "%Villas%"     # Filtro de dispositivos
```

### **`config.py` - Configuración Centralizada**
**Constantes y configuración del sistema:**
- `POLITICA_PERMISOS`: Política de manejo de diferentes tipos de permisos
- `TOLERANCIA_RETARDO_MINUTOS`: 15 minutos de tolerancia para retardos
- `UMBRAL_FALTA_INJUSTIFICADA_MINUTOS`: 60 minutos para considerar falta injustificada
- `TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS`: 15 minutos de tolerancia para salidas anticipadas
- `OUTPUT_*`: Rutas de archivos de salida
- `validate_api_credentials()`: Validación de credenciales de API

### **`utils.py` - Funciones de Utilidad**
**Funciones auxiliares compartidas:**
- `obtener_codigos_empleados_api()`: Extrae códigos únicos de empleados
- `determine_period_type()`: Determina si incluye primera/segunda quincena
- `normalize_leave_type()`: Normaliza tipos de permisos
- `time_to_decimal()`: Convierte tiempo HH:MM:SS a decimal
- `format_timedelta_with_sign()`: Formatea diferencias de tiempo
- `calculate_working_days()`: Calcula días laborales en un período
- `safe_timedelta()`: Conversión segura a Timedelta

### **`api_client.py` - Cliente de APIs Externas**
**Manejo de APIs de checadas y permisos:**

**Clase Principal:**
- `APIClient`: Cliente para APIs de asistencia y permisos

**Funciones Core:**
- `fetch_checkins()`: Obtiene checadas desde la API de asistencia
- `fetch_leave_applications()`: Obtiene permisos aprobados desde ERPNext
- `procesar_permisos_empleados()`: Organiza permisos por empleado y fecha

### **`data_processor.py` - Procesamiento de Datos**
**Lógica central de negocio para análisis de asistencia:**

**Clase Principal:**
- `AttendanceProcessor`: Procesador principal de datos de asistencia

**Funciones Core:**
- `process_checkins_to_dataframe()`: Convierte datos a DataFrame base
- `procesar_horarios_con_medianoche()`: Maneja turnos nocturnos
- `analizar_asistencia_con_horarios_cache()`: Analiza retardos y salidas anticipadas
- `aplicar_calculo_horas_descanso()`: Calcula automáticamente horas de descanso
- `ajustar_horas_esperadas_con_permisos()`: Ajusta horas considerando permisos
- `aplicar_regla_perdon_retardos()`: Aplica perdón de retardos por cumplimiento de horas
- `clasificar_faltas_con_permisos()`: Reclasifica faltas como justificadas

### **`report_generator.py` - Generación de Reportes**
**Generación de reportes CSV y HTML:**

**Clase Principal:**
- `ReportGenerator`: Generador de todos los tipos de reportes

**Funciones Core:**
- `save_detailed_report()`: Guarda reporte detallado en CSV
- `generar_resumen_periodo()`: Genera resumen del período
- `generar_reporte_html()`: **CORREGIDO** - Genera dashboard interactivo con DataTables.net
- `_generate_html_template()`: Template HTML completo con JavaScript corregido

### **`generar_reporte_optimizado.py` - Script Original**
**Script monolítico original** mantenido para referencia y compatibilidad. Contiene toda la funcionalidad en un solo archivo de 1800+ líneas.

### **`db_postgres_connection.py` - Gestión de Base de Datos**

**Funciones Principales:**
- `connect_db()`: Conexión a PostgreSQL
- `obtener_tabla_horarios()`: Obtiene horarios programados
- `mapear_horarios_por_empleado()`: Organiza horarios por empleado
- `obtener_horario_empleado()`: Consulta horario específico desde caché

### **`db_postgres.sql` - Estructura de Base de Datos**

**Funciones SQL:**
- `f_tabla_horarios()`: Devuelve horarios programados por sucursal
- `F_CrearJsonHorario()`: Crea JSON con información de horarios

## 🚀 **Uso del Sistema**

### **📦 Ejecución con Arquitectura Modular (Recomendado):**
```bash
# Ejecutar análisis completo con la nueva arquitectura modular
uv run main.py

# O usando python directamente
python main.py
```

### **📄 Ejecución con Script Original:**
```bash
# Ejecutar con el script monolítico original
python generar_reporte_optimizado.py
```

**💡 Nota:** Ambas versiones generan exactamente los mismos resultados. La versión modular es más fácil de mantener y extender.

### **⚙️ Configuración de Fechas:**

**Para la versión modular (`main.py`):**
Edita las variables en la sección de configuración del archivo:
```python
# ==========================================================================
# CONFIGURATION SECTION - MODIFY THESE PARAMETERS AS NEEDED
# ==========================================================================

# Date range for the report
start_date = "2025-07-01"
end_date = "2025-07-31"

# Branch and device filter
sucursal = "Villas"
device_filter = "%Villas%"
```

**Para la versión original (`generar_reporte_optimizado.py`):**
Edita las variables al final del script:
```python
start_date = "2025-01-01"    # Fecha de inicio
end_date = "2025-01-15"      # Fecha de fin
sucursal = "Villas"          # Sucursal
device_filter = "%villas%"   # Filtro de dispositivos
```

### **Archivos de Salida:**
- `reporte_asistencia_analizado.csv`: Análisis detallado por empleado con permisos
- `resumen_periodo.csv`: Resumen agregado del período incluyendo faltas justificadas
- `dashboard_asistencia.html`: Dashboard interactivo con gráficas D3.js

**Columnas del Resumen:**
- `employee`: Código del empleado
- `Nombre`: Nombre completo
- `total_horas_trabajadas`: **CORREGIDO** - Horas trabajadas netas (después de descontar horas de descanso)
- `total_horas_esperadas`: Horas programadas en el periodo
- `total_horas_descontadas_permiso`: Horas restadas por permisos
- `total_horas`: Horas efectivas esperadas
- `total_retardos`: Número de retardos (sin contar perdonados)
- `faltas_del_periodo`: Faltas totales registradas
- `faltas_justificadas`: Faltas justificadas por permisos
- `total_faltas`: Faltas reales descontando justificadas
- **`total_salidas_anticipadas`**: **NUEVO** - Total de salidas anticipadas en el período
- `diferencia_HHMMSS`: **CORREGIDO** - Diferencia entre horas esperadas y trabajadas netas (después de descanso)

**Nuevas Columnas en el Reporte:**
- `tiene_permiso`: Indica si el empleado tiene permiso aprobado para el día
- `tipo_permiso`: Tipo de permiso (Vacaciones, Incapacidad, etc.)
- **🆕 `es_permiso_medio_dia`**: **NUEVO** - Indica si el permiso es de medio día (0.5 días)
- `falta_justificada`: Indica si una falta fue justificada por permiso
- `horas_esperadas_originales`: Horas originales antes del ajuste por permisos
- `horas_descontadas_permiso`: Horas descontadas por permisos aprobados
- `tipo_falta_ajustada`: Clasificación final considerando permisos
- **`retardo_perdonado`**: Indica si se aplicó perdón por cumplir horas
- **`tipo_retardo_original`**: Clasificación original antes del perdón
- **`minutos_tarde_original`**: Minutos de retardo originales
- **`salida_anticipada`**: **NUEVO** - Indica si el empleado se retiró antes del horario programado
- **`horas_descanso`**: **NUEVO** - Horas de descanso calculadas automáticamente (formato HH:MM:SS)
- **`horas_descanso_td`**: **NUEVO** - Horas de descanso en formato Timedelta
- **`horas_trabajadas_originales`**: **NUEVO** - Horas trabajadas antes del ajuste por descanso

## 🚪 **Nueva Funcionalidad: Detección de Salidas Anticipadas**

### **¿Qué hace?**
Detecta cuando un empleado se retira antes de que finalice su turno programado, proporcionando un control de asistencia más completo.

### **Configuración:**
```python
# En generar_reporte_optimizado.py
TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS = 15  # Margen de tolerancia
```

### **Lógica de Detección:**
- **Compara** la última checada del día con la `hora_salida_programada`
- **Se considera salida anticipada** si la última checada es anterior a la hora de salida programada menos 15 minutos
- **Maneja turnos nocturnos** correctamente para horarios que cruzan medianoche
- **Requiere múltiples checadas** - No se considera salida anticipada si solo hay una checada

### **Casos de Aplicación:**
- ✅ **Salida anticipada**: Última checada 17:30, salida programada 18:00 (30 min antes)
- ❌ **Salida normal**: Última checada 17:50, salida programada 18:00 (10 min antes, dentro de tolerancia)
- ✅ **Turno nocturno**: Entrada 22:00, salida programada 06:00 del día siguiente
- ❌ **Una sola checada**: No se considera salida anticipada

### **Impacto en Métricas:**
- `salida_anticipada = True/False` en reporte detallado
- `total_salidas_anticipadas` en resumen del período
- Integración completa en CSV y dashboard

## ☕ **Funcionalidad: Cálculo Automático de Horas de Descanso**

### **¿Qué hace?**
Calcula automáticamente las horas de descanso basándose en los checados del día, permitiendo múltiples intervalos de descanso y ajustando las horas trabajadas y esperadas en consecuencia.

### **Lógica de Cálculo:**
- **Requisito mínimo**: Al menos 4 checadas para considerar descanso
- **Múltiples intervalos**: Calcula descansos entre pares de checadas (1-2, 3-4, etc.)
- **Ordenamiento cronológico**: Ordena las checadas por hora antes del cálculo
- **Suma total**: Acumula todos los intervalos de descanso válidos

### **Ajustes Automáticos:**
- **Horas trabajadas**: Se restan las horas de descanso calculadas
- **Horas esperadas**: Se restan 1 hora por cada día con descanso
- **Sincronización**: Se actualiza `duration_td` para consistencia con el resumen

### **Casos de Aplicación:**
- ✅ **Descanso simple**: 4 checadas → descanso entre 2ª y 3ª checada
- ✅ **Múltiples descansos**: 6 checadas → descansos entre 2ª-3ª y 4ª-5ª checadas
- ✅ **Sin descanso**: Menos de 4 checadas → 0 horas de descanso
- ✅ **Intervalos negativos**: Si la diferencia es negativa, no se considera descanso

### **Ejemplo de Cálculo:**
```
Checadas: 08:00, 12:00, 13:00, 17:00
- Descanso 1: 13:00 - 12:00 = 1:00 hora
- Total descanso: 1:00 hora
- Horas trabajadas ajustadas: 8:00 - 1:00 = 7:00 horas
- Horas esperadas ajustadas: 8:00 - 1:00 = 7:00 horas
```

### **Impacto en Métricas:**
- `horas_descanso` en reporte detallado (formato HH:MM:SS)
- `horas_descanso_td` en reporte detallado (formato Timedelta)
- `total_horas_descanso` en resumen del período
- `total_horas_trabajadas` usa horas netas (después de descanso)
- `diferencia_HHMMSS` refleja diferencia real entre horas esperadas y trabajadas netas

## 🎯 **Funcionalidad: Regla de Perdón de Retardos**

### **¿Qué hace?**
Si un empleado trabajó las horas correspondientes de su turno o más, ese día NO se cuenta como retardo, incluso si llegó tarde.

### **Configuración:**
```python
# En generar_reporte_optimizado.py
PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA = False  # Por defecto desactivado
```

### **Casos de Aplicación:**
- ✅ **Retardo perdonado**: Llega 20 min tarde pero trabaja 8:30 horas (esperadas: 8:00)
- ❌ **Retardo NO perdonado**: Llega 20 min tarde pero trabaja 7:30 horas (esperadas: 8:00)
- ✅ **Permiso con horas=0**: Cualquier trabajo > 0 horas perdona el retardo
- ✅ **Turno nocturno**: Funciona con cruce de medianoche

### **Impacto en Métricas:**
- `es_retardo_acumulable = 0` para días perdonados
- `retardos_acumulados` se recalcula automáticamente
- `descuento_por_3_retardos` se ajusta correctamente
- `total_retardos` en resumen se reduce automáticamente

## 🧪 **Pruebas Unitarias**

El proyecto incluye **209+ pruebas unitarias** completas que garantizan la calidad del código:

### **📊 Resumen de Pruebas:**
- **Pruebas básicas**: Funcionalidad core del sistema
- **Casos edge**: Casos límite y validaciones
- **Integración permisos**: Conecta con ERPNext
- **Rendimiento**: Validación de escalabilidad
- **Normalización**: Tipos de permiso y variantes
- **Cruce medianoche**: Turnos nocturnos
- **Resumen periodo**: **MEJORADO** - Generación de reportes con cálculo corregido de horas netas
- **Umbral faltas**: Umbral de 60 minutos para falta injustificada
- **Perdón retardos**: **NUEVO** - Regla de perdón por cumplimiento de horas
- **🆕 Permisos de medio día**: **NUEVO** - Tests completos para permisos de medio día vs día completo
- **Cobertura**: 68% del código principal
- **Tiempo de ejecución**: ~2.6 segundos

### **🚀 Ejecutar Pruebas:**
```bash
# Ejecutar todas las pruebas
uv run pytest

# Con cobertura de código
uv run pytest --cov=. --cov-report=term-missing

# Pruebas específicas
uv run pytest tests/test_perdon_retardos.py -v
uv run pytest tests/test_umbral_falta_injustificada.py -v
uv run pytest tests/test_permisos_integration.py -v
uv run pytest tests/test_resumen_periodo.py -v
```

### **🔧 Corrección del Cálculo del Resumen del Periodo**

**Problema Resuelto:**
El resumen del periodo (`resumen_periodo.csv`) calculaba incorrectamente las horas extra usando horas trabajadas **brutas** en lugar de **netas** (después de descontar las horas de descanso).

**Solución Implementada:**
- **Sincronización de `duration_td`**: Se actualiza correctamente cuando se aplican ajustes de descanso
- **Plan B robusto**: El resumen recalcula siempre desde `horas_trabajadas` (ya ajustada) en lugar de `duration_td`
- **Cálculo preciso**: `diferencia_HHMMSS` ahora refleja la diferencia real entre horas esperadas y trabajadas netas
- **Tests específicos**: 2 nuevos tests verifican el uso correcto de horas netas

**Impacto:**
- ✅ `total_horas_trabajadas` = suma de horas **netas** (después de descanso)
- ✅ `diferencia_HHMMSS` = diferencia **neta** (puede ser cero, positiva o negativa)
- ✅ Compatibilidad total con funcionalidad existente
- ✅ Verificación automática: `sum(detalle.horas_trabajadas) == resumen.total_horas_trabajadas`

### **📖 Documentación Completa de Pruebas:**
Para información detallada sobre las pruebas, tipos de tests, configuración y ejemplos, consulta:
- **[README_PYTEST.md](README_PYTEST.md)** - Pruebas generales del sistema
- **[README_PERMISOS_TESTS.md](README_PERMISOS_TESTS.md)** - Suite de pruebas de permisos ERPNext
- **[INTEGRACION_PERMISOS.md](INTEGRACION_PERMISOS.md)** - Documentación de integración con ERPNext
- **[PERMISOS_SIN_GOCE_DOCS.md](PERMISOS_SIN_GOCE_DOCS.md)** - Documentación de permisos sin goce
- **[RESUMEN_IMPLEMENTACION_PERDON_RETARDOS.md](RESUMEN_IMPLEMENTACION_PERDON_RETARDOS.md)** - Documentación de la regla de perdón
- **[🆕 RESUMEN_CAMBIOS_PERMISOS_MEDIO_DIA.md](RESUMEN_CAMBIOS_PERMISOS_MEDIO_DIA.md)** - **NUEVO** - Documentación completa de implementación de permisos de medio día
- **[INFORME_ESTABILIZACION_TESTS.md](INFORME_ESTABILIZACION_TESTS.md)** - Informe completo de estabilización

## ⚡ **Optimizaciones Implementadas**

### **1. Sistema de Caché**
- Los horarios se consultan una sola vez por período
- Almacenamiento en memoria para evitar consultas repetitivas
- Reducción significativa en tiempo de procesamiento

### **2. Gestión de Turnos Nocturnos**
- Manejo correcto de horarios que cruzan medianoche
- Asociación automática de checadas de salida con entrada del día anterior
- Cálculo preciso de horas trabajadas

### **3. Optimización de Consultas**
- Uso directo del campo `codigo_frappe`
- Función `f_tabla_horarios` para consultas eficientes
- Eliminación de checadas duplicadas

### **4. Integración de Permisos ERPNext**
- **Conexión automática**: Obtiene permisos aprobados desde la API
- **Ajuste de horas**: Reduce horas esperadas para días con permiso
- **Faltas justificadas**: Reclasifica automáticamente faltas con permisos válidos
- **Tipos de permiso**: Vacaciones, incapacidades, permisos personales
- **Cálculo de diferencias**: Considera horas descontadas por permisos en resúmenes
- **🆕 Permisos de Medio Día**: **NUEVO** - Maneja permisos de medio día (0.5 días) correctamente
- **🆕 Campo half_day**: **NUEVO** - Procesa el campo `half_day` de la API para distinguir entre día completo y medio día
- **🆕 Cálculo proporcional**: **NUEVO** - Para permisos de medio día, descuenta solo la mitad de las horas esperadas

### **5. Lógica de Retardos Mejorada**
- **Tolerancia**: 15 minutos después de la hora programada
- **Umbral falta injustificada**: 60 minutos (configurable)
- **Clasificación**: A Tiempo → Retardo → Falta Injustificada
- **Acumulación**: 3 retardos = 1 día de descuento
- **Perdón automático**: Por cumplimiento de horas del turno

### **6. Cálculo Automático de Horas de Descanso**
- **Detección automática**: Basada en múltiples checadas del día
- **Múltiples intervalos**: Calcula descansos entre pares de checadas
- **Ajuste de horas**: Resta descanso de horas trabajadas y 1 hora de horas esperadas
- **Sincronización**: Actualiza `duration_td` para consistencia con resumen
- **Validación**: Requiere mínimo 4 checadas para considerar descanso válido

### **7. Dashboard Interactivo con DataTables.net**
- **Gráficas D3.js**: Visualización dinámica de datos
- **Tabla Profesional**: **CORREGIDO** - DataTables.net con funcionalidades avanzadas y JavaScript funcionando
- **Búsqueda Inteligente**: Filtrado en tiempo real por empleado o ID
- **Paginación Automática**: 10 registros por página con navegación
- **Ordenamiento**: Click en encabezados para ordenar por cualquier columna
- **Localización**: Interfaz completamente en español
- **Responsive Design**: Compatible con móviles y tablets
- **KPIs en tiempo real**: Tasa de asistencia, puntualidad, desviación
- **JavaScript Corregido**: **NUEVO** - Error de sintaxis JavaScript reparado que causaba dashboard en blanco

### **8. Arquitectura Modular y Mejoras**
- **Separación de Módulos**: **NUEVO** - 6 módulos especializados para mejor organización
- **Configuración Centralizada**: **NUEVO** - Todas las constantes en `config.py`
- **Utilidades Compartidas**: **NUEVO** - Funciones reutilizables en `utils.py`
- **Cliente API Dedicado**: **NUEVO** - Manejo especializado de APIs externas
- **Procesador de Datos**: **NUEVO** - Lógica de negocio centralizada
- **Generador de Reportes**: **NUEVO** - Módulo especializado para reportes CSV/HTML
- **Interfaz en Español**: **NUEVO** - Mensajes de consola traducidos completamente
- **Orquestación Principal**: **NUEVO** - Script `main.py` que coordina todos los módulos

## 📈 **Métricas del Sistema**

### **Rendimiento:**
- **Procesamiento**: ~1000 registros/segundo
- **Memoria**: Optimizado con caché inteligente
- **Base de datos**: Consultas optimizadas con índices

### **Precisión:**
- **Cobertura de pruebas**: 68%
- **Casos edge**: Múltiples pruebas específicas
- **Integración permisos**: Pruebas completas
- **Validaciones**: Formato de horas, fechas, datos nulos, APIs externas

## 🔍 **Casos de Uso**

### **1. Análisis Quincenal**
```python
# Primera quincena
start_date = "2025-01-01"
end_date = "2025-01-15"

# Segunda quincena  
start_date = "2025-01-16"
end_date = "2025-01-31"
```

### **2. Múltiples Sucursales**
```python
# Sucursal Villas
sucursal = "Villas"
device_filter = "%villas%"

# Sucursal Centro
sucursal = "Centro"
device_filter = "%centro%"
```

### **3. Integración de Permisos**
El sistema automáticamente:
- Consulta permisos aprobados para el período
- Ajusta horas esperadas según días con permiso  
- Justifica faltas que coinciden con permisos válidos
- Incluye estadísticas de permisos en el resumen final

### **4. Turnos Nocturnos**
El sistema maneja automáticamente:
- Entrada: 22:00 (día actual)
- Salida: 06:00 (día siguiente)
- Cálculo correcto de horas trabajadas

### **5. Perdón de Retardos**
El sistema automáticamente:
- Detecta cuando se cumplen las horas del turno
- Perdona retardos por cumplimiento de horas
- Recalcula métricas de retardos acumulados
- Proporciona trazabilidad completa en CSV

### **6. Detección de Salidas Anticipadas**
El sistema automáticamente:
- **NUEVO** - Detecta cuando empleados se retiran antes del horario programado
- Aplica tolerancia configurable (15 minutos por defecto)
- Maneja correctamente turnos que cruzan medianoche
- Incluye métricas en reportes detallados y resúmenes
- Integra con dashboard interactivo para análisis visual

### **7. ☕ Cálculo Automático de Horas de Descanso**
El sistema automáticamente:
- **Calcula descansos** basándose en múltiples checadas del día
- **Permite múltiples intervalos** de descanso (pares 1-2, 3-4, etc.)
- **Ajusta horas trabajadas** restando las horas de descanso calculadas
- **Ajusta horas esperadas** restando 1 hora por cada día con descanso
- **Sincroniza duration_td** para consistencia con el resumen del periodo
- **Requiere mínimo 4 checadas** para considerar descanso válido
- **Ordena cronológicamente** las checadas antes del cálculo
- **Acumula todos los intervalos** de descanso válidos

### **8. 🆕 Permisos de Medio Día**
El sistema automáticamente:
- **NUEVO** - Procesa el campo `half_day` de la API de ERPNext
- **NUEVO** - Distingue entre permisos de día completo (`half_day: 0`) y medio día (`half_day: 1`)
- **NUEVO** - Para permisos de medio día, descuenta solo la mitad de las horas esperadas
- **NUEVO** - Calcula correctamente 0.5 días de ausencia para permisos de medio día
- **NUEVO** - Incluye la columna `es_permiso_medio_dia` en reportes detallados
- **NUEVO** - Mantiene estadísticas separadas para permisos de día completo vs medio día

### **9. 🔧 Cálculo Corregido del Resumen del Periodo**
El sistema automáticamente:
- **CORREGIDO** - Calcula `total_horas_trabajadas` usando horas netas (después de descanso)
- **CORREGIDO** - Calcula `diferencia_HHMMSS` usando la diferencia real entre horas esperadas y trabajadas netas
- **CORREGIDO** - Sincroniza `duration_td` con ajustes de descanso para consistencia
- **CORREGIDO** - Implementa Plan B robusto que recalcula desde `horas_trabajadas` ya ajustada
- **CORREGIDO** - Verifica automáticamente que la suma de horas en detalle coincida con el resumen
- **CORREGIDO** - Mantiene compatibilidad total con funcionalidad existente

**Ejemplo de datos de la API:**
```json
{
    "employee": "34",
    "employee_name": "Liliana Pérez Medina",
    "leave_type": "Compensación de tiempo por tiempo",
    "from_date": "2025-07-04",
    "to_date": "2025-07-04",
    "status": "Approved",
    "half_day": 1  // 1 = medio día, 0 = día completo
}
```

**Comportamiento del sistema:**
- **`half_day: 0`**: Permiso de día completo → descuento total de horas (8:00 → 0:00)
- **`half_day: 1`**: Permiso de medio día → descuento de la mitad (8:00 → 4:00)

## 🚨 **Solución de Problemas**

### **Error de Conexión a BD:**
```bash
# Verificar variables de entorno
cat .env

# Probar conexión
python -c "from db_postgres_connection import connect_db; print(connect_db())"
```

### **Error de API:**
```bash
# Verificar credenciales API
echo $ASIATECH_API_KEY
echo $ASIATECH_API_SECRET
```

### **Error en Pruebas:**
```bash
# Verificar estructura
uv run pytest --collect-only

# Ejecutar con debug
uv run pytest tests/ -v -s
```

## 📝 **Notas Importantes**

- **Determinación automática**: El sistema detecta primera o segunda quincena
- **Filtros de dispositivo**: Usar `%sucursal%` para filtrar por ubicación
- **Formato de fechas**: YYYY-MM-DD (ISO 8601)
- **Zona horaria**: Todas las fechas en zona horaria local
- **Perdón de retardos**: Se aplica automáticamente cuando se cumplen las horas
- **Umbral de falta injustificada**: 60 minutos (configurable)
- **Cálculo de resumen**: **CORREGIDO** - Usa horas trabajadas netas (después de descanso) para cálculos precisos
- **Horas de descanso**: Se calculan automáticamente con mínimo 4 checadas, ajustando horas trabajadas y esperadas

## 🤝 **Contribución**

### **Agregar Nuevas Funcionalidades:**
1. Crear pruebas unitarias primero
2. Implementar funcionalidad
3. Ejecutar todas las pruebas
4. Actualizar documentación

### **Reportar Problemas:**
1. Ejecutar pruebas para verificar
2. Incluir logs de error
3. Especificar configuración usada

## 📄 **Licencia**

Este proyecto está bajo la Licencia MIT. Ver archivo LICENSE para más detalles.

---

## 🔄 **Historial de Versiones**

### **Versión 6.0 - Arquitectura Modular (Agosto 2025)**
- **🏗️ Arquitectura Modular**: Refactorización completa en 6 módulos especializados
- **🌐 Interfaz en Español**: Traducción completa de mensajes de consola
- **🐛 Dashboard Corregido**: Reparado error crítico de JavaScript en el dashboard HTML
- **📦 Mejor Organización**: Separación clara de responsabilidades entre módulos
- **🔧 Configuración Centralizada**: Todas las constantes en un módulo dedicado
- **🚀 Mantenibilidad Mejorada**: Código más fácil de mantener y extender

### **Versión 5.1 - Funcionalidades Avanzadas (Julio 2025)**
- PostgreSQL + Pytest + Permisos ERPNext + Perdón de Retardos
- Salidas Anticipadas + DataTables.net + Cálculo Corregido de Resumen

**Versión Actual:** 6.0 (Arquitectura Modular + Dashboard Corregido + Interfaz en Español)  
**Última actualización:** Agosto 2025  
**Estado:** Completamente funcional con 209+ pruebas pasando ✅  
**Compatibilidad:** 100% compatible con versión original, con mejoras y correcciones
