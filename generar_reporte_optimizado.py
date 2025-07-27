import json
import os
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
# SECCIÓN 5: EJECUCIÓN PRINCIPAL DEL SCRIPT
# ==============================================================================
if __name__ == "__main__":
    # Define aquí el rango de fechas y el dispositivo que quieres analizar
    start_date = "2025-07-16"
    end_date = "2025-07-23"
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
