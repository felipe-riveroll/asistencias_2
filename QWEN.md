# Sistema de Reportes de Asistencia - Contexto para Qwen Code

## Descripción General del Proyecto

Este es un sistema completo de reportes de asistencia para empleados que integra datos de marcaciones de entrada/salida con horarios programados desde una base de datos PostgreSQL. El sistema está implementado en Python con una arquitectura modular moderna.

## Tecnologías Principales

- **Lenguaje**: Python 3.8+
- **Base de Datos**: PostgreSQL 12+
- **APIs Externas**: ERPNext/Frappe API
- **Librerías Principales**: pandas, numpy, requests, psycopg2, openpyxl
- **Testing**: pytest

## Arquitectura Modular

El sistema ha sido refactorizado completamente en una arquitectura modular con 6 módulos especializados:

1. **`main.py`** - Orquestación principal del sistema
2. **`config.py`** - Configuración centralizada y constantes
3. **`utils.py`** - Funciones de utilidad compartidas
4. **`api_client.py`** - Cliente para APIs externas
5. **`data_processor.py`** - Procesamiento de datos de asistencia
6. **`report_generator.py`** - Generación de reportes CSV, HTML y Excel

## Funcionalidades Clave

### Procesamiento de Datos
- Análisis automático de checadas comparándolas con horarios programados
- Gestión de retardos con clasificación (A Tiempo, Retardo, Falta)
- Detección de salidas anticipadas antes del horario programado
- Regla de perdón de retardos cuando se cumplen las horas del turno
- Manejo de turnos nocturnos que cruzan medianoche
- Cálculo automático de horas de descanso basado en múltiples checadas

### Integración de Permisos
- Conexión automática con ERPNext para obtener permisos aprobados
- Reclasificación automática de faltas como justificadas cuando coinciden con permisos
- Manejo de permisos de medio día (0.5 días) con cálculo proporcional de horas
- Fechas de contratación para evitar falsas faltas en empleados nuevos

### Reportes
- **CSV Detallado**: Análisis completo por empleado y día
- **CSV Resumen**: Métricas agregadas por período
- **HTML Dashboard**: Interfaz interactiva con DataTables y gráficos D3.js
- **Excel**: Reporte avanzado con múltiples hojas y KPIs

### Optimizaciones
- Sistema de caché inteligente para optimizar consultas a base de datos
- Pruebas unitarias con más de 200 tests automatizados
- Cálculos corregidos del resumen del período usando horas netas (después de descanso)

## Configuración del Sistema

### Variables de Entorno (.env)
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

### Dependencias Python
```bash
pandas>=1.5.0
numpy>=1.21.0
requests>=2.28.0
python-dotenv>=0.19.0
psycopg2-binary>=2.9.0
pytz>=2022.1
pytest>=7.0.0
openpyxl>=3.1.5
```

## Ejecución del Sistema

### Ejecución Principal
```bash
# Ejecutar análisis completo con la nueva arquitectura modular
python main.py
```

### Parámetros de Configuración (en main.py)
```python
# Date range for the report
start_date = "2025-07-01"      # Fecha inicio del análisis
end_date = "2025-07-31"        # Fecha fin del análisis
sucursal = "31pte"             # Sucursal a analizar
device_filter = "%31%"         # Filtro de dispositivos para BD
```

### Archivos Generados
- `reporte_asistencia_analizado.csv` - Reporte detallado diario por empleado
- `resumen_periodo.csv` - Resumen agregado con KPIs del período  
- `dashboard_asistencia.html` - Dashboard interactivo con gráficos
- `reporte_asistencia_[sucursal]_[fecha].xlsx` - Reporte Excel con múltiples hojas

## Testing

### Ejecutar Pruebas
```bash
# Ejecutar todas las pruebas
pytest

# Con cobertura de código
pytest --cov=. --cov-report=term-missing

# Pruebas específicas
pytest tests/test_perdon_retardos.py -v
```

### Suite de Pruebas
- Más de 200 pruebas unitarias automatizadas
- Cobertura del 68% del código principal
- Pruebas de casos límite, integración con ERPNext, rendimiento
- Validación de turnos nocturnos, permisos, reglas de negocio

## Convenciones de Desarrollo

### Estructura del Código
- Separación clara de responsabilidades por módulo
- Nombres de funciones y variables en español para consistencia
- Documentación en docstrings para todas las funciones públicas
- Manejo de errores con mensajes amigables en español

### Estilo de Código
- Seguir convenciones PEP 8 para Python
- Uso de type hints para mejorar la legibilidad
- Comentarios en español para funciones complejas
- Mensajes de consola con emojis para mejor experiencia de usuario

### Contribución
1. Crear pruebas unitarias primero
2. Implementar funcionalidad
3. Ejecutar todas las pruebas
4. Actualizar documentación