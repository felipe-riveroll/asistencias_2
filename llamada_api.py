import json
import os
import requests
from dotenv import load_dotenv
import pandas as pd

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


def process_checkins_to_dataframe(checkin_data):
    """Procesa los datos de checadas para crear el DataFrame deseado."""
    if not checkin_data:
        return pd.DataFrame()

    df = pd.DataFrame(checkin_data)

    # Convierte la columna 'time' a formato de fecha y hora
    df["time"] = pd.to_datetime(df["time"])

    # Extrae la fecha y la hora en columnas separadas
    df["dia"] = df["time"].dt.date
    df["checado_time"] = df["time"].dt.strftime("%H:%M:%S")

    # Crea un contador para cada checada por empleado y día
    df["checado_rank"] = df.groupby(["employee", "dia"]).cumcount() + 1

    # Pivota la tabla para tener las checadas en columnas
    df_pivot = df.pivot_table(
        index=["employee", "dia"],
        columns="checado_rank",
        values="checado_time",
        aggfunc="first",
    ).reset_index()

    # Renombra las columnas dinámicamente
    num_checkins = len(df_pivot.columns) - 2
    df_pivot.columns = ["employee", "dia"] + [
        f"checado_{i}" for i in range(1, num_checkins + 1)
    ]

    return df_pivot


if __name__ == "__main__":
    # Obtiene los registros de la API
    results = fetch_checkins("2025-06-01", "2025-06-30", "%31%")

    # Procesa los datos para crear el DataFrame
    df_final = process_checkins_to_dataframe(results)

    # Imprime las primeras filas del DataFrame resultante
    print("DataFrame procesado:")
    print(df_final.head())

    # Guarda el DataFrame en un archivo CSV
    df_final.to_csv("cheques_agrupados.csv", index=False)
    print("\nEl DataFrame ha sido guardado en 'cheques_agrupados.csv'")
