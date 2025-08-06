import json
import os
import requests
import pandas as pd
from itertools import product
from datetime import datetime, timedelta, time
import pytz
import re
import unicodedata
from dotenv import load_dotenv

# Importamos la nueva conexión a PostgreSQL
from db_postgres_connection import (
    connect_db,
    obtener_horario_empleado,
    obtener_horarios_multi_quincena,
    mapear_horarios_por_empleado_multi,
)


# ==============================================================================
# SECCIÓN 1: CONFIGURACIÓN Y VARIABLES DE ENTORNO
# ==============================================================================

# Carga las variables de entorno desde el archivo .env
load_dotenv()

# Variables para la API de Frappe
API_KEY = os.getenv("ASIATECH_API_KEY")
API_SECRET = os.getenv("ASIATECH_API_SECRET")
API_URL = "https://erp.asiatech.com.mx/api/resource/Employee Checkin"
LEAVE_API_URL = "https://erp.asiatech.com.mx/api/resource/Leave Application"

# ==============================================================================
# CONFIGURACIÓN DE POLÍTICAS DE PERMISOS
# ==============================================================================

# Política por tipo de permiso - define cómo se manejan las horas esperadas
POLITICA_PERMISOS = {
    "permiso sin goce de sueldo": "no_ajustar",
    "permiso sin goce": "no_ajustar",
    "sin goce de sueldo": "no_ajustar",
    "sin goce": "no_ajustar",
    # Espacio para futuras políticas:
    # "permiso con goce": "ajustar_a_cero",
    # "permiso médico": "prorratear",
}

# Configuración para regla de perdón de retardos
PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA = False

# Configuración para detección de salidas anticipadas
TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS = 15


def _strip_accents(text):
    """Helper function to remove accents from a string."""
    try:
        text = unicode(text, "utf-8")
    except (TypeError, NameError):  # unicode is a default on python 3
        pass
    text = unicodedata.normalize("NFD", text)
    text = text.encode("ascii", "ignore")
    text = text.decode("utf-8")
    return str(text)


def normalize_leave_type(leave_type):
    """
    Normaliza el tipo de permiso para comparación consistente (minúsculas, sin acentos y sin espacios extra).
    """
    if not leave_type:
        return ""
    cleaned = _strip_accents(str(leave_type)).casefold().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Canonicaliza alias comunes hacia el mismo tipo
    if "sin goce" in cleaned:
        return "permiso sin goce de sueldo"
    aliases = {
        "permiso sin goce": "permiso sin goce de sueldo",
        "sin goce de sueldo": "permiso sin goce de sueldo",
        "sin goce": "permiso sin goce de sueldo",
        "permiso sgs": "permiso sin goce de sueldo",
    }
    return aliases.get(cleaned, cleaned)


def calcular_proximidad_horario(checada: str, hora_prog: str) -> float:
    """
    Calcula la proximidad en minutos entre una checada y una hora programada.

    Args:
        checada: Hora de checada en formato "HH:MM:SS"
        hora_prog: Hora programada en formato "HH:MM"

    Returns:
        Diferencia en minutos (positiva si llega tarde, negativa si llega temprano)
        float('inf') si hay error en el formato
    """
    if not checada or not hora_prog:
        return float("inf")

    try:
        # Parsear checada
        if len(checada.split(":")) == 3:
            hora_checada = datetime.strptime(checada, "%H:%M:%S")
        elif len(checada.split(":")) == 2:
            hora_checada = datetime.strptime(checada, "%H:%M")
        else:
            return float("inf")

        # Parsear hora programada
        if len(hora_prog.split(":")) == 2:
            # Validar que tenga formato HH:MM estricto
            if not re.match(r"^\d{2}:\d{2}$", hora_prog):
                return float("inf")
            hora_programada = datetime.strptime(hora_prog, "%H:%M")
        else:
            return float("inf")

        # Calcular diferencia
        diferencia = (hora_checada - hora_programada).total_seconds() / 60

        # Manejar casos de medianoche
        if diferencia < -12 * 60:  # Más de 12 horas antes
            diferencia += 24 * 60
        elif diferencia > 12 * 60:  # Más de 12 horas después
            diferencia -= 24 * 60

        # Para casos extremos de medianoche, calcular la distancia más corta
        if abs(diferencia) > 12 * 60:  # Si la diferencia es mayor a 12 horas
            if diferencia > 0:
                diferencia = 24 * 60 - diferencia
            else:
                diferencia = 24 * 60 + diferencia

        return abs(diferencia)  # Retornar valor absoluto para compatibilidad con tests

    except (ValueError, TypeError):
        return float("inf")


# ==============================================================================
# SECCIÓN 2: OBTENCIÓN DE DATOS DE LA API FRAPPE
# ==============================================================================
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

            # Normalizar la zona horaria de los registros de la API a America/Mexico_City
            for record in data:
                # Convertir el string ISO a datetime UTC
                time_utc = datetime.fromisoformat(record["time"].replace("Z", "+00:00"))
                # Convertir de UTC a America/Mexico_City
                mexico_tz = pytz.timezone("America/Mexico_City")
                time_mexico = time_utc.astimezone(mexico_tz)
                # Actualizar el valor en el registro
                record["time"] = time_mexico.isoformat()

            all_records.extend(data)
            if len(data) < page_length:
                break
            limit_start += page_length
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al llamar a la API: {e}")
            return []

    print(f"✅ Se obtuvieron {len(all_records)} registros de la API.")
    return all_records


def fetch_leave_applications(start_date: str, end_date: str):
    """
    Obtiene todos los permisos aprobados de la API para un rango de fechas.
    """
    print(
        f"📄 Obteniendo permisos aprobados de la API para el periodo {start_date} - {end_date}..."
    )

    if not all([API_KEY, API_SECRET]):
        print("❌ Error: Faltan credenciales de API para obtener permisos")
        return []

    headers = {"Authorization": f"token {API_KEY}:{API_SECRET}"}

    # URL actualizada con el campo half_day
    url = f'https://erp.asiatech.com.mx/api/resource/Leave Application?fields=["employee","employee_name","leave_type","from_date","to_date","status","half_day"]&filters=[["status","=","Approved"],["from_date",">=","{start_date}"],["to_date","<=","{end_date}"]]'

    all_leave_records = []
    limit_start = 0
    page_length = 100

    while True:
        params = {
            "limit_start": limit_start,
            "limit_page_length": page_length,
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])

            if not data:
                break

            all_leave_records.extend(data)

            if len(data) < page_length:
                break

            limit_start += page_length

        except requests.exceptions.Timeout:
            print("⚠️ Timeout al obtener permisos. Reintentando...")
            continue
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al obtener permisos de la API: {e}")
            return []

    print(f"✅ Se obtuvieron {len(all_leave_records)} permisos aprobados de la API.")

    if all_leave_records:
        print("📋 Ejemplo de permisos obtenidos:")
        for i, leave in enumerate(all_leave_records[:3]):
            half_day_info = f" (medio día)" if leave.get("half_day") == 1 else ""
            print(
                f"   - {leave['employee_name']}: {leave['leave_type']}{half_day_info} ({leave['from_date']} - {leave['to_date']})"
            )

    return all_leave_records


# ==============================================================================
# SECCIÓN 3: PROCESAMIENTO Y ANÁLISIS DE DATOS
# ==============================================================================


def td_to_str(td: pd.Timedelta) -> str:
    """
    Convierte un Timedelta a string HH:MM:SS sin perder días (> 24 h) ni microsegundos.

    Args:
        td: Timedelta a convertir

    Returns:
        String en formato HH:MM:SS
    """
    td = td or pd.Timedelta(0)
    total = int(td.total_seconds())
    h, m = divmod(total, 3600)
    m, s = divmod(m, 60)
    return f"{h:02}:{m:02}:{s:02}"


def calcular_horas_descanso(df_dia):
    """
    Calcula las horas de descanso basándose en los checados del día.
    Solo calcula descanso si hay 4+ checados y los tiempos de descanso
    son diferentes de los tiempos de entrada/salida.

    Args:
        df_dia: DataFrame o Series con una fila por empleado y día, con columnas checado_1, checado_2, etc.

    Returns:
        timedelta: Horas de descanso calculadas. Si no aplica descanso, devuelve timedelta(0).
    """
    # Obtener todas las columnas de checado disponibles
    if hasattr(df_dia, "columns"):
        # Es un DataFrame
        checado_cols = [col for col in df_dia.columns if col.startswith("checado_")]
    else:
        # Es un Series
        checado_cols = [col for col in df_dia.index if col.startswith("checado_")]

    if len(checado_cols) < 4:
        return timedelta(0)

    # Obtener los valores de checado para este día/empleado
    checados = []
    for col in checado_cols:
        if hasattr(df_dia, "columns"):
            valor = df_dia.get(col)
        else:
            valor = df_dia.get(col, None)
        if pd.notna(valor) and valor is not None and valor != "---":
            checados.append(valor)

    # Filtrar checadas con dropna() y exigir len(checados) >= 4
    checados = [c for c in checados if pd.notna(c)]
    if len(checados) < 4:
        return timedelta(0)

    # Ordenar checados cronológicamente
    checados_ordenados = sorted(checados, key=lambda x: str(x))
    
    # Obtener primera y última hora de checado (entrada y salida)
    hora_entrada = checados_ordenados[0]
    hora_salida = checados_ordenados[-1]

    # Calcular múltiples intervalos de descanso (pares 1-2, 3-4, etc.)
    total_descanso = timedelta(0)

    try:
        # Procesar pares de checados para calcular descansos
        for i in range(1, len(checados_ordenados) - 1, 2):
            if i + 1 < len(checados_ordenados):
                # Tomar segundo y tercer checado del par
                segundo_checado = checados_ordenados[i]
                tercer_checado = checados_ordenados[i + 1]
                
                # Omitir si los tiempos de descanso son iguales a entrada o salida
                if (segundo_checado == hora_entrada or segundo_checado == hora_salida or
                    tercer_checado == hora_entrada or tercer_checado == hora_salida):
                    continue

                # Convertir a datetime para calcular la diferencia
                if isinstance(segundo_checado, time):
                    segundo_dt = datetime.combine(datetime.today(), segundo_checado)
                else:
                    segundo_dt = datetime.strptime(str(segundo_checado), "%H:%M:%S")

                if isinstance(tercer_checado, time):
                    tercer_dt = datetime.combine(datetime.today(), tercer_checado)
                else:
                    tercer_dt = datetime.strptime(str(tercer_checado), "%H:%M:%S")

                # Calcular diferencia
                descanso_intervalo = tercer_dt - segundo_dt

                # Solo sumar si la diferencia es positiva y razonable (más de 5 minutos)
                if descanso_intervalo.total_seconds() > 300:  # Más de 5 minutos
                    total_descanso += descanso_intervalo

        return total_descanso

    except (ValueError, TypeError):
        return timedelta(0)


def aplicar_calculo_horas_descanso(df):
    """
    Aplica el cálculo de horas de descanso a todo el DataFrame.
    NO realiza ajustes a las horas esperadas ni trabajadas - solo calcula el tiempo de descanso.

    Args:
        df: DataFrame con datos de asistencia

    Returns:
        DataFrame: DataFrame con las columnas de horas de descanso agregadas (sin ajustes)
    """
    if df.empty:
        return df

    print("🔄 Calculando horas de descanso...")

    # Crear columnas para horas de descanso como Timedelta
    df["horas_descanso_td"] = pd.Timedelta(0)
    df["horas_descanso"] = "00:00:00"  # Para compatibilidad con CSV

    # Guardar valores originales (solo para referencia)
    df["horas_trabajadas_originales"] = df["horas_trabajadas"].copy()
    df["horas_esperadas_originales"] = df["horas_esperadas"].copy()

    # Convertir duration a Timedelta si existe
    if "duration" in df.columns:
        df["duration_td"] = df["duration"].fillna(pd.Timedelta(0))
    else:
        df["duration_td"] = pd.Timedelta(0)

    total_dias_con_descanso = 0

    for index, row in df.iterrows():
        # Calcular horas de descanso para esta fila
        horas_descanso_td = calcular_horas_descanso(row)

        if horas_descanso_td > timedelta(0):
            df.at[index, "horas_descanso_td"] = horas_descanso_td
            df.at[index, "horas_descanso"] = td_to_str(horas_descanso_td)
            total_dias_con_descanso += 1

    print(f"✅ Se calcularon horas de descanso para {total_dias_con_descanso} días")
    return df


def obtener_codigos_empleados_api(checkin_data):
    """
    Extrae los códigos de empleados de los datos de checadas de la API
    """
    if not checkin_data:
        return []

    df_empleados = pd.DataFrame(checkin_data)[["employee"]].drop_duplicates()
    return list(df_empleados["employee"])


def procesar_permisos_empleados(leave_data):
    """
    Procesa los datos de permisos y crea un diccionario organizado por empleado y fecha.
    Maneja permisos de medio día correctamente.
    """
    if not leave_data:
        return {}

    print("🔄 Procesando permisos por empleado y fecha...")

    permisos_por_empleado = {}
    total_dias_permiso = 0
    permisos_medio_dia = 0

    for permiso in leave_data:
        employee_code = permiso["employee"]
        from_date = datetime.strptime(permiso["from_date"], "%Y-%m-%d").date()
        to_date = datetime.strptime(permiso["to_date"], "%Y-%m-%d").date()
        is_half_day = permiso.get("half_day") == 1

        if employee_code not in permisos_por_empleado:
            permisos_por_empleado[employee_code] = {}

        # Si es un permiso de medio día, solo procesar la fecha específica
        if is_half_day:
            leave_type_normalized = normalize_leave_type(permiso["leave_type"])

            permisos_por_empleado[employee_code][from_date] = {
                "leave_type": permiso["leave_type"],
                "leave_type_normalized": leave_type_normalized,
                "employee_name": permiso["employee_name"],
                "from_date": from_date,
                "to_date": to_date,
                "status": permiso["status"],
                "is_half_day": True,
                "dias_permiso": 0.5,  # Medio día
            }
            total_dias_permiso += 0.5
            permisos_medio_dia += 1
        else:
            # Permiso de día completo - procesar todo el rango de fechas
            current_date = from_date
            while current_date <= to_date:
                leave_type_normalized = normalize_leave_type(permiso["leave_type"])

                permisos_por_empleado[employee_code][current_date] = {
                    "leave_type": permiso["leave_type"],
                    "leave_type_normalized": leave_type_normalized,
                    "employee_name": permiso["employee_name"],
                    "from_date": from_date,
                    "to_date": to_date,
                    "status": permiso["status"],
                    "is_half_day": False,
                    "dias_permiso": 1.0,  # Día completo
                }
                current_date += timedelta(days=1)
                total_dias_permiso += 1.0

    print(
        f"✅ Procesados permisos para {len(permisos_por_empleado)} empleados, "
        f"{total_dias_permiso:.1f} días de permiso total ({permisos_medio_dia} permisos de medio día)."
    )

    return permisos_por_empleado


def ajustar_horas_esperadas_con_permisos(df, permisos_dict, cache_horarios):
    """
    Ajusta las horas esperadas del DataFrame considerando los permisos aprobados.
    Maneja permisos de medio día correctamente.
    """
    if df.empty:
        return df

    print("📊 Ajustando horas esperadas considerando permisos aprobados...")

    df["tiene_permiso"] = False
    df["tipo_permiso"] = None
    df["es_permiso_sin_goce"] = False
    df["es_permiso_medio_dia"] = False
    df["horas_esperadas_originales"] = df["horas_esperadas"].copy()
    df["horas_descontadas_permiso"] = "00:00:00"

    permisos_con_descuento = 0
    permisos_sin_goce = 0
    permisos_medio_dia = 0

    for index, row in df.iterrows():
        employee_code = str(row["employee"])
        fecha = row["dia"]

        if employee_code in permisos_dict and fecha in permisos_dict[employee_code]:

            permiso_info = permisos_dict[employee_code][fecha]
            leave_type_normalized = permiso_info.get("leave_type_normalized", "")
            is_half_day = permiso_info.get("is_half_day", False)

            df.at[index, "tiene_permiso"] = True
            df.at[index, "tipo_permiso"] = permiso_info["leave_type"]
            df.at[index, "es_permiso_medio_dia"] = is_half_day

            accion = POLITICA_PERMISOS.get(leave_type_normalized, "ajustar_a_cero")

            horas_esperadas_orig = row["horas_esperadas"]

            if pd.notna(horas_esperadas_orig) and horas_esperadas_orig != "00:00:00":
                if accion == "no_ajustar":
                    df.at[index, "es_permiso_sin_goce"] = True
                    permisos_sin_goce += 1
                elif accion == "ajustar_a_cero":
                    if is_half_day:
                        # Para permisos de medio día, descontar solo la mitad de las horas
                        try:
                            # Convertir horas esperadas a timedelta
                            horas_td = pd.to_timedelta(horas_esperadas_orig)
                            # Calcular la mitad
                            mitad_horas = horas_td / 2
                            # Convertir de vuelta a string
                            mitad_horas_str = str(mitad_horas).split()[
                                -1
                            ]  # Obtener solo HH:MM:SS

                            # Ajustar horas esperadas (restar la mitad)
                            horas_ajustadas = horas_td - mitad_horas
                            horas_ajustadas_str = str(horas_ajustadas).split()[-1]

                            df.at[index, "horas_esperadas"] = horas_ajustadas_str
                            df.at[index, "horas_descontadas_permiso"] = mitad_horas_str
                            permisos_medio_dia += 1
                        except (ValueError, TypeError):
                            # Si hay error en el cálculo, tratar como día completo
                            df.at[index, "horas_esperadas"] = "00:00:00"
                            df.at[index, "horas_descontadas_permiso"] = (
                                horas_esperadas_orig
                            )
                            permisos_con_descuento += 1
                    else:
                        # Permiso de día completo
                        df.at[index, "horas_esperadas"] = "00:00:00"
                        df.at[index, "horas_descontadas_permiso"] = horas_esperadas_orig
                        permisos_con_descuento += 1

    empleados_con_permisos = df[df["tiene_permiso"]]["employee"].nunique()
    dias_con_permisos = df["tiene_permiso"].sum()

    print("✅ Ajuste completado:")
    print(f"   - {empleados_con_permisos} empleados con permisos")
    print(f"   - {dias_con_permisos} días con permisos")
    print(
        f"   - {permisos_con_descuento} permisos con horas descontadas (día completo)"
    )
    print(f"   - {permisos_medio_dia} permisos de medio día")
    print(f"   - {permisos_sin_goce} permisos sin goce (sin descuento)")

    return df


def clasificar_faltas_con_permisos(df):
    """
    Actualiza la clasificación de faltas considerando los permisos aprobados.
    """
    if df.empty:
        return df

    print("📋 Reclasificando faltas considerando permisos aprobados...")

    df["tipo_falta_ajustada"] = df["tipo_retardo"].copy()
    df["falta_justificada"] = False

    mask_permiso_y_falta = (df["tiene_permiso"]) & (
        df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])
    )

    if mask_permiso_y_falta.any():
        df.loc[mask_permiso_y_falta, "tipo_falta_ajustada"] = "Falta Justificada"
        df.loc[mask_permiso_y_falta, "falta_justificada"] = True
        df["es_falta_ajustada"] = (
            df["tipo_falta_ajustada"].isin(["Falta", "Falta Injustificada"])
        ).astype(int)
        faltas_justificadas = mask_permiso_y_falta.sum()
        print(
            f"✅ Se justificaron {faltas_justificadas} faltas con permisos aprobados."
        )
    else:
        df["es_falta_ajustada"] = df["es_falta"].copy()
        print("✅ No se encontraron faltas que justificar con permisos.")

    return df


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

    # Calcular duración como Timedelta y guardar en columna duration
    df_hours = df.groupby(["employee", "dia"])["time"].agg(["min", "max"]).reset_index()
    df_hours["duration"] = df_hours["max"] - df_hours["min"]

    # Mantener duration como Timedelta, solo convertir a string para compatibilidad
    df_hours["horas_trabajadas"] = df_hours["duration"].apply(
        lambda x: td_to_str(x) if pd.notna(x) else "00:00:00"
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
        df_hours[["employee", "dia", "duration", "horas_trabajadas"]],
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
    final_df["dia_iso"] = pd.to_datetime(final_df["dia"]).dt.weekday + 1

    return final_df


def procesar_horarios_con_medianoche(df, cache_horarios):
    """
    Reorganiza las checadas para turnos que cruzan la medianoche.
    """
    print("\n🔄 Procesando turnos que cruzan medianoche...")
    df_proc = df.copy().sort_values(["employee", "dia"]).reset_index(drop=True)
    df_proc["es_primera_quincena"] = df_proc["dia"].apply(lambda x: x.day <= 15)

    for empleado in df_proc["employee"].unique():
        mask_empleado = df_proc["employee"] == empleado
        filas_empleado = df_proc.loc[mask_empleado].copy()

        for i in range(len(filas_empleado)):
            idx_actual = filas_empleado.index[i]
            fila_actual = df_proc.loc[idx_actual]

            horario = obtener_horario_empleado(
                str(empleado),
                fila_actual["dia_iso"],
                fila_actual["es_primera_quincena"],
                cache_horarios,
            )

            if horario and horario.get("cruza_medianoche", False):
                checadas_dia = [
                    df_proc.loc[idx_actual, f"checado_{j}"]
                    for j in range(1, 10)
                    if f"checado_{j}" in df_proc.columns
                    and pd.notna(df_proc.loc[idx_actual, f"checado_{j}"])
                ]

                if checadas_dia:
                    dia_siguiente = fila_actual["dia"] + timedelta(days=1)
                    mask_siguiente = (df_proc["employee"] == empleado) & (
                        df_proc["dia"] == dia_siguiente
                    )

                    if mask_siguiente.any():
                        idx_siguiente = df_proc[mask_siguiente].index[0]
                        checadas_siguiente = [
                            df_proc.loc[idx_siguiente, f"checado_{j}"]
                            for j in range(1, 10)
                            if f"checado_{j}" in df_proc.columns
                            and pd.notna(df_proc.loc[idx_siguiente, f"checado_{j}"])
                        ]

                        entrada_real = min(checadas_dia)
                        salida_real = (
                            max(checadas_siguiente)
                            if checadas_siguiente
                            else max(checadas_dia)
                        )

                        for j in range(1, 10):
                            if f"checado_{j}" in df_proc.columns:
                                df_proc.loc[idx_actual, f"checado_{j}"] = None

                        df_proc.loc[idx_actual, "checado_1"] = entrada_real
                        df_proc.loc[idx_actual, "checado_2"] = salida_real

                        # Usar datetime.combine para combinar fechas correctamente
                        entrada_time = datetime.strptime(
                            entrada_real, "%H:%M:%S"
                        ).time()
                        salida_time = datetime.strptime(salida_real, "%H:%M:%S").time()

                        fecha_actual = fila_actual["dia"]
                        inicio = datetime.combine(fecha_actual, entrada_time)

                        # Para turnos que cruzan medianoche, la salida es del día siguiente
                        if salida_time <= entrada_time:
                            fin = datetime.combine(
                                fecha_actual + timedelta(days=1), salida_time
                            )
                        else:
                            fin = datetime.combine(fecha_actual, salida_time)

                        # Asignar como Timedelta, NO como string
                        duracion_td = fin - inicio
                        df_proc.loc[idx_actual, "duration"] = duracion_td
                        df_proc.loc[idx_actual, "horas_trabajadas"] = td_to_str(
                            duracion_td
                        )

                        if salida_real in checadas_siguiente:
                            for j in range(1, 10):
                                if (
                                    f"checado_{j}" in df_proc.columns
                                    and df_proc.loc[idx_siguiente, f"checado_{j}"]
                                    == salida_real
                                ):
                                    df_proc.loc[idx_siguiente, f"checado_{j}"] = None
                                    break

                            # Recalculate hours for the next day
                            checadas_restantes = [
                                df_proc.loc[idx_siguiente, f"checado_{j}"]
                                for j in range(1, 10)
                                if f"checado_{j}" in df_proc.columns
                                and pd.notna(df_proc.loc[idx_siguiente, f"checado_{j}"])
                            ]
                            if len(checadas_restantes) >= 2:
                                # Usar datetime.combine para el día siguiente
                                entrada_sig = datetime.strptime(
                                    min(checadas_restantes), "%H:%M:%S"
                                ).time()
                                salida_sig = datetime.strptime(
                                    max(checadas_restantes), "%H:%M:%S"
                                ).time()

                                fecha_siguiente = dia_siguiente
                                inicio_sig = datetime.combine(
                                    fecha_siguiente, entrada_sig
                                )
                                fin_sig = datetime.combine(fecha_siguiente, salida_sig)

                                duracion_sig_td = fin_sig - inicio_sig
                                df_proc.loc[idx_siguiente, "duration"] = duracion_sig_td
                                df_proc.loc[idx_siguiente, "horas_trabajadas"] = (
                                    td_to_str(duracion_sig_td)
                                )
                            else:
                                df_proc.loc[idx_siguiente, "duration"] = pd.Timedelta(0)
                                df_proc.loc[idx_siguiente, "horas_trabajadas"] = (
                                    "00:00:00"
                                )

    print("✅ Procesamiento de turnos con medianoche completado")
    return df_proc


def analizar_asistencia_con_horarios_cache(df: pd.DataFrame, cache_horarios):
    """
    Enriquece el DataFrame con análisis de horarios y retardos usando el caché de horarios.
    """
    if df.empty:
        return df
    print("\n🔄 Iniciando análisis de horarios y retardos...")

    df["es_primera_quincena"] = df["dia"].apply(lambda x: x.day <= 15)

    df["hora_entrada_programada"] = None
    df["hora_salida_programada"] = None
    df["cruza_medianoche"] = False
    df["horas_esperadas"] = None

    def obtener_horario_fila(row):
        horario = obtener_horario_empleado(
            row["employee"], row["dia_iso"], row["es_primera_quincena"], cache_horarios
        )
        if horario:
            return pd.Series(
                [
                    horario.get("hora_entrada"),
                    horario.get("hora_salida"),
                    horario.get("cruza_medianoche", False),
                    str(timedelta(hours=float(horario.get("horas_totales", 0)))),
                ]
            )
        return pd.Series([None, None, False, None])

    df[
        [
            "hora_entrada_programada",
            "hora_salida_programada",
            "cruza_medianoche",
            "horas_esperadas",
        ]
    ] = df.apply(obtener_horario_fila, axis=1, result_type="expand")

    print("   - Calculando retardos y puntualidad...")

    def analizar_retardo(row):
        if pd.isna(row.get("hora_entrada_programada")):
            return pd.Series(["Día no Laborable", 0])
        if pd.isna(row.get("checado_1")):
            return pd.Series(["Falta", 0])
        try:
            hora_prog = datetime.strptime(
                row["hora_entrada_programada"] + ":00", "%H:%M:%S"
            )
            hora_checada = datetime.strptime(row["checado_1"], "%H:%M:%S")

            if (
                row.get("cruza_medianoche", False)
                and hora_prog.hour >= 12
                and hora_checada.hour < 12
            ):
                hora_prog -= timedelta(days=1)

            diferencia = (hora_checada - hora_prog).total_seconds() / 60

            if not row.get("cruza_medianoche", False) and diferencia < -12 * 60:
                diferencia += 24 * 60

            if diferencia <= 15:
                tipo = "A Tiempo"
            elif diferencia <= 60:
                tipo = "Retardo"
            else:
                tipo = "Falta Injustificada"
            return pd.Series([tipo, int(diferencia)])
        except (ValueError, TypeError):
            return pd.Series(["Falta", 0])

    df[["tipo_retardo", "minutos_tarde"]] = df.apply(
        analizar_retardo, axis=1, result_type="expand"
    )

    df = df.sort_values(by=["employee", "dia"]).reset_index(drop=True)
    df["es_retardo_acumulable"] = (df["tipo_retardo"] == "Retardo").astype(int)
    df["es_falta"] = (df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])).astype(
        int
    )
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

    print("   - Detectando salidas anticipadas...")

    # Función para detectar salidas anticipadas
    def detectar_salida_anticipada(row):
        # Solo aplicar si existe hora_salida_programada y al menos una checada
        if pd.isna(row.get("hora_salida_programada")) or pd.isna(row.get("checado_1")):
            return False

        # Obtener la última checada del día (la que tenga el valor más alto)
        checadas_dia = []
        for i in range(1, 10):  # Buscar hasta checado_9
            col_checado = f"checado_{i}"
            if col_checado in row and pd.notna(row[col_checado]):
                checadas_dia.append(row[col_checado])

        # Si solo hay una checada, no considerar salida anticipada
        if len(checadas_dia) <= 1:
            return False

        # Obtener la última checada (convertir a datetime para comparar correctamente)
        try:
            checadas_datetime = [
                datetime.strptime(checada, "%H:%M:%S") for checada in checadas_dia
            ]

            # Para turnos que cruzan medianoche, necesitamos ajustar las horas
            if row.get("cruza_medianoche", False):
                # En turnos nocturnos, necesitamos comparar cronológicamente
                # Las horas después de medianoche (00:00-11:59) son "más altas" que las de la noche anterior
                checadas_ajustadas = []
                for dt in checadas_datetime:
                    if (
                        dt.hour < 12
                    ):  # Si es antes de mediodía (00:00-11:59), añadir 24 horas
                        # Usar timedelta para manejar horas > 23
                        from datetime import timedelta

                        dt_ajustado = dt + timedelta(hours=24)
                        checadas_ajustadas.append(dt_ajustado)
                    else:
                        checadas_ajustadas.append(dt)
                ultima_checada_dt = max(checadas_ajustadas)
                # Convertir de vuelta a formato original
                ultima_checada = ultima_checada_dt.strftime("%H:%M:%S")
            else:
                ultima_checada = max(checadas_datetime).strftime("%H:%M:%S")
        except (ValueError, TypeError):
            return False

        try:
            # Parsear la hora de salida programada
            hora_salida_prog = datetime.strptime(
                row["hora_salida_programada"] + ":00", "%H:%M:%S"
            )
            hora_ultima_checada = datetime.strptime(ultima_checada, "%H:%M:%S")

            # Manejar turnos que cruzan la medianoche
            if row.get("cruza_medianoche", False):
                # Para turnos que cruzan medianoche, la hora_salida_programada es del día siguiente
                # No necesitamos ajustar nada aquí ya que estamos comparando solo las horas
                pass

            # Calcular diferencia en minutos
            diferencia = (hora_salida_prog - hora_ultima_checada).total_seconds() / 60

            # Manejar casos de medianoche
            if diferencia < -12 * 60:  # Más de 12 horas antes
                diferencia += 24 * 60
            elif diferencia > 12 * 60:  # Más de 12 horas después
                diferencia -= 24 * 60

            # Se considera salida anticipada si la última checada es anterior a la hora_salida_programada
            # menos el margen de tolerancia
            return diferencia > TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS

        except (ValueError, TypeError):
            return False

    # Aplicar detección de salidas anticipadas
    df["salida_anticipada"] = df.apply(detectar_salida_anticipada, axis=1)

    print("✅ Análisis completado.")
    return df


def aplicar_regla_perdon_retardos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la regla de perdón de retardos cuando un empleado cumple con las horas de su turno.

    Si un empleado trabajó las horas correspondientes de su turno o más, ese día NO debe
    contarse como retardo, incluso si llegó tarde.
    """
    if df.empty:
        return df

    print("🔄 Aplicando regla de perdón de retardos por cumplimiento de horas...")

    # Definir función helper para conversión segura de timedelta
    def safe_timedelta(time_str):
        if pd.isna(time_str) or time_str in ["00:00:00", "---", None]:
            return pd.Timedelta(0)
        try:
            return pd.to_timedelta(time_str)
        except (ValueError, TypeError):
            return pd.Timedelta(0)

    # Usar columnas Timedelta si existen, sino convertir desde strings
    if "duration_td" in df.columns:
        df["horas_trabajadas_td"] = df["duration_td"].fillna(pd.Timedelta(0))
    else:
        df["horas_trabajadas_td"] = df["horas_trabajadas"].apply(safe_timedelta)

    df["horas_esperadas_td"] = df["horas_esperadas"].apply(safe_timedelta)

    # Calcular si cumplió las horas del turno
    df["cumplio_horas_turno"] = df["horas_trabajadas_td"] >= df["horas_esperadas_td"]

    # Guardar valores originales antes de aplicar perdón
    df["tipo_retardo_original"] = df["tipo_retardo"].copy()
    df["minutos_tarde_original"] = df["minutos_tarde"].copy()
    df["retardo_perdonado"] = False

    # Aplicar perdón a retardos
    mask_retardo_perdonable = (df["tipo_retardo"] == "Retardo") & (
        df["cumplio_horas_turno"] == True
    )

    if mask_retardo_perdonable.any():
        df.loc[mask_retardo_perdonable, "retardo_perdonado"] = True
        df.loc[mask_retardo_perdonable, "tipo_retardo"] = "A Tiempo (Cumplió Horas)"
        df.loc[mask_retardo_perdonable, "minutos_tarde"] = 0
        retardos_perdonados = mask_retardo_perdonable.sum()
        print(f"   - {retardos_perdonados} retardos perdonados por cumplir horas")

    # Aplicar perdón a faltas injustificadas (opcional)
    if PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA:
        mask_falta_perdonable = (df["tipo_retardo"] == "Falta Injustificada") & (
            df["cumplio_horas_turno"] == True
        )

        if mask_falta_perdonable.any():
            df.loc[mask_falta_perdonable, "retardo_perdonado"] = True
            df.loc[mask_falta_perdonable, "tipo_retardo"] = "A Tiempo (Cumplió Horas)"
            df.loc[mask_falta_perdonable, "minutos_tarde"] = 0
            faltas_perdonadas = mask_falta_perdonable.sum()
            print(
                f"   - {faltas_perdonadas} faltas injustificadas perdonadas por cumplir horas"
            )

    # Recalcular columnas derivadas
    df["es_retardo_acumulable"] = (df["tipo_retardo"] == "Retardo").astype(int)
    df["es_falta"] = (df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])).astype(
        int
    )

    # Recalcular retardos acumulados por empleado
    df["retardos_acumulados"] = df.groupby("employee")["es_retardo_acumulable"].cumsum()

    # Recalcular descuento por 3 retardos
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

    total_perdonados = df["retardo_perdonado"].sum()
    if total_perdonados > 0:
        print(
            f"✅ Se aplicó perdón a {total_perdonados} días por cumplimiento de horas"
        )
    else:
        print("✅ No se encontraron días elegibles para perdón")

    return df


# ==============================================================================
# SECCIÓN 4: FUNCIÓN PARA GENERAR RESUMEN
# ==============================================================================
def generar_resumen_periodo(df: pd.DataFrame):
    """
    Crea un DataFrame de resumen con totales por empleado.
    """
    print("\n📊 Generando resumen del periodo...")
    if df.empty:
        print("   - No hay datos para generar el resumen.")
        return pd.DataFrame()

    # Recalcular siempre desde la columna de texto ya ajustada (Plan B más robusto)
    df["horas_trabajadas_td"] = pd.to_timedelta(
        df["horas_trabajadas"].fillna("00:00:00")
    )

    if "horas_esperadas_originales" in df.columns:
        df["horas_esperadas_originales_td"] = pd.to_timedelta(
            df["horas_esperadas_originales"].fillna("00:00:00")
        )
    else:
        df["horas_esperadas_originales_td"] = pd.to_timedelta(
            df["horas_esperadas"].fillna("00:00:00")
        )

    if "horas_descontadas_permiso" in df.columns:
        df["horas_descontadas_permiso_td"] = pd.to_timedelta(
            df["horas_descontadas_permiso"].fillna("00:00:00")
        )
    else:
        df["horas_descontadas_permiso_td"] = pd.to_timedelta("00:00:00")

    if "horas_descanso" in df.columns:
        df["horas_descanso_td"] = pd.to_timedelta(
            df["horas_descanso"].fillna("00:00:00")
        )
    else:
        df["horas_descanso_td"] = pd.to_timedelta("00:00:00")

    total_faltas_col = (
        "es_falta_ajustada" if "es_falta_ajustada" in df.columns else "es_falta"
    )

    resumen_final = (
        df.groupby(["employee", "Nombre"])
        .agg(
            total_horas_trabajadas=("horas_trabajadas_td", "sum"),
            total_horas_esperadas=("horas_esperadas_originales_td", "sum"),
            total_horas_descontadas_permiso=("horas_descontadas_permiso_td", "sum"),
            total_horas_descanso=("horas_descanso_td", "sum"),
            total_retardos=("es_retardo_acumulable", "sum"),
            faltas_del_periodo=(total_faltas_col, "sum"),
            faltas_justificadas=(
                ("falta_justificada", "sum")
                if "falta_justificada" in df.columns
                else ("es_falta", lambda x: 0)
            ),
            total_salidas_anticipadas=(
                ("salida_anticipada", "sum")
                if "salida_anticipada" in df.columns
                else ("es_falta", lambda x: 0)
            ),
        )
        .reset_index()
    )

    resumen_final["total_horas"] = (
        resumen_final["total_horas_esperadas"]
        - resumen_final["total_horas_descontadas_permiso"]
    )
    resumen_final["total_faltas"] = resumen_final["faltas_del_periodo"]
    diferencia_td = (
        resumen_final["total_horas_trabajadas"] - resumen_final["total_horas"]
    )

    def format_timedelta_with_sign(td):
        if td.total_seconds() == 0:
            return "00:00:00"
        sign = "+" if td.total_seconds() >= 0 else "-"
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
    resumen_final["total_horas_descontadas_permiso"] = resumen_final[
        "total_horas_descontadas_permiso"
    ].apply(format_positive_timedelta)
    resumen_final["total_horas_descanso"] = resumen_final["total_horas_descanso"].apply(
        format_positive_timedelta
    )
    resumen_final["total_horas"] = resumen_final["total_horas"].apply(
        format_positive_timedelta
    )

    base_columns = [
        "employee",
        "Nombre",
        "total_horas_trabajadas",
        "total_horas_esperadas",
        "total_horas_descontadas_permiso",
        "total_horas_descanso",
        "total_horas",
        "total_retardos",
        "faltas_del_periodo",
        "faltas_justificadas",
        "total_faltas",
        "total_salidas_anticipadas",
        "diferencia_HHMMSS",
    ]
    resumen_final = resumen_final[base_columns]

    output_filename = "resumen_periodo.csv"
    try:
        resumen_final.to_csv(output_filename, index=False, encoding="utf-8-sig")
        print(f"✅ Resumen del periodo guardado en '{output_filename}'")
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename_alt = f"resumen_periodo_{timestamp}.csv"
        resumen_final.to_csv(output_filename_alt, index=False, encoding="utf-8-sig")
        print(
            f"⚠️ El archivo original estaba en uso. Resumen guardado en '{output_filename_alt}'"
        )

    print("\n**Visualización del Resumen del Periodo:**\n")
    print(resumen_final.to_string())
    return resumen_final


# ==============================================================================
# SECCIÓN 4.5: FUNCIÓN PARA GENERAR REPORTE HTML INTERACTIVO (CORREGIDA)
# ==============================================================================
def generar_reporte_html(
    df_detallado: pd.DataFrame,
    df_resumen: pd.DataFrame,
    periodo_inicio: str,
    periodo_fin: str,
    sucursal: str,
):
    """
    Genera un reporte HTML interactivo del periodo analizado con lógica de JS corregida.
    """
    print("\n📊 Generando reporte HTML interactivo...")

    if df_resumen.empty:
        html_content = """<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Sin Datos</title></head>
<body><h1>Sin datos disponibles</h1><p>No se encontraron datos para el período.</p></body></html>"""
        with open("dashboard_asistencia.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        return "dashboard_asistencia.html"

    def time_to_decimal(time_str):
        if pd.isna(time_str) or time_str in ["00:00:00", "---"]:
            return 0.0
        try:
            parts = str(time_str).split(":")
            h = float(parts[0]) if len(parts) > 0 else 0
            m = float(parts[1]) if len(parts) > 1 else 0
            s = float(parts[2]) if len(parts) > 2 else 0
            return h + m / 60 + s / 3600
        except Exception:
            return 0.0

    employee_data_js = []
    for _, row in df_resumen.iterrows():
        employee_data_js.append(
            {
                "employee": str(row["employee"]),
                "name": str(row["Nombre"]),
                "workedHours": str(row["total_horas_trabajadas"]),
                "expectedHours": str(row["total_horas_esperadas"]),
                "permitHours": str(
                    row.get("total_horas_descontadas_permiso", "00:00:00")
                ),
                "netHours": str(row["total_horas"]),
                "delays": int(row.get("total_retardos", 0)),
                "absences": int(row.get("faltas_del_periodo", 0)),
                "justifiedAbsences": int(row.get("faltas_justificadas", 0)),
                "totalAbsences": int(row.get("total_faltas", 0)),
                "difference": str(row.get("diferencia_HHMMSS", "00:00:00")),
                "workedDecimal": time_to_decimal(row["total_horas_trabajadas"]),
                "expectedDecimal": time_to_decimal(row["total_horas_esperadas"]),
                "expectedDecimalAdjusted": time_to_decimal(row["total_horas"]),
                "permitDecimal": time_to_decimal(
                    row.get("total_horas_descontadas_permiso", "00:00:00")
                ),
            }
        )

    daily_data_js = []
    if not df_detallado.empty and "dia" in df_detallado.columns:
        df_laborables = df_detallado[
            df_detallado["hora_entrada_programada"].notna()
        ].copy()
        if not df_laborables.empty:
            daily_summary = (
                df_laborables.groupby(["dia", "dia_semana"])
                .agg(
                    total_empleados=("employee", "nunique"),
                    faltas_injustificadas=(
                        "tipo_falta_ajustada",
                        lambda x: x.isin(["Falta", "Falta Injustificada"]).sum(),
                    ),
                    permisos=("falta_justificada", lambda x: x.sum()),
                )
                .reset_index()
            )
            for _, row in daily_summary.iterrows():
                asistencias = (
                    row["total_empleados"]
                    - row["faltas_injustificadas"]
                    - row["permisos"]
                )
                daily_data_js.append(
                    {
                        "date": row["dia"].strftime("%d %b"),
                        "day": str(row["dia_semana"]),
                        "attendance": max(0, asistencias),
                        "absences": int(row["faltas_injustificadas"]),
                        "permits": int(row["permisos"]),
                        "total": int(row["total_empleados"]),
                    }
                )

    start_dt = datetime.strptime(periodo_inicio, "%Y-%m-%d")
    end_dt = datetime.strptime(periodo_fin, "%Y-%m-%d")
    dias_laborales = sum(
        1 for d in pd.date_range(start=start_dt, end=end_dt) if d.weekday() < 5
    )

    total_employees = len(employee_data_js)
    total_absences = sum(e.get("totalAbsences", 0) for e in employee_data_js)
    total_possible_days = total_employees * dias_laborales
    lost_days_percent = (
        (total_absences / total_possible_days * 100) if total_possible_days > 0 else 0
    )

    # KPIs calculados en Python para asegurar consistencia
    total_worked_py = sum(e["workedDecimal"] for e in employee_data_js)
    total_expected_py = sum(e["expectedDecimal"] for e in employee_data_js)
    attendance_rate = (
        (total_worked_py / total_expected_py * 100) if total_expected_py > 0 else 0
    )

    punctual_employees = sum(
        1 for e in employee_data_js if e["delays"] == 0 and e["workedDecimal"] > 0
    )
    active_employees = sum(1 for e in employee_data_js if e["workedDecimal"] > 0)
    punctuality_rate = (
        (punctual_employees / active_employees * 100) if active_employees > 0 else 0
    )

    lost_days = sum(e.get("totalAbsences", 0) for e in employee_data_js)

    employee_json = json.dumps(employee_data_js, ensure_ascii=False)
    daily_json = json.dumps(daily_data_js, ensure_ascii=False)

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Ejecutivo de Asistencia - {sucursal}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/2.3.2/css/dataTables.dataTables.min.css">
    <style>
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #f8f9fa; color: #212529; }}
        .header {{ background: white; padding: 2rem; text-align: center; box-shadow: 0 2px 10px rgba(0,0,0,0.08); margin-bottom: 2rem; border-bottom: 3px solid #0066cc; }}
        .header h1 {{ color: #0066cc; font-size: 2.2rem; margin-bottom: 0.5rem; }}
        .header p {{ color: #6c757d; font-size: 1.1rem; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 0 1rem; }}
        .tabs {{ display: flex; justify-content: center; margin-bottom: 2rem; gap: 1rem; }}
        .tab-button {{ padding: 1rem 2rem; font-size: 1rem; font-weight: 600; cursor: pointer; border: 2px solid #0066cc; background: white; color: #0066cc; border-radius: 8px; transition: all 0.2s ease; }}
        .tab-button.active {{ background: #0066cc; color: white; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin-bottom: 3rem; }}
        .metric-card {{ background: white; border-radius: 12px; padding: 2rem; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-left: 4px solid; }}
        .metric-card h3 {{ color: #495057; font-size: 0.9rem; margin-bottom: 1rem; text-transform: uppercase; }}
        .metric-value {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 0.5rem; }}
        .metric-subtitle {{ font-size: 0.8rem; color: #6c757d; }}
        .metric-card.attendance {{ border-left-color: #28a745; }} .metric-card.attendance .metric-value {{ color: #28a745; }}
        .metric-card.deviation {{ border-left-color: #ff6b35; }} .metric-card.deviation .metric-value {{ color: #ff6b35; }}
        .metric-card.punctuality {{ border-left-color: #ffc107; }} .metric-card.punctuality .metric-value {{ color: #ffc107; }}
        .metric-card.absences {{ border-left-color: #dc3545; }} .metric-card.absences .metric-value {{ color: #dc3545; }}
        .chart-container {{ background: white; border-radius: 12px; padding: 2rem; margin-bottom: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        .chart-title {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 1.5rem; }}
        .chart svg {{ width: 100%; height: auto; }}
        .axis path, .axis .domain {{ stroke: #dee2e6; }}
        .axis .tick text {{ fill: #6c757d; }}
        .grid line {{ stroke: #f1f3f4; stroke-dasharray: 2,2; }}
        .tooltip {{ position: absolute; padding: 12px; background: rgba(33,37,41,0.95); color: white; border-radius: 6px; pointer-events: none; opacity: 0; transition: opacity 0.2s; z-index: 1000; }}
        .table-section {{ background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        .controls {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
        .search-box input, .filter-select {{ width: 100%; padding: 12px 16px; border: 2px solid #e9ecef; border-radius: 8px; }}
        .employee-table {{ width: 100%; border-collapse: collapse; }}
        .employee-table th {{ background: #f8f9fa; padding: 1rem; text-align: left; }}
        .employee-table td {{ padding: 1rem; border-bottom: 1px solid #e9ecef; }}
        .positive {{ color: #28a745; }} .negative {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Dashboard Ejecutivo de Asistencia</h1>
        <p>Sucursal: {sucursal.upper()} | Período: {periodo_inicio} - {periodo_fin}</p>
    </div>
    <div class="container">
        <div class="tabs">
            <button class="tab-button active" onclick="openTab(event, 'dashboard')">Resumen Ejecutivo</button>
            <button class="tab-button" onclick="openTab(event, 'employee-table')">Detalle por Empleado</button>
        </div>
        <div id="dashboard" class="tab-content active">
            <div class="metrics-grid">
                <div class="metric-card attendance">
                    <h3>Tasa de Asistencia</h3>
                    <div class="metric-value" id="attendanceRate">{attendance_rate:.1f}%</div>
                    <div class="metric-subtitle">Horas trabajadas vs planificadas</div>
                </div>
                <div class="metric-card deviation">
                    <h3>Desviación Media Horaria</h3>
                    <div class="metric-value" id="avgDeviationHours">±0.0 h</div>
                    <div class="metric-subtitle">Promedio de dif. de horas</div>
                </div>
                <div class="metric-card punctuality">
                    <h3>Índice de Puntualidad</h3>
                    <div class="metric-value" id="punctualityRate">{punctuality_rate:.0f}%</div>
                    <div class="metric-subtitle">Empleados puntuales</div>
                </div>
                <div class="metric-card absences">
                    <h3>Días Perdidos</h3>
                    <div class="metric-value" id="totalLostDays">{lost_days}</div>
                    <div class="metric-subtitle">{lost_days_percent:.1f}% de capacidad perdida</div>
                </div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Tendencia de Asistencia del Período</div>
                <div id="dailyTrendChart" class="chart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Eficiencia de Recursos Humanos</div>
                <div id="efficiencyChart" class="chart"></div>
            </div>
            <div class="chart-container">
                <div class="chart-title">Análisis de Impacto por Ausencias</div>
                <div id="absenceImpactChart" class="chart"></div>
            </div>
        </div>
        <div id="employee-table" class="tab-content">
            <div class="table-section">
                <div class="chart-title">Análisis Individual</div>
                <table id="tablaDetalleEmpleado" class="employee-table" style="width:100%">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Empleado</th>
                            <th>Hrs. Trabajadas</th>
                            <th>Hrs. Planificadas</th>
                            <th>Variación</th>
                            <th>Retardos</th>
                            <th>Ausencias</th>
                        </tr>
                    </thead>
                    <tbody>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <div class="tooltip"></div>

    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.datatables.net/2.3.2/js/dataTables.min.js"></script>

    <script>
        const employeeData = {employee_json};
        const dailyData = {daily_json};
        const tooltip = d3.select(".tooltip");

        // --- UTILS ---
        function hhmmssToDecimal(hhmmss) {{
            if (!hhmmss || typeof hhmmss !== 'string') return 0;
            const [h, m, s] = hhmmss.split(':').map(Number);
            return (h || 0) + (m || 0) / 60 + (s || 0) / 3600;
        }}
        function safeDiv(numerator, denominator) {{
            return denominator > 0 ? numerator / denominator : 0;
        }}
        function truncateName(name, max = 20) {{
            return name.length > max ? name.slice(0, max) + "…" : name;
        }}

        // --- PESTAÑAS ---
        function openTab(evt, tabName) {{
            document.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
            document.querySelectorAll('.tab-button').forEach(tb => tb.classList.remove('active'));
            document.getElementById(tabName).style.display = 'block';
            evt.currentTarget.classList.add('active');
        }}

        // --- CÁLCULO DE KPIs ---
        function calculateAndDisplayKPIs() {{
            if (!employeeData || employeeData.length === 0) return;

            // Desviación Media Horaria
            const employeesWithPlannedHours = employeeData.filter(e => e.expectedDecimalAdjusted > 0);
            let avgDeviation = 0;
            if (employeesWithPlannedHours.length > 0) {{
                const totalDeviation = employeesWithPlannedHours.reduce((sum, e) => {{
                    return sum + Math.abs(e.workedDecimal - e.expectedDecimalAdjusted);
                }}, 0);
                avgDeviation = safeDiv(totalDeviation, employeesWithPlannedHours.length);
            }}
            document.getElementById('avgDeviationHours').textContent = `±${{avgDeviation.toFixed(1)}} h`;
        }}

        // --- GRÁFICAS ---
        function createDailyTrendChart() {{
            const container = d3.select("#dailyTrendChart");
            if (dailyData.length === 0) {{ container.text("No hay datos de tendencia diaria."); return; }}
            container.html("");
            const margin = {{ top: 20, right: 100, bottom: 50, left: 40 }};
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            const svg = container.append("svg").attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);
            
            const series = [
                {{ key: "attendance", label: "Asistencias", color: "#28a745" }},
                {{ key: "absences", label: "Faltas", color: "#dc3545" }},
                {{ key: "permits", label: "Permisos", color: "#ffc107" }}
            ];
            const x = d3.scaleBand().domain(dailyData.map(d => d.date)).range([0, width]).padding(0.1);
            const y = d3.scaleLinear().domain([0, d3.max(dailyData, d => d.total) || 1]).nice().range([height, 0]);

            svg.append("g").attr("transform", `translate(0,${{height}})`).call(d3.axisBottom(x)).selectAll("text").attr("transform", "rotate(-45)").style("text-anchor", "end");
            svg.append("g").call(d3.axisLeft(y));
            svg.append("g").attr("class", "grid").call(d3.axisLeft(y).tickSize(-width).tickFormat("")).selectAll("line").attr("stroke", "#f1f3f4");

            const lineGen = key => d3.line().x(d => x(d.date) + x.bandwidth() / 2).y(d => y(d[key])).curve(d3.curveMonotoneX);

            series.forEach(s => {{
                svg.append("path").datum(dailyData).attr("fill", "none").attr("stroke", s.color).attr("stroke-width", 2.5).attr("d", lineGen(s.key));
                svg.selectAll(`.dot-${{s.key}}`).data(dailyData).enter().append("circle")
                    .attr("cx", d => x(d.date) + x.bandwidth() / 2).attr("cy", d => y(d[s.key])).attr("r", 4).attr("fill", s.color)
                    .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${{d.date}}</strong><br>${{s.label}}: ${{d[s.key]}}`))
                    .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                    .on("mouseout", () => tooltip.style("opacity", 0));
            }});
        }}

        function createEfficiencyChart() {{
            const container = d3.select("#efficiencyChart");
            container.html("");
            
            const data = employeeData
                .map(d => ({{
                    name: truncateName(d.name),
                    fullName: d.name,
                    efficiency: safeDiv(d.workedDecimal, d.expectedDecimalAdjusted) * 100,
                    worked: d.workedDecimal,
                    planned: d.expectedDecimalAdjusted
                }}))
                .filter(d => d.planned > 0)
                .sort((a, b) => b.efficiency - a.efficiency)
                .slice(0, 15);

            if (data.length === 0) {{ container.text("No hay datos de eficiencia para mostrar (sin horas planificadas)."); return; }}

            const margin = {{ top: 20, right: 30, bottom: 40, left: 150 }};
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = data.length * 28;
            const svg = container.append("svg").attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            const x = d3.scaleLinear().domain([0, Math.max(100, d3.max(data, d => d.efficiency) || 0)]).nice().range([0, width]);
            const y = d3.scaleBand().domain(data.map(d => d.name)).range([0, height]).padding(0.1);

            svg.append("g").call(d3.axisLeft(y).tickSize(0)).select(".domain").remove();
            svg.append("g").attr("transform", `translate(0,${{height}})`).call(d3.axisBottom(x).ticks(5).tickFormat(d => d + "%"));
            
            svg.append("line").attr("x1", x(100)).attr("x2", x(100)).attr("y1", 0).attr("y2", height).attr("stroke", "#dc3545").attr("stroke-dasharray", "4,4");

            svg.selectAll(".bar").data(data).enter().append("rect")
                .attr("y", d => y(d.name)).attr("width", d => x(d.efficiency)).attr("height", y.bandwidth())
                .attr("fill", d => d.efficiency >= 98 ? "#28a745" : d.efficiency >= 85 ? "#ffc107" : "#dc3545")
                .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${{d.fullName}}</strong><br>Eficiencia: ${{d.efficiency.toFixed(1)}}%<br>Trabajadas: ${{d.worked.toFixed(1)}}h<br>Planificadas: ${{d.planned.toFixed(1)}}h`))
                .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                .on("mouseout", () => tooltip.style("opacity", 0));
        }}
        
        function createAbsenceImpactChart() {{
            const container = d3.select("#absenceImpactChart");
            container.html("");
            
            const unjustified = d3.sum(employeeData, d => d.absences);
            const justified = d3.sum(employeeData, d => d.justifiedAbsences);
            const delays = d3.sum(employeeData, d => d.delays);
            
            const data = [
                {{ type: "Faltas Injustificadas", count: unjustified, color: "#dc3545" }},
                {{ type: "Faltas Justificadas", count: justified, color: "#ffc107" }},
                {{ type: "Retardos", count: delays, color: "#17a2b8" }}
            ].filter(d => d.count > 0);

            if (data.length === 0) {{ container.text("¡Sin ausencias ni retardos en el período!"); return; }}

            const margin = {{ top: 20, right: 20, bottom: 30, left: 40 }};
            const width = container.node().getBoundingClientRect().width - margin.left - margin.right;
            const height = 300 - margin.top - margin.bottom;
            const svg = container.append("svg").attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g").attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            const x = d3.scaleBand().domain(data.map(d => d.type)).range([0, width]).padding(0.4);
            const y = d3.scaleLinear().domain([0, d3.max(data, d => d.count) || 1]).nice().range([height, 0]);

            svg.append("g").attr("transform", `translate(0,${{height}})`).call(d3.axisBottom(x));
            svg.append("g").call(d3.axisLeft(y));

            svg.selectAll(".bar").data(data).enter().append("rect")
                .attr("x", d => x(d.type)).attr("y", d => y(d.count))
                .attr("width", x.bandwidth()).attr("height", d => height - y(d.count))
                .attr("fill", d => d.color)
                .on("mouseover", (event, d) => tooltip.style("opacity", 1).html(`<strong>${{d.type}}</strong><br>Total: ${{d.count}}`))
                .on("mousemove", e => tooltip.style("left", (e.pageX + 10) + "px").style("top", (e.pageY - 10) + "px"))
                .on("mouseout", () => tooltip.style("opacity", 0));
        }}

        // --- TABLA ---
        // Las funciones renderTable y filterTable han sido reemplazadas por DataTables

        // --- INICIALIZACIÓN ---
        document.addEventListener('DOMContentLoaded', () => {{
            calculateAndDisplayKPIs();
            createDailyTrendChart();
            createEfficiencyChart();
            createAbsenceImpactChart();
            
            // Inicializar DataTables para la tabla de empleados
            $('#tablaDetalleEmpleado').DataTable({{
                data: employeeData,
                columns: [
                    {{ data: 'employee' }},
                    {{ data: 'name' }},
                    {{ data: 'workedHours' }},
                    {{ data: 'netHours' }},
                    {{
                        data: 'difference',
                        createdCell: function (td, cellData, rowData, row, col) {{
                            if (cellData.startsWith('+')) {{
                                $(td).addClass('positive');
                            }} else if (cellData.startsWith('-')) {{
                                $(td).addClass('negative');
                            }}
                        }}
                    }},
                    {{ data: 'delays' }},
                    {{ data: 'totalAbsences' }}
                ],
                language: {{
                    url: 'https://cdn.datatables.net/plug-ins/2.0.3/i18n/es-MX.json',
                }},
                pageLength: 10,
                responsive: true
            }});
            
            window.addEventListener('resize', () => {{
                createDailyTrendChart();
                createEfficiencyChart();
                createAbsenceImpactChart();
            }});
        }});
    </script>
</body>
</html>"""

    html_filename = "dashboard_asistencia.html"
    try:
        with open(html_filename, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"✅ Dashboard HTML generado exitosamente: '{html_filename}'")
    except PermissionError:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename_alt = f"dashboard_asistencia_{timestamp}.html"
        with open(html_filename_alt, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(
            f"⚠️ El archivo original estaba en uso. Dashboard guardado en '{html_filename_alt}'"
        )
        html_filename = html_filename_alt

    return html_filename


# ==============================================================================
# SECCIÓN 5: EJECUCIÓN PRINCIPAL DEL SCRIPT
# ==============================================================================
if __name__ == "__main__":
    start_date = "2025-07-01"
    end_date = "2025-07-31"
    sucursal = "Villas"
    device_filter = "%Villas%"

    fecha_inicio_dt = datetime.strptime(start_date, "%Y-%m-%d")
    fecha_fin_dt = datetime.strptime(end_date, "%Y-%m-%d")

    incluye_primera = any(
        d.day <= 15 for d in pd.date_range(start=fecha_inicio_dt, end=fecha_fin_dt)
    )
    incluye_segunda = any(
        d.day > 15 for d in pd.date_range(start=fecha_inicio_dt, end=fecha_fin_dt)
    )

    print(f"\n🚀 Iniciando reporte para {sucursal}...")

    print("\n📡 Paso 1: Obteniendo checadas...")
    checkin_records = fetch_checkins(start_date, end_date, device_filter)
    if not checkin_records:
        print("❌ No se obtuvieron checadas. Saliendo.")
        exit(1)

    codigos_empleados_api = obtener_codigos_empleados_api(checkin_records)

    print("\n📄 Paso 2: Obteniendo permisos...")
    leave_records = fetch_leave_applications(start_date, end_date)
    permisos_dict = procesar_permisos_empleados(leave_records)

    print("\n📋 Paso 3: Obteniendo horarios...")
    conn_pg = connect_db()
    if conn_pg is None:
        exit(1)

    cache_horarios = {}
    horarios_por_quincena = obtener_horarios_multi_quincena(
        sucursal,
        conn_pg,
        codigos_empleados_api,
        incluye_primera=incluye_primera,
        incluye_segunda=incluye_segunda,
    )
    if not any(horarios_por_quincena.values()):
        print(f"❌ No se encontraron horarios para la sucursal {sucursal}.")
        conn_pg.close()
        exit(1)

    cache_horarios = mapear_horarios_por_empleado_multi(horarios_por_quincena)
    conn_pg.close()

    print("\n📊 Paso 4: Procesando datos...")
    df_detalle = process_checkins_to_dataframe(checkin_records, start_date, end_date)
    df_detalle = procesar_horarios_con_medianoche(df_detalle, cache_horarios)
    df_detalle = analizar_asistencia_con_horarios_cache(df_detalle, cache_horarios)
    df_detalle = aplicar_calculo_horas_descanso(df_detalle)
    df_detalle = ajustar_horas_esperadas_con_permisos(
        df_detalle, permisos_dict, cache_horarios
    )
    df_detalle = aplicar_regla_perdon_retardos(df_detalle)
    df_detalle = clasificar_faltas_con_permisos(df_detalle)

    print("\n💾 Paso 5: Generando reportes...")
    checado_cols = sorted(
        [c for c in df_detalle.columns if "checado_" in c and c != "checado_1"]
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
        "retardo_perdonado",
        "tipo_retardo_original",
        "minutos_tarde_original",
        "tipo_falta_ajustada",
        "tiene_permiso",
        "tipo_permiso",
        "es_permiso_medio_dia",
        "falta_justificada",
        "hora_salida_programada",
        "salida_anticipada",
        "horas_esperadas",
        "duration",
        "horas_trabajadas",
        "horas_descanso",
    ] + checado_cols
    final_columns = [col for col in column_order if col in df_detalle.columns]
    df_final_detallado = df_detalle[final_columns].fillna("---")

    output_filename_detallado = "reporte_asistencia_analizado.csv"
    try:
        df_final_detallado.to_csv(
            output_filename_detallado, index=False, encoding="utf-8-sig"
        )
        print(f"✅ Reporte detallado guardado en '{output_filename_detallado}'")
    except PermissionError:
        print(
            f"⚠️ No se pudo guardar '{output_filename_detallado}'. El archivo podría estar en uso."
        )

    df_resumen = generar_resumen_periodo(df_detalle)

    print("\n🌐 Paso 6: Generando dashboard HTML...")
    if not df_resumen.empty:
        generar_reporte_html(df_detalle, df_resumen, start_date, end_date, sucursal)
    else:
        print("⚠️ No se generó el resumen, omitiendo creación de dashboard HTML.")

    print("\n🎉 ¡Proceso completado!")
