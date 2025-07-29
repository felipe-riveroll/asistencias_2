# Funcionalidad: Permisos Sin Goce de Sueldo

## Resumen

Esta funcionalidad implementa un manejo diferenciado de permisos según su tipo, específicamente excluyendo los "Permisos Sin Goce de Sueldo" del descuento de horas esperadas, mientras mantiene trazabilidad completa y captura permisos que traslapan el periodo de análisis.

## Cambios Implementados

### 1. Captura de Permisos con Traslape

**Ubicación:** `fetch_leave_applications()`

**Cambio:** Modificado el filtro de la API para capturar permisos que traslapan el periodo:
- **Antes:** `from_date Between [start_date, end_date]`
- **Ahora:** `from_date <= end_date AND to_date >= start_date`

**Beneficio:** Captura permisos que:
- Empiecen antes del periodo pero terminen dentro
- Empiecen dentro del periodo pero terminen después  
- Estén completamente contenidos en el periodo

### 2. Normalización y Política por Tipo

**Nuevas constantes:**
```python
POLITICA_PERMISOS = {
    "permiso sin goce de sueldo": "no_ajustar",
    # Preparado para futuras políticas como "ajustar_a_cero", "prorratear"
}

def normalize_leave_type(leave_type):
    """Normaliza tipos de permiso para comparación consistente."""
    return leave_type.strip().casefold()
```

**Ubicación:** `procesar_permisos_empleados()`

**Cambio:** Cada permiso ahora incluye `leave_type_normalized` además del `leave_type` original.

### 3. Ajuste Diferenciado de Horas Esperadas

**Ubicación:** `ajustar_horas_esperadas_con_permisos()`

**Nueva lógica:**
- **Nueva columna:** `es_permiso_sin_goce` para trazabilidad
- **Permiso sin goce:** NO modifica `horas_esperadas`, NO suma a `horas_descontadas_permiso`
- **Permiso normal:** Mantiene comportamiento actual (horas_esperadas = '00:00:00')

**Output mejorado:**
```
✅ Ajuste completado:
   - X empleados con permisos
   - Y días con permisos  
   - Z permisos con horas descontadas
   - W permisos sin goce (sin descuento)
```

### 4. Estadísticas Enriquecidas en Resumen

**Ubicación:** `generar_resumen_periodo()`

**Nuevas estadísticas:**
```
📋 Estadísticas de permisos:
   - Empleados con permisos: X
   - Total faltas justificadas: Y
   - Total horas descontadas por permisos: Z.ZZ
   - Empleados con permisos sin goce: W
   - Total días con permisos sin goce: V
```

### 5. Soporte Preparatorio para Medio Día

**Cambio:** Añadidos campos `half_day` y `half_day_date` en `fetch_leave_applications()`

**Estado:** Campos capturados pero lógica de prorrateo pendiente (documentada con TODO)

## Trazabilidad y Auditoría

### Columnas Nuevas en DataFrame Detallado:
- `es_permiso_sin_goce`: Boolean indicando si es permiso sin descuento
- `horas_esperadas_originales`: Respaldo de horas antes de ajuste por permisos
- `tiene_permiso`: Boolean indicando presencia de permiso
- `tipo_permiso`: Tipo original del permiso
- `horas_descontadas_permiso`: Horas que se descontaron por permisos

### Logging Diferenciado:
```
   - Juan Pérez (EMP001): 2025-07-15 - Permiso Sin Goce De Sueldo - SIN DESCUENTO (permiso sin goce)
   - María García (EMP002): 2025-07-16 - Permiso Médico - Horas descontadas: 08:00:00
```

## Impacto en KPIs

- **Horas Esperadas:** Usan `horas_esperadas_originales` como base
- **Horas Ajustadas:** Restan solo `total_horas_descontadas_permiso` (excluye sin goce)
- **Cálculo de Diferencia:** `horas_trabajadas - (horas_esperadas - horas_descontadas_permiso)`

## Testing

**Ubicación:** `tests/test_permisos_sin_goce.py`

**Cobertura:**
1. ✅ **Caso 1:** Permiso sin goce → NO descuenta horas
2. ✅ **Caso 2:** Permiso normal → SÍ descuenta horas  
3. ✅ **Caso 3:** Traslape de permisos → Se capturan correctamente
4. ⏳ **Caso 4:** Medio día (marcado como `xfail` hasta implementación)

**Ejecución:**
```bash
uv run pytest tests/test_permisos_sin_goce.py -v
# Resultado: 9 passed, 1 xfailed
```

## Plan de Rollback

**En caso de problemas:**

1. **Inmediato:** Revertir a comportamiento anterior
   ```bash
   git revert <commit-hash>
   ```

2. **Datos afectados:** Solo campos nuevos, sin pérdida de información existente

3. **Compatibilidad:** Mantiene toda la funcionalidad previa intacta

## Riesgos Identificados

1. **Bajo:** Cambio en cálculo de KPIs (esperado y documentado)
2. **Bajo:** Campos adicionales en API podrían no existir en algunas instalaciones de Frappe
3. **Medio:** Normalización de tipos de permiso depende de nomenclatura consistente

## Próximos Pasos

1. ✅ Implementación base completada
2. ⏳ Soporte para medios días (TODO documentado)
3. ⏳ Extensión de políticas para otros tipos de permisos
4. ⏳ Configuración dinámica de políticas vía archivo de configuración
