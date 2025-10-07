import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import logging
from functools import lru_cache

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Variables de conexión a la Base de Datos PostgreSQL
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")  # Puerto por defecto para PostgreSQL
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

# Configuración del pool de conexiones
MIN_POOL_CONNECTIONS = int(os.getenv("MIN_POOL_CONNECTIONS", "2"))
MAX_POOL_CONNECTIONS = int(os.getenv("MAX_POOL_CONNECTIONS", "10"))

# Pool de conexiones global
_connection_pool = None
logger = logging.getLogger(__name__)


def get_connection_pool():
    """
    Inicializa y retorna el pool de conexiones a la base de datos PostgreSQL.
    Utiliza ThreadedConnectionPool para ser seguro en aplicaciones multi-thread.
    """
    global _connection_pool

    if _connection_pool is not None:
        return _connection_pool

    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        logger.error("❌ Error de Configuración de BD: Faltan variables en el archivo .env")
        return None

    try:
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=MIN_POOL_CONNECTIONS,
            maxconn=MAX_POOL_CONNECTIONS,
            host=DB_HOST,
            port=int(DB_PORT),
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        logger.info(f"✅ Pool de conexiones inicializado: {MIN_POOL_CONNECTIONS}-{MAX_POOL_CONNECTIONS} conexiones")
        return _connection_pool
    except psycopg2.Error as err:
        logger.error(f"❌ Error al crear pool de conexiones: {err}")
        return None


def connect_db():
    """
    Establece y retorna una conexión a la base de datos PostgreSQL.
    Esta función es mantenida por compatibilidad, pero se recomienda usar get_connection_from_pool().
    """
    pool = get_connection_pool()
    if pool is None:
        return None

    try:
        return pool.getconn()
    except psycopg2.Error as err:
        logger.error(f"❌ Error obteniendo conexión del pool: {err}")
        return None


def get_connection_from_pool():
    """
    Obtiene una conexión del pool de conexiones de forma segura.

    Returns:
        psycopg2.extensions.connection: Conexión a la base de datos o None si hay error
    """
    pool = get_connection_pool()
    if pool is None:
        return None

    try:
        conn = pool.getconn()
        logger.debug("Conexión obtenida del pool")
        return conn
    except psycopg2.Error as err:
        logger.error(f"❌ Error obteniendo conexión del pool: {err}")
        return None


def return_connection_to_pool(conn):
    """
    Devuelve una conexión al pool de forma segura.

    Args:
        conn: Conexión a la base de datos para devolver al pool
    """
    if conn is None:
        return

    pool = get_connection_pool()
    if pool is None:
        return

    try:
        pool.putconn(conn)
        logger.debug("Conexión devuelta al pool")
    except psycopg2.Error as err:
        logger.error(f"❌ Error devolviendo conexión al pool: {err}")


def close_all_connections():
    """
    Cierra todas las conexiones del pool.
    Útil para limpieza al finalizar la aplicación.
    """
    global _connection_pool

    if _connection_pool is not None:
        try:
            _connection_pool.closeall()
            _connection_pool = None
            logger.info("✅ Todas las conexiones del pool han sido cerradas")
        except psycopg2.Error as err:
            logger.error(f"❌ Error cerrando conexiones del pool: {err}")


def connection_context_manager():
    """
    Context manager para manejar conexiones del pool automáticamente.

    Usage:
        with connection_context_manager() as conn:
            cursor = conn.cursor()
            # Usar la conexión
            # La conexión se devuelve automáticamente al pool
    """
    class ConnectionContext:
        def __enter__(self):
            self.conn = get_connection_from_pool()
            return self.conn

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.conn is not None:
                if exc_type is None:
                    # Si no hay excepción, hacer commit
                    try:
                        self.conn.commit()
                    except psycopg2.Error:
                        pass  # La conexión podría no estar en una transacción
                else:
                    # Si hay excepción, hacer rollback
                    try:
                        self.conn.rollback()
                    except psycopg2.Error:
                        pass  # La conexión podría no estar en una transacción

                return_connection_to_pool(self.conn)

    return ConnectionContext()


def obtener_tabla_horarios(
    sucursal: str, es_primera_quincena: bool, conn=None, codigos_frappe=None
):
    """
    Obtiene la tabla de horarios completa para una sucursal y quincena específica.
    Utiliza la función f_tabla_horarios_multi_quincena de PostgreSQL que devuelve los horarios
    de todos los empleados por día de la semana con información de cruza_medianoche.

    Args:
        sucursal: Nombre de la sucursal (ej: 'Villas')
        es_primera_quincena: True si es primera quincena, False si es segunda
        conn: Conexión a la base de datos (opcional, para compatibilidad)
        codigos_frappe: Lista de códigos frappe de la API para filtrar (opcional)

    Returns:
        Lista de diccionarios con los horarios por empleado y día
    """
    close_conn = False

    # Si no se proporciona conexión, usar el pool
    if conn is None:
        conn = get_connection_from_pool()
        close_conn = True
        if conn is None:
            return []

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Usar la nueva función f_tabla_horarios_multi_quincena que incluye cruza_medianoche
        sql_horarios = """
        SELECT * FROM f_tabla_horarios_multi_quincena(%s)
        WHERE es_primera_quincena = %s
        """
        cursor.execute(sql_horarios, (sucursal, es_primera_quincena))
        horarios_result = cursor.fetchall()

        # Filtrar por códigos frappe si se proporcionan
        if codigos_frappe:
            # Convertir los códigos a string para comparación
            codigos_str = [str(codigo) for codigo in codigos_frappe]
            horarios_result = [
                horario
                for horario in horarios_result
                if str(horario.get("codigo_frappe")) in codigos_str
            ]

        cursor.close()

        # Procesar los resultados para manejar los datos JSONB
        horarios_procesados = []
        for row in horarios_result:
            horario_empleado = dict(row)
            for dia in [
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
                "Sábado",
                "Domingo",
            ]:
                if horario_empleado[dia] is not None:
                    # Si es una cadena JSON, convertirla a diccionario Python
                    if isinstance(horario_empleado[dia], str):
                        horario_empleado[dia] = json.loads(horario_empleado[dia])
                    # Si ya es un dict o un objeto JSON deserializado, no hacer nada
            horarios_procesados.append(horario_empleado)

        return horarios_procesados
    except psycopg2.Error as err:
        logger.error(f"❌ Error en consulta de horarios para {sucursal}: {err}")
        return []
    finally:
        if close_conn and conn:
            return_connection_to_pool(conn)


def mapear_horarios_por_empleado(horarios_tabla, empleados_codigos):
    """
    Mapea los horarios de la tabla por código de empleado y día de la semana

    Args:
        horarios_tabla: Lista de diccionarios obtenida de obtener_tabla_horarios
        empleados_codigos: Set con los códigos frappe de empleados de la API

    Returns:
        Diccionario con la estructura {codigo_frappe: {dia_semana: horario}}

    Note:
        Función legada. Para soporte multi-quincena use mapear_horarios_por_empleado_multi.
    """
    dias_semana = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    dias_indices = {dias_semana[i - 1]: i for i in range(1, 8)}  # Lunes=1, Domingo=7

    horarios_mapeados = {}
    empleados_mapeados = 0

    # Convertir empleados_codigos a strings para comparación consistente
    empleados_codigos_str = {str(codigo) for codigo in empleados_codigos}

    # Iterar directamente por los horarios obtenidos de la función f_tabla_horarios
    for horario in horarios_tabla:
        # Usar el codigo_frappe directamente desde la tabla
        codigo_frappe = str(horario.get("codigo_frappe"))

        # Verificar que el código frappe exista en los datos de la API
        if codigo_frappe == "None" or codigo_frappe not in empleados_codigos_str:
            continue

        empleados_mapeados += 1
        horarios_mapeados[codigo_frappe] = {}

        for dia in dias_semana:
            if horario[dia] is not None:
                hora_entrada = horario[dia].get("horario_entrada")
                hora_salida = horario[dia].get("horario_salida")
                horas_totales = horario[dia].get("horas_totales")
                # Usar el campo cruza_medianoche de la base de datos
                cruza_medianoche = horario[dia].get("cruza_medianoche", False)

                horarios_mapeados[codigo_frappe][dias_indices[dia]] = {
                    "hora_entrada": hora_entrada,
                    "hora_salida": hora_salida,
                    "horas_totales": horas_totales,
                    "cruza_medianoche": cruza_medianoche,
                }

    print(
        f"✅ Se mapearon horarios para {empleados_mapeados} empleados usando código frappe"
    )
    return horarios_mapeados


def obtener_horarios_multi_quincena(
    sucursal, conn, codigos_frappe, incluye_primera=False, incluye_segunda=False
):
    """
    Obtiene las tablas de horarios para ambas quincenas si son requeridas.

    Args:
        sucursal: Nombre de la sucursal (ej: 'Villas')
        conn: Conexión a la base de datos
        codigos_frappe: Lista de códigos frappe de la API para filtrar
        incluye_primera: True si el rango incluye días de la primera quincena (1-15)
        incluye_segunda: True si el rango incluye días de la segunda quincena (16-31)

    Returns:
        Diccionario con las claves True (primera quincena) y/o False (segunda quincena)
        conteniendo cada uno la lista de filas de f_tabla_horarios para esa quincena.
    """
    result = {}

    if incluye_primera:
        result[True] = obtener_tabla_horarios(sucursal, True, conn, codigos_frappe)
        print(
            f"✅ Se obtuvieron {len(result[True])} registros de horarios para la primera quincena"
        )

    if incluye_segunda:
        result[False] = obtener_tabla_horarios(sucursal, False, conn, codigos_frappe)
        print(
            f"✅ Se obtuvieron {len(result[False])} registros de horarios para la segunda quincena"
        )

    return result


def mapear_horarios_por_empleado_multi(horarios_por_quincena):
    """
    Mapea los horarios de ambas quincenas por código de empleado, día de la semana y quincena

    Args:
        horarios_por_quincena: Diccionario {True|False: [filas_f_tabla_horarios]} obtenido de
                               obtener_horarios_multi_quincena

    Returns:
        Diccionario con la estructura {codigo_frappe: {True|False: {dia_semana: horario}}}
        donde True representa primera quincena y False la segunda
    """
    dias_semana = [
        "Lunes",
        "Martes",
        "Miércoles",
        "Jueves",
        "Viernes",
        "Sábado",
        "Domingo",
    ]
    dias_indices = {dias_semana[i - 1]: i for i in range(1, 8)}  # Lunes=1, Domingo=7

    horarios_mapeados = {}
    empleados_mapeados = set()

    # Procesar cada quincena
    for es_primera_quincena, horarios_tabla in horarios_por_quincena.items():
        # Iterar por los horarios obtenidos de la función f_tabla_horarios para esta quincena
        for horario in horarios_tabla:
            # Usar el codigo_frappe directamente desde la tabla
            codigo_frappe = str(horario.get("codigo_frappe"))

            # Verificar que el código frappe sea válido
            if codigo_frappe == "None":
                continue

            # Inicializar estructura si no existe
            if codigo_frappe not in horarios_mapeados:
                horarios_mapeados[codigo_frappe] = {}

            # Inicializar submapa para esta quincena si no existe
            if es_primera_quincena not in horarios_mapeados[codigo_frappe]:
                horarios_mapeados[codigo_frappe][es_primera_quincena] = {}

            empleados_mapeados.add(codigo_frappe)

            for dia in dias_semana:
                if horario[dia] is not None:
                    hora_entrada = horario[dia].get("horario_entrada")
                    hora_salida = horario[dia].get("horario_salida")
                    horas_totales = horario[dia].get("horas_totales")
                    # Usar el campo cruza_medianoche de la base de datos
                    cruza_medianoche = horario[dia].get("cruza_medianoche", False)

                    horarios_mapeados[codigo_frappe][es_primera_quincena][
                        dias_indices[dia]
                    ] = {
                        "hora_entrada": hora_entrada,
                        "hora_salida": hora_salida,
                        "horas_totales": horas_totales,
                        "cruza_medianoche": cruza_medianoche,
                    }

    print(
        f"✅ Se mapearon horarios para {len(empleados_mapeados)} empleados usando código frappe en formato multi-quincena"
    )
    return horarios_mapeados


# Cache para consultas de horarios individuales
_horario_cache = {}


@lru_cache(maxsize=10000)
def obtener_horario_empleado_cached(
    codigo_frappe: str, dia_semana: int, es_primera_quincena: bool, cache_horarios_id: int
):
    """
    Obtiene el horario de un empleado para un día específico con cache LRU.
    Esta función está optimizada para llamadas repetitivas con los mismos parámetros.

    Args:
        codigo_frappe: Código frappe del empleado
        dia_semana: Día de la semana (1-7, lunes=1)
        es_primera_quincena: True si es primera quincena, False si es segunda
        cache_horarios_id: ID del caché de horarios (para evitar problemas con objetos mutables)

    Returns:
        Tupla con (horario_dict, encontrado) o (None, False) si no existe
    """
    global _horario_cache

    cache_key = f"{codigo_frappe}_{dia_semana}_{es_primera_quincena}_{cache_horarios_id}"

    if cache_key in _horario_cache:
        return _horario_cache[cache_key], True

    # Si no está en caché, buscar en el cache_horarios principal
    cache_horarios = _horario_cache.get('_main_cache', {})
    horario = obtener_horario_empleado_base(codigo_frappe, dia_semana, es_primera_quincena, cache_horarios)

    if horario:
        _horario_cache[cache_key] = horario
        return horario, True

    return None, False


def obtener_horario_empleado(
    codigo_frappe, dia_semana, es_primera_quincena, cache_horarios
):
    """
    Obtiene el horario de un empleado para un día específico desde el caché.
    Versión optimizada con cache LRU para mejorar rendimiento.

    Args:
        codigo_frappe: Código frappe del empleado
        dia_semana: Día de la semana (1-7, lunes=1)
        es_primera_quincena: True si es primera quincena, False si es segunda
        cache_horarios: Diccionario con la estructura {codigo_frappe: {dia_semana: horario}} o
                        {codigo_frappe: {es_primera_quincena: {dia_semana: horario}}} para multi-quincena

    Returns:
        Diccionario con el horario o None si no existe
    """
    # Almacenar el cache_horarios principal para acceso posterior
    global _horario_cache
    if '_main_cache' not in _horario_cache:
        _horario_cache['_main_cache'] = cache_horarios

    # Usar una versión simplificada del cache_horarios_id para el cache LRU
    cache_horarios_id = id(cache_horarios) % 1000  # Simplificar para evitar problemas de memoria

    horario, _ = obtener_horario_empleado_cached(
        str(codigo_frappe), int(dia_semana), bool(es_primera_quincena), cache_horarios_id
    )

    return horario


def obtener_horario_empleado_base(
    codigo_frappe, dia_semana, es_primera_quincena, cache_horarios
):
    """
    Función base para obtener horarios sin caché LRU (usada internamente).

    Args:
        codigo_frappe: Código frappe del empleado
        dia_semana: Día de la semana (1-7, lunes=1)
        es_primera_quincena: True si es primera quincena, False si es segunda
        cache_horarios: Diccionario con la estructura {codigo_frappe: {dia_semana: horario}} o
                        {codigo_frappe: {es_primera_quincena: {dia_semana: horario}}} para multi-quincena

    Returns:
        Diccionario con el horario o None si no existe
    """
    if codigo_frappe not in cache_horarios:
        return None

    codigo_cache = cache_horarios[codigo_frappe]

    # Detectar si estamos usando el formato multi-quincena
    # En el formato multi-quincena, el valor en codigo_cache[True/False] es un dict de días
    keys_bool = [k for k in codigo_cache.keys() if isinstance(k, bool)]

    if keys_bool:
        # Formato multi-quincena: cache[codigo][es_primera_quincena][dia_semana]
        if es_primera_quincena not in codigo_cache:
            return None
        return codigo_cache[es_primera_quincena].get(dia_semana)
    else:
        # Formato legacy: cache[codigo][dia_semana]
        return codigo_cache.get(dia_semana)


def clear_horario_cache():
    """
    Limpia el caché de horarios.
    Útil para liberar memoria o cuando los datos horarios cambian.
    """
    global _horario_cache
    _horario_cache.clear()
    obtener_horario_empleado_cached.cache_clear()
    logger.info("✅ Caché de horarios limpiado")


def get_cache_stats():
    """
    Retorna estadísticas del caché de horarios.

    Returns:
        Dict con información del estado del caché
    """
    global _horario_cache

    cache_info = obtener_horario_empleado_cached.cache_info()

    return {
        'lru_cache': {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'current_size': cache_info.currsize,
            'max_size': cache_info.maxsize,
            'hit_ratio': cache_info.hits / (cache_info.hits + cache_info.misses) if (cache_info.hits + cache_info.misses) > 0 else 0
        },
        'local_cache_size': len(_horario_cache)
    }


# Función auxiliar para pruebas
if __name__ == "__main__":
    # Ejemplo de uso
    conn = connect_db()
    if conn:
        print("✅ Conexión establecida correctamente")

        # Consultar todas las sucursales disponibles
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT sucursal_id, nombre_sucursal FROM Sucursales ORDER BY sucursal_id"
            )
            sucursales = cursor.fetchall()
            print("\nSucursales disponibles en la base de datos:")
            for sucursal in sucursales:
                print(f"ID: {sucursal[0]}, Nombre: {sucursal[1]}")
            cursor.close()
        except Exception as e:
            print(f"Error al consultar sucursales: {e}")

        # Prueba la función de obtener tabla de horarios
        horarios = obtener_tabla_horarios("Villas", False, conn)
        print(f"\nSe encontraron {len(horarios)} empleados con horarios en 'Villas'")

        # Muestra un ejemplo de los horarios
        if horarios:
            print("\nEjemplo de horario para el primer empleado:")
            print(f"Nombre: {horarios[0]['nombre_completo']}")
            for dia in [
                "Lunes",
                "Martes",
                "Miércoles",
                "Jueves",
                "Viernes",
                "Sábado",
                "Domingo",
            ]:
                if horarios[0][dia]:
                    print(f"{dia}: {horarios[0][dia]}")

        conn.close()
