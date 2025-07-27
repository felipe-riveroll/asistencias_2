import json
import os
import glob
import requests
import pandas as pd
from itertools import product
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv

# Importamos la nueva conexión a PostgreSQL
from db_postgres_connection import connect_db, obtener_tabla_horarios, mapear_horarios_por_empleado, obtener_horario_empleado

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
    
    Args:
        start_date: Fecha de inicio en formato 'YYYY-MM-DD'
        end_date: Fecha de fin en formato 'YYYY-MM-DD'
    
    Returns:
        Lista de permisos aprobados
    """
    print(f"📄 Obteniendo permisos aprobados de la API para el periodo {start_date} - {end_date}...")
    
    if not all([API_KEY, API_SECRET]):
        print("❌ Error: Faltan credenciales de API para obtener permisos")
        return []

    headers = {"Authorization": f"token {API_KEY}:{API_SECRET}"}
    
    # Filtros para obtener solo permisos aprobados en el rango de fechas
    filters = json.dumps([
        ["Leave Application", "status", "=", "Approved"],
        ["Leave Application", "from_date", "Between", [start_date, end_date]],
    ])
    
    params = {
        "fields": json.dumps([
            "employee", 
            "employee_name", 
            "leave_type", 
            "from_date", 
            "to_date", 
            "status"
        ]),
        "filters": filters,
        "limit_page_length": 100
    }

    all_leave_records = []
    limit_start = 0

    while True:
        params["limit_start"] = limit_start
        try:
            response = requests.get(LEAVE_API_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json().get("data", [])
            
            if not data:
                break
                
            all_leave_records.extend(data)
            
            if len(data) < params["limit_page_length"]:
                break
                
            limit_start += params["limit_page_length"]
            
        except requests.exceptions.Timeout:
            print("⚠️ Timeout al obtener permisos. Reintentando...")
            continue
        except requests.exceptions.RequestException as e:
            print(f"❌ Error al obtener permisos de la API: {e}")
            return []

    print(f"✅ Se obtuvieron {len(all_leave_records)} permisos aprobados de la API.")
    
    # Debug: Mostrar algunos permisos obtenidos
    if all_leave_records:
        print(f"📋 Ejemplo de permisos obtenidos:")
        for i, leave in enumerate(all_leave_records[:3]):
            print(f"   - {leave['employee_name']}: {leave['leave_type']} ({leave['from_date']} - {leave['to_date']})")
    
    return all_leave_records


# ==============================================================================
# SECCIÓN 3: PROCESAMIENTO Y ANÁLISIS DE DATOS
# ==============================================================================

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
    
    Args:
        leave_data: Lista de permisos obtenidos de la API
    
    Returns:
        dict: Diccionario con estructura {employee_code: {fecha: permiso_info}}
    """
    if not leave_data:
        return {}
    
    print("🔄 Procesando permisos por empleado y fecha...")
    
    permisos_por_empleado = {}
    
    for permiso in leave_data:
        employee_code = permiso['employee']
        from_date = datetime.strptime(permiso['from_date'], '%Y-%m-%d').date()
        to_date = datetime.strptime(permiso['to_date'], '%Y-%m-%d').date()
        
        # Crear entrada para el empleado si no existe
        if employee_code not in permisos_por_empleado:
            permisos_por_empleado[employee_code] = {}
        
        # Iterar por cada día del permiso
        current_date = from_date
        while current_date <= to_date:
            permisos_por_empleado[employee_code][current_date] = {
                'leave_type': permiso['leave_type'],
                'employee_name': permiso['employee_name'],
                'from_date': from_date,
                'to_date': to_date,
                'status': permiso['status']
            }
            current_date += timedelta(days=1)
    
    total_dias_con_permiso = sum(len(fechas) for fechas in permisos_por_empleado.values())
    print(f"✅ Procesados permisos para {len(permisos_por_empleado)} empleados, {total_dias_con_permiso} días con permiso total.")
    
    return permisos_por_empleado


def ajustar_horas_esperadas_con_permisos(df, permisos_dict, cache_horarios):
    """
    Ajusta las horas esperadas del DataFrame considerando los permisos aprobados.
    
    Args:
        df: DataFrame con los datos de asistencia
        permisos_dict: Diccionario de permisos por empleado
        cache_horarios: Caché de horarios por empleado
    
    Returns:
        DataFrame actualizado con horas esperadas ajustadas y información de permisos
    """
    if df.empty:
        return df
    
    print("📊 Ajustando horas esperadas considerando permisos aprobados...")
    
    # Añadir columnas para información de permisos
    df['tiene_permiso'] = False
    df['tipo_permiso'] = None
    df['horas_esperadas_originales'] = df['horas_esperadas'].copy()
    df['horas_descontadas_permiso'] = '00:00:00'
    
    for index, row in df.iterrows():
        employee_code = str(row['employee'])
        fecha = row['dia']
        
        # Verificar si el empleado tiene permiso en esta fecha
        if (employee_code in permisos_dict and 
            fecha in permisos_dict[employee_code]):
            
            permiso_info = permisos_dict[employee_code][fecha]
            
            # Marcar que tiene permiso
            df.at[index, 'tiene_permiso'] = True
            df.at[index, 'tipo_permiso'] = permiso_info['leave_type']
            
            # Obtener las horas esperadas originales para este día
            horas_esperadas_orig = row['horas_esperadas']
            
            if pd.notna(horas_esperadas_orig) and horas_esperadas_orig != '00:00:00':
                # Las horas esperadas se reducen a 0 para días con permiso
                df.at[index, 'horas_esperadas'] = '00:00:00'
                df.at[index, 'horas_descontadas_permiso'] = horas_esperadas_orig
                
                print(f"   - {permiso_info['employee_name']} ({employee_code}): "
                      f"{fecha} - {permiso_info['leave_type']} - "
                      f"Horas descontadas: {horas_esperadas_orig}")
    
    # Contar empleados afectados
    empleados_con_permisos = df[df['tiene_permiso'] == True]['employee'].nunique()
    dias_con_permisos = df['tiene_permiso'].sum()
    
    print(f"✅ Ajuste completado: {empleados_con_permisos} empleados con permisos, {dias_con_permisos} días ajustados.")
    
    return df


def clasificar_faltas_con_permisos(df):
    """
    Actualiza la clasificación de faltas considerando los permisos aprobados.
    
    Args:
        df: DataFrame con datos de asistencia y permisos
    
    Returns:
        DataFrame actualizado con faltas justificadas
    """
    if df.empty:
        return df
    
    print("📋 Reclasificando faltas considerando permisos aprobados...")
    
    # Crear nueva columna para el tipo de falta actualizado
    df['tipo_falta_ajustada'] = df['tipo_retardo'].copy()
    df['falta_justificada'] = False
    
    # Procesar filas que tienen permiso y eran consideradas faltas
    mask_permiso_y_falta = (df['tiene_permiso'] == True) & (df['tipo_retardo'].isin(['Falta', 'Falta Injustificada']))
    
    if mask_permiso_y_falta.any():
        # Cambiar el tipo de falta para días con permiso
        df.loc[mask_permiso_y_falta, 'tipo_falta_ajustada'] = 'Falta Justificada'
        df.loc[mask_permiso_y_falta, 'falta_justificada'] = True
        
        # Actualizar el contador de faltas (no contar las justificadas)
        df['es_falta_ajustada'] = (df['tipo_falta_ajustada'].isin(['Falta', 'Falta Injustificada'])).astype(int)
        
        faltas_justificadas = mask_permiso_y_falta.sum()
        print(f"✅ Se justificaron {faltas_justificadas} faltas con permisos aprobados.")
    else:
        # Si no hay faltas justificadas, mantener el contador original
        df['es_falta_ajustada'] = df['es_falta'].copy()
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

    # Agrupar por empleado y día para obtener entrada y salida
    df_hours = df.groupby(["employee", "dia"])["time"].agg(["min", "max"]).reset_index()
    duration = df_hours["max"] - df_hours["min"]
    df_hours["horas_trabajadas"] = duration.apply(
        lambda x: str(x).split(" ")[-1] if pd.notna(x) else "00:00:00"
    )

    # Generar pivot para múltiples checadas por día
    df["checado_rank"] = df.groupby(["employee", "dia"]).cumcount() + 1
    df_pivot = df.pivot_table(
        index=["employee", "dia"],
        columns="checado_rank",
        values="checado_time",
        aggfunc="first",
    )
    if not df_pivot.empty:
        df_pivot.columns = [f"checado_{i}" for i in range(1, len(df_pivot.columns) + 1)]

    # Crear base completa de todos los empleados para todos los días
    all_employees = df["employee"].unique()
    all_dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date)).date
    base_df = pd.DataFrame(
        list(product(all_employees, all_dates)), columns=["employee", "dia"]
    )

    # Unir con las checadas y los datos de horas
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

    # Añadir día de la semana en español
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
    
    # Añadir día de la semana como número (1-7)
    final_df["dia_iso"] = pd.to_datetime(final_df["dia"]).dt.weekday + 1

    return final_df


def procesar_horarios_con_medianoche(df, cache_horarios):
    """
    Reorganiza las checadas para turnos que cruzan la medianoche, respetando los horarios
    programados en la base de datos y corrigiendo errores de múltiples checadas.
    
    Args:
        df: DataFrame con las checadas
        cache_horarios: Caché de horarios por empleado
    
    Returns:
        DataFrame actualizado
    """
    print("\n🔄 Procesando turnos que cruzan medianoche...")
    
    # Creamos una copia para no modificar el original durante el procesamiento
    df_proc = df.copy()
    
    # Ordenar por empleado y fecha para procesar secuencialmente
    df_proc = df_proc.sort_values(['employee', 'dia']).reset_index(drop=True)
    
    # Determinar si es primera quincena para cada registro
    df_proc['es_primera_quincena'] = df_proc['dia'].apply(lambda x: x.day <= 15)
    
    # Iterar por cada empleado para procesar sus checadas
    for empleado in df_proc['employee'].unique():
        # Obtener todas las filas del empleado
        mask_empleado = df_proc['employee'] == empleado
        filas_empleado = df_proc.loc[mask_empleado].copy()
        
        # Procesar cada día
        for i in range(len(filas_empleado)):
            idx_actual = filas_empleado.index[i]
            fila_actual = df_proc.loc[idx_actual]
            
            # Obtener el horario programado para el día actual
            horario = obtener_horario_empleado(
                str(empleado),
                fila_actual['dia_iso'],
                fila_actual['es_primera_quincena'],
                cache_horarios
            )
            
            if horario and horario.get('cruza_medianoche', False):
                # Para turnos que cruzan medianoche, necesitamos reorganizar las checadas
                checadas_dia = []
                
                # Recopilar todas las checadas del día actual
                for j in range(1, 10):  # Hasta 10 checadas posibles
                    col_name = f'checado_{j}'
                    if col_name in df_proc.columns and pd.notna(df_proc.loc[idx_actual, col_name]):
                        checadas_dia.append(df_proc.loc[idx_actual, col_name])
                
                # Si tenemos checadas, buscar la checada de salida en el día siguiente
                if checadas_dia:
                    # Buscar el día siguiente
                    dia_siguiente = fila_actual['dia'] + timedelta(days=1)
                    mask_siguiente = (df_proc['employee'] == empleado) & (df_proc['dia'] == dia_siguiente)
                    
                    if mask_siguiente.any():
                        idx_siguiente = df_proc[mask_siguiente].index[0]
                        
                        # Recopilar checadas del día siguiente
                        checadas_siguiente = []
                        for j in range(1, 10):
                            col_name = f'checado_{j}'
                            if col_name in df_proc.columns and pd.notna(df_proc.loc[idx_siguiente, col_name]):
                                checadas_siguiente.append(df_proc.loc[idx_siguiente, col_name])
                        
                        # Usar la hora programada como referencia para determinar entrada/salida
                        hora_entrada_prog = horario['hora_entrada']
                        hora_salida_prog = horario['hora_salida']
                        
                        # Filtrar checadas por proximidad a los horarios programados
                        entrada_real = None
                        salida_real = None
                        
                        # Buscar la entrada más cercana a la hora programada
                        for checada in checadas_dia:
                            if calcular_proximidad_horario(checada, hora_entrada_prog) <= 120:  # 2 horas de tolerancia
                                if entrada_real is None or calcular_proximidad_horario(checada, hora_entrada_prog) < calcular_proximidad_horario(entrada_real, hora_entrada_prog):
                                    entrada_real = checada
                        
                        # Buscar la salida más cercana en el día siguiente
                        for checada in checadas_siguiente:
                            if calcular_proximidad_horario(checada, hora_salida_prog) <= 120:  # 2 horas de tolerancia
                                if salida_real is None or calcular_proximidad_horario(checada, hora_salida_prog) < calcular_proximidad_horario(salida_real, hora_salida_prog):
                                    salida_real = checada
                        
                        # Si no encontramos salida en día siguiente, usar la última checada del día actual
                        if salida_real is None and len(checadas_dia) > 1:
                            salida_real = checadas_dia[-1]
                        
                        # Reorganizar las checadas en el día actual
                        # Limpiar todas las checadas existentes
                        for j in range(1, 10):
                            col_name = f'checado_{j}'
                            if col_name in df_proc.columns:
                                df_proc.loc[idx_actual, col_name] = None
                        
                        # Asignar entrada y salida corregidas
                        if entrada_real:
                            df_proc.loc[idx_actual, 'checado_1'] = entrada_real
                        if salida_real:
                            df_proc.loc[idx_actual, 'checado_2'] = salida_real
                        
                        # Recalcular horas trabajadas
                        if entrada_real and salida_real:
                            entrada_time = datetime.strptime(entrada_real, '%H:%M:%S')
                            salida_time = datetime.strptime(salida_real, '%H:%M:%S')
                            
                            # Si la salida es menor que la entrada, añadir un día
                            if salida_time <= entrada_time:
                                salida_time = salida_time + timedelta(days=1)
                            
                            duracion = salida_time - entrada_time
                            df_proc.loc[idx_actual, 'horas_trabajadas'] = str(duracion)
                        
                        # Limpiar checadas del día siguiente si la usamos como salida
                        if salida_real in checadas_siguiente:
                            for j in range(1, 10):
                                col_name = f'checado_{j}'
                                if col_name in df_proc.columns and df_proc.loc[idx_siguiente, col_name] == salida_real:
                                    df_proc.loc[idx_siguiente, col_name] = None
                                    break
                            
                            # Recalcular horas del día siguiente
                            checadas_restantes = []
                            for j in range(1, 10):
                                col_name = f'checado_{j}'
                                if col_name in df_proc.columns and pd.notna(df_proc.loc[idx_siguiente, col_name]):
                                    checadas_restantes.append(df_proc.loc[idx_siguiente, col_name])
                            
                            if len(checadas_restantes) >= 2:
                                entrada_sig = min(checadas_restantes)
                                salida_sig = max(checadas_restantes)
                                entrada_time_sig = datetime.strptime(entrada_sig, '%H:%M:%S')
                                salida_time_sig = datetime.strptime(salida_sig, '%H:%M:%S')
                                duracion_sig = salida_time_sig - entrada_time_sig
                                df_proc.loc[idx_siguiente, 'horas_trabajadas'] = str(duracion_sig)
                            else:
                                df_proc.loc[idx_siguiente, 'horas_trabajadas'] = "00:00:00"
    
    print("✅ Procesamiento de turnos con medianoche completado")
    return df_proc


def calcular_proximidad_horario(checada_str, horario_prog_str):
    """
    Calcula la proximidad en minutos entre una checada y un horario programado.
    
    Args:
        checada_str: Hora de checada en formato "HH:MM:SS"
        horario_prog_str: Hora programada en formato "HH:MM"
        
    Returns:
        Diferencia en minutos (valor absoluto)
    """
    try:
        checada_time = datetime.strptime(checada_str, '%H:%M:%S')
        horario_prog_time = datetime.strptime(horario_prog_str + ":00", '%H:%M:%S')
        
        # Calcular diferencia en minutos
        diff = abs((checada_time - horario_prog_time).total_seconds() / 60)
        return diff
    except:
        return float('inf')  # Si hay error, devolver infinito


def analizar_asistencia_con_horarios_cache(df: pd.DataFrame, cache_horarios):
    """
    Enriquece el DataFrame con análisis de horarios y retardos usando el caché de horarios.
    """
    if df.empty:
        return df
    print("\n🔄 Iniciando análisis de horarios y retardos...")

    # Determinar si es primera quincena para cada registro
    df['es_primera_quincena'] = df['dia'].apply(lambda x: x.day <= 15)
    
    # Crear columnas para almacenar los horarios programados
    df['hora_entrada_programada'] = None
    df['hora_salida_programada'] = None
    df['cruza_medianoche'] = False
    df['horas_esperadas'] = None
    
    # Para cada fila, obtener el horario desde la caché
    def obtener_horario_fila(row):
        horario = obtener_horario_empleado(
            row['employee'], 
            row['dia_iso'], 
            row['es_primera_quincena'], 
            cache_horarios
        )
        
        if horario:
            return pd.Series([
                horario.get('hora_entrada'),
                horario.get('hora_salida'),
                horario.get('cruza_medianoche', False),
                str(timedelta(hours=float(horario.get('horas_totales', 0))))
            ])
        return pd.Series([None, None, False, None])
    
    # Aplicar la función a cada fila
    df[['hora_entrada_programada', 'hora_salida_programada', 'cruza_medianoche', 'horas_esperadas']] = df.apply(
        obtener_horario_fila, axis=1, result_type='expand'
    )

    print("   - Calculando retardos y puntualidad con nueva lógica:")
    print("     • Puntual: hasta 15 minutos de tolerancia")
    print("     • Retardo: entre 16 y 30 minutos")
    print("     • Falta Injustificada: más de 30 minutos")

    def analizar_retardo(row):
        if pd.isna(row.get("hora_entrada_programada")):
            return pd.Series(["Día no Laborable", 0])

        if pd.isna(row.get("checado_1")):
            return pd.Series(["Falta", 0])

        # Convertir strings de tiempo a datetime para manejar mejor los cruces de medianoche
        try:
            hora_prog = datetime.strptime(row['hora_entrada_programada'] + ":00", '%H:%M:%S')
            hora_checada = datetime.strptime(row['checado_1'], '%H:%M:%S')
            
            # Para horarios que cruzan medianoche, la entrada puede ser en la tarde/noche
            # Si la hora programada es mayor que 12:00 y la checada es menor que 12:00,
            # probablemente la checada es del día siguiente
            if row.get('cruza_medianoche', False):
                if hora_prog.hour >= 12 and hora_checada.hour < 12:
                    # La checada es del día siguiente, restar un día a la programada para comparar
                    hora_prog = hora_prog - timedelta(days=1)
            
            # Calcular diferencia en minutos
            diferencia = (hora_checada - hora_prog).total_seconds() / 60
            
            # Para horarios normales, si la diferencia es muy negativa, 
            # podría ser que la checada sea del día siguiente
            if not row.get('cruza_medianoche', False) and diferencia < -12 * 60:
                diferencia += 24 * 60  # Añadir un día
            
            # Clasificar según la nueva lógica de puntualidad y retardos:
            # - Puntual: Check-in hasta 15 minutos después de la hora acordada
            # - Retardo: Check-in entre 16 y 30 minutos después (cuenta para acumulación)
            # - Falta Injustificada: Check-in después de 30 minutos (se marca automáticamente como falta)
            if diferencia <= 15:
                tipo = "A Tiempo"
            elif diferencia <= 30:
                tipo = "Retardo"
            else:
                # Más de 30 minutos se considera Falta Injustificada automáticamente
                tipo = "Falta Injustificada"
                
            return pd.Series([tipo, int(diferencia)])
            
        except (ValueError, TypeError):
            # Si hay error en el parsing, considerarlo como falta
            return pd.Series(["Falta", 0])

    df[["tipo_retardo", "minutos_tarde"]] = df.apply(
        analizar_retardo, axis=1, result_type="expand"
    )

    print("   - Verificando acumulación de retardos y faltas para descuentos...")
    df = df.sort_values(by=["employee", "dia"]).reset_index(drop=True)
    df["es_retardo_acumulable"] = (df["tipo_retardo"] == "Retardo").astype(int)
    df["es_falta"] = (df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])).astype(int)
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
    Crea un DataFrame de resumen con totales por empleado, incluyendo faltas justificadas, y
    calcula la diferencia entre horas trabajadas y esperadas ajustadas por permisos.
    """
    print("\n📊 Generando resumen del periodo con cálculo de diferencia de horas y permisos...")
    if df.empty:
        print("   - No hay datos para generar el resumen.")
        return

    # Convertir las columnas de horas a timedelta
    df["horas_trabajadas_td"] = pd.to_timedelta(
        df["horas_trabajadas"].fillna("00:00:00")
    )
    # Para horas esperadas, usar las originales (antes de ajustar por permisos)
    if 'horas_esperadas_originales' in df.columns:
        df["horas_esperadas_originales_td"] = pd.to_timedelta(
            df["horas_esperadas_originales"].fillna("00:00:00")
        )
    else:
        df["horas_esperadas_originales_td"] = pd.to_timedelta(
            df["horas_esperadas"].fillna("00:00:00")
        )
    
    # Convertir horas descontadas por permisos a timedelta
    if 'horas_descontadas_permiso' in df.columns:
        df["horas_descontadas_permiso_td"] = pd.to_timedelta(
            df["horas_descontadas_permiso"].fillna("00:00:00")
        )
    else:
        df["horas_descontadas_permiso_td"] = pd.to_timedelta("00:00:00")

    # Preparar las columnas de faltas
    total_faltas_col = "es_falta_ajustada" if "es_falta_ajustada" in df.columns else "es_falta"
    
    # Agregaciones base para horas y conteo de incidencias
    resumen_final = (
        df.groupby(["employee", "Nombre"])
        .agg(
            total_horas_trabajadas=("horas_trabajadas_td", "sum"),
            total_horas_esperadas=("horas_esperadas_originales_td", "sum"),
            total_horas_descontadas_permiso=("horas_descontadas_permiso_td", "sum"),
            total_retardos=("es_retardo_acumulable", "sum"),
            faltas_del_periodo=(total_faltas_col, "sum"),
            faltas_justificadas=("falta_justificada", "sum") if "falta_justificada" in df.columns else ("es_falta", lambda x: 0),
        )
        .reset_index()
    )

    # Calcular horas esperadas ajustadas (horas esperadas - horas descontadas por permisos)
    resumen_final["total_horas"] = (
        resumen_final["total_horas_esperadas"] - resumen_final["total_horas_descontadas_permiso"]
    )
    
    # Total de faltas es el mismo que faltas del periodo (ya viene ajustado)
    resumen_final["total_faltas"] = resumen_final["faltas_del_periodo"]

    # Diferencia: horas trabajadas - horas esperadas ajustadas
    # Si es positivo = horas extra, si es negativo = horas faltantes
    diferencia_td = resumen_final["total_horas_trabajadas"] - resumen_final["total_horas"]

    def format_timedelta_with_sign(td):
        sign = "+" if td.total_seconds() > 0 else "-" if td.total_seconds() < 0 else ""
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

    # Formatear las columnas de tiempo
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
    resumen_final["total_horas"] = resumen_final["total_horas"].apply(format_positive_timedelta)

    # Ordenar columnas para la presentación
    base_columns = [
        "employee",
        "Nombre",
        "total_horas_trabajadas",
        "total_horas_esperadas",
        "total_horas_descontadas_permiso",
        "total_horas",
        "total_retardos",
        "faltas_del_periodo",
        "faltas_justificadas",
        "total_faltas",
        "diferencia_HHMMSS",
    ]
    
    resumen_final = resumen_final[base_columns]

    output_filename = "resumen_periodo.csv"
    
    # Intentar guardar el archivo, usando un nombre alternativo si hay conflictos
    try:
        resumen_final.to_csv(output_filename, index=False, encoding="utf-8-sig")
        print(f"✅ Resumen del periodo guardado en '{output_filename}'")
    except PermissionError:
        # Si el archivo está abierto, usar un nombre con timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename_alt = f"resumen_periodo_{timestamp}.csv"
        resumen_final.to_csv(output_filename_alt, index=False, encoding="utf-8-sig")
        print(f"⚠️ El archivo original estaba en uso. Resumen guardado en '{output_filename_alt}'")
        output_filename = output_filename_alt
    
    # Mostrar estadísticas de permisos si están disponibles
    if 'faltas_justificadas' in resumen_final.columns:
        total_faltas_justificadas = resumen_final['faltas_justificadas'].sum()
        total_horas_descontadas = resumen_final['total_horas_descontadas_permiso'].apply(
            lambda x: pd.to_timedelta(x).total_seconds() / 3600 if x != "00:00:00" else 0
        ).sum()
        empleados_con_permisos = (resumen_final['faltas_justificadas'] > 0).sum()
        
        print(f"\n📋 Estadísticas de permisos:")
        print(f"   - Empleados con permisos: {empleados_con_permisos}")
        print(f"   - Total faltas justificadas: {total_faltas_justificadas}")
        print(f"   - Total horas descontadas por permisos: {total_horas_descontadas:.2f}")
    
    print("\n**Visualización del Resumen del Periodo:**\n")
    print(resumen_final.to_string())
# ==============================================================================
# SECCIÓN 4.5: FUNCIÓN PARA GENERAR REPORTE HTML INTERACTIVO
# ==============================================================================
def generar_reporte_html(df_detallado: pd.DataFrame, df_resumen: pd.DataFrame, periodo_inicio: str, periodo_fin: str, sucursal: str):
    """
    Genera un reporte HTML interactivo del periodo analizado.
    
    Args:
        df_detallado: DataFrame con los datos detallados por empleado y día
        df_resumen: DataFrame con el resumen del periodo
        periodo_inicio: Fecha de inicio del periodo
        periodo_fin: Fecha de fin del periodo
        sucursal: Nombre de la sucursal
    """
    print("\n📊 Generando reporte HTML interactivo...")
    
    # Convertir datos para JavaScript
    def time_to_decimal(time_str):
        """Convierte tiempo HH:MM:SS a decimal"""
        if pd.isna(time_str) or time_str == "00:00:00" or time_str == "---":
            return 0.0
        try:
            parts = str(time_str).split(':')
            hours = float(parts[0]) if len(parts) > 0 else 0
            minutes = float(parts[1]) if len(parts) > 1 else 0
            seconds = float(parts[2]) if len(parts) > 2 else 0
            return hours + minutes/60 + seconds/3600
        except:
            return 0.0
    
    # Preparar datos del resumen para JavaScript
    employee_data_js = []
    for _, row in df_resumen.iterrows():
        worked_hours = time_to_decimal(row['total_horas_trabajadas'])
        # Para KPIs, usar horas esperadas originales (sin ajustar por permisos)
        expected_hours_original = time_to_decimal(row['total_horas_esperadas'])
        # Para análisis individual, usar horas ajustadas por permisos
        expected_hours_adjusted = time_to_decimal(row['total_horas'])
        permit_hours = time_to_decimal(row.get('total_horas_descontadas_permiso', '00:00:00'))
        
        # Debug: Imprimir valores para los primeros 3 empleados
        if len(employee_data_js) < 3:
            print(f"\n🔍 DEBUG Empleado {len(employee_data_js) + 1}:")
            print(f"  - ID: {row['employee']}")
            print(f"  - Nombre: {row['Nombre']}")
            print(f"  - total_horas_trabajadas: '{row['total_horas_trabajadas']}'")
            print(f"  - total_horas_esperadas: '{row['total_horas_esperadas']}'")
            print(f"  - total_horas: '{row['total_horas']}'")
            print(f"  - worked_hours decimal: {worked_hours}")
            print(f"  - expected_hours_original decimal: {expected_hours_original}")
            print(f"  - expected_hours_adjusted decimal: {expected_hours_adjusted}")
            print(f"  - ¿Válido para gráfica? {expected_hours_adjusted > 0}")
        
        employee_data_js.append({
            'employee': str(row['employee']),
            'name': str(row['Nombre']),
            'workedHours': str(row['total_horas_trabajadas']),
            'expectedHours': str(row['total_horas_esperadas']),
            'permitHours': str(row.get('total_horas_descontadas_permiso', '00:00:00')),
            'netHours': str(row['total_horas']),
            'delays': int(row.get('total_retardos', 0)),
            'absences': int(row.get('faltas_del_periodo', 0)),
            'justifiedAbsences': int(row.get('faltas_justificadas', 0)),
            'totalAbsences': int(row.get('total_faltas', 0)),
            'difference': str(row.get('diferencia_HHMMSS', '00:00:00')),
            'workedDecimal': worked_hours,
            'expectedDecimal': expected_hours_original,  # Usar horas originales para KPIs
            'expectedDecimalAdjusted': expected_hours_adjusted,  # Horas ajustadas para análisis
            'permitDecimal': permit_hours
        })
    
    # Preparar datos de tendencia diaria
    daily_data_js = []
    if not df_detallado.empty and 'dia' in df_detallado.columns:
        # Filtrar solo días laborables (con horarios programados)
        df_laborables = df_detallado[df_detallado['hora_entrada_programada'].notna()].copy()
        
        if not df_laborables.empty:
            daily_summary = df_laborables.groupby(['dia', 'dia_semana']).agg({
                'employee': 'nunique',  # Total empleados únicos por día
                'tipo_falta_ajustada': lambda x: (x.isin(['Falta', 'Falta Injustificada'])).sum(),  # Faltas injustificadas
                'falta_justificada': lambda x: (x == True).sum(),  # Permisos/faltas justificadas
            }).reset_index()
            
            for _, row in daily_summary.iterrows():
                total_empleados = int(row['employee'])
                faltas_injustificadas = int(row['tipo_falta_ajustada'])
                permisos = int(row['falta_justificada'])
                asistencias = total_empleados - faltas_injustificadas - permisos
                
                daily_data_js.append({
                    'date': row['dia'].strftime('%d %b'),
                    'day': str(row['dia_semana']),
                    'attendance': max(0, asistencias),
                    'absences': faltas_injustificadas,
                    'permits': permisos,
                    'total': total_empleados
                })
    
    # Si no hay datos de tendencia, crear datos de ejemplo básicos
    if not daily_data_js:
        # Generar datos básicos para el período
        from datetime import datetime, timedelta
        start_dt = datetime.strptime(periodo_inicio, "%Y-%m-%d")
        end_dt = datetime.strptime(periodo_fin, "%Y-%m-%d")
        current_dt = start_dt
        
        # Días de la semana en español
        days_es = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
        
        while current_dt <= end_dt:
            day_name = days_es[current_dt.weekday()]
            # Estimar datos básicos basados en el resumen
            total_emp = len(employee_data_js)
            estimated_absences = total_absences // 7 if total_absences > 0 else 0
            estimated_permits = total_justified // 7 if total_justified > 0 else 0
            estimated_attendance = max(0, total_emp - estimated_absences - estimated_permits)
            
            daily_data_js.append({
                'date': current_dt.strftime('%d %b'),
                'day': day_name,
                'attendance': estimated_attendance,
                'absences': estimated_absences,
                'permits': estimated_permits,
                'total': total_emp
            })
            current_dt += timedelta(days=1)
    # Calcular KPIs corregidos según las especificaciones
    # Filtrar empleados con horas esperadas > 0 para evitar divisiones por cero
    empleados_validos = [emp for emp in employee_data_js if emp['expectedDecimal'] > 0]
    
    # Calcular días laborales del período
    from datetime import datetime, timedelta
    start_dt = datetime.strptime(periodo_inicio, "%Y-%m-%d")
    end_dt = datetime.strptime(periodo_fin, "%Y-%m-%d")
    dias_laborales = 0
    current_dt = start_dt
    while current_dt <= end_dt:
        # Contar días de lunes a viernes como laborales
        if current_dt.weekday() < 5:  # 0-4 = lunes a viernes
            dias_laborales += 1
        current_dt += timedelta(days=1)
    
    if empleados_validos:
        total_worked = sum(emp['workedDecimal'] for emp in empleados_validos)
        total_expected = sum(emp['expectedDecimal'] for emp in empleados_validos)
        total_delays = sum(emp['delays'] for emp in employee_data_js)
        total_absences = sum(emp['totalAbsences'] for emp in employee_data_js)
        total_justified = sum(emp['justifiedAbsences'] for emp in employee_data_js)
        total_employees = len(employee_data_js)
        
        # Puntualidad mejorada: solo empleados que asistieron al menos una vez Y no tuvieron retardos
        punctual_employees = sum(1 for emp in employee_data_js 
                               if emp['delays'] == 0 and emp['workedDecimal'] > 0)
        
        # Fórmulas corregidas:
        # Tasa de Asistencia = (Σ horas trabajadas / Σ horas planificadas) × 100
        attendance_rate = (total_worked / total_expected * 100) if total_expected > 0 else 0
        
        # Eficiencia Horaria = igual que tasa de asistencia en este contexto
        efficiency_rate = attendance_rate
        
        # Índice de Puntualidad = (empleados puntuales que asistieron / total empleados) × 100
        punctuality_rate = (punctual_employees / total_employees * 100) if total_employees > 0 else 0
        
        # Días perdidos = total de ausencias (justificadas + injustificadas)
        lost_days = total_absences + total_justified
        
        # Porcentaje de capacidad perdida
        total_possible_days = total_employees * dias_laborales
        lost_days_percent = (lost_days / total_possible_days * 100) if total_possible_days > 0 else 0
    else:
        # Si no hay empleados válidos, usar valores por defecto
        attendance_rate = 0
        efficiency_rate = 0
        punctuality_rate = 0
        lost_days = 0
        lost_days_percent = 0    # Generar HTML
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Ejecutivo de Asistencia - {sucursal}</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        /* Estilos Generales - Diseño Ejecutivo */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            min-height: 100vh;
            color: #212529;
            line-height: 1.5;
        }}

        .header {{
            background: white;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08);
            margin-bottom: 2rem;
            border-bottom: 3px solid #0066cc;
        }}

        .header h1 {{
            color: #0066cc;
            font-size: 2.2rem;
            margin-bottom: 0.5rem;
            font-weight: 700;
        }}

        .header p {{
            color: #6c757d;
            font-size: 1.1rem;
            font-weight: 500;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 1rem;
        }}
        
        /* Pestañas - Diseño Limpio */
        .tabs {{
            display: flex;
            justify-content: center;
            margin-bottom: 2rem;
            gap: 1rem;
        }}

        .tab-button {{
            padding: 1rem 2rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            border: 2px solid #0066cc;
            background-color: white;
            color: #0066cc;
            border-radius: 8px;
            transition: all 0.2s ease;
        }}

        .tab-button.active {{
            background: #0066cc;
            color: white;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        /* KPIs Ejecutivos */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .metric-card {{
            background: white;
            border-radius: 12px;
            padding: 2rem;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            border-left: 4px solid;
            position: relative;
        }}

        .metric-card h3 {{
            color: #495057;
            font-size: 0.9rem;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            font-weight: 600;
        }}

        .metric-value {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }}

        .metric-subtitle {{
            font-size: 0.8rem;
            color: #6c757d;
            margin-top: 0.5rem;
        }}

        /* Semáforos de estado */
        .status-indicator {{
            position: absolute;
            top: 15px;
            right: 15px;
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}

        .status-excellent {{ background: #28a745; }}
        .status-good {{ background: #ffc107; }}
        .status-poor {{ background: #dc3545; }}

        .metric-card.attendance {{ border-left-color: #28a745; }}
        .metric-card.attendance .metric-value {{ color: #28a745; }}

        .metric-card.efficiency {{ border-left-color: #007bff; }}
        .metric-card.efficiency .metric-value {{ color: #007bff; }}

        .metric-card.punctuality {{ border-left-color: #ffc107; }}
        .metric-card.punctuality .metric-value {{ color: #fd7e14; }}

        .metric-card.absences {{ border-left-color: #dc3545; }}
        .metric-card.absences .metric-value {{ color: #dc3545; }}

        /* Contenedores de Gráficas */
        .chart-container {{
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }}

        .chart-title {{
            color: #212529;
            font-size: 1.4rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            text-align: left;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid #e9ecef;
        }}

        .chart-subtitle {{
            color: #6c757d;
            font-size: 0.9rem;
            margin-bottom: 1rem;
            font-weight: 500;
        }}

        /* Estilos D3 - Minimalistas */
        .chart svg {{
            width: 100%;
            height: auto;
            font-family: inherit;
        }}

        .axis path, .axis .domain {{
            stroke: #dee2e6;
            stroke-width: 1;
        }}

        .axis .tick line {{
            stroke: #e9ecef;
            stroke-width: 1;
        }}

        .axis .tick text {{
            fill: #6c757d;
            font-size: 12px;
        }}

        .grid line {{
            stroke: #f1f3f4;
            stroke-width: 1;
            stroke-dasharray: 2,2;
        }}

        .tooltip {{
            position: absolute;
            padding: 12px;
            background: rgba(33, 37, 41, 0.95);
            color: white;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 500;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            backdrop-filter: blur(4px);
            z-index: 1000;
        }}

        /* Tabla Ejecutiva */
        .table-section {{
            background: white;
            border-radius: 12px;
            padding: 2rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        }}

        .controls {{
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}

        .search-box {{
            flex: 1;
            min-width: 250px;
        }}

        .search-box input, .filter-select {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }}

        .search-box input:focus, .filter-select:focus {{
            outline: none;
            border-color: #0066cc;
        }}

        .employee-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .employee-table th {{
            background: #f8f9fa;
            padding: 1rem;
            text-align: left;
            font-weight: 600;
            color: #495057;
            border-bottom: 2px solid #dee2e6;
        }}

        .employee-table td {{
            padding: 1rem;
            border-bottom: 1px solid #e9ecef;
        }}

        .employee-table tbody tr:hover {{
            background: #f8f9fa;
        }}

        .status-badge {{
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .status-complete {{ background: #d4edda; color: #155724; }}
        .status-overtime {{ background: #cce5ff; color: #004085; }}
        .status-incomplete {{ background: #f8d7da; color: #721c24; }}

        .positive {{ color: #28a745; font-weight: 600; }}
        .negative {{ color: #dc3545; font-weight: 600; }}

        @media (max-width: 768px) {{
            .header h1 {{ font-size: 1.8rem; }}
            .metrics-grid {{ grid-template-columns: 1fr; }}
            .controls {{ flex-direction: column; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Dashboard Ejecutivo de Asistencia</h1>
        <p>Sucursal: {sucursal.upper()} | Período: {periodo_inicio} - {periodo_fin}</p>
    </div>

    <div class="container">
        <div class="tabs">
            <button class="tab-button active" onclick="window.openTab(event, 'dashboard')">Resumen Ejecutivo</button>
            <button class="tab-button" onclick="window.openTab(event, 'employee-table')">Detalle por Empleado</button>
        </div>

        <div id="dashboard" class="tab-content active">
            <!-- KPIs Principales -->
            <div class="metrics-grid">
                <div class="metric-card attendance">
                    <div class="status-indicator" id="attendanceStatus"></div>
                    <h3>Tasa de Asistencia</h3>
                    <div class="metric-value" id="attendanceRate">{attendance_rate:.1f}%</div>
                    <div class="metric-subtitle">Horas trabajadas vs planificadas</div>
                </div>
                <div class="metric-card efficiency">
                    <div class="status-indicator" id="efficiencyStatus"></div>
                    <h3>Eficiencia Horaria</h3>
                    <div class="metric-value" id="efficiencyRate">{efficiency_rate:.1f}%</div>
                    <div class="metric-subtitle">Productividad del equipo</div>
                </div>
                <div class="metric-card punctuality">
                    <div class="status-indicator" id="punctualityStatus"></div>
                    <h3>Índice de Puntualidad</h3>
                    <div class="metric-value" id="punctualityRate">{punctuality_rate:.0f}%</div>
                    <div class="metric-subtitle">Empleados puntuales activos</div>
                </div>
                <div class="metric-card absences">
                    <div class="status-indicator" id="absencesStatus"></div>
                    <h3>Días Perdidos</h3>
                    <div class="metric-value" id="totalLostDays">{lost_days}</div>
                    <div class="metric-subtitle" id="lostDaysPercent">{lost_days_percent:.1f}% de capacidad perdida</div>
                </div>
            </div>

            <!-- Gráficas Principales -->
            <div class="chart-container">
                <div class="chart-title">Tendencia de Asistencia del Período</div>
                <div class="chart-subtitle">Comparativo de asistencias, faltas y permisos por día</div>
                <div id="dailyTrendChart" class="chart"></div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Eficiencia de Recursos Humanos</div>
                <div class="chart-subtitle">Horas trabajadas vs. horas planificadas por empleado</div>
                <div id="efficiencyChart" class="chart"></div>
            </div>

            <div class="chart-container">
                <div class="chart-title">Análisis de Impacto por Ausencias</div>
                <div class="chart-subtitle">Distribución de faltas y retardos. % de capacidad solo aplica a ausencias.</div>
                <div id="absenceImpactChart" class="chart"></div>
            </div>
        </div>

        <div id="employee-table" class="tab-content">
            <div class="table-section">
                <div class="chart-title">Análisis Individual de Rendimiento</div>
                <div class="controls">
                    <div class="search-box">
                        <input type="text" id="searchInput" placeholder="Buscar empleado..." onkeyup="window.filterTable()">
                    </div>
                    <select id="statusFilter" onchange="window.filterTable()" class="filter-select">
                        <option value="">Todos los estados</option>
                        <option value="complete">Rendimiento Completo</option>
                        <option value="overtime">Tiempo Extra</option>
                        <option value="incomplete">Rendimiento Incompleto</option>
                    </select>
                </div>
                <div style="overflow-x: auto;">
                    <table class="employee-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Empleado</th>
                                <th>Hrs. Trabajadas</th>
                                <th>Hrs. Planificadas</th>
                                <th>Variación</th>
                                <th>Retardos</th>
                                <th>Ausencias</th>
                                <th>Estado</th>
                            </tr>
                        </thead>
                        <tbody id="tableBody"></tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="tooltip"></div>

    <script>
        // Variables globales
        const tooltip = d3.select(".tooltip");
        window.tooltip = tooltip;
        
        // Datos del período analizado
        const employeeData = {employee_data_js};
        const dailyData = {daily_data_js};
        const diasLaborales = {dias_laborales};
        
        // Asegurar que employeeData esté disponible globalmente
        window.employeeData = employeeData;

        console.log("Datos de empleados:", employeeData.length);
        console.log("Datos diarios:", dailyData.length);
        console.log("Días laborales del período:", diasLaborales);
        console.log("Datos diarios:", dailyData);

        // Debug KPIs
        console.log("=== DEBUG KPIs ===");
        const empleadosValidos = employeeData.filter(emp => emp.expectedDecimal > 0);
        console.log("Empleados válidos (horas esperadas > 0):", empleadosValidos.length);
        
        if (empleadosValidos.length > 0) {{
            const totalTrabajadas = empleadosValidos.reduce((sum, emp) => sum + emp.workedDecimal, 0);
            const totalEsperadas = empleadosValidos.reduce((sum, emp) => sum + emp.expectedDecimal, 0);
            console.log("Total horas trabajadas:", totalTrabajadas.toFixed(2));
            console.log("Total horas esperadas:", totalEsperadas.toFixed(2));
            console.log("Tasa calculada:", ((totalTrabajadas / totalEsperadas) * 100).toFixed(1) + "%");
        }}

        // === Utils tiempo ===
        function timeToHours(hhmmss) {{
            if (!hhmmss || hhmmss === "00:00:00") return 0;
            const [h, m, s] = hhmmss.split(":").map(Number);
            return (h || 0) + (m || 0) / 60 + (s || 0) / 3600;
        }}

        function safeDiv(a, b) {{
            return b > 0 ? a / b : 0;
        }}

        // ===== Utils: tiempo y números =====
        function hhmmssToDecimal(hhmmss) {{
            if (!hhmmss || typeof hhmmss !== "string") return 0;
            const [h, m, s] = hhmmss.split(":").map(Number);
            return (h || 0) + (m || 0)/60 + (s || 0)/3600;
        }}

        function safeNumber(n) {{
            return Number.isFinite(n) ? n : 0;
        }}

        function truncateName(name, max=24) {{
            if (!name) return "";
            return name.length > max ? name.slice(0, max) + "…" : name;
        }}

        // ===== Preparación robusta del dataset para eficiencia =====
        // Usa los campos del resumen: total_horas_trabajadas vs total_horas (ajustadas por permisos)
        function prepareEfficiencyData(employeeData) {{
            console.log("Preparando datos de eficiencia...", employeeData.length, "empleados");
            
            // Debug: mostrar estructura del primer empleado
            if (employeeData.length > 0) {{
                console.log("DEBUG: Estructura primer empleado:", employeeData[0]);
            }}
            
            const processedData = employeeData
                .map(d => {{
                    // 1) Horas trabajadas (siempre disponible)
                    const worked = d.workedDecimal != null
                        ? safeNumber(d.workedDecimal)
                        : hhmmssToDecimal(d.workedHours || "00:00:00");

                    // 2) Horas planificadas ajustadas (total_horas = esperadas - permisos)
                    const planned = d.expectedDecimalAdjusted != null
                        ? safeNumber(d.expectedDecimalAdjusted)
                        : hhmmssToDecimal(d.netHours || "00:00:00");

                    // 3) Calcular eficiencia solo si hay horas planificadas
                    const efficiency = planned > 0 ? (worked / planned) * 100 : 0;

                    const fullName = d.name || d.fullName || "";
                    
                    const result = {{
                        name: truncateName(fullName, 24),
                        fullName,
                        efficiency,
                        worked,
                        planned,
                        employee: d.employee
                    }};
                    
                    console.log(`${{d.employee}} - ${{fullName}}: ${{worked.toFixed(2)}}h trabajadas / ${{planned.toFixed(2)}}h planificadas = ${{efficiency.toFixed(1)}}%`);
                    
                    return result;
                }})
                .filter(d => {{
                    const valid = d.planned > 0;
                    if (!valid) {{
                        console.log(`Filtrado empleado ${{d.employee}} - ${{d.fullName}}: sin horas planificadas (${{d.planned}})`);
                    }}
                    return valid;
                }})
                .sort((a, b) => b.efficiency - a.efficiency)
                .slice(0, 15);
                
            console.log("Datos procesados para eficiencia:", processedData.length, "empleados válidos");
            return processedData;
        }}

        // === KPIs: Asistencia (%) y Eficiencia (%) ===
        // Ambas son (Σ horas_trabajadas / Σ horas_planificadas_ajustadas) * 100
        function calculateKPIs() {{
            console.log("Calculando KPIs...");
            
            const rows = employeeData
                .map(e => ({{ 
                    worked: timeToHours(e.workedHours), 
                    planned: timeToHours(e.netHours)  // netHours = total_horas (ajustadas por permisos)
                }}))
                .filter(r => r.planned > 0);

            console.log("Filas válidas para KPIs:", rows.length);
            
            const totalWorked = rows.reduce((a, b) => a + b.worked, 0);
            const totalPlanned = rows.reduce((a, b) => a + b.planned, 0);
            
            console.log(`Total trabajadas: ${{totalWorked.toFixed(2)}}h, Total planificadas: ${{totalPlanned.toFixed(2)}}h`);

            const pct = totalPlanned > 0 ? (totalWorked / totalPlanned) * 100 : 0;
            const attendanceRate = pct.toFixed(1) + "%";
            const efficiencyRate = pct.toFixed(1) + "%";

            console.log(`KPI calculado: ${{pct.toFixed(1)}}%`);

            document.getElementById("attendanceRate").textContent = attendanceRate;
            document.getElementById("efficiencyRate").textContent = efficiencyRate;

            // Puntualidad y días perdidos (si ya existen en el DOM)
            const punctualEmployees = employeeData.filter(emp => emp.delays === 0).length;
            const punctuality = (punctualEmployees / employeeData.length) * 100;
            const totalAbsences = employeeData.reduce((s, e) => s + (e.totalAbsences || 0), 0);
            const totalJustified = employeeData.reduce((s, e) => s + (e.justifiedAbsences || 0), 0);

            const punctualityNode = document.getElementById("punctualityRate");
            if (punctualityNode) punctualityNode.textContent = `${{punctuality.toFixed(0)}}%`;
            const lostNode = document.getElementById("totalLostDays");
            if (lostNode) lostNode.textContent = (totalAbsences + totalJustified).toString();
        }}

        // Función para cambiar pestañas
        window.openTab = function(evt, tabName) {{
            const tabcontent = document.getElementsByClassName("tab-content");
            const tablinks = document.getElementsByClassName("tab-button");
            
            for (let i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].style.display = "none";
            }}
            for (let i = 0; i < tablinks.length; i++) {{
                tablinks[i].classList.remove("active");
            }}
            
            document.getElementById(tabName).style.display = "block";
            evt.currentTarget.classList.add("active");
        }};

        // Función para establecer semáforos de estado
        function setStatusIndicators() {{
            // Semáforo de asistencia
            const attendanceRate = parseFloat(document.getElementById('attendanceRate').textContent);
            const attendanceStatus = document.getElementById('attendanceStatus');
            if (attendanceRate >= 95) {{
                attendanceStatus.className = 'status-indicator status-excellent';
            }} else if (attendanceRate >= 85) {{
                attendanceStatus.className = 'status-indicator status-good';
            }} else {{
                attendanceStatus.className = 'status-indicator status-poor';
            }}

            // Semáforo de eficiencia
            const efficiencyRate = parseFloat(document.getElementById('efficiencyRate').textContent);
            const efficiencyStatus = document.getElementById('efficiencyStatus');
            if (efficiencyRate >= 95) {{
                efficiencyStatus.className = 'status-indicator status-excellent';
            }} else if (efficiencyRate >= 85) {{
                efficiencyStatus.className = 'status-indicator status-good';
            }} else {{
                efficiencyStatus.className = 'status-indicator status-poor';
            }}

            // Semáforo de puntualidad
            const punctualityRate = parseFloat(document.getElementById('punctualityRate').textContent);
            const punctualityStatus = document.getElementById('punctualityStatus');
            if (punctualityRate >= 80) {{
                punctualityStatus.className = 'status-indicator status-excellent';
            }} else if (punctualityRate >= 60) {{
                punctualityStatus.className = 'status-indicator status-good';
            }} else {{
                punctualityStatus.className = 'status-indicator status-poor';
            }}

            // Semáforo de días perdidos (invertido: menos días perdidos = mejor)
            const lostDaysPercent = parseFloat(document.getElementById('lostDaysPercent').textContent);
            const absencesStatus = document.getElementById('absencesStatus');
            if (lostDaysPercent <= 5) {{
                absencesStatus.className = 'status-indicator status-excellent';
            }} else if (lostDaysPercent <= 10) {{
                absencesStatus.className = 'status-indicator status-good';
            }} else {{
                absencesStatus.className = 'status-indicator status-poor';
            }}
        }}

        // Gráfica de tendencia diaria
        function createDailyTrendChart() {{
            console.log("Creando gráfica de tendencia diaria...");
            const container = d3.select("#dailyTrendChart");
            container.html("");

            if (!dailyData || dailyData.length === 0) {{
                console.log("No hay datos diarios disponibles");
                container.append("div")
                    .style("text-align", "center")
                    .style("padding", "2rem")
                    .style("color", "#6c757d")
                    .text("No hay datos de tendencia diaria disponibles");
                return;
            }}

            console.log("Datos diarios:", dailyData);
            const margin = {{ top: 20, right: 120, bottom: 60, left: 48 }};
            const cw = container.node().getBoundingClientRect().width;
            const width = Math.max(480, cw - margin.left - margin.right);
            const height = 400 - margin.top - margin.bottom;

            const svg = container.append("svg")
                .attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g")
                .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            // Series a graficar
            const series = [
                {{ key: "attendance", label: "Asistencias", color: "#28a745", strokeWidth: 3, z: 3 }},
                {{ key: "absences",   label: "Faltas",      color: "#dc3545", strokeWidth: 2, z: 2 }},
                {{ key: "permits",    label: "Permisos",    color: "#ffc107", strokeWidth: 2, z: 1 }}
            ];

            // Escalas
            const x = d3.scaleBand()
                .domain(dailyData.map(d => d.date))
                .range([0, width])
                .padding(0.1);

            const y = d3.scaleLinear()
                .domain([0, d3.max(dailyData, d => Math.max(d.total, d.attendance, d.absences, d.permits)) || 1])
                .nice()
                .range([height, 0]);

            // Ejes (minimalistas, legibles)
            svg.append("g")
                .attr("class", "axis")
                .attr("transform", `translate(0,${{height}})`)
                .call(d3.axisBottom(x))
                .selectAll("text")
                .style("text-anchor", "end")
                .attr("dx", "-0.6em")
                .attr("dy", "0.15em")
                .attr("transform", "rotate(-45)");

            svg.append("g")
                .attr("class", "axis")
                .call(d3.axisLeft(y).ticks(6));

            // Grid horizontal sutil (decluttering)
            svg.append("g")
                .attr("class", "grid")
                .call(d3.axisLeft(y).tickSize(-width).tickFormat(""))
                .selectAll("line")
                .attr("stroke", "#f1f3f4")
                .attr("stroke-dasharray", "2,2");

            // Generador de línea
            const lineGen = key => d3.line()
                .x(d => x(d.date) + x.bandwidth() / 2)
                .y(d => y(d[key]))
                .curve(d3.curveMonotoneX);

            // Dibujar cada serie
            series.forEach(s => {{
                // línea
                svg.append("path")
                    .datum(dailyData)
                    .attr("fill", "none")
                    .attr("stroke", s.color)
                    .attr("stroke-width", s.strokeWidth)
                    .attr("d", lineGen(s.key))
                    .attr("opacity", 0.95);

                // puntos
                svg.selectAll(`.dot-${{s.key}}`)
                    .data(dailyData)
                    .enter()
                    .append("circle")
                    .attr("class", `dot-${{s.key}}`)
                    .attr("cx", d => x(d.date) + x.bandwidth() / 2)
                    .attr("cy", d => y(d[s.key]))
                    .attr("r", 4.5)
                    .attr("fill", s.color)
                    .attr("stroke", "white")
                    .attr("stroke-width", 1.5)
                    .on("mouseover", (event, d) => {{
                        window.tooltip.style("opacity", 1)
                            .html(`<strong>${{d.date}} (${{d.day}})</strong><br/>
                                   Asistencias: ${{d.attendance}}<br/>
                                   Faltas: ${{d.absences}}<br/>
                                   Permisos: ${{d.permits}}<br/>
                                   Total: ${{d.total}}`);
                    }})
                    .on("mousemove", event => {{
                        window.tooltip
                            .style("left", (event.pageX + 10) + "px")
                            .style("top", (event.pageY - 10) + "px");
                    }})
                    .on("mouseout", () => window.tooltip.style("opacity", 0));
            }});

            // Etiquetas del último punto (storytelling)
            series.forEach(s => {{
                const last = dailyData[dailyData.length - 1];
                svg.append("text")
                    .attr("x", x(last.date) + x.bandwidth() / 2 + 8)
                    .attr("y", y(last[s.key]))
                    .attr("dominant-baseline", "middle")
                    .attr("font-size", 12)
                    .attr("font-weight", s.key === "attendance" ? 700 : 600)
                    .attr("fill", s.color)
                    .text(`${{s.label}}: ${{last[s.key]}}`);
            }});

            // Leyenda
            const legend = svg.append("g")
                .attr("transform", `translate(${{width + 16}}, 4)`);
            const li = legend.selectAll(".litem")
                .data(series)
                .enter().append("g")
                .attr("class", "litem")
                .attr("transform", (d, i) => `translate(0, ${{i * 22}})`);
            li.append("line")
                .attr("x1", 0).attr("x2", 20).attr("y1", 8).attr("y2", 8)
                .attr("stroke", d => d.color).attr("stroke-width", d => d.strokeWidth);
            li.append("circle")
                .attr("cx", 10).attr("cy", 8).attr("r", 3.5)
                .attr("fill", d => d.color).attr("stroke", "white").attr("stroke-width", 1);
            li.append("text")
                .attr("x", 28).attr("y", 11)
                .attr("font-size", 12)
                .text(d => d.label);

            console.log("Gráfica diaria completada");
        }}

        // ===== Gráfica: Eficiencia de Recursos Humanos =====
        function createEfficiencyChart() {{
            console.log("=== INICIANDO GRÁFICA DE EFICIENCIA ===");
            console.log("employeeData disponible:", typeof window.employeeData, window.employeeData ? window.employeeData.length : 'undefined');
            
            const container = d3.select("#efficiencyChart");
            container.html(""); // limpiar

            if (!window.employeeData || window.employeeData.length === 0) {{
                console.error("❌ No hay employeeData disponible");
                container.append("div")
                    .style("padding", "2rem")
                    .style("color", "#dc3545")
                    .style("font-weight", "600")
                    .style("text-align", "center")
                    .text("Error: No hay datos de empleados disponibles.");
                return;
            }}

            const data = prepareEfficiencyData(window.employeeData);
            console.log("Datos después de prepareEfficiencyData:", data.length);
            
            if (!data || data.length === 0) {{
                console.log("❌ No hay datos de eficiencia válidos");
                container.append("div")
                    .style("padding", "2rem")
                    .style("color", "#6c757d")
                    .style("font-weight", "600")
                    .style("text-align", "center")
                    .text("Sin datos suficientes para mostrar la eficiencia (no hay horas planificadas).");
                return;
            }}

            console.log("✅ Datos de eficiencia válidos:", data);
            
            // Margen izquierdo amplio para nombres; ajusta dinámicamente en función del nombre más largo
            const longestName = data.reduce((a, b) => (a.length > b.fullName.length ? a : b.fullName), "");
            const baseLeft = 200;
            const extra = Math.min(200, Math.max(0, longestName.length - 18) * 6); // heurística
            const margin = {{ top: 20, right: 30, bottom: 40, left: baseLeft + extra }};

            const cw = container.node().getBoundingClientRect().width;
            const width = Math.max(480, cw - margin.left - margin.right);
            const height = Math.max(420, data.length * 30);

            const svg = container.append("svg")
                .attr("viewBox", `0 0 ${{width + margin.left + margin.right}} ${{height + margin.top + margin.bottom}}`)
                .append("g")
                .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            // Eje X: % con techo dinámico (mínimo 100%)
            const maxEff = d3.max(data, d => d.efficiency) || 0;
            const upper = Math.max(100, Math.ceil(maxEff / 10) * 10, 110); // margen extra por encima de 100
            const x = d3.scaleLinear().domain([0, upper]).range([0, width]);

            // Eje Y: nombres
            const y = d3.scaleBand()
                .domain(data.map(d => d.name))
                .range([0, height])
                .padding(0.15);

            // Ejes
            svg.append("g")
                .attr("class", "axis")
                .call(d3.axisLeft(y).tickSize(0))
                .select(".domain").remove();

            svg.append("g")
                .attr("class", "axis")
                .attr("transform", `translate(0,${{height}})`)
                .call(d3.axisBottom(x).tickFormat(d => d + "%"));

            // Grid horizontal sutil (decluttering)
            svg.append("g")
                .attr("class", "grid")
                .call(d3.axisBottom(x).tickSize(height).tickFormat(""))
                .selectAll("line")
                .attr("stroke", "#f1f3f4")
                .attr("stroke-dasharray", "2,2");

            // Línea de referencia 100%
            if (x(100) <= width) {{
                svg.append("line")
                    .attr("x1", x(100))
                    .attr("x2", x(100))
                    .attr("y1", 0)
                    .attr("y2", height)
                    .attr("stroke", "#dc3545")
                    .attr("stroke-width", 2)
                    .attr("stroke-dasharray", "5,5");
            }}

            // Barras con color semáforo
            svg.selectAll(".bar")
                .data(data)
                .enter().append("rect")
                .attr("class", "bar")
                .attr("x", 0)
                .attr("y", d => y(d.name))
                .attr("width", d => x(d.efficiency))
                .attr("height", y.bandwidth())
                .attr("fill", d => d.efficiency >= 100 ? "#28a745" : (d.efficiency >= 80 ? "#ffc107" : "#dc3545"))
                .on("mouseover", (event, d) => {{
                    window.tooltip.style("opacity", 1)
                        .html(
                            `<strong>${{d.fullName}}</strong><br/>
                             Eficiencia: ${{d.efficiency.toFixed(1)}}%<br/>
                             Trabajadas: ${{d.worked.toFixed(1)}} h<br/>
                             Planificadas: ${{d.planned.toFixed(1)}} h`
                        );
                }})
                .on("mousemove", event => {{
                    window.tooltip
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 10) + "px");
                }})
                .on("mouseout", () => window.tooltip.style("opacity", 0))
                .append("title")
                .text(d => d.fullName); // accesibilidad extra

            // Etiquetas de porcentaje con colocación inteligente
            svg.selectAll(".label")
                .data(data)
                .enter().append("text")
                .attr("class", "label")
                .attr("y", d => y(d.name) + y.bandwidth() / 2)
                .attr("dy", "0.35em")
                .attr("x", d => {{
                    const px = x(d.efficiency);
                    // si la barra es muy corta, coloca afuera
                    return px > 40 ? px - 6 : px + 6;
                }})
                .attr("text-anchor", d => x(d.efficiency) > 40 ? "end" : "start")
                .attr("fill", d => x(d.efficiency) > 40 ? "white" : "#212529")
                .attr("font-weight", 600)
                .attr("font-size", "12px")
                .text(d => `${{d.efficiency.toFixed(1)}}%`);

            // (Opcional) Anotaciones storytelling: top y bottom
            const top = data[0];
            const bottom = data[data.length - 1];
            if (top) {{
                svg.append("text")
                    .attr("x", x(top.efficiency) + 10)
                    .attr("y", y(top.name) + y.bandwidth() / 2)
                    .attr("dy", "0.35em")
                    .attr("fill", "#28a745")
                    .attr("font-size", 11)
                    .attr("font-weight", 600)
                    .text("Top");
            }}
            if (bottom && bottom !== top) {{
                svg.append("text")
                    .attr("x", x(bottom.efficiency) + 10)
                    .attr("y", y(bottom.name) + y.bandwidth() / 2)
                    .attr("dy", "0.35em")
                    .attr("fill", "#dc3545")
                    .attr("font-size", 11)
                    .attr("font-weight", 600)
                    .text("Bottom");
            }}

            console.log("✅ Gráfica de eficiencia completada exitosamente");
        }}

        // ===== Gráfica: Análisis de Impacto por Ausencias (Refactorizada) =====
        function createAbsenceImpactChart() {{
            console.log("=== INICIANDO GRÁFICA DE IMPACTO POR AUSENCIAS ===");
            const container = d3.select("#absenceImpactChart");
            container.html("");

            // 1) Validación robusta de datos
            if (!window.employeeData || !Array.isArray(window.employeeData) || window.employeeData.length === 0) {{
                console.warn("❌ No hay datos de empleados disponibles para análisis de ausencias");
                container.append("div")
                    .style("padding", "2rem")
                    .style("color", "#6c757d")
                    .style("font-weight", "500")
                    .style("text-align", "center")
                    .style("background", "#f8f9fa")
                    .style("border-radius", "8px")
                    .text("No hay datos de empleados disponibles para el análisis de ausencias.");
                return;
            }}

            // 2) Cálculo seguro de totales con fallbacks
            const totalUnjustified = window.employeeData.reduce((sum, emp) => {{
                // Priorizar 'absences' sobre 'faltas_del_periodo', fallback a 0
                const unjustified = emp.absences ?? emp.faltas_del_periodo ?? 0;
                return sum + (Number.isFinite(unjustified) ? unjustified : 0);
            }}, 0);

            const totalJustified = window.employeeData.reduce((sum, emp) => {{
                const justified = emp.justifiedAbsences ?? emp.faltas_justificadas ?? 0;
                return sum + (Number.isFinite(justified) ? justified : 0);
            }}, 0);

            const totalDelays = window.employeeData.reduce((sum, emp) => {{
                const delays = emp.delays ?? emp.total_retardos ?? 0;
                return sum + (Number.isFinite(delays) ? delays : 0);
            }}, 0);

            // 3) Determinar días laborales de forma segura
            let diasLaboralesCalc = 0;
            if (typeof diasLaborales !== 'undefined' && Number.isFinite(diasLaborales) && diasLaborales > 0) {{
                diasLaboralesCalc = diasLaborales;
            }} else if (typeof dailyData !== 'undefined' && Array.isArray(dailyData) && dailyData.length > 0) {{
                diasLaboralesCalc = dailyData.length;
                console.log("📊 Días laborales inferidos de dailyData:", diasLaboralesCalc);
            }} else {{
                diasLaboralesCalc = 10; // Valor por defecto documentado (2 semanas típicas)
                console.warn("⚠️ Usando días laborales por defecto:", diasLaboralesCalc);
            }}

            // 4) Calcular totales para verificación
            const totalEmployees = window.employeeData.length;
            const totalPossibleDays = totalEmployees * diasLaboralesCalc;

            // 5) Logging de trazabilidad (solo en desarrollo)
            console.log("📊 DATOS DE AUSENCIAS:");
            console.log(`  - Total empleados: ${{totalEmployees}}`);
            console.log(`  - Días laborales: ${{diasLaboralesCalc}}`);
            console.log(`  - Días posibles totales: ${{totalPossibleDays}}`);
            console.log(`  - Faltas injustificadas: ${{totalUnjustified}}`);
            console.log(`  - Faltas justificadas: ${{totalJustified}}`);
            console.log(`  - Retardos: ${{totalDelays}}`);

            // 6) Función helper para calcular porcentaje seguro
            function calculateCapacityPercentage(absences, totalDays) {{
                if (!Number.isFinite(absences) || !Number.isFinite(totalDays) || totalDays <= 0) {{
                    return "—";
                }}
                return ((absences / totalDays) * 100).toFixed(1);
            }}

            // 7) Estructura de datos fija y consistente
            const impactData = [
                {{
                    type: "Faltas Injustificadas",
                    shortType: "Injustificadas",
                    count: totalUnjustified,
                    impact: "Alto",
                    color: "#dc3545",
                    percentage: calculateCapacityPercentage(totalUnjustified, totalPossibleDays),
                    focus: true // Para destacar visualmente
                }},
                {{
                    type: "Faltas Justificadas", 
                    shortType: "Justificadas",
                    count: totalJustified,
                    impact: "Medio",
                    color: "#ffc107",
                    percentage: calculateCapacityPercentage(totalJustified, totalPossibleDays),
                    focus: false
                }},
                {{
                    type: "Retardos",
                    shortType: "Retardos", 
                    count: totalDelays,
                    impact: "Bajo",
                    color: "#17a2b8",
                    percentage: "—", // No aplica a retardos
                    focus: false
                }}
            ];

            // 8) Verificar si hay datos para mostrar
            const totalEvents = totalUnjustified + totalJustified + totalDelays;
            if (totalEvents === 0) {{
                console.log("ℹ️ Sin datos de ausencias/retardos en el período");
                container.append("div")
                    .style("padding", "2rem")
                    .style("color", "#28a745")
                    .style("font-weight", "500")
                    .style("text-align", "center")
                    .style("background", "#d4edda")
                    .style("border-radius", "8px")
                    .style("border", "1px solid #c3e6cb")
                    .text("Sin ausencias ni retardos registrados en el período. ¡Excelente asistencia!");
                return;
            }}

            // 9) Configuración de dimensiones y escalas
            const margin = {{top: 30, right: 40, bottom: 90, left: 60}};
            const containerWidth = container.node().getBoundingClientRect().width;
            const width = Math.max(450, containerWidth - margin.left - margin.right);
            const height = 350 - margin.top - margin.bottom;

            // 10) Crear SVG con accesibilidad
            const svg = container.append("svg")
                .attr("viewBox", `0 0 ${{containerWidth}} 430`)
                .attr("role", "img")
                .attr("aria-label", `Gráfica de impacto por ausencias: ${{totalUnjustified}} faltas injustificadas (mayor impacto), ${{totalJustified}} justificadas, ${{totalDelays}} retardos`)
                .append("g")
                .attr("transform", `translate(${{margin.left}},${{margin.top}})`);

            // 11) Escalas optimizadas
            const maxCount = Math.max(1, d3.max(impactData, d => d.count) || 0);
            const yUpperLimit = maxCount + Math.ceil(maxCount * 0.15); // 15% de margen superior

            const xScale = d3.scaleBand()
                .domain(impactData.map(d => d.shortType))
                .range([0, width])
                .padding(0.4); // Más espacio entre barras para claridad

            const yScale = d3.scaleLinear()
                .domain([0, yUpperLimit])
                .range([height, 0])
                .nice();

            // 12) Ejes limpios y legibles
            svg.append("g")
                .attr("class", "axis")
                .attr("transform", `translate(0,${{height}})`)
                .call(d3.axisBottom(xScale).tickSize(0))
                .select(".domain").remove();

            svg.append("g")
                .attr("class", "axis")
                .call(d3.axisLeft(yScale).ticks(6).tickSize(-width))
                .call(g => {{
                    g.select(".domain").remove();
                    g.selectAll(".tick line")
                        .attr("stroke", "#f1f3f4")
                        .attr("stroke-dasharray", "2,2");
                    g.selectAll(".tick text")
                        .attr("fill", "#6c757d")
                        .attr("font-size", "12px");
                }});

            // 13) Barras principales con enfoque visual
            svg.selectAll(".impact-bar")
                .data(impactData)
                .enter().append("rect")
                .attr("class", "impact-bar")
                .attr("x", d => xScale(d.shortType))
                .attr("y", d => yScale(d.count))
                .attr("width", xScale.bandwidth())
                .attr("height", d => height - yScale(d.count))
                .attr("fill", d => d.color)
                .attr("stroke", d => d.focus ? "#212529" : "white") // Destacar faltas injustificadas
                .attr("stroke-width", d => d.focus ? 2 : 1)
                .attr("opacity", 0.9)
                .on("mouseover", (event, d) => {{
                    // Tooltip enriquecido según especificaciones
                    let tooltipHTML = `<strong>${{d.type}}</strong><br/>Cantidad: ${{d.count}}<br/>Impacto: ${{d.impact}}`;
                    
                    if (d.percentage !== "—") {{
                        tooltipHTML += `<br/>% Capacidad: ${{d.percentage}}%<br/><small>sobre ${{totalPossibleDays}} días-persona</small>`;
                    }}
                    
                    window.tooltip.style("opacity", 1).html(tooltipHTML);
                }})
                .on("mousemove", event => {{
                    window.tooltip
                        .style("left", (event.pageX + 15) + "px")
                        .style("top", (event.pageY - 10) + "px");
                }})
                .on("mouseout", () => window.tooltip.style("opacity", 0));

            // 14) Etiquetas de conteo sobre las barras
            svg.selectAll(".count-label")
                .data(impactData.filter(d => d.count > 0))
                .enter().append("text")
                .attr("class", "count-label")
                .attr("x", d => xScale(d.shortType) + xScale.bandwidth() / 2)
                .attr("y", d => yScale(d.count) - 8)
                .attr("text-anchor", "middle")
                .attr("font-weight", "bold")
                .attr("font-size", "14px")
                .attr("fill", "#212529")
                .text(d => d.count);

            // 15) Etiquetas de porcentaje solo para faltas
            svg.selectAll(".percentage-label")
                .data(impactData.filter(d => d.percentage !== "—" && d.count > 0))
                .enter().append("text")
                .attr("class", "percentage-label")
                .attr("x", d => xScale(d.shortType) + xScale.bandwidth() / 2)
                .attr("y", d => yScale(d.count) - 28)
                .attr("text-anchor", "middle")
                .attr("font-size", "11px")
                .attr("font-weight", "500")
                .attr("fill", "#495057")
                .text(d => `(${{d.percentage}}%)`);

            // 16) Etiquetas de impacto bajo las barras
            svg.selectAll(".impact-label")
                .data(impactData)
                .enter().append("text")
                .attr("class", "impact-label")
                .attr("x", d => xScale(d.shortType) + xScale.bandwidth() / 2)
                .attr("y", height + 35)
                .attr("text-anchor", "middle")
                .attr("font-size", "10px")
                .attr("font-weight", "600")
                .attr("fill", d => d.color)
                .text(d => `Impacto ${{d.impact}}`);

            // 17) Mensaje informativo si no hay base de capacidad
            if (totalPossibleDays <= 0) {{
                svg.append("text")
                    .attr("x", width / 2)
                    .attr("y", -10)
                    .attr("text-anchor", "middle")
                    .attr("font-size", "11px")
                    .attr("fill", "#6c757d")
                    .attr("font-style", "italic")
                    .text("% de capacidad no disponible - sin base de cálculo");
            }}

            console.log("✅ Gráfica de impacto por ausencias completada exitosamente");
        }}

        // Función para envolver texto
        function wrapText(text, width) {{
            text.each(function() {{
                const textElement = d3.select(this);
                const words = textElement.text().split(/\\s+/).reverse();
                let word;
                let line = [];
                let lineNumber = 0;
                const lineHeight = 1.1;
                const y = textElement.attr("y");
                const dy = parseFloat(textElement.attr("dy")) || 0;
                let tspan = textElement.text(null).append("tspan").attr("x", 0).attr("y", y).attr("dy", dy + "em");
                
                while (word = words.pop()) {{
                    line.push(word);
                    tspan.text(line.join(" "));
                    if (tspan.node().getComputedTextLength() > width) {{
                        line.pop();
                        tspan.text(line.join(" "));
                        line = [word];
                        tspan = textElement.append("tspan").attr("x", 0).attr("y", y).attr("dy", ++lineNumber * lineHeight + dy + "em").text(word);
                    }}
                }}
            }});
        }}

        // Funciones de la tabla
        function getStatus(difference) {{
            const isPositive = difference.startsWith('+');
            const timeStr = difference.substring(1);
            const hours = timeToHours(timeStr);
            
            if (isPositive && hours > 1) return 'overtime';
            if (!isPositive && hours > 0.5) return 'incomplete';
            return 'complete';
        }}

        function renderTable(data) {{
            const tableBody = document.getElementById('tableBody');
            tableBody.innerHTML = '';
            
            if (data.length === 0) {{
                tableBody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding: 20px; color: #6c757d;">No se encontraron empleados que coincidan con los criterios de búsqueda.</td></tr>';
                return;
            }}

            data.forEach(emp => {{
                const status = getStatus(emp.difference);
                const row = document.createElement('tr');
                
                const statusLabels = {{
                    'complete': 'Completo',
                    'overtime': 'Tiempo Extra',
                    'incomplete': 'Incompleto'
                }};

                row.innerHTML = `
                    <td><strong>${{emp.employee}}</strong></td>
                    <td>${{emp.name}}</td>
                    <td>${{emp.workedHours}}</td>
                    <td>${{emp.netHours}}</td>
                    <td class="${{emp.difference.startsWith('+') ? 'positive' : 'negative'}}">${{emp.difference}}</td>
                    <td>${{emp.delays}}</td>
                    <td>${{emp.totalAbsences + emp.justifiedAbsences}}</td>
                    <td><span class="status-badge status-${{status}}">${{statusLabels[status]}}</span></td>
                `;
                tableBody.appendChild(row);
            }});
        }}

        // Función de filtrado de tabla
        window.filterTable = function() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase();
            const statusFilter = document.getElementById('statusFilter').value;
            
            const filteredData = employeeData.filter(employee => {{
                const matchesSearch = employee.name.toLowerCase().includes(searchTerm) ||
                                        employee.employee.toString().includes(searchTerm);
                const matchesStatus = !statusFilter || getStatus(employee.difference) === statusFilter;
                return matchesSearch && matchesStatus;
            }});
            
            renderTable(filteredData);
        }};

        // Inicialización
        function initDashboard() {{
            console.log("Inicializando dashboard...");
            console.log("Empleados:", employeeData.length);
            console.log("Días:", dailyData.length);
            
            // Calcular KPIs corregidos
            calculateKPIs();
            
            // Establecer semáforos de estado
            setStatusIndicators();
            
            // Esperar a que D3 esté completamente cargado
            setTimeout(() => {{
                try {{
                    createDailyTrendChart();
                    console.log("Gráfica diaria creada");
                }} catch (e) {{
                    console.error("Error en gráfica diaria:", e);
                }}
                
                try {{
                    createEfficiencyChart();
                    console.log("Gráfica de eficiencia creada");
                }} catch (e) {{
                    console.error("Error en gráfica de eficiencia:", e);
                }}
                
                try {{
                    createAbsenceImpactChart();
                    console.log("Gráfica de ausencias creada");
                }} catch (e) {{
                    console.error("Error en gráfica de ausencias:", e);
                }}
                
                try {{
                    renderTable(employeeData);
                    console.log("Tabla renderizada");
                }} catch (e) {{
                    console.error("Error en tabla:", e);
                }}
            }}, 500);
        }}

        // Event listeners
        document.addEventListener('DOMContentLoaded', initDashboard);

        let resizeTimer;
        window.addEventListener('resize', () => {{
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(() => {{
                createDailyTrendChart();
                createEfficiencyChart();
                createAbsenceImpactChart();
            }}, 250);
        }});
    </script>
</body>
</html>"""

    # Guardar el archivo HTML
    html_filename = "dashboard_asistencia.html"
    
    try:
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✅ Dashboard HTML generado exitosamente: '{html_filename}'")
    except PermissionError:
        # Si el archivo está abierto, usar un nombre con timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename_alt = f"dashboard_asistencia_{timestamp}.html"
        with open(html_filename_alt, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"⚠️ El archivo original estaba en uso. Dashboard guardado en '{html_filename_alt}'")
        html_filename = html_filename_alt
    
    print(f"🌐 Puedes abrir el dashboard en tu navegador: {html_filename}")
    return html_filename
# ==============================================================================
# SECCIÓN 5: EJECUCIÓN PRINCIPAL DEL SCRIPT
# ==============================================================================
if __name__ == "__main__":
    # Define aquí el rango de fechas y el dispositivo que quieres analizar
    start_date = "2025-07-01"
    end_date = "2025-07-15"
    sucursal = "31pte"
    device_filter = "%31%"
    
    # Determinar si es primera quincena según la fecha de inicio
    fecha_inicio_dt = datetime.strptime(start_date, "%Y-%m-%d")
    es_primera_quincena = fecha_inicio_dt.day <= 15

    print(f"\n🚀 Iniciando generación de reporte para {sucursal} - {'Primera' if es_primera_quincena else 'Segunda'} quincena")
    
    # 1. Obtener datos de la API para las checadas primero
    print("\n📡 Paso 1: Obteniendo checadas de la API...")
    checkin_records = fetch_checkins(start_date, end_date, device_filter)

    if not checkin_records:
        print("❌ Error: No se obtuvieron registros de checadas de la API.")
        exit(1)
    
    # 2. Extraer los códigos de empleados de la API
    codigos_empleados_api = obtener_codigos_empleados_api(checkin_records)
    print(f"📑 Se obtuvieron {len(codigos_empleados_api)} códigos de empleados únicos de la API.")
    
    # 2.5. Obtener permisos aprobados de la API para el mismo período
    print("\n📄 Paso 2.5: Obteniendo permisos aprobados de la API...")
    leave_records = fetch_leave_applications(start_date, end_date)
    
    # Procesar permisos por empleado y fecha
    permisos_dict = procesar_permisos_empleados(leave_records)
    
    # 3. Conectar a PostgreSQL y obtener horarios filtrados por los códigos de la API
    print("\n📋 Paso 3: Obteniendo horarios programados desde la base de datos...")
    conn_pg = connect_db()
    
    if conn_pg is None:
        print("❌ Error: No se pudo conectar a la base de datos PostgreSQL. Verificar configuración.")
        exit(1)
    
    # Debug: Verificar sucursales disponibles
    try:
        cursor = conn_pg.cursor()
        cursor.execute("SELECT sucursal_id, nombre_sucursal FROM Sucursales ORDER BY sucursal_id")
        sucursales_disponibles = cursor.fetchall()
        print("\nSucursales disponibles en la base de datos:")
        for suc in sucursales_disponibles:
            print(f"ID: {suc[0]}, Nombre: {suc[1]}")
        cursor.close()
    except Exception as e:
        print(f"Error al consultar sucursales: {e}")

    print(f"\nConsultando horarios para sucursal: '{sucursal}', primera quincena: {es_primera_quincena}")
    print(f"Filtrando por {len(codigos_empleados_api)} códigos frappe de la API")
    
    # Obtener horarios programados filtrados por los códigos frappe de la API
    horarios_programados = obtener_tabla_horarios(sucursal, es_primera_quincena, conn_pg, codigos_empleados_api)
    conn_pg.close()
    
    if not horarios_programados:
        print(f"❌ Error: No se encontraron horarios programados para la sucursal {sucursal} con los códigos de empleados de la API.")
        print("Códigos de empleados de la API:", codigos_empleados_api[:10], "..." if len(codigos_empleados_api) > 10 else "")
        exit(1)
    
    # Verificar que los horarios corresponden a la sucursal correcta
    print(f"✅ Se obtuvieron horarios para {len(horarios_programados)} empleados.")
    if horarios_programados and len(horarios_programados) > 0:
        print(f"Verificando sucursal de los datos obtenidos: '{horarios_programados[0]['nombre_sucursal']}'")
        if horarios_programados[0]['nombre_sucursal'] != sucursal:
            print(f"⚠️ ADVERTENCIA: Se solicitó la sucursal '{sucursal}' pero los datos son de '{horarios_programados[0]['nombre_sucursal']}'")
    
    # 4. Mapear los horarios obtenidos por empleado y día usando los códigos frappe
    print("\n📅 Paso 4: Preparando caché de horarios por empleado y día...")
    cache_horarios = mapear_horarios_por_empleado(horarios_programados, set(codigos_empleados_api))
    print(f"✅ Caché de horarios creada para {len(cache_horarios)} empleados.")
    
    # Mostrar algunos empleados mapeados para verificación
    print("\nEmpleados con horarios mapeados:")
    for i, codigo in enumerate(list(cache_horarios.keys())[:5]):
        dias_con_horario = len([dia for dia in cache_horarios[codigo] if cache_horarios[codigo][dia]])
        print(f"  - Código {codigo}: {dias_con_horario} días programados")
    
    # 5. Crear el DataFrame base con las checadas
    print("\n📊 Paso 5: Procesando checadas y creando DataFrame base...")
    df_base = process_checkins_to_dataframe(checkin_records, start_date, end_date)
    
    # 6. Procesar los turnos que cruzan la medianoche
    print("\n🔄 Paso 6: Procesando turnos que cruzan medianoche...")
    df_procesado = procesar_horarios_con_medianoche(df_base, cache_horarios)
    
    # 7. Aplicar el análisis de asistencia usando el caché de horarios
    print("\n📈 Paso 7: Analizando asistencia con horarios programados...")
    df_analizado = analizar_asistencia_con_horarios_cache(df_procesado, cache_horarios)
    
    # 8. Ajustar horas esperadas considerando permisos aprobados
    print("\n🏖️ Paso 8: Ajustando horas esperadas con permisos aprobados...")
    df_con_permisos = ajustar_horas_esperadas_con_permisos(df_analizado, permisos_dict, cache_horarios)
    
    # 9. Reclasificar faltas considerando permisos
    print("\n📋 Paso 9: Reclasificando faltas con permisos...")
    df_final_permisos = clasificar_faltas_con_permisos(df_con_permisos)

    # 10. Organizar y guardar el reporte detallado
    print("\n💾 Paso 10: Generando reporte detallado...")
    checado_cols = sorted(
        [c for c in df_final_permisos.columns if "checado_" in c and c != "checado_1"]
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
        "tipo_falta_ajustada",
        "tiene_permiso",
        "tipo_permiso",
        "falta_justificada",
        "hora_salida_programada",
        "cruza_medianoche",
        "horas_esperadas_originales",
        "horas_esperadas",
        "horas_descontadas_permiso",
        "horas_trabajadas",
        "retardos_acumulados",
        "descuento_por_3_retardos",
    ] + checado_cols

    final_columns = [col for col in column_order if col in df_final_permisos.columns]
    df_final = df_final_permisos[final_columns].fillna("---")

    output_filename_detallado = "reporte_asistencia_analizado.csv"
    
    # Intentar guardar el archivo, usando un nombre alternativo si hay conflictos
    try:
        df_final.to_csv(output_filename_detallado, index=False, encoding="utf-8-sig")
        print(f"\n\n🎉 ¡Reporte detallado finalizado! Los datos se han guardado en '{output_filename_detallado}'")
    except PermissionError:
        # Si el archivo está abierto, usar un nombre con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename_detallado_alt = f"reporte_asistencia_analizado_{timestamp}.csv"
        df_final.to_csv(output_filename_detallado_alt, index=False, encoding="utf-8-sig")
        print(f"\n\n🎉 ¡Reporte detallado finalizado! El archivo original estaba en uso. Los datos se han guardado en '{output_filename_detallado_alt}'")
        output_filename_detallado = output_filename_detallado_alt
    print("\n**Visualización de las primeras 15 filas del reporte detallado:**\n")
    print(df_final.head(15).to_string())

    # 11. Generar y guardar el reporte de resumen
    print("\n📋 Paso 11: Generando reporte de resumen...")
    generar_resumen_periodo(df_final_permisos)
    
    # 12. Generar dashboard HTML interactivo
    print("\n🌐 Paso 12: Generando dashboard HTML interactivo...")
    try:
        # Leer el resumen recién generado para el dashboard
        resumen_filename = "resumen_periodo.csv"
        if not os.path.exists(resumen_filename):
            # Buscar archivo con timestamp
            resumen_files = glob.glob("resumen_periodo_*.csv")
            if resumen_files:
                resumen_filename = max(resumen_files)  # Tomar el más reciente
        
        if os.path.exists(resumen_filename):
            df_resumen_para_html = pd.read_csv(resumen_filename, encoding='utf-8-sig')
            html_filename = generar_reporte_html(
                df_final_permisos, 
                df_resumen_para_html, 
                start_date, 
                end_date, 
                sucursal
            )
            print(f"✅ Dashboard HTML disponible en: {html_filename}")
        else:
            print("⚠️ No se pudo encontrar el archivo de resumen para generar el dashboard HTML")
    except Exception as e:
        print(f"⚠️ Error al generar el dashboard HTML: {e}")
        print("   Los archivos CSV se generaron correctamente.")
