# 🏢 Sistema de Reportes de Asistencia - Optimizado

Sistema completo para generar reportes de asistencia, retardos y horas trabajadas, integrando datos de marcaciones de empleados con horarios programados desde PostgreSQL.

## 🚀 **Características Principales**

- **📊 Análisis Automático**: Procesa checadas y las compara con horarios programados
- **⏰ Gestión de Retardos**: Clasifica asistencias (A Tiempo, Retardo, Falta)
- **🎯 Regla de Perdón de Retardos**: Perdona retardos cuando se cumplen las horas del turno
- **📋 Integración de Permisos**: Conecta con ERPNext para obtener permisos aprobados
- **✅ Faltas Justificadas**: Reclasifica automáticamente faltas con permisos válidos
- **🌙 Turnos Nocturnos**: Maneja correctamente horarios que cruzan medianoche
- **💾 Caché Inteligente**: Optimiza consultas a base de datos con sistema de caché
- **📈 Reportes Detallados**: Genera CSV con análisis completo y resúmenes
- **🌐 Dashboard HTML**: Genera dashboard interactivo con D3.js
- **🧪 Pruebas Unitarias**: 177+ pruebas automatizadas con pytest

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

## 🏗️ **Estructura del Proyecto**

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
├── 📄 generar_reporte_optimizado.py            # Script principal
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

## 🔧 **Componentes Principales**

### **`generar_reporte_optimizado.py` - Script Principal**

**Funciones Core:**
- `fetch_checkins()`: Obtiene checadas desde la API
- `fetch_leave_applications()`: Obtiene permisos aprobados desde ERPNext
- `process_checkins_to_dataframe()`: Convierte datos a DataFrame
- `procesar_permisos_empleados()`: Organiza permisos por empleado y fecha
- `ajustar_horas_esperadas_con_permisos()`: Ajusta horas considerando permisos
- `aplicar_regla_perdon_retardos()`: **NUEVO** - Aplica perdón de retardos por cumplimiento de horas
- `clasificar_faltas_con_permisos()`: Reclasifica faltas como justificadas
- `procesar_horarios_con_medianoche()`: Maneja turnos nocturnos
- `analizar_asistencia_con_horarios_cache()`: Analiza retardos y asistencias
- `generar_resumen_periodo()`: Genera reportes finales
- `generar_reporte_html()`: Genera dashboard interactivo

**Configuración de Ejecución:**
```python
# Al final del script, configurar:
start_date = "2025-01-01"      # Fecha inicio
end_date = "2025-01-15"        # Fecha fin
sucursal = "Villas"            # Sucursal a analizar
device_filter = "%villas%"     # Filtro de dispositivos
```

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

### **Ejecución Básica:**
```bash
# Ejecutar análisis completo
python generar_reporte_optimizado.py
```

### **Configuración de Fechas:**
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
- `total_horas_trabajadas`: Horas trabajadas sin descuentos
- `total_horas_esperadas`: Horas programadas en el periodo
- `total_horas_descontadas_permiso`: Horas restadas por permisos
- `total_horas`: Horas efectivas esperadas
- `total_retardos`: Número de retardos (sin contar perdonados)
- `faltas_del_periodo`: Faltas totales registradas
- `faltas_justificadas`: Faltas justificadas por permisos
- `total_faltas`: Faltas reales descontando justificadas
- `diferencia_HHMMSS`: Diferencia entre horas esperadas y trabajadas

**Nuevas Columnas en el Reporte:**
- `tiene_permiso`: Indica si el empleado tiene permiso aprobado para el día
- `tipo_permiso`: Tipo de permiso (Vacaciones, Incapacidad, etc.)
- `falta_justificada`: Indica si una falta fue justificada por permiso
- `horas_esperadas_originales`: Horas originales antes del ajuste por permisos
- `horas_descontadas_permiso`: Horas descontadas por permisos aprobados
- `tipo_falta_ajustada`: Clasificación final considerando permisos
- **`retardo_perdonado`**: **NUEVO** - Indica si se aplicó perdón por cumplir horas
- **`tipo_retardo_original`**: **NUEVO** - Clasificación original antes del perdón
- **`minutos_tarde_original`**: **NUEVO** - Minutos de retardo originales

## 🎯 **Nueva Funcionalidad: Regla de Perdón de Retardos**

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

El proyecto incluye **177+ pruebas unitarias** completas que garantizan la calidad del código:

### **📊 Resumen de Pruebas:**
- **Pruebas básicas**: Funcionalidad core del sistema
- **Casos edge**: Casos límite y validaciones
- **Integración permisos**: Conecta con ERPNext
- **Rendimiento**: Validación de escalabilidad
- **Normalización**: Tipos de permiso y variantes
- **Cruce medianoche**: Turnos nocturnos
- **Resumen periodo**: Generación de reportes
- **Umbral faltas**: Umbral de 60 minutos para falta injustificada
- **Perdón retardos**: **NUEVO** - Regla de perdón por cumplimiento de horas
- **Cobertura**: 68% del código principal
- **Tiempo de ejecución**: ~3.5 segundos

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
```

### **📖 Documentación Completa de Pruebas:**
Para información detallada sobre las pruebas, tipos de tests, configuración y ejemplos, consulta:
- **[README_PYTEST.md](README_PYTEST.md)** - Pruebas generales del sistema
- **[README_PERMISOS_TESTS.md](README_PERMISOS_TESTS.md)** - Suite de pruebas de permisos ERPNext
- **[INTEGRACION_PERMISOS.md](INTEGRACION_PERMISOS.md)** - Documentación de integración con ERPNext
- **[PERMISOS_SIN_GOCE_DOCS.md](PERMISOS_SIN_GOCE_DOCS.md)** - Documentación de permisos sin goce
- **[RESUMEN_IMPLEMENTACION_PERDON_RETARDOS.md](RESUMEN_IMPLEMENTACION_PERDON_RETARDOS.md)** - Documentación de la regla de perdón
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

### **5. Lógica de Retardos Mejorada**
- **Tolerancia**: 15 minutos después de la hora programada
- **Umbral falta injustificada**: 60 minutos (configurable)
- **Clasificación**: A Tiempo → Retardo → Falta Injustificada
- **Acumulación**: 3 retardos = 1 día de descuento
- **Perdón automático**: Por cumplimiento de horas del turno

### **6. Dashboard Interactivo**
- **Gráficas D3.js**: Visualización dinámica de datos
- **KPIs en tiempo real**: Tasa de asistencia, puntualidad, desviación
- **Filtros interactivos**: Búsqueda por empleado
- **Responsive design**: Compatible con móviles

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

**Versión:** 4.0 (PostgreSQL + Pytest + Permisos ERPNext + Perdón de Retardos + Dashboard)  
**Última actualización:** Julio 2025  
**Estado:** Completamente funcional con 177+ pruebas pasando ✅
