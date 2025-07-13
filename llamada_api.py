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
        "fields": json.dumps(["employee", "time"]),
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
    Procesa los datos de checadas para crear un DataFrame que incluye todos los
    días del periodo para cada empleado, y añade el día de la semana.
    """
    if not checkin_data:
        print("No se encontraron registros de checadas para el periodo especificado.")
        return pd.DataFrame()

    df = pd.DataFrame(checkin_data)
    df["time"] = pd.to_datetime(df["time"])
    df["dia"] = df["time"].dt.date
    df["checado_time"] = df["time"].dt.strftime("%H:%M:%S")

    # Pivota los datos de checadas como antes
    df["checado_rank"] = df.groupby(["employee", "dia"]).cumcount() + 1
    df_pivot = df.pivot_table(
        index=["employee", "dia"],
        columns="checado_rank",
        values="checado_time",
        aggfunc="first",
    )

    # Renombra las columnas de checadas para que sean más genéricas antes del merge
    df_pivot.columns = [f"checado_{i}" for i in range(1, len(df_pivot.columns) + 1)]
    df_pivot.reset_index(inplace=True)

    # --- Nueva lógica para incluir todos los días del periodo ---

    # 1. Obtener todos los empleados únicos y crear el rango de fechas
    all_employees = df["employee"].unique()
    all_dates = pd.to_datetime(pd.date_range(start=start_date, end=end_date)).date

    # 2. Crear un DataFrame base con todas las combinaciones de empleado y fecha
    base_df_data = list(product(all_employees, all_dates))
    base_df = pd.DataFrame(base_df_data, columns=["employee", "dia"])

    # 3. Convertir 'dia' a objeto de fecha en df_pivot para que el merge funcione
    df_pivot["dia"] = pd.to_datetime(df_pivot["dia"]).dt.date

    # 4. Unir el DataFrame base con los datos de checadas
    final_df = pd.merge(base_df, df_pivot, on=["employee", "dia"], how="left")

    # 5. Añadir la columna del día de la semana en español
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

    # 6. Reordenar las columnas
    checado_cols = sorted([c for c in final_df.columns if "checado_" in c])
    new_col_order = ["employee", "dia", "dia_semana"] + checado_cols
    final_df = final_df[new_col_order]

    return final_df


if __name__ == "__main__":
    # Define aquí el periodo que quieres consultar
    start_date = "2025-06-01"
    end_date = "2025-06-30"

    print(f"Obteniendo registros desde {start_date} hasta {end_date}...")

    # Obtiene los registros de la API
    results = fetch_checkins(start_date, end_date, "%31%")

    # Procesa los datos para crear el DataFrame final
    df_final = process_checkins_to_dataframe(results, start_date, end_date)

    if not df_final.empty:
        # Imprime las primeras filas del DataFrame resultante
        print("\nDataFrame procesado (primeras 5 filas):")
        print(df_final.head())

        # Guarda el DataFrame en un archivo CSV
        output_filename = "cheques_completos_por_dia.csv"
        df_final.to_csv(output_filename, index=False)
        print(f"\nEl DataFrame ha sido guardado en '{output_filename}'")
