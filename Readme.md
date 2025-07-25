# Sistema de Gestión de Asistencias (Optimizado con PostgreSQL)

Este proyecto es un sistema de gestión de asistencias que integra datos de marcaciones de empleados con horarios programados para generar reportes de asistencia, retardos y horas trabajadas.

## Requisitos

- Python 3.8+
- Base de datos PostgreSQL (versión original usaba MariaDB/MySQL)
- Acceso a la API de registros de asistencia
- Copia el archivo `.env.example` a `.env` y completa las siguientes variables:
  - `DB_HOST`: Host de la base de datos
  - `DB_PORT`: Puerto de la base de datos (por defecto: 5432 para PostgreSQL)
  - `DB_NAME`: Nombre de la base de datos
  - `DB_USER`: Usuario de la base de datos
  - `DB_PASSWORD`: Contraseña de la base de datos
  - `ASIATECH_API_KEY`: Clave de API para acceder a los datos de asistencia
  - `ASIATECH_API_SECRET`: Secreto de API para acceder a los datos de asistencia

## Novedades en la versión optimizada con PostgreSQL

La nueva versión del sistema incluye importantes mejoras:

1. **Migración a PostgreSQL**: Mejor rendimiento y funcionalidades avanzadas.
2. **Función f_tabla_horarios**: Obtiene todos los horarios programados de una sucursal en una sola consulta.
3. **Sistema de caché**: Los horarios se consultan una sola vez y se almacenan en memoria para evitar consultas repetitivas.
4. **Manejo de turnos que cruzan medianoche**: Ahora se gestionan correctamente los horarios que empiezan un día y terminan al día siguiente.
5. **Flujo de trabajo optimizado**: Primero se cargan los horarios programados y luego se procesan los datos del API.

## Estructura del Proyecto

### `db_postgres_connection.py`

Este archivo proporciona funcionalidades para conectarse a la base de datos PostgreSQL y obtener los horarios programados utilizando la función f_tabla_horarios.

**Funciones principales:**
- `connect_db()`: Establece y retorna una conexión a la base de datos PostgreSQL.
- `obtener_tabla_horarios(sucursal, es_primera_quincena, conn)`: Obtiene todos los horarios programados para una sucursal y quincena específica.
- `mapear_horarios_por_empleado(horarios_tabla, empleados_codigos)`: Mapea los horarios por código de empleado y día de la semana.
- `obtener_horario_empleado(codigo_frappe, dia_semana, es_primera_quincena, cache_horarios)`: Obtiene el horario de un empleado para un día específico desde el caché.

### `generar_reporte_optimizado.py`

Versión optimizada que utiliza PostgreSQL y el sistema de caché para generar reportes detallados de asistencia.

**Secciones y funciones principales:**
1. **Configuración y Conexión**: Inicialización de conexiones a PostgreSQL.
2. **Obtención de horarios**: Carga todos los horarios desde la función `f_tabla_horarios`.
3. **Procesamiento de Datos**:
   - `process_checkins_to_dataframe()`: Convierte los datos de marcaciones en un DataFrame estructurado.
   - `procesar_horarios_con_medianoche()`: Gestiona correctamente los turnos que cruzan la medianoche.
4. **Análisis de Asistencia**:
   - `analizar_asistencia_con_horarios_cache()`: Enriquece el DataFrame con análisis de horarios y retardos usando el caché.
5. **Generación de Resumen**:
   - `generar_resumen_periodo()`: Crea un resumen con totales por empleado.

### `conexión_bd.py` y `db_connection.py`

Versiones anteriores para MariaDB/MySQL (mantenidas por compatibilidad).

### `db_postgres.sql`

Archivo SQL con la estructura y funciones para la base de datos PostgreSQL, incluidas:
- `f_tabla_horarios`: Función que devuelve todos los horarios programados para una sucursal.
- `F_CrearJsonHorario`: Función auxiliar para crear JSON con información de horarios.

## Archivos de Salida

El sistema genera varios archivos CSV como resultado de su ejecución:
- `reporte_asistencia_analizado.csv`: Reporte detallado con análisis de asistencias.
- `resumen_periodo.csv`: Resumen del período con métricas agregadas por empleado.

## Uso

### Versión optimizada con PostgreSQL:

1. Copia `.env.example` a `.env` y configura tus credenciales (asegúrate de usar los datos de PostgreSQL).
2. Instala las dependencias:

```bash
pip install -r requirements.txt
```

3. Ejecuta el script optimizado:

```bash
python generar_reporte_optimizado.py
```

### Versión original con MySQL:

1. Copia `.env.example` a `.env` y configura tus credenciales para MySQL.
2. Ejecuta `generar_reporte_avanzado.py` especificando las fechas de inicio y fin del período a analizar.

```bash
python generar_reporte_avanzado.py
```

## Notas Importantes

- Para configurar las fechas y sucursal en la versión optimizada, edita los valores al final del script `generar_reporte_optimizado.py`:
  ```python
  start_date = "2025-07-01"
  end_date = "2025-07-15"
  sucursal = "Villas"
  device_filter = "%villas%"
  ```
- El sistema determina automáticamente si es primera o segunda quincena basándose en la fecha de inicio.
- Se consideran retardos después de 15 minutos de la hora de entrada programada.
- Tres retardos acumulados generan un descuento equivalente a un día.
- Para turnos que cruzan medianoche, la checada de salida del día siguiente se asocia correctamente con la entrada del día anterior.