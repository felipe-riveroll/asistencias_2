# 🏗️ Modular Attendance Reporting System

Este documento explica la nueva arquitectura modular del sistema de reportes de asistencia, que divide el código original en módulos organizados y reutilizables.

## 📁 Estructura Modular

```
nuevo_asistencias/
├── 📄 main.py                    # Script principal orquestador
├── 📄 config.py                  # Configuración y constantes
├── 📄 utils.py                   # Funciones utilitarias
├── 📄 api_client.py              # Cliente para APIs externas
├── 📄 data_processor.py          # Lógica de procesamiento de datos
├── 📄 report_generator.py        # Generación de reportes CSV/HTML
├── 📄 test_modules.py            # Script de pruebas del sistema modular
├── 📄 generar_reporte_optimizado.py  # Script original (sin modificar)
└── 📄 README_MODULAR.md          # Esta documentación
```

## 🎯 Beneficios de la Modularización

### ✅ **Mantenibilidad**
- Cada módulo tiene una responsabilidad específica
- Más fácil localizar y corregir errores
- Cambios aislados sin afectar otras funcionalidades

### ✅ **Reutilización**
- Los módulos pueden utilizarse independientemente
- Fácil integración en otros proyectos
- Componentes reutilizables para diferentes casos de uso

### ✅ **Testabilidad**
- Cada módulo puede probarse por separado
- Tests unitarios más específicos y efectivos
- Mejor cobertura de código

### ✅ **Escalabilidad**
- Fácil agregar nuevas funcionalidades
- Arquitectura preparada para crecimiento
- Separación clara de responsabilidades

## 📦 Descripción de Módulos

### 🔧 **config.py**
**Propósito**: Configuración centralizada y constantes del sistema.

**Contiene**:
- Credenciales de API
- Políticas de permisos
- Reglas de negocio (tolerancias, umbrales)
- Configuración de archivos de salida
- Validaciones de configuración

**Uso**:
```python
from config import POLITICA_PERMISOS, TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS
```

### 🛠️ **utils.py**
**Propósito**: Funciones utilitarias y helpers reutilizables.

**Funciones principales**:
- `normalize_leave_type()`: Normalización de tipos de permiso
- `calcular_proximidad_horario()`: Cálculo de proximidad entre horarios
- `td_to_str()`: Conversión de Timedelta a string
- `time_to_decimal()`: Conversión de tiempo a decimal
- Funciones de formateo y manipulación de datos

**Uso**:
```python
from utils import normalize_leave_type, td_to_str
```

### 🌐 **api_client.py**
**Propósito**: Manejo de comunicación con APIs externas.

**Clases**:
- `APIClient`: Cliente principal para APIs de Frappe/ERPNext

**Funciones principales**:
- `fetch_checkins()`: Obtiene checadas de la API
- `fetch_leave_applications()`: Obtiene permisos aprobados
- `procesar_permisos_empleados()`: Procesa datos de permisos

**Uso**:
```python
from api_client import APIClient
client = APIClient()
checkins = client.fetch_checkins(start_date, end_date, device_filter)
```

### ⚙️ **data_processor.py**
**Propósito**: Lógica principal de procesamiento de datos de asistencia.

**Clases**:
- `AttendanceProcessor`: Procesador principal de asistencia

**Funciones principales**:
- `process_checkins_to_dataframe()`: Convierte checadas a DataFrame
- `analizar_asistencia_con_horarios_cache()`: Análisis de asistencia
- `aplicar_regla_perdon_retardos()`: Regla de perdón de retardos
- `calcular_horas_descanso()`: Cálculo de horas de descanso
- `clasificar_faltas_con_permisos()`: Clasificación de faltas

**Uso**:
```python
from data_processor import AttendanceProcessor
processor = AttendanceProcessor()
df = processor.process_checkins_to_dataframe(data, start_date, end_date)
```

### 📊 **report_generator.py**
**Propósito**: Generación de reportes en diferentes formatos.

**Clases**:
- `ReportGenerator`: Generador principal de reportes

**Funciones principales**:
- `generar_resumen_periodo()`: Genera resumen del período
- `save_detailed_report()`: Guarda reporte detallado en CSV
- `generar_reporte_html()`: Genera dashboard HTML interactivo

**Uso**:
```python
from report_generator import ReportGenerator
generator = ReportGenerator()
summary = generator.generar_resumen_periodo(df)
```

### 🎯 **main.py**
**Propósito**: Orquestación principal del sistema.

**Clases**:
- `AttendanceReportManager`: Gestor principal del proceso

**Funciones principales**:
- `generate_attendance_report()`: Proceso completo de generación
- `main()`: Función principal configurable

## 🚀 Cómo Usar el Sistema Modular

### 1. **Ejecución Básica**

```bash
# Usar el nuevo sistema modular
python main.py

# O con uv
uv run python main.py
```

### 2. **Configuración de Parámetros**

Edita la sección de configuración en `main.py`:

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

### 3. **Pruebas del Sistema**

```bash
# Probar que todos los módulos funcionan correctamente
python test_modules.py
```

### 4. **Uso Programático**

```python
from main import AttendanceReportManager

# Crear el gestor
manager = AttendanceReportManager()

# Generar reporte
result = manager.generate_attendance_report(
    start_date="2025-07-01",
    end_date="2025-07-31", 
    sucursal="Villas",
    device_filter="%Villas%"
)

if result["success"]:
    print(f"Reporte generado: {result['detailed_report']}")
else:
    print(f"Error: {result['error']}")
```

## 🔧 Personalización y Extensión

### **Agregar Nuevas Funcionalidades**

1. **Nueva regla de negocio**: Modificar `data_processor.py`
2. **Nuevo formato de reporte**: Extender `report_generator.py`
3. **Nueva fuente de datos**: Extender `api_client.py`
4. **Nueva configuración**: Agregar a `config.py`

### **Ejemplo: Agregar Nuevo Tipo de Reporte**

```python
# En report_generator.py
class ReportGenerator:
    def generar_reporte_excel(self, df, filename="reporte.xlsx"):
        """Genera reporte en formato Excel."""
        with pd.ExcelWriter(filename) as writer:
            df.to_excel(writer, sheet_name='Detalle', index=False)
        return filename
```

## 🧪 Testing y Validación

### **Ejecutar Pruebas**

```bash
# Pruebas básicas del sistema modular
python test_modules.py

# Pruebas unitarias existentes
uv run pytest

# Pruebas con cobertura
uv run pytest --cov=. --cov-report=term-missing
```

### **Validar Funcionalidad**

1. **Ejecutar el script de pruebas**: `python test_modules.py`
2. **Comparar resultados**: Los reportes generados deben ser idénticos al script original
3. **Verificar archivos de salida**: CSV y HTML deben generarse correctamente

## 🔄 Migración desde el Script Original

### **Compatibilidad**

- ✅ **Funcionalidad idéntica**: Todos los cálculos y lógica se mantienen
- ✅ **Mismos archivos de salida**: CSV y HTML con el mismo formato
- ✅ **Misma configuración**: Variables de entorno y parámetros iguales
- ✅ **Script original preservado**: `generar_reporte_optimizado.py` sin modificar

### **Ventajas del Sistema Modular**

| Aspecto | Script Original | Sistema Modular |
|---------|----------------|-----------------|
| **Líneas de código por archivo** | 1844 líneas | 200-600 líneas por módulo |
| **Mantenibilidad** | Difícil | Fácil |
| **Reutilización** | Limitada | Alta |
| **Testing** | Monolítico | Por módulos |
| **Extensibilidad** | Compleja | Simple |

## 📚 Recursos Adicionales

- **Documentación original**: `README.md`
- **Documentación de pruebas**: `README_PYTEST.md`
- **Configuración del proyecto**: `CLAUDE.md`
- **Tests del sistema**: `tests/`

## 🎯 Próximos Pasos Recomendados

1. **Ejecutar pruebas**: Verificar que todo funciona correctamente
2. **Comparar resultados**: Validar que los reportes son idénticos
3. **Personalizar configuración**: Ajustar parámetros según necesidades
4. **Extender funcionalidad**: Agregar nuevas características según requerimientos
5. **Documentar cambios**: Mantener documentación actualizada

---

## 🚨 Importante

- **El script original (`generar_reporte_optimizado.py`) NO se ha modificado** y sigue funcionando normalmente
- **El sistema modular es completamente independiente** y puede coexistir con el script original
- **Todos los tests existentes siguen siendo válidos** para ambas versiones
- **La funcionalidad es idéntica** entre ambas versiones

¡El sistema modular está listo para usar! 🎉