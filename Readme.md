# Sistema de Gestión de Asistencias

Este proyecto es un sistema de gestión de asistencias que integra datos de marcaciones de empleados con horarios programados para generar reportes de asistencia, retardos y horas trabajadas.

## Requisitos

- Python 3.8+
- Base de datos MariaDB/MySQL
- Acceso a la API de registros de asistencia
- Archivo `.env` con las siguientes variables configuradas:
  - `DB_HOST`: Host de la base de datos
  - `DB_PORT`: Puerto de la base de datos (por defecto: 3306)
  - `DB_NAME`: Nombre de la base de datos
  - `DB_USER`: Usuario de la base de datos
  - `DB_PASSWORD`: Contraseña de la base de datos
  - `ASIATECH_API_KEY`: Clave de API para acceder a los datos de asistencia
  - `ASIATECH_API_SECRET`: Secreto de API para acceder a los datos de asistencia

## Estructura del Proyecto

### `conexión_bd.py`

Este archivo proporciona funcionalidades para conectarse a la base de datos MariaDB y realizar consultas relacionadas con los horarios de los empleados.

**Funciones principales:**
- `connect_db()`: Establece y retorna una conexión a la base de datos utilizando las credenciales del archivo `.env`.
- `query_horario_programado(codigo_frappe, fecha)`: Consulta el horario programado para un empleado en una fecha específica, aplicando lógica de prioridad para determinar el horario aplicable. Retorna un diccionario con información del horario o `None` si no hay asignación.

### `db_connection.py`

Archivo con funciones para probar la conexión a la base de datos.

**Funciones principales:**
- `test_db_connection()`: Verifica la conexión a la base de datos y muestra información del servidor. Útil para diagnósticos.

### `llamada_api.py`

Este módulo se encarga de la comunicación con la API de registros de asistencia para obtener los datos de marcaciones de los empleados.

**Funciones principales:**
- `fetch_checkins(start_date, end_date, device_filter)`: Obtiene registros de marcaciones entre dos fechas, con filtro por dispositivo.
- Procesamiento de datos de la API y transformación a formatos útiles para el análisis.

### `generar_reporte_avanzado.py`

Es el módulo principal que integra todos los componentes para generar reportes detallados de asistencia.

**Secciones y funciones principales:**
1. **Configuración y Conexión**: Inicialización de conexiones a bases de datos.
2. **Procesamiento de Datos**:
   - `process_checkins_to_dataframe()`: Convierte los datos de marcaciones en un DataFrame estructurado.
   - `dia_en_turno()`: Verifica si un día pertenece a un turno específico según descripción textual.
3. **Análisis de Asistencia**:
   - `analizar_asistencia_y_horarios()`: Enriquece el DataFrame con análisis de horarios y retardos.
   - Cálculo de retardos, faltas y descuentos por acumulación.
4. **Generación de Resumen**:
   - `generar_resumen_periodo()`: Crea un resumen con totales por empleado, incluyendo faltas y cálculo de diferencia entre horas trabajadas y esperadas.

## Archivos de Salida

El sistema genera varios archivos CSV como resultado de su ejecución:
- `reporte_asistencia_analizado.csv`: Reporte detallado con análisis de asistencias.
- `reporte_asistencia_final.csv`: Reporte final con todos los datos procesados.
- `resumen_periodo.csv`: Resumen del período con métricas agregadas por empleado.
- `cheques_agrupados.csv`: Datos para cálculo de cheques agrupados.
- `cheques_completos_por_dia.csv`: Desglose diario de datos para cheques.

## Uso

1. Asegúrate de tener el archivo `.env` configurado con todas las credenciales necesarias.
2. Ejecuta `generar_reporte_avanzado.py` especificando las fechas de inicio y fin del período a analizar.

```bash
python generar_reporte_avanzado.py --start-date 2025-07-01 --end-date 2025-07-15
```

## Notas Importantes

- El sistema utiliza una lógica de prioridad para determinar los horarios aplicables a cada empleado.
- Se consideran retardos después de 15 minutos de la hora de entrada programada.
- Tres retardos acumulados generan un descuento equivalente a un día.