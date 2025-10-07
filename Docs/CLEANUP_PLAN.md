# 🧹 Plan de Limpieza de Imports y Referencias
## Phase 1 Task 1.10: Orphaned Imports and References Cleanup

**Fecha**: 2025-10-06
**Estado**: Plan de limpieza completado, ejecución requerida

---

## 🎯 Resumen Ejecutivo

**ANÁLISIS COMPLETADO**: Se han identificado todos los archivos que requieren actualización para eliminar referencias al sistema legacy eliminado.

**PRIORIDAD**: MEDIA - Las referencias son principalmente de testing y documentación, no afectan la funcionalidad del sistema en producción.

---

## 📋 Archivos que Requieren Actualización

### 🔧 **Archivos de Testing (13 archivos)**

| Archivo | Tipo de Import | Acción Requerida | Prioridad |
|---------|---------------|------------------|-----------|
| **tests/test_generar_reporte_optimizado.py** | 15+ funciones | Migrar a tests modulares existentes | ALTA |
| **tests/test_perdon_retardos.py** | `aplicar_regla_perdon_retardos` | Actualizar a `AttendanceProcessor` | MEDIA |
| **tests/test_umbral_falta_injustificada.py** | `analizar_asistencia_con_horarios_cache` | Actualizar a `AttendanceProcessor` | MEDIA |
| **tests/test_resumen_periodo.py** | `generar_resumen_periodo` | Actualizar a `ReportGenerator` | MEDIA |
| **tests/test_horas_descanso.py** | `calcular_horas_descanso`, `aplicar_calculo_horas_descanso`, `td_to_str` | Actualizar a `AttendanceProcessor` y `utils` | MEDIA |
| **tests/test_normalizacion_permisos.py** | `normalize_leave_type`, `POLITICA_PERMISOS` | Actualizar a `utils` y `config` | BAJA |
| **tests/test_deteccion_salidas_anticipadas.py** | `TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS`, `analizar_asistencia_con_horarios_cache` | Actualizar a `config` y `AttendanceProcessor` | MEDIA |
| **tests/test_permisos_integration.py** | 4+ funciones API | Actualizar a `api_client` | MEDIA |
| **tests/test_permisos_performance.py** | 3+ funciones | Actualizar a `api_client` y `AttendanceProcessor` | BAJA |
| **tests/test_permisos_sin_goce.py** | 3+ funciones de permisos | Actualizar a `api_client` y `config` | BAJA |
| **tests/test_casos_edge.py** | 5+ funciones | Distribuir entre módulos correspondientes | BAJA |
| **tests/test_quincenas.py** | `datetime`, `timedelta` (imports básicos) | Cambiar a imports estándar de Python | BAJA |
| **tests/test_permisos_integration.py** | Varios imports de API | Actualizar a `api_client` | MEDIA |

### 🔧 **Archivos de Configuración (2 archivos)**

| Archivo | Referencia | Acción Requerida | Prioridad |
|---------|------------|------------------|-----------|
| **run_tests.py** | `test_generar_reporte_optimizado.py`, coverage legacy | Eliminar referencias a legacy tests y coverage | MEDIA |
| **tests/run_tests.py** | Múltiples referencias a legacy | Actualizar a tests modulares | MEDIA |

### 📚 **Archivos de Documentación (20+ archivos)**

| Archivo | Referencias | Acción Requerida | Prioridad |
|---------|-------------|------------------|-----------|
| **Readme.md** | 8 referencias | Actualizar ejemplos y comandos | BAJA |
| **CRUSH.md** | 6 referencias | Actualizar comandos y ejemplos | BAJA |
| **CLAUDE.md** | 5 referencias | Actualizar documentación | BAJA |
| **pytest.ini** | Coverage legacy | Eliminar comentario de coverage | BAJA |
| **Docs/*.md** | 50+ referencias | Actualizar documentación técnica | BAJA |

---

## 🔄 Patrón de Migración de Tests

### ✅ **Mapeo de Imports Legacy → Modular**

```python
# Legacy imports (eliminar)
from generar_reporte_optimizado import aplicar_regla_perdon_retardos
from generar_reporte_optimizado import generar_resumen_periodo
from generar_reporte_optimizado import analizar_asistencia_con_horarios_cache
from generar_reporte_optimizado import calcular_horas_descanso
from generar_reporte_optimizado import normalize_leave_type
from generar_reporte_optimizado import POLITICA_PERMISOS
from generar_reporte_optimizado import TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS

# Modular imports (usar)
from data_processor import AttendanceProcessor
from report_generator import ReportGenerator
from api_client import APIClient
from utils import normalize_leave_type, td_to_str
from config import POLITICA_PERMISOS, TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS
```

### ✅ **Mapeo de Llamadas a Funciones**

```python
# Legacy function calls (actualizar)
df_resultado = aplicar_regla_perdon_retardos(df)
resumen = generar_resumen_periodo(df_detalle)
df_analizado = analizar_asistencia_con_horarios_cache(df, cache)
horas_descanso = calcular_horas_descanso(df_dia)

# Modular method calls (usar)
processor = AttendanceProcessor()
df_resultado = processor.aplicar_regla_perdon_retardos(df)

report_gen = ReportGenerator()
resumen = report_gen.generar_resumen_periodo(df_detalle)

df_analizado = processor.analizar_asistencia_con_horarios_cache(df, cache)
horas_descanso = processor.calcular_horas_descanso(df_dia)
```

---

## 📋 Plan de Ejecución

### 🚀 **Fase 1: Tests Críticos (Alta Prioridad)**

1. **tests/test_generar_reporte_optimizado.py**
   - **Acción**: Evaluar si este test es aún necesario
   - **Alternativa**: Ya existe cobertura equivalente en tests modulares
   - **Decisión**: Posible eliminación si es redundante

2. **tests/test_perdon_retardos.py**
   - **Acción**: Actualizar import y llamadas a métodos
   - **Ejemplo**: `aplicar_regla_perdon_retardos(df)` → `AttendanceProcessor().aplicar_regla_perdon_retardos(df)`

3. **tests/test_umbral_falta_injustificada.py**
   - **Acción**: Actualizar a uso de `AttendanceProcessor`
   - **Ejemplo**: `analizar_asistencia_con_horarios_cache()` → `AttendanceProcessor().analizar_asistencia_con_horarios_cache()`

### 🔧 **Fase 2: Tests de Soporte (Media Prioridad)**

4. **tests/test_resumen_periodo.py**
   - **Acción**: Actualizar a uso de `ReportGenerator`
   - **Ejemplo**: `generar_resumen_periodo(df)` → `ReportGenerator().generar_resumen_periodo(df)`

5. **tests/test_horas_descanso.py**
   - **Acción**: Actualizar imports mixtos
   - **Ejemplo**: Usar `AttendanceProcessor` y `utils`

6. **tests/test_deteccion_salidas_anticipadas.py**
   - **Acción**: Actualizar imports de constantes y funciones
   - **Ejemplo**: `config.TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS`

### 📚 **Fase 3: Documentación (Baja Prioridad)**

7. **Actualización de documentación**
   - **Readme.md**: Actualizar ejemplos de uso
   - **CRUSH.md**: Actualizar comandos
   - **CLAUDE.md**: Actualizar referencias técnicas

8. **Configuración de testing**
   - **run_tests.py**: Eliminar referencias legacy
   - **pytest.ini**: Limpiar configuración

---

## 🎯 Script de Migración Automatizado

### 🔧 **Comandos de Busqueda y Reemplazo**

```bash
# Actualizar imports principales
find tests/ -name "*.py" -exec sed -i 's/from generar_reporte_optimizado import aplicar_regla_perdon_retardos/from data_processor import AttendanceProcessor/g' {} \;
find tests/ -name "*.py" -exec sed -i 's/from generar_reporte_optimizado import generar_resumen_periodo/from report_generator import ReportGenerator/g' {} \;

# Actualizar llamadas a funciones
find tests/ -name "*.py" -exec sed -i 's/aplicar_regla_perdon_retardos(df/AttendanceProcessor().aplicar_regla_perdon_retardos(df/g' {} \;
find tests/ -name "*.py" -exec sed -i 's/generar_resumen_periodo(df_detalle/ReportGenerator().generar_resumen_periodo(df_detalle/g' {} \;

# Actualizar imports de utils
find tests/ -name "*.py" -exec sed -i 's/from generar_reporte_optimizado import normalize_leave_type/from utils import normalize_leave_type/g' {} \;
find tests/ -name "*.py" -exec sed -i 's/from generar_reporte_optimizado import td_to_str/from utils import td_to_str/g' {} \;

# Actualizar imports de config
find tests/ -name "*.py" -exec sed -i 's/from generar_reporte_optimizado import POLITICA_PERMISOS/from config import POLITICA_PERMISOS/g' {} \;
find tests/ -name "*.py" -exec sed -i 's/from generar_reporte_optimizado import TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS/from config import TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS/g' {} \;
```

---

## 🚀 Impacto de la Limpieza

### ✅ **Beneficios Esperados**

1. **Consistencia**: Todos los tests usarán sistema modular
2. **Maintainability**: Un solo sistema de referencia
3. **Claridad**: Eliminación de código legacy en tests
4. **Coverage**: Mejor cobertura del sistema modular
5. **Documentation**: Actualizada y consistente

### ⚠️ **Riesgos Mitigados**

1. **Tests rotos**: Validar cada actualización
2. **Coverage reducido**: Verificar que la cobertura se mantenga
3. **Documentación desactualizada**: Actualizar referencias cuidadosamente

---

## 📊 Métricas de Progreso

| Categoría | Archivos Totales | Por Actualizar | Completado | Restante |
|-----------|------------------|----------------|------------|----------|
| **Tests** | 13 | 13 | 1 (ejemplo) | 12 |
| **Configuración** | 2 | 2 | 0 | 2 |
| **Documentación** | 20+ | 20+ | 0 | 20+ |
| **TOTAL** | 35+ | 35+ | 1 | 34+ |

---

## 🎯 Recomendación Final

**EJECUTAR LIMPIEZA PLANIFICADA**: Aunque el sistema funciona correctamente sin estas actualizaciones (solo afectan tests y documentación), se recomienda completar la limpieza para maintainability a largo plazo.

**Prioridad**: MEDIA - No bloquea el funcionamiento del sistema, pero es importante para la salud del codebase.

---

## 📋 Checklist de Limpieza

### 🔄 **Tests (12 archivos restantes)**
- [ ] tests/test_generar_reporte_optimizado.py
- [ ] tests/test_umbral_falta_injustificada.py
- [ ] tests/test_resumen_periodo.py
- [ ] tests/test_horas_descanso.py
- [ ] tests/test_normalizacion_permisos.py
- [ ] tests/test_deteccion_salidas_anticipadas.py
- [ ] tests/test_permisos_integration.py
- [ ] tests/test_permisos_performance.py
- [ ] tests/test_permisos_sin_goce.py
- [ ] tests/test_casos_edge.py
- [ ] tests/test_quincenas.py
- [ ] tests/test_permisos_integration.py (segunda referencia)

### 🔧 **Configuración (2 archivos)**
- [ ] run_tests.py
- [ ] tests/run_tests.py

### 📚 **Documentación (20+ archivos)**
- [ ] Readme.md
- [ ] CRUSH.md
- [ ] CLAUDE.md
- [ ] pytest.ini
- [ ] Docs/*.md (varios archivos)

---

**Archivo**: `/home/felipillo/proyectos/asistencias_2/Docs/CLEANUP_PLAN.md`
**Creado por**: Claude Code Assistant
**Status**: ✅ PLAN COMPLETADO
**Resultado**: **LISTO PARA EJECUCIÓN** - Todos los cambios identificados y documentados