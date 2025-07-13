import os
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv

# Carga las variables de entorno
load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")  # Puerto por defecto si no está en .env
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def connect_db():
    """
    Establece y retorna una conexión a la base de datos MariaDB.
    """
    if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
        print(
            "❌ Error: Faltan variables en el archivo .env (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)"
        )
        return None

    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=int(DB_PORT),
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
        )
        return conn
    except mysql.connector.Error as err:
        print(f"❌ Error al conectar a la base de datos: {err}")
        return None


def query_horario_programado(codigo_frappe: int, fecha: datetime):
    """
    Consulta el horario programado para un empleado (por codigo_frappe)
    en una fecha específica, aplicando la lógica de prioridad correcta.
    Retorna: dict con el horario y detalles del empleado o None si no hay asignación.
    """
    conn = connect_db()
    if conn is None:
        return None

    try:
        # Determina si es primera quincena (TRUE/1) o segunda quincena (FALSE/0)
        es_primera_quincena = 1 if fecha.day <= 15 else 0

        # Día de la semana (1 = Lunes, ..., 7 = Domingo), estándar ISO
        dia_semana_id = fecha.isoweekday()

        # Consulta SQL corregida, adaptada de tu versión funcional
        sql = """
        SELECT
            E.empleado_id,
            E.codigo_frappe,
            CONCAT(E.nombre, ' ', E.apellido_paterno) AS nombre_completo,
            DS.nombre_dia AS dia_semana_checado,
            -- Usamos COALESCE para priorizar horarios específicos sobre los de catálogo
            COALESCE(H.hora_entrada, AH.hora_entrada_especifica) AS hora_entrada,
            COALESCE(H.hora_salida, AH.hora_salida_especifica) AS hora_salida,
            COALESCE(H.cruza_medianoche, AH.hora_salida_especifica_cruza_medianoche, FALSE) AS cruza_medianoche,
            AH.comentarios
        FROM
            Empleados AS E
        LEFT JOIN AsignacionHorario AS AH ON E.empleado_id = AH.empleado_id
        LEFT JOIN Horario AS H ON AH.horario_id = H.horario_id
        LEFT JOIN DiaSemana AS DS ON %s = DS.dia_id
        WHERE
            E.codigo_frappe = %s
            AND (
                -- Filtros para encontrar la regla aplicable
                (AH.dia_especifico_id = %s)
                OR (AH.tipo_turno_id IS NOT NULL)
                OR (E.tiene_horario_asignado = FALSE)
            )
        ORDER BY
            -- La clave es este CASE para replicar la lógica de prioridad.
            -- Un número menor tiene mayor prioridad.
            CASE
                WHEN AH.dia_especifico_id = %s AND AH.es_primera_quincena = %s THEN 1
                WHEN AH.dia_especifico_id = %s AND AH.es_primera_quincena IS NULL THEN 2
                WHEN AH.tipo_turno_id IS NOT NULL AND AH.es_primera_quincena = %s THEN 3
                WHEN AH.tipo_turno_id IS NOT NULL AND AH.es_primera_quincena IS NULL THEN 4
                WHEN E.tiene_horario_asignado = FALSE THEN 5
                ELSE 99
            END ASC
        LIMIT 1;
        """

        cursor = conn.cursor(dictionary=True)
        # Los parámetros deben repetirse para cada placeholder '?' o '%s'
        params = (
            dia_semana_id,
            codigo_frappe,
            dia_semana_id,
            dia_semana_id,
            es_primera_quincena,
            dia_semana_id,
            es_primera_quincena,
        )
        cursor.execute(sql, params)

        result = cursor.fetchone()
        if result:
            print(
                f"✅ Horario encontrado para el código Frappe {codigo_frappe} el {fecha.date()}:"
            )
            # Convertir timedelta a string si es necesario para la impresión
            if result.get("hora_entrada"):
                result["hora_entrada"] = str(result["hora_entrada"])
            if result.get("hora_salida"):
                result["hora_salida"] = str(result["hora_salida"])
            print(result)
            return result
        else:
            print(
                f"⚠️  No se encontró un horario asignado para el código Frappe {codigo_frappe} el {fecha.date()}"
            )
            return None

    except mysql.connector.Error as err:
        print(f"❌ Error al ejecutar la consulta: {err}")
        return None
    finally:
        # Cierra el cursor y la conexión
        if "cursor" in locals():
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("✅ Conexión a la base de datos cerrada.")


# Ejemplo de uso
if __name__ == "__main__":
    # Define la fecha que quieres consultar (Lunes 7 de Julio de 2025)
    fecha_ejemplo = datetime(2025, 7, 7)
    # Usa el código Frappe del empleado
    codigo_frappe_ejemplo = 52

    horario = query_horario_programado(codigo_frappe_ejemplo, fecha_ejemplo)

    if horario:
        print("\n--- Resultado Final ---")
        print(f"Horario programado: {horario}")
    else:
        print("\n--- Resultado Final ---")
        print("No se encontró horario programado.")
