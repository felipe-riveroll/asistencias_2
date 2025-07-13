import json
import os
import requests
from dotenv import load_dotenv

# API credentials are now read from environment variables
load_dotenv()
api_key = os.getenv('ASIATECH_API_KEY')
api_secret = os.getenv('ASIATECH_API_SECRET')

url = "https://erp.asiatech.com.mx/api/resource/Employee Checkin"

headers = {
    'Authorization': f'token {api_key}:{api_secret}'
}


def fetch_checkins(start_date: str, end_date: str, device_filter: str):
    """Return employee checkins between two dates filtered by device."""
    allowed_devices = ["%31%", "%villas%", "%nave%"]
    if device_filter not in allowed_devices:
        raise ValueError(f"device_filter must be one of {allowed_devices}")

    filters = json.dumps([
        ["Employee Checkin", "time", "Between", [start_date, end_date]],
        ["Employee Checkin", "device_id", "like", device_filter],
    ])

    params = {
        'fields': json.dumps(["employee", "time"]),
        'filters': filters,
    }

    all_records = []
    page_length = 100
    limit_start = 0

    while True:
        params['limit_start'] = limit_start
        params['limit_page_length'] = page_length

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        current_records = data.get('data', [])
        if not current_records:
            break

        all_records.extend(current_records)
        if len(current_records) < page_length:
            break
        limit_start += page_length

    return all_records


if __name__ == "__main__":
    results = fetch_checkins("2025-06-01", "2025-06-30", "%31%")
    print(json.dumps({"data": results}, indent=4))