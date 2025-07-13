import json
import os
import requests
from dotenv import load_dotenv
import pandas as pd
from itertools import product

# Carga las variables de entorno para las credenciales de la API
load_dotenv()
api_key = os.getenv("ASIATECH_API_KEY")
api_secret = os.getenv("ASIATECH_API_SECRET")

url = "https://erp.asiatech.com.mx/api/resource/Employee Checkin"

headers = {"Authorization": f"token {api_key}:{api_secret}"}


def fetch_checkins(start_date: str, end_date: str, device_filter: str):
    """Obtiene los registros de checadas de los empleados entre dos fechas, filtrados por dispositivo."""
    allowed_devices = ["%31%", "%villas%", "%nave%"]
    if device_filter not in allowed_devices:
        raise ValueError(f"El filtro de dispositivo debe ser uno de {allowed_devices}")

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
        params["limit_start"] = limit_start
        params["limit_page_length"] = page_length

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        current_records = data.get("data", [])
        if not current_records:
            break

        all_records.extend(current_records)
        if len(current_records) < page_length:
            break
        limit_start += page_length

    return all_records


def process_checkins_to_dataframe(checkin_data, start_date, end_date):
    """
    Procesa los datos de checadas para crear un DataFrame que incluye el nombre,
    días del periodo, día de la semana y horas trabajadas.
    """
    if not checkin_data:
        print("No se encontraron registros de checadas para el periodo especificado.")
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

    # --- Nueva lógica para calcular horas trabajadas ---
    # 1. Calcular la primera y última checada por día
    df_hours = df.groupby(["employee", "dia"])["time"].agg(["min", "max"]).reset_index()
    # 2. Calcular la duración y formatearla como HH:MM:SS
    # Se calcula solo si hay más de un registro, de lo contrario la duración es 0.
    duration = df_hours["max"] - df_hours["min"]
    total_seconds = duration.dt.total_seconds()
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    df_hours["horas trabajadas"] = df_hours.apply(
        lambda row: (
            f"{int(hours[row.name]):02}:{int(minutes[row.name]):02}:{int(seconds[row.name]):02}"
            if (row["max"] != row["min"])
            else "00:00:00"
        ),
        axis=1,
    )

    # Pivota los datos de checadas
    df["checado_rank"] = df.groupby(["employee", "dia"]).cumcount() + 1
    df_pivot = df.pivot_table(
        index=["employee", "dia"],
        columns="checado_rank",
        values="checado_time",
        aggfunc="first",
    )
    df_pivot.columns = [f"checado_{i}" for i in range(1, len(df_pivot.columns) + 1)]
    df_pivot.reset_index(inplace=True)

    all_employees = df["employee"].unique()
    all_dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date)).date

    base_df_data = list(product(all_employees, all_dates))
    base_df = pd.DataFrame(base_df_data, columns=["employee", "dia"])

    df_pivot["dia"] = pd.to_datetime(df_pivot["dia"]).dt.date

    daily_df = pd.merge(base_df, df_pivot, on=["employee", "dia"], how="left")

    # Unir con el mapa de nombres y las horas trabajadas
    final_df = pd.merge(daily_df, employee_map, on="employee", how="left")
    df_hours["dia"] = pd.to_datetime(df_hours["dia"]).dt.date
    final_df = pd.merge(
        final_df,
        df_hours[["employee", "dia", "horas trabajadas"]],
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

    # Reordenar las columnas para el formato final
    checado_cols = sorted([c for c in final_df.columns if "checado_" in c])
    new_col_order = [
        "employee",
        "Nombre",
        "dia",
        "dia_semana",
        "horas trabajadas",
    ] + checado_cols
    final_df = final_df[new_col_order]

    return final_df


if __name__ == "__main__":
    start_date = "2025-06-01"
    end_date = "2025-06-30"

    print(f"Obteniendo registros desde {start_date} hasta {end_date}...")

    results = fetch_checkins(start_date, end_date, "%31%")

    df_final = process_checkins_to_dataframe(results, start_date, end_date)

    if not df_final.empty:
        print("\nDataFrame procesado (primeras 5 filas):")
        print(df_final.head())

        output_filename = "reporte_asistencia_final.csv"
        df_final.to_csv(output_filename, index=False)
        print(f"\nEl DataFrame ha sido guardado en '{output_filename}'")
