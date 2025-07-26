# 🏢 Sistema de Reportes de Asistencia - Optimizado

Sistema completo para generar reportes de asistencia, retardos y horas trabajadas, integrando datos de marcaciones de empleados con horarios programados desde PostgreSQL.

## 🚀 **Características Principales**

- **📊 Análisis Automático**: Procesa checadas y las compara con horarios programados
- **⏰ Gestión de Retardos**: Clasifica asistencias (A Tiempo, Retardo, Falta)
- **�️ Integración de Permisos**: Conecta con ERPNext para obtener permisos aprobados
- **✅ Faltas Justificadas**: Reclasifica automáticamente faltas con permisos válidos
- **�🌙 Turnos Nocturnos**: Maneja correctamente horarios que cruzan medianoche
- **💾 Caché Inteligente**: Optimiza consultas a base de datos con sistema de caché
- **📈 Reportes Detallados**: Genera CSV con análisis completo y resúmenes
- **🧪 Pruebas Unitarias**: 93 pruebas automatizadas con pytest

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
openpyxl>=3.0.0
xlsxwriter>=3.0.0
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
│   ├── test_generar_reporte_optimizado.py      # 31 pruebas básicas
│   ├── test_casos_edge.py                      # 34 pruebas edge
│   ├── test_permisos_integration.py            # 17 pruebas permisos
│   ├── test_permisos_performance.py            # 11 pruebas rendimiento
│   ├── conftest_permisos.py                    # Fixtures permisos
│   └── run_tests.py                            # Ejecutor interno
├── 📄 generar_reporte_optimizado.py            # Script principal
├── 📄 db_postgres_connection.py                # Conexión BD
├── 📄 db_postgres.sql                          # Estructura BD
├── 📄 pyproject.toml                           # Configuración proyecto
├── 📄 pytest.ini                               # Configuración pytest
├── 📄 pytest_permisos.ini                     # Config pytest permisos
├── 📄 run_tests.py                             # Ejecutor pruebas
├── 📄 README_PYTEST.md                         # Documentación pruebas
└── 📄 README_PERMISOS_TESTS.md                 # Documentación pruebas permisos
```

## 🔧 **Componentes Principales**

### **`generar_reporte_optimizado.py` - Script Principal**

**Funciones Core:**
- `fetch_checkins()`: Obtiene checadas desde la API
- `fetch_leave_applications()`: Obtiene permisos aprobados desde ERPNext
- `process_checkins_to_dataframe()`: Convierte datos a DataFrame
- `procesar_permisos_empleados()`: Organiza permisos por empleado y fecha
- `ajustar_horas_esperadas_con_permisos()`: Ajusta horas considerando permisos
- `clasificar_faltas_con_permisos()`: Reclasifica faltas como justificadas
- `procesar_horarios_con_medianoche()`: Maneja turnos nocturnos
- `analizar_asistencia_con_horarios_cache()`: Analiza retardos y asistencias
- `generar_resumen_periodo()`: Genera reportes finales

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

**Nuevas Columnas en el Reporte:**
- `tiene_permiso`: Indica si el empleado tiene permiso aprobado para el día
- `tipo_permiso`: Tipo de permiso (Vacaciones, Incapacidad, etc.)
- `falta_justificada`: Indica si una falta fue justificada por permiso
- `horas_esperadas_originales`: Horas originales antes del ajuste por permisos
- `horas_descontadas_permiso`: Horas descontadas por permisos aprobados
- `tipo_falta_ajustada`: Clasificación final considerando permisos

## 🧪 **Pruebas Unitarias**

El proyecto incluye **93 pruebas unitarias** completas que garantizan la calidad del código:

### **📊 Resumen de Pruebas:**
- **31 pruebas básicas**: Funcionalidad core del sistema
- **34 pruebas edge**: Casos límite y validaciones
- **17 pruebas permisos**: Integración completa con ERPNext
- **11 pruebas rendimiento**: Validación de escalabilidad y casos extremos
- **Cobertura**: ~98% del código principal
- **Tiempo de ejecución**: ~1.60 segundos

### **🚀 Ejecutar Pruebas:**
```bash
# Ver resumen de pruebas
python run_tests.py summary

# Ejecutar todas las pruebas
python run_tests.py all

# Solo pruebas básicas
python run_tests.py basic

# Solo casos edge
python run_tests.py edge

# Pruebas de integración de permisos
uv run pytest tests/test_permisos_integration.py -v

# Pruebas de rendimiento de permisos  
uv run pytest tests/test_permisos_performance.py -v

# Con cobertura de código
python run_tests.py coverage
```

### **📖 Documentación Completa de Pruebas:**
Para información detallada sobre las pruebas, tipos de tests, configuración y ejemplos, consulta:
- **[README_PYTEST.md](README_PYTEST.md)** - Pruebas generales del sistema
- **[README_PERMISOS_TESTS.md](README_PERMISOS_TESTS.md)** - Suite de pruebas de permisos ERPNext

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

### **5. Lógica de Retardos**
- **Tolerancia**: 15 minutos después de la hora programada
- **Clasificación**: A Tiempo → Retardo → Falta Injustificada
- **Acumulación**: 3 retardos = 1 día de descuento

## 📈 **Métricas del Sistema**

### **Rendimiento:**
- **Procesamiento**: ~1000 registros/segundo
- **Memoria**: Optimizado con caché inteligente
- **Base de datos**: Consultas optimizadas con índices

### **Precisión:**
- **Cobertura de pruebas**: 98%
- **Casos edge**: 34 pruebas específicas
- **Integración permisos**: 28 pruebas completas
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

### **4. Integración de Permisos**
El sistema automáticamente:
- Consulta permisos aprobados para el período
- Ajusta horas esperadas según días con permiso  
- Justifica faltas que coinciden con permisos válidos
- Incluye estadísticas de permisos en el resumen final
### **5. Turnos Nocturnos**
El sistema maneja automáticamente:
- Entrada: 22:00 (día actual)
- Salida: 06:00 (día siguiente)
- Cálculo correcto de horas trabajadas

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
python run_tests.py summary

# Ejecutar con debug
uv run python -m pytest tests/ -v -s
```

## 📝 **Notas Importantes**

- **Determinación automática**: El sistema detecta primera o segunda quincena
- **Filtros de dispositivo**: Usar `%sucursal%` para filtrar por ubicación
- **Formato de fechas**: YYYY-MM-DD (ISO 8601)
- **Zona horaria**: Todas las fechas en zona horaria local

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

**Versión:** 3.0 (PostgreSQL + Pytest + Permisos ERPNext)  
**Última actualización:** Julio 2025  
**Estado:** Completamente funcional con 93 pruebas pasando ✅
