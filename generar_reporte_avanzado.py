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
    Consulta el horario programado para un empleado, obteniendo también la regla que se aplicó.
    """
    if conn is None or not conn.is_connected():
        return None

    try:
        es_primera_quincena = 1 if fecha.day <= 15 else 0
        dia_semana_id = fecha.isoweekday()  # Lunes=1, Domingo=7

        # SQL MODIFICADA: Ahora trae también el tipo de regla para validación posterior
        sql = """
        SELECT 
            COALESCE(H.hora_entrada, AH.hora_entrada_especifica) as hora_entrada, 
            COALESCE(H.hora_salida, AH.hora_salida_especifica) as hora_salida,
            COALESCE(H.cruza_medianoche, AH.hora_salida_especifica_cruza_medianoche, FALSE) AS cruza_medianoche,
            AH.dia_especifico_id,
            T.descripcion AS tipo_turno_descripcion
        FROM Empleados AS E
        LEFT JOIN AsignacionHorario AS AH ON E.empleado_id = AH.empleado_id
        LEFT JOIN Horario AS H ON AH.horario_id = H.horario_id
        LEFT JOIN TipoTurno AS T ON AH.tipo_turno_id = T.tipo_turno_id
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


def dia_en_turno(dia_semana_iso, descripcion_turno):
    """
    Función auxiliar para verificar si un día pertenece a un turno descrito por texto (ej. 'L-V').
    """
    if not isinstance(descripcion_turno, str):
        return False

    descripcion_turno = descripcion_turno.upper().replace(" ", "")
    dias_map = {"L": 1, "M": 2, "X": 3, "J": 4, "V": 5, "S": 6, "D": 7}

    # Revisa rangos como L-V
    match = re.search(r"([LMXJVSD])-([LMXJVSD])", descripcion_turno)
    if match:
        start_day_char, end_day_char = match.groups()
        start_day_iso = dias_map.get(start_day_char)
        end_day_iso = dias_map.get(end_day_char)
        if start_day_iso is not None and end_day_iso is not None:
            if start_day_iso <= dia_semana_iso <= end_day_iso:
                return True

    # Revisa letras individuales o separadas por coma
    turno_dias_iso = set()
    for char, iso_val in dias_map.items():
        if char in descripcion_turno:
            turno_dias_iso.add(iso_val)

    return dia_semana_iso in turno_dias_iso


def analizar_asistencia_y_horarios(df: pd.DataFrame):
    """Función principal que enriquece el DataFrame con análisis de horarios y retardos."""
    if df.empty:
        return df
    print("\n🔄 Iniciando análisis de horarios y retardos...")

    db_conn = connect_db()

    print(
        "   - Consultando horarios programados en la base de datos (esto puede tardar)..."
    )
    horarios_data_raw = df.apply(
        lambda row: query_horario_programado(
            row["employee"], pd.to_datetime(row["dia"]).to_pydatetime(), db_conn
        ),
        axis=1,
    )

    if db_conn and db_conn.is_connected():
        db_conn.close()
        print("   - Conexión a la base de datos cerrada.")

    print("   - Validando reglas de turno para días de descanso...")
    df["dia_iso"] = pd.to_datetime(df["dia"]).dt.weekday + 1

    def validar_horario_aplicable(horario_info, dia_iso):
        if not isinstance(horario_info, dict):
            return None

        if pd.notna(horario_info.get("dia_especifico_id")):
            return horario_info

        descripcion = horario_info.get("tipo_turno_descripcion")
        if dia_en_turno(dia_iso, descripcion):
            return horario_info
        else:
            return None

    horarios_data_validado = [
        validar_horario_aplicable(info, dia)
        for info, dia in zip(horarios_data_raw, df["dia_iso"])
    ]

    df_horarios = pd.json_normalize(horarios_data_validado).rename(
        columns={
            "hora_entrada": "hora_entrada_programada",
            "hora_salida": "hora_salida_programada",
        }
    )
    df = pd.concat([df.reset_index(drop=True), df_horarios], axis=1)

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

    print("   - Calculando retardos y puntualidad con tolerancia de 15 minutos...")

    def analizar_retardo(row):
        if pd.isna(row.get("hora_entrada_programada")):
            return pd.Series(["Día no Laborable", 0])

        if pd.isna(row.get("checado_1")):
            return pd.Series(["Falta", 0])

        entrada_prog = pd.to_timedelta(str(row["hora_entrada_programada"]))
        checado = pd.to_timedelta(row["checado_1"])
        minutos_tarde = (checado - entrada_prog).total_seconds() / 60

        if minutos_tarde <= 15:
            tipo = "A Tiempo"
        else:
            tipo = "Retardo"

        return pd.Series([tipo, int(minutos_tarde)])

    df[["tipo_retardo", "minutos_tarde"]] = df.apply(
        analizar_retardo, axis=1, result_type="expand"
    )

    print("   - Verificando acumulación de retardos y faltas para descuentos...")
    df = df.sort_values(by=["employee", "dia"]).reset_index(drop=True)
    df["es_retardo_acumulable"] = (df["tipo_retardo"] == "Retardo").astype(int)
    df["es_falta"] = (df["tipo_retardo"] == "Falta").astype(int)  # NUEVA LÍNEA
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
# SECCIÓN 4: FUNCIÓN PARA GENERAR RESUMEN
# ==============================================================================
def generar_resumen_periodo(df: pd.DataFrame):
    """
    Crea un DataFrame de resumen con totales por empleado, incluyendo faltas, y
    calcula la diferencia entre horas trabajadas y esperadas.
    """
    print("\n📊 Generando resumen del periodo con cálculo de diferencia de horas...")
    if df.empty:
        print("   - No hay datos para generar el resumen.")
        return

    df["horas_trabajadas_td"] = pd.to_timedelta(
        df["horas_trabajadas"].fillna("00:00:00")
    )
    df["horas_esperadas_td"] = pd.to_timedelta(df["horas_esperadas"].fillna("00:00:00"))

    # AGREGACIÓN ACTUALIZADA: Se añade la suma de 'es_falta'
    resumen_final = (
        df.groupby(["employee", "Nombre"])
        .agg(
            total_horas_trabajadas=("horas_trabajadas_td", "sum"),
            total_horas_esperadas=("horas_esperadas_td", "sum"),
            total_retardos=("es_retardo_acumulable", "sum"),
            total_faltas=("es_falta", "sum"),  # NUEVA LÍNEA
        )
        .reset_index()
    )

    diferencia_td = (
        resumen_final["total_horas_trabajadas"] - resumen_final["total_horas_esperadas"]
    )

    resumen_final["diferencia_segundos"] = diferencia_td.dt.total_seconds().astype(int)

    def format_timedelta_with_sign(td):
        sign = "-" if td.total_seconds() < 0 else ""
        td_abs = abs(td)
        total_seconds = int(td_abs.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{sign}{hours:02}:{minutes:02}:{seconds:02}"

    def format_positive_timedelta(td):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"

    resumen_final["diferencia_HHMMSS"] = diferencia_td.apply(format_timedelta_with_sign)
    resumen_final["total_horas_trabajadas"] = resumen_final[
        "total_horas_trabajadas"
    ].apply(format_positive_timedelta)
    resumen_final["total_horas_esperadas"] = resumen_final[
        "total_horas_esperadas"
    ].apply(format_positive_timedelta)

    # ORDEN DE COLUMNAS ACTUALIZADO
    resumen_final = resumen_final[
        [
            "employee",
            "Nombre",
            "total_horas_trabajadas",
            "total_horas_esperadas",
            "total_retardos",
            "total_faltas",
            "diferencia_segundos",
            "diferencia_HHMMSS",
        ]
    ]

    output_filename = "resumen_periodo.csv"
    resumen_final.to_csv(output_filename, index=False, encoding="utf-8-sig")

    print(f"✅ Resumen del periodo guardado en '{output_filename}'")
    print("\n**Visualización del Resumen del Periodo (Corregido):**\n")
    print(resumen_final.to_string())


# ==============================================================================
# SECCIÓN 5: EJECUCIÓN PRINCIPAL DEL SCRIPT
# ==============================================================================
if __name__ == "__main__":
    # Define aquí el rango de fechas y el dispositivo que quieres analizar
    start_date = "2025-06-01"
    end_date = "2025-06-15"
    device_filter = "%villas%"

    # 1. Obtener datos de la API
    checkin_records = fetch_checkins(start_date, end_date, device_filter)

    if checkin_records:
        # 2. Crear el DataFrame base
        df_base = process_checkins_to_dataframe(checkin_records, start_date, end_date)

        # 3. Aplicar todo el análisis diario
        df_analizado = analizar_asistencia_y_horarios(df_base)

        # 4. Organizar y guardar el reporte detallado
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

        output_filename_detallado = "reporte_asistencia_analizado.csv"
        df_final.to_csv(output_filename_detallado, index=False, encoding="utf-8-sig")

        print(
            f"\n\n🎉 ¡Reporte detallado finalizado! Los datos se han guardado en '{output_filename_detallado}'"
        )
        print("\n**Visualización de las primeras 15 filas del reporte detallado:**\n")
        print(df_final.head(15).to_string())

        # 5. Generar y guardar el nuevo reporte de resumen
        generar_resumen_periodo(df_analizado)
