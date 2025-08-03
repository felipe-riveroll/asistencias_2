"""
Data processing module for the attendance reporting system.
Contains all core business logic for processing check-ins, schedules, and generating analysis.
"""

import pandas as pd
from datetime import datetime, timedelta, time
from itertools import product
from typing import Dict, List

from config import (
    POLITICA_PERMISOS,
    PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA,
    TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS,
    TOLERANCIA_RETARDO_MINUTOS,
    UMBRAL_FALTA_INJUSTIFICADA_MINUTOS,
    DIAS_ESPANOL,
)
from utils import td_to_str, safe_timedelta
from db_postgres_connection import obtener_horario_empleado


class AttendanceProcessor:
    """Main class for processing attendance data and applying business rules."""

    def __init__(self):
        """Initialize the attendance processor."""
        pass

    def process_checkins_to_dataframe(
        self, checkin_data: List[Dict], start_date: str, end_date: str
    ) -> pd.DataFrame:
        """Creates a base DataFrame with one row per employee and day."""
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

        # Calculate duration as Timedelta and save in duration column
        df_hours = (
            df.groupby(["employee", "dia"])["time"].agg(["min", "max"]).reset_index()
        )
        df_hours["duration"] = df_hours["max"] - df_hours["min"]

        # Keep duration as Timedelta, only convert to string for compatibility
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
            df_pivot.columns = [
                f"checado_{i}" for i in range(1, len(df_pivot.columns) + 1)
            ]

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

        final_df["dia_semana"] = (
            pd.to_datetime(final_df["dia"]).dt.day_name().map(DIAS_ESPANOL)
        )
        final_df["dia_iso"] = pd.to_datetime(final_df["dia"]).dt.weekday + 1

        return final_df

    def calcular_horas_descanso(self, df_dia) -> timedelta:
        """
        Calculates break hours based on check-ins for the day.
        Allows multiple break intervals (pairs 1-2, 3-4, etc.) summing all.
        """
        # Get all available check-in columns
        if hasattr(df_dia, "columns"):
            # It's a DataFrame
            checado_cols = [col for col in df_dia.columns if col.startswith("checado_")]
        else:
            # It's a Series
            checado_cols = [col for col in df_dia.index if col.startswith("checado_")]

        if len(checado_cols) < 4:
            return timedelta(0)

        # Get check-in values for this day/employee
        checados = []
        for col in checado_cols:
            if hasattr(df_dia, "columns"):
                valor = df_dia.get(col)
            else:
                valor = df_dia.get(col, None)
            if pd.notna(valor) and valor is not None and valor != "---":
                checados.append(valor)

        # Filter check-ins with dropna() and require len(checados) >= 4
        checados = [c for c in checados if pd.notna(c)]
        if len(checados) < 4:
            return timedelta(0)

        # Sort check-ins chronologically
        checados_ordenados = sorted(checados, key=lambda x: str(x))

        # Calculate multiple break intervals (pairs 1-2, 3-4, etc.)
        total_descanso = timedelta(0)

        try:
            # Process pairs of check-ins to calculate breaks
            for i in range(1, len(checados_ordenados) - 1, 2):
                if i + 1 < len(checados_ordenados):
                    # Take second and third check-in of the pair
                    segundo_checado = checados_ordenados[i]
                    tercer_checado = checados_ordenados[i + 1]

                    # Convert to datetime to calculate difference
                    if isinstance(segundo_checado, time):
                        segundo_dt = datetime.combine(datetime.today(), segundo_checado)
                    else:
                        segundo_dt = datetime.strptime(str(segundo_checado), "%H:%M:%S")

                    if isinstance(tercer_checado, time):
                        tercer_dt = datetime.combine(datetime.today(), tercer_checado)
                    else:
                        tercer_dt = datetime.strptime(str(tercer_checado), "%H:%M:%S")

                    # Calculate difference
                    descanso_intervalo = tercer_dt - segundo_dt

                    # Only add if difference is positive
                    if descanso_intervalo.total_seconds() > 0:
                        total_descanso += descanso_intervalo

            return total_descanso

        except (ValueError, TypeError):
            return timedelta(0)

    def aplicar_calculo_horas_descanso(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies break hours calculation to the entire DataFrame and adjusts worked and expected hours.
        Keeps columns as Timedelta; formats to text only when exporting CSV.
        """
        if df.empty:
            return df

        print("🔄 Calculando horas de descanso...")

        # Create columns for break hours as Timedelta
        df["horas_descanso_td"] = pd.Timedelta(0)
        df["horas_descanso"] = "00:00:00"  # For CSV compatibility

        # Save original values
        df["horas_trabajadas_originales"] = df["horas_trabajadas"].copy()
        df["horas_esperadas_originales"] = df["horas_esperadas"].copy()

        # Convert duration to Timedelta if it exists
        if "duration" in df.columns:
            df["duration_td"] = df["duration"].fillna(pd.Timedelta(0))
        else:
            df["duration_td"] = pd.Timedelta(0)

        total_dias_con_descanso = 0

        for index, row in df.iterrows():
            # Calculate break hours for this row
            horas_descanso_td = self.calcular_horas_descanso(row)

            if horas_descanso_td > timedelta(0):
                df.at[index, "horas_descanso_td"] = horas_descanso_td
                df.at[index, "horas_descanso"] = td_to_str(horas_descanso_td)

                # Adjust worked hours (subtract break) using Timedelta
                if "duration" in df.columns and pd.notna(row.get("duration")):
                    try:
                        # Convert duration to Timedelta if necessary
                        if isinstance(row["duration"], str):
                            duration_td = pd.to_timedelta(row["duration"])
                        else:
                            duration_td = row["duration"]

                        horas_trabajadas_ajustadas = duration_td - horas_descanso_td
                        if horas_trabajadas_ajustadas.total_seconds() >= 0:
                            df.at[index, "duration"] = horas_trabajadas_ajustadas
                            df.at[index, "duration_td"] = horas_trabajadas_ajustadas
                            df.at[index, "horas_trabajadas"] = td_to_str(
                                horas_trabajadas_ajustadas
                            )
                    except (ValueError, TypeError):
                        pass  # Keep original value if there's an error

                # Adjust expected hours (subtract 1 hour if there's a break)
                if (
                    pd.notna(row["horas_esperadas"])
                    and row["horas_esperadas"] != "00:00:00"
                ):
                    try:
                        horas_esperadas_td = pd.to_timedelta(row["horas_esperadas"])
                        horas_esperadas_ajustadas = horas_esperadas_td - timedelta(
                            hours=1
                        )

                        if horas_esperadas_ajustadas.total_seconds() >= 0:
                            df.at[index, "horas_esperadas"] = td_to_str(
                                horas_esperadas_ajustadas
                            )
                    except (ValueError, TypeError):
                        pass  # Keep original value if there's an error

                total_dias_con_descanso += 1

        print(f"✅ Se calcularon horas de descanso para {total_dias_con_descanso} días")
        return df

    def procesar_horarios_con_medianoche(
        self, df: pd.DataFrame, cache_horarios: Dict
    ) -> pd.DataFrame:
        """
        Reorganizes check-ins for shifts that cross midnight.
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

                    # Buscar también checadas del día siguiente para turnos nocturnos
                    dia_siguiente = fila_actual["dia"] + timedelta(days=1)
                    mask_siguiente = (df_proc["employee"] == empleado) & (
                        df_proc["dia"] == dia_siguiente
                    )

                    checadas_siguiente = []
                    idx_siguiente = None
                    if mask_siguiente.any():
                        idx_siguiente = df_proc[mask_siguiente].index[0]
                        checadas_siguiente = [
                            df_proc.loc[idx_siguiente, f"checado_{j}"]
                            for j in range(1, 10)
                            if f"checado_{j}" in df_proc.columns
                            and pd.notna(df_proc.loc[idx_siguiente, f"checado_{j}"])
                        ]

                        # Determinar entrada y salida real
                        entrada_real = None
                        salida_real = None

                        # Si hay checadas del día de entrada, usar la más temprana como entrada
                        if checadas_dia:
                            entrada_real = min(checadas_dia)

                        # Si hay checadas del día siguiente, usar la más tardía como salida
                        if checadas_siguiente:
                            salida_real = max(checadas_siguiente)
                        # Si no hay checadas del día siguiente pero sí del día de entrada, usar la más tardía
                        elif checadas_dia:
                            salida_real = max(checadas_dia)

                        # Si solo hay checadas del día siguiente (sin entrada), no crear primera checada
                        if not checadas_dia and checadas_siguiente:
                            # Marcar como ausencia de entrada - esto se manejará en el análisis posterior
                            entrada_real = None
                            salida_real = max(checadas_siguiente)

                        # Limpiar todas las checadas del día actual
                        for j in range(1, 10):
                            if f"checado_{j}" in df_proc.columns:
                                df_proc.loc[idx_actual, f"checado_{j}"] = None

                        # Asignar las checadas procesadas
                        if entrada_real:
                            df_proc.loc[idx_actual, "checado_1"] = entrada_real
                        if salida_real:
                            df_proc.loc[idx_actual, "checado_2"] = salida_real

                        # Calcular duración solo si tenemos tanto entrada como salida
                        if entrada_real and salida_real:
                            try:
                                entrada_time = datetime.strptime(
                                    entrada_real, "%H:%M:%S"
                                ).time()
                                salida_time = datetime.strptime(
                                    salida_real, "%H:%M:%S"
                                ).time()

                                fecha_actual = fila_actual["dia"]
                                inicio = datetime.combine(fecha_actual, entrada_time)

                                # Para turnos que cruzan medianoche, la salida es al día siguiente
                                if salida_time <= entrada_time:
                                    fin = datetime.combine(
                                        fecha_actual + timedelta(days=1), salida_time
                                    )
                                else:
                                    fin = datetime.combine(fecha_actual, salida_time)

                                duracion_td = fin - inicio
                                df_proc.loc[idx_actual, "duration"] = duracion_td
                                df_proc.loc[idx_actual, "horas_trabajadas"] = td_to_str(
                                    duracion_td
                                )
                            except (ValueError, TypeError):
                                df_proc.loc[idx_actual, "duration"] = pd.Timedelta(0)
                                df_proc.loc[idx_actual, "horas_trabajadas"] = "00:00:00"
                        else:
                            # Si no tenemos entrada o salida completa, marcar como sin horas
                            df_proc.loc[idx_actual, "duration"] = pd.Timedelta(0)
                            df_proc.loc[idx_actual, "horas_trabajadas"] = "00:00:00"

                        # Limpiar la checada utilizada del día siguiente para evitar duplicación
                        if (
                            idx_siguiente is not None
                            and salida_real
                            and salida_real in checadas_siguiente
                        ):
                            for j in range(1, 10):
                                if (
                                    f"checado_{j}" in df_proc.columns
                                    and df_proc.loc[idx_siguiente, f"checado_{j}"]
                                    == salida_real
                                ):
                                    df_proc.loc[idx_siguiente, f"checado_{j}"] = None
                                    break

                            # Recalcular horas para el día siguiente con checadas restantes
                            checadas_restantes = [
                                df_proc.loc[idx_siguiente, f"checado_{j}"]
                                for j in range(1, 10)
                                if f"checado_{j}" in df_proc.columns
                                and pd.notna(df_proc.loc[idx_siguiente, f"checado_{j}"])
                            ]
                            if len(checadas_restantes) >= 2:
                                try:
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
                                    fin_sig = datetime.combine(
                                        fecha_siguiente, salida_sig
                                    )

                                    duracion_sig_td = fin_sig - inicio_sig
                                    df_proc.loc[idx_siguiente, "duration"] = (
                                        duracion_sig_td
                                    )
                                    df_proc.loc[idx_siguiente, "horas_trabajadas"] = (
                                        td_to_str(duracion_sig_td)
                                    )
                                except (ValueError, TypeError):
                                    df_proc.loc[idx_siguiente, "duration"] = (
                                        pd.Timedelta(0)
                                    )
                                    df_proc.loc[idx_siguiente, "horas_trabajadas"] = (
                                        "00:00:00"
                                    )
                            else:
                                df_proc.loc[idx_siguiente, "duration"] = pd.Timedelta(0)
                                df_proc.loc[idx_siguiente, "horas_trabajadas"] = (
                                    "00:00:00"
                                )

        print("✅ Procesamiento de turnos con medianoche completado")
        return df_proc

    def analizar_asistencia_con_horarios_cache(
        self, df: pd.DataFrame, cache_horarios: Dict
    ) -> pd.DataFrame:
        """
        Enriches the DataFrame with schedule and tardiness analysis using the schedule cache.
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
                row["employee"],
                row["dia_iso"],
                row["es_primera_quincena"],
                cache_horarios,
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
                # Para turnos nocturnos sin checada de entrada pero con salida, marcar especialmente
                if row.get("cruza_medianoche", False) and pd.notna(
                    row.get("checado_2")
                ):
                    return pd.Series(["Falta Entrada Nocturno", 0])
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

                if diferencia <= TOLERANCIA_RETARDO_MINUTOS:
                    tipo = "A Tiempo"
                elif diferencia <= UMBRAL_FALTA_INJUSTIFICADA_MINUTOS:
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
        df["es_falta"] = (
            df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])
        ).astype(int)
        df["retardos_acumulados"] = df.groupby("employee")[
            "es_retardo_acumulable"
        ].cumsum()

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

        # Function to detect early departures
        def detectar_salida_anticipada(row):
            # Only apply if scheduled exit time exists and at least one check-in
            if pd.isna(row.get("hora_salida_programada")) or pd.isna(
                row.get("checado_1")
            ):
                return False

            # Get the last check-in of the day (the one with the highest value)
            checadas_dia = []
            for i in range(1, 10):  # Search up to checado_9
                col_checado = f"checado_{i}"
                if col_checado in row and pd.notna(row[col_checado]):
                    checadas_dia.append(row[col_checado])

            # If there's only one check-in, don't consider early departure
            if len(checadas_dia) <= 1:
                return False

            # Get the last check-in (convert to datetime to compare correctly)
            try:
                checadas_datetime = [
                    datetime.strptime(checada, "%H:%M:%S") for checada in checadas_dia
                ]

                # For shifts that cross midnight, we need to adjust hours
                if row.get("cruza_medianoche", False):
                    # In night shifts, we need to compare chronologically
                    checadas_ajustadas = []
                    for dt in checadas_datetime:
                        if dt.hour < 12:  # If before noon (00:00-11:59), add 24 hours
                            dt_ajustado = dt + timedelta(hours=24)
                            checadas_ajustadas.append(dt_ajustado)
                        else:
                            checadas_ajustadas.append(dt)
                    ultima_checada_dt = max(checadas_ajustadas)
                    # Convert back to original format
                    ultima_checada = ultima_checada_dt.strftime("%H:%M:%S")
                else:
                    ultima_checada = max(checadas_datetime).strftime("%H:%M:%S")
            except (ValueError, TypeError):
                return False

            try:
                # Parse scheduled exit time
                hora_salida_prog = datetime.strptime(
                    row["hora_salida_programada"] + ":00", "%H:%M:%S"
                )
                hora_ultima_checada = datetime.strptime(ultima_checada, "%H:%M:%S")

                # Handle shifts that cross midnight
                if row.get("cruza_medianoche", False):
                    # For shifts that cross midnight, scheduled exit time is on the next day
                    # We don't need to adjust anything here since we're only comparing hours
                    pass

                # Calculate difference in minutes
                diferencia = (
                    hora_salida_prog - hora_ultima_checada
                ).total_seconds() / 60

                # Handle midnight cases
                if diferencia < -12 * 60:  # More than 12 hours before
                    diferencia += 24 * 60
                elif diferencia > 12 * 60:  # More than 12 hours after
                    diferencia -= 24 * 60

                # Consider early departure if last check-in is before scheduled exit time
                # minus tolerance margin
                return diferencia > TOLERANCIA_SALIDA_ANTICIPADA_MINUTOS

            except (ValueError, TypeError):
                return False

        # Apply early departure detection
        df["salida_anticipada"] = df.apply(detectar_salida_anticipada, axis=1)

        print("✅ Análisis completado.")
        return df

    def ajustar_horas_esperadas_con_permisos(
        self, df: pd.DataFrame, permisos_dict: Dict, cache_horarios: Dict
    ) -> pd.DataFrame:
        """
        Adjusts expected hours in the DataFrame considering approved leaves.
        Properly handles half-day leaves.
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

                if (
                    pd.notna(horas_esperadas_orig)
                    and horas_esperadas_orig != "00:00:00"
                ):
                    if accion == "no_ajustar":
                        df.at[index, "es_permiso_sin_goce"] = True
                        permisos_sin_goce += 1
                    elif accion == "ajustar_a_cero":
                        if is_half_day:
                            # For half-day leaves, deduct only half the hours
                            try:
                                # Convert expected hours to timedelta
                                horas_td = pd.to_timedelta(horas_esperadas_orig)
                                # Calculate half
                                mitad_horas = horas_td / 2
                                # Convert back to string
                                mitad_horas_str = str(mitad_horas).split()[
                                    -1
                                ]  # Get only HH:MM:SS

                                # Adjust expected hours (subtract half)
                                horas_ajustadas = horas_td - mitad_horas
                                horas_ajustadas_str = str(horas_ajustadas).split()[-1]

                                df.at[index, "horas_esperadas"] = horas_ajustadas_str
                                df.at[index, "horas_descontadas_permiso"] = (
                                    mitad_horas_str
                                )
                                permisos_medio_dia += 1
                            except (ValueError, TypeError):
                                # If there's an error in calculation, treat as full day
                                df.at[index, "horas_esperadas"] = "00:00:00"
                                df.at[index, "horas_descontadas_permiso"] = (
                                    horas_esperadas_orig
                                )
                                permisos_con_descuento += 1
                        else:
                            # Full day leave
                            df.at[index, "horas_esperadas"] = "00:00:00"
                            df.at[index, "horas_descontadas_permiso"] = (
                                horas_esperadas_orig
                            )
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

    def aplicar_regla_perdon_retardos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies the tardiness forgiveness rule when an employee fulfills their shift hours.

        If an employee worked the corresponding hours of their shift or more, that day should NOT
        count as tardiness, even if they arrived late.
        """
        if df.empty:
            return df

        print("🔄 Applying tardiness forgiveness rule for hour fulfillment...")

        # Use Timedelta columns if they exist, otherwise convert from strings
        if "duration_td" in df.columns:
            df["horas_trabajadas_td"] = df["duration_td"].fillna(pd.Timedelta(0))
        else:
            df["horas_trabajadas_td"] = df["horas_trabajadas"].apply(safe_timedelta)

        df["horas_esperadas_td"] = df["horas_esperadas"].apply(safe_timedelta)

        # Calculate if shift hours were fulfilled
        df["cumplio_horas_turno"] = (
            df["horas_trabajadas_td"] >= df["horas_esperadas_td"]
        )

        # Save original values before applying forgiveness
        df["tipo_retardo_original"] = df["tipo_retardo"].copy()
        df["minutos_tarde_original"] = df["minutos_tarde"].copy()
        df["retardo_perdonado"] = False

        # Apply forgiveness to tardiness
        mask_retardo_perdonable = (df["tipo_retardo"] == "Retardo") & (
            df["cumplio_horas_turno"]
        )

        if mask_retardo_perdonable.any():
            df.loc[mask_retardo_perdonable, "retardo_perdonado"] = True
            df.loc[mask_retardo_perdonable, "tipo_retardo"] = "A Tiempo (Cumplió Horas)"
            df.loc[mask_retardo_perdonable, "minutos_tarde"] = 0
            retardos_perdonados = mask_retardo_perdonable.sum()
            print(f"   - {retardos_perdonados} tardiness forgiven for fulfilling hours")

        # Apply forgiveness to unjustified absences (optional)
        if PERDONAR_TAMBIEN_FALTA_INJUSTIFICADA:
            mask_falta_perdonable = (df["tipo_retardo"] == "Falta Injustificada") & (
                df["cumplio_horas_turno"]
            )

            if mask_falta_perdonable.any():
                df.loc[mask_falta_perdonable, "retardo_perdonado"] = True
                df.loc[mask_falta_perdonable, "tipo_retardo"] = (
                    "A Tiempo (Cumplió Horas)"
                )
                df.loc[mask_falta_perdonable, "minutos_tarde"] = 0
                faltas_perdonadas = mask_falta_perdonable.sum()
                print(
                    f"   - {faltas_perdonadas} unjustified absences forgiven for fulfilling hours"
                )

        # Recalculate derived columns
        df["es_retardo_acumulable"] = (df["tipo_retardo"] == "Retardo").astype(int)
        df["es_falta"] = (
            df["tipo_retardo"].isin(["Falta", "Falta Injustificada"])
        ).astype(int)

        # Recalculate accumulated tardiness by employee
        df["retardos_acumulados"] = df.groupby("employee")[
            "es_retardo_acumulable"
        ].cumsum()

        # Recalculate discount for 3 tardiness
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
                f"✅ Forgiveness applied to {total_perdonados} days for hour fulfillment"
            )
        else:
            print("✅ No days found eligible for forgiveness")

        return df

    def clasificar_faltas_con_permisos(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Updates absence classification considering approved leaves.
        """
        if df.empty:
            return df

        print("📋 Reclassifying absences considering approved leaves...")

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
            print(f"✅ {faltas_justificadas} absences justified with approved leaves.")
        else:
            df["es_falta_ajustada"] = df["es_falta"].copy()
            print("✅ No absences found to justify with leaves.")

        return df
