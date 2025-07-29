import os
import json
import psycopg2
from psycopg2.extras import DictCursor, RealDictCursor
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Variables de conexión a la Base de Datos PostgreSQL
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")  # Puerto por defecto para PostgreSQL
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def connect_db():
    """
    Establece y retorna una conexión a la base de datos PostgreSQL.
    """
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        print("❌ Error de Configuración de BD: Faltan variables en el archivo .env")
        return None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        return conn
    except psycopg2.Error as err:
        print(
            f"❌ Error de Conexión a BD: {err}. No se pueden obtener los horarios programados."
        )
        return None


def obtener_tabla_horarios(sucursal: str, es_primera_quincena: bool, conn=None, codigos_frappe=None):
    """
    Obtiene la tabla de horarios completa para una sucursal y quincena específica.
    Utiliza la función f_tabla_horarios de PostgreSQL que devuelve los horarios
    de todos los empleados por día de la semana.
    
    Args:
        sucursal: Nombre de la sucursal (ej: 'Villas')
        es_primera_quincena: True si es primera quincena, False si es segunda
        conn: Conexión a la base de datos (opcional)
        codigos_frappe: Lista de códigos frappe de la API para filtrar (opcional)
        
    Returns:
        Lista de diccionarios con los horarios por empleado y día
    """
    if conn is None:
        conn = connect_db()
        close_conn = True
    else:
        close_conn = False
        
    if conn is None:
        return []

    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # La función f_tabla_horarios ya incluye el codigo_frappe en los resultados
        sql_horarios = """
        SELECT * FROM f_tabla_horarios(%s, %s)
        """
        cursor.execute(sql_horarios, (sucursal, es_primera_quincena))
        horarios_result = cursor.fetchall()
        
        # Filtrar por códigos frappe si se proporcionan
        if codigos_frappe:
            # Convertir los códigos a string para comparación
            codigos_str = [str(codigo) for codigo in codigos_frappe]
            horarios_result = [
                horario for horario in horarios_result 
                if str(horario.get('codigo_frappe')) in codigos_str
            ]
            
        cursor.close()
        
        # Procesar los resultados para manejar los datos JSONB
        horarios_procesados = []
        for row in horarios_result:
            horario_empleado = dict(row)
            for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]:
                if horario_empleado[dia] is not None:
                    # Si es una cadena JSON, convertirla a diccionario Python
                    if isinstance(horario_empleado[dia], str):
                        horario_empleado[dia] = json.loads(horario_empleado[dia])
                    # Si ya es un dict o un objeto JSON deserializado, no hacer nada
            horarios_procesados.append(horario_empleado)
            
        return horarios_procesados
    except psycopg2.Error as err:
        print(f"❌ Error en consulta de horarios para {sucursal}: {err}")
        return []
    finally:
        if close_conn and conn:
            conn.close()


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
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dias_indices = {dias_semana[i-1]: i for i in range(1, 8)}  # Lunes=1, Domingo=7
    
    horarios_mapeados = {}
    empleados_mapeados = 0
    
    # Convertir empleados_codigos a strings para comparación consistente
    empleados_codigos_str = {str(codigo) for codigo in empleados_codigos}
    
    # Iterar directamente por los horarios obtenidos de la función f_tabla_horarios
    for horario in horarios_tabla:
        # Usar el codigo_frappe directamente desde la tabla
        codigo_frappe = str(horario.get("codigo_frappe"))
        
        # Verificar que el código frappe exista en los datos de la API
        if codigo_frappe == 'None' or codigo_frappe not in empleados_codigos_str:
            continue
            
        empleados_mapeados += 1
        horarios_mapeados[codigo_frappe] = {}
        
        for dia in dias_semana:
            if horario[dia] is not None:
                hora_entrada = horario[dia].get("horario_entrada")
                hora_salida = horario[dia].get("horario_salida")
                horas_totales = horario[dia].get("horas_totales")
                
                # Detectamos si cruza medianoche cuando la hora de salida es menor que la de entrada
                hora_entrada_parts = list(map(int, hora_entrada.split(":")))
                hora_salida_parts = list(map(int, hora_salida.split(":")))
                entrada_mins = hora_entrada_parts[0] * 60 + hora_entrada_parts[1]
                salida_mins = hora_salida_parts[0] * 60 + hora_salida_parts[1]
                cruza_medianoche = salida_mins < entrada_mins
                
                horarios_mapeados[codigo_frappe][dias_indices[dia]] = {
                    "hora_entrada": hora_entrada,
                    "hora_salida": hora_salida,
                    "horas_totales": horas_totales,
                    "cruza_medianoche": cruza_medianoche
                }
    
    print(f"✅ Se mapearon horarios para {empleados_mapeados} empleados usando código frappe")
    return horarios_mapeados


def obtener_horarios_multi_quincena(sucursal, conn, codigos_frappe, incluye_primera=False, incluye_segunda=False):
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
        print(f"✅ Se obtuvieron {len(result[True])} registros de horarios para la primera quincena")
    
    if incluye_segunda:
        result[False] = obtener_tabla_horarios(sucursal, False, conn, codigos_frappe)
        print(f"✅ Se obtuvieron {len(result[False])} registros de horarios para la segunda quincena")
    
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
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dias_indices = {dias_semana[i-1]: i for i in range(1, 8)}  # Lunes=1, Domingo=7
    
    horarios_mapeados = {}
    empleados_mapeados = set()
    
    # Procesar cada quincena
    for es_primera_quincena, horarios_tabla in horarios_por_quincena.items():
        # Iterar por los horarios obtenidos de la función f_tabla_horarios para esta quincena
        for horario in horarios_tabla:
            # Usar el codigo_frappe directamente desde la tabla
            codigo_frappe = str(horario.get("codigo_frappe"))
            
            # Verificar que el código frappe sea válido
            if codigo_frappe == 'None':
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
                    
                    # Detectamos si cruza medianoche cuando la hora de salida es menor que la de entrada
                    hora_entrada_parts = list(map(int, hora_entrada.split(":")))
                    hora_salida_parts = list(map(int, hora_salida.split(":")))
                    entrada_mins = hora_entrada_parts[0] * 60 + hora_entrada_parts[1]
                    salida_mins = hora_salida_parts[0] * 60 + hora_salida_parts[1]
                    cruza_medianoche = salida_mins < entrada_mins
                    
                    horarios_mapeados[codigo_frappe][es_primera_quincena][dias_indices[dia]] = {
                        "hora_entrada": hora_entrada,
                        "hora_salida": hora_salida,
                        "horas_totales": horas_totales,
                        "cruza_medianoche": cruza_medianoche
                    }
    
    print(f"✅ Se mapearon horarios para {len(empleados_mapeados)} empleados usando código frappe en formato multi-quincena")
    return horarios_mapeados


def obtener_horario_empleado(codigo_frappe, dia_semana, es_primera_quincena, cache_horarios):
    """
    Obtiene el horario de un empleado para un día específico desde el caché
    
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


# Función auxiliar para pruebas
if __name__ == "__main__":
    # Ejemplo de uso
    conn = connect_db()
    if conn:
        print("✅ Conexión establecida correctamente")
        
        # Consultar todas las sucursales disponibles
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT sucursal_id, nombre_sucursal FROM Sucursales ORDER BY sucursal_id")
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
            for dia in ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]:
                if horarios[0][dia]:
                    print(f"{dia}: {horarios[0][dia]}")
        
        conn.close()
