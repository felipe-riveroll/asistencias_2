# Integración de Permisos ERPNext - Documentación

## 🎯 Resumen de la Implementación

Se ha integrado exitosamente la funcionalidad de permisos aprobados desde ERPNext al sistema de reportes de asistencia. Esta integración permite un cálculo más preciso de horas esperadas y una clasificación más justa de las faltas.

## 🔧 Nuevas Funcionalidades

### 1. Obtención Automática de Permisos
- **Fuente**: API ERPNext (`/api/resource/Leave Application`)
- **Filtros**: Solo permisos con status "Approved" en el período de análisis
- **Campos obtenidos**: employee, employee_name, leave_type, from_date, to_date, status

### 2. Ajuste de Horas Esperadas
- Las horas esperadas se reducen automáticamente para días con permiso aprobado
- Se mantiene un registro de las horas originales vs. las horas ajustadas
- Calculo preciso considerando solo días laborables

### 3. Reclasificación de Faltas
- Las faltas en días con permiso aprobado se reclasifican como "Falta Justificada"
- El conteo de faltas totales excluye las faltas justificadas
- Se mantiene un registro separado de faltas justificadas

## 📊 Nuevas Columnas en los Reportes

### Reporte Detallado (`reporte_asistencia_analizado.csv`)
| Columna | Descripción |
|---------|-------------|
| `tiene_permiso` | Booleano que indica si hay permiso aprobado para esa fecha |
| `tipo_permiso` | Tipo específico del permiso (vacaciones, incapacidad, etc.) |
| `falta_justificada` | Booleano que indica si la falta fue justificada por permiso |
| `tipo_falta_ajustada` | Clasificación de falta actualizada considerando permisos |
| `horas_esperadas_originales` | Horas originales antes del ajuste por permisos |
| `horas_descontadas_permiso` | Horas descontadas específicamente por permiso |

### Reporte Resumen (`resumen_periodo.csv`)
| Columna | Descripción |
|---------|-------------|
| `total_horas_descontadas_permiso` | Total de horas descontadas por permisos en el período |
| `total_faltas_justificadas` | Total de faltas justificadas por permisos |

## 🔄 Proceso de Integración

### Paso 2.5: Obtención de Permisos
```
📄 Obteniendo permisos aprobados de la API para el periodo [start_date] - [end_date]...
✅ Se obtuvieron X permisos aprobados de la API.
🔄 Procesando permisos por empleado y fecha...
✅ Procesados permisos para X empleados, Y días con permiso total.
```

### Paso 8: Ajuste de Horas Esperadas
```
🏖️ Ajustando horas esperadas con permisos aprobados...
📊 Ajustando horas esperadas considerando permisos aprobados...
✅ Ajuste completado: X empleados con permisos, Y días ajustados.
```

### Paso 9: Reclasificación de Faltas
```
📋 Reclasificando faltas con permisos...
📋 Reclasificando faltas considerando permisos aprobados...
✅ Se justificaron X faltas con permisos aprobados.
```

## 📈 Estadísticas de Permisos

Al final del proceso, se muestran estadísticas consolidadas:
- Empleados con permisos en el período
- Total de faltas justificadas
- Total de horas descontadas por permisos

## 🛠️ Funciones Principales Añadidas

### `fetch_leave_applications(start_date, end_date)`
Obtiene permisos aprobados de la API ERPNext para un rango de fechas.

### `procesar_permisos_empleados(leave_data)`
Procesa los datos de permisos y crea un diccionario organizado por empleado y fecha.

### `ajustar_horas_esperadas_con_permisos(df, permisos_dict, cache_horarios)`
Ajusta las horas esperadas del DataFrame considerando los permisos aprobados.

### `clasificar_faltas_con_permisos(df)`
Actualiza la clasificación de faltas considerando los permisos aprobados.

## 🔄 Manejo de Errores

- **Timeout de API**: Reintento automático
- **Respuestas vacías**: Manejo graceful sin interrupción del proceso
- **Archivos en uso**: Generación automática de nombres alternativos con timestamp
- **Empleados sin permisos**: Procesamiento normal sin afectación

## 📝 Tipos de Permisos Soportados

El sistema procesa todos los tipos de permisos aprobados en ERPNext, incluyendo:
- Vacaciones
- Incapacidades por enfermedad
- Permisos ocasionales
- Permisos por eventos familiares
- Salidas por trabajo
- Compensación de tiempo
- Permisos sin goce de sueldo
- Días de cumpleaños

## 🧪 Casos de Prueba Validados

1. ✅ Empleado con permiso de un día
2. ✅ Empleado con permiso de múltiples días consecutivos
3. ✅ Empleado sin permisos en el período
4. ✅ Permisos que abarcan fines de semana
5. ✅ Múltiples permisos del mismo empleado en el período
6. ✅ Manejo de errores de conexión a API
7. ✅ Respuesta vacía de la API

## 📅 Ejemplo de Uso

Para el período del 16 al 23 de julio de 2025:
- **19 permisos** procesados para 15 empleados
- **47 días** con permiso en total
- **6 empleados** con ajustes en horas esperadas
- **56 horas** descontadas por permisos
- **6 faltas** justificadas

## 🔗 Integración con el Flujo Existente

La integración de permisos se añadió sin afectar el flujo existente:
- Los pasos 1-7 permanecen inalterados
- Se añadieron los pasos 8-9 para procesamiento de permisos
- Los pasos finales se renumeraron a 10-11
- Compatibilidad total con reportes existentes
