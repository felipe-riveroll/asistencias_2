import json
import os
import requests
import pandas as pd
from itertools import product
from datetime import datetime, timedelta
import re
import mysql.connector
from dotenv import load_dotenv

# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN Y CONEXIÓN A LA BASE DE DATOS
# ==============================================================================

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Variables de conexión a la Base de Datos
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def connect_db():
    """
    Establece y retorna una conexión a la base de datos MariaDB.
    Maneja errores si faltan credenciales o si la conexión falla.
    """
    if not all([DB_HOST, DB_NAME, DB_USER, DB_PASSWORD]):
        print("❌ Error de Configuración de BD: Faltan variables en el archivo .env")
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
        print(
            f"❌ Error de Conexión a BD: {err}. No se pueden obtener los horarios programados."
        )
        return None


def query_horario_programado(codigo_frappe: int, fecha: datetime, conn):
    """
    Consulta el horario programado para un empleado en una fecha específica usando la lógica de prioridad.
    """
    if conn is None or not conn.is_connected():
        return None

    try:
        es_primera_quincena = 1 if fecha.day <= 15 else 0
        dia_semana_id = fecha.isoweekday()  # Lunes=1, Domingo=7

        # La consulta SQL completa que considera todas las reglas de prioridad
        sql = """
        SELECT 
            COALESCE(H.hora_entrada, AH.hora_entrada_especifica) as hora_entrada, 
            COALESCE(H.hora_salida, AH.hora_salida_especifica) as hora_salida,
            COALESCE(H.cruza_medianoche, AH.hora_salida_especifica_cruza_medianoche, FALSE) AS cruza_medianoche
        FROM Empleados AS E
        LEFT JOIN AsignacionHorario AS AH ON E.empleado_id = AH.empleado_id
        LEFT JOIN Horario AS H ON AH.horario_id = H.horario_id
        WHERE E.codigo_frappe = %s AND (
            (AH.dia_especifico_id = %s) OR 
            (AH.tipo_turno_id IS NOT NULL) OR 
            (E.tiene_horario_asignado = FALSE)
        )
        ORDER BY 
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
        # Los parámetros deben coincidir con cada %s en la consulta
        params = (
            codigo_frappe,
            dia_semana_id,
            dia_semana_id,
            es_primera_quincena,
            dia_semana_id,
            es_primera_quincena,
        )
        cursor.execute(sql, params)
        result = cursor.fetchone()
        cursor.close()
        # Convierte timedelta a string para que pandas lo maneje bien
        if result:
            if isinstance(result.get("hora_entrada"), timedelta):
                result["hora_entrada"] = str(result["hora_entrada"])
            if isinstance(result.get("hora_salida"), timedelta):
                result["hora_salida"] = str(result["hora_salida"])
        return result
    except mysql.connector.Error as err:
        print(
            f" -> Error en consulta para empleado {codigo_frappe} en fecha {fecha.date()}: {err}"
        )
        return None


# ==============================================================================
# SECCIÓN 2: OBTENCIÓN DE DATOS DE LA API FRAPPE
# ==============================================================================
API_KEY = os.getenv("ASIATECH_API_KEY")
API_SECRET = os.getenv("ASIATECH_API_SECRET")
API_URL = "https://erp.asiatech.com.mx/api/resource/Employee Checkin"


def fetch_checkins(start_date: str, end_date: str, device_filter: str):
    """Obtiene todos los registros de checadas de la API para un rango de fechas."""
    print(f"📡 Obteniendo checadas de la API para el dispositivo '{device_filter}'...")
    if not all([API_KEY, API_SECRET]):
        print(
            "❌ Error: Faltan credenciales de API (ASIATECH_API_KEY, ASIATECH_API_SECRET) en el archivo .env"
        )
        return []

    headers = {"Authorization": f"token {API_KEY}:{API_SECRET}"}
    filters = json.dumps(
        [
            ["Employee Checkin", "time", "Between", [start_date, end_date]],
            ["Employee Checkin", "device_id", "like", device_filter],
        ]
    )
    params = {
        "fields": json.dumps(["employee", "employee_name", "time"]),
        "filters": filters,
    }

    all_records = []
    page_length = 100
    limit_start = 0

    while True:
        params["limit_start"], params["limit_page_length"] = limit_start, page_length
        try:
            response = requests.get(API_URL, headers=headers, params=params)
            response.raise_for_status()
            data = response.json().get("data", [])
            if not data:
                break
            all_records.extend(data)
            if len(data) < page_length:
                break
            limit_start += page_length
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al llamar a la API: {e}")
            return []

    print(f"✅ Se obtuvieron {len(all_records)} registros de la API.")
    return all_records


# ==============================================================================
# SECCIÓN 3: PROCESAMIENTO Y ANÁLISIS DE DATOS
# ==============================================================================
def process_checkins_to_dataframe(checkin_data, start_date, end_date):
    """Crea un DataFrame base con una fila por empleado y día."""
    if not checkin_data:
        return pd.DataFrame()

    df = pd.DataFrame(checkin_data)
    df["time"] = pd.to_datetime(df["time"])
    df["dia"] = df["time"].dt.date
    df["checado_time"] = df["time"].dt.strftime("%H:%M:%S")

    employee_map = (
        df[["employee", "employee_name"]]
        .drop_duplicates()
        .rename(columns={"employee_name": "Nombre"})
    )

    df_hours = df.groupby(["employee", "dia"])["time"].agg(["min", "max"]).reset_index()
    duration = df_hours["max"] - df_hours["min"]
    df_hours["horas_trabajadas"] = duration.apply(
        lambda x: str(x).split(" ")[-1] if pd.notna(x) else "00:00:00"
    )

    df["checado_rank"] = df.groupby(["employee", "dia"]).cumcount() + 1
    df_pivot = df.pivot_table(
        index=["employee", "dia"],
        columns="checado_rank",
        values="checado_time",
        aggfunc="first",
    )
    if not df_pivot.empty:
        df_pivot.columns = [f"checado_{i}" for i in range(1, len(df_pivot.columns) + 1)]

    all_employees = df["employee"].unique()
    all_dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date)).date
    base_df = pd.DataFrame(
        list(product(all_employees, all_dates)), columns=["employee", "dia"]
    )

    daily_df = pd.merge(
        base_df, df_pivot.reset_index(), on=["employee", "dia"], how="left"
    )
    final_df = pd.merge(daily_df, employee_map, on="employee", how="left")
    df_hours["dia"] = pd.to_datetime(df_hours["dia"]).dt.date
    final_df = pd.merge(
        final_df,
        df_hours[["employee", "dia", "horas_trabajadas"]],
        on=["employee", "dia"],
        how="left",
    )

    dias_espanol = {
        "Monday": "Lunes",
        "Tuesday": "Martes",
        "Wednesday": "Miércoles",
        "Thursday": "Jueves",
        "Friday": "Viernes",
        "Saturday": "Sábado",
        "Sunday": "Domingo",
    }
    final_df["dia_semana"] = (
        pd.to_datetime(final_df["dia"]).dt.day_name().map(dias_espanol)
    )

    return final_df


def analizar_asistencia_y_horarios(df: pd.DataFrame):
    """Función principal que enriquece el DataFrame con análisis de horarios y retardos."""
    if df.empty:
        return df
    print("\n🔄 Iniciando análisis de horarios y retardos...")

    db_conn = connect_db()

    print(
        "   - Consultando horarios programados en la base de datos (esto puede tardar)..."
    )
    # Aplica la función de consulta a cada fila del DataFrame
    horarios_data = df.apply(
        lambda row: query_horario_programado(
            row["employee"], pd.to_datetime(row["dia"]).to_pydatetime(), db_conn
        ),
        axis=1,
    )

    if db_conn and db_conn.is_connected():
        db_conn.close()
        print("   - Conexión a la base de datos cerrada.")

    # Combina los resultados de la BD con el DataFrame principal
    df_horarios = pd.json_normalize(horarios_data).rename(
        columns={
            "hora_entrada": "hora_entrada_programada",
            "hora_salida": "hora_salida_programada",
        }
    )
    df = pd.concat([df.reset_index(drop=True), df_horarios], axis=1)

    # --- Calcular Horas Esperadas ---
    def calcular_horas_esperadas(row):
        if pd.isna(row.get("hora_entrada_programada")) or pd.isna(
            row.get("hora_salida_programada")
        ):
            return None
        entrada = pd.to_timedelta(str(row["hora_entrada_programada"]))
        salida = pd.to_timedelta(str(row["hora_salida_programada"]))
        duracion = (
            (salida - entrada) + pd.Timedelta(days=1)
            if row.get("cruza_medianoche")
            else salida - entrada
        )
        return str(duracion).split(" ")[-1]

    df["horas_esperadas"] = df.apply(calcular_horas_esperadas, axis=1)

    # --- Analizar Retardos (LÓGICA CORREGIDA) ---
    print("   - Calculando retardos y puntualidad con tolerancia de 15 minutos...")

    def analizar_retardo(row):
        if pd.isna(row.get("hora_entrada_programada")) or pd.isna(row.get("checado_1")):
            return pd.Series(["Sin Checada", 0])

        entrada_prog = pd.to_timedelta(str(row["hora_entrada_programada"]))
        checado = pd.to_timedelta(row["checado_1"])
        minutos_tarde = (checado - entrada_prog).total_seconds() / 60

        # Nueva lógica con 15 minutos de tolerancia
        if minutos_tarde <= 15:
            # Si llega antes, a tiempo, o dentro de los 15 min de tolerancia
            tipo = "A Tiempo"
        else:
            # Cualquier llegada después de los 15 minutos es un retardo
            tipo = "Retardo"

        return pd.Series([tipo, int(minutos_tarde)])

    df[["tipo_retardo", "minutos_tarde"]] = df.apply(
        analizar_retardo, axis=1, result_type="expand"
    )

    # --- Acumular Retardos para Descuento (LÓGICA CORREGIDA) ---
    print("   - Verificando acumulación de retardos para descuentos...")
    df = df.sort_values(by=["employee", "dia"]).reset_index(drop=True)
    # Ahora solo se cuenta si el tipo es "Retardo"
    df["es_retardo_acumulable"] = df["tipo_retardo"].isin(["Retardo"]).astype(int)
    df["retardos_acumulados"] = df.groupby("employee")["es_retardo_acumulable"].cumsum()

    df["descuento_por_3_retardos"] = df.apply(
        lambda row: (
            "Sí (3er retardo)"
            if row["es_retardo_acumulable"]
            and row["retardos_acumulados"] > 0
            and row["retardos_acumulados"] % 3 == 0
            else "No"
        ),
        axis=1,
    )

    print("✅ Análisis completado.")
    return df


# ==============================================================================
# SECCIÓN 4: EJECUCIÓN PRINCIPAL DEL SCRIPT
# ==============================================================================
if __name__ == "__main__":
    # Define aquí el rango de fechas y el dispositivo que quieres analizar
    start_date = "2025-06-01"
    end_date = "2025-06-15"
    device_filter = "%31%"

    # 1. Obtener datos de la API
    checkin_records = fetch_checkins(start_date, end_date, device_filter)

    if checkin_records:
        # 2. Crear el DataFrame base
        df_base = process_checkins_to_dataframe(checkin_records, start_date, end_date)

        # 3. Aplicar todo el análisis
        df_analizado = analizar_asistencia_y_horarios(df_base)

        # 4. Organizar las columnas para el reporte final
        checado_cols = sorted(
            [c for c in df_analizado.columns if "checado_" in c and c != "checado_1"]
        )
        column_order = [
            "employee",
            "Nombre",
            "dia",
            "dia_semana",
            "hora_entrada_programada",
            "checado_1",
            "minutos_tarde",
            "tipo_retardo",
            "horas_esperadas",
            "horas_trabajadas",
            "retardos_acumulados",
            "descuento_por_3_retardos",
        ] + checado_cols

        final_columns = [col for col in column_order if col in df_analizado.columns]
        df_final = df_analizado[final_columns].fillna("---")

        # 5. Guardar el reporte en un archivo CSV
        output_filename = "reporte_asistencia_analizado.csv"
        df_final.to_csv(output_filename, index=False, encoding="utf-8-sig")

        print(
            f"\n\n🎉 ¡Reporte finalizado! Los datos se han guardado en '{output_filename}'"
        )
        print("\n**Visualización de las primeras 15 filas del reporte:**\n")
        print(df_final.head(15).to_string())
