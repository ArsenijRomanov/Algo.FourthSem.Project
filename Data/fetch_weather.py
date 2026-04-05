"""
Загрузка почасовых метеоданных из Open-Meteo Historical API
за последние 10 лет для расчёта солнечной генерации телеком-узла.

Требования:
    pip install openmeteo-requests requests-cache retry-requests pandas openpyxl tqdm

Запуск:
    python fetch_weather.py

Результат:
    weather_data_<lat>_<lon>.csv  —  почасовые данные за 10 лет
    weather_data_<lat>_<lon>.xlsx —  то же самое в Excel (один лист)
"""

import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from datetime import date
from dateutil.relativedelta import relativedelta
from tqdm import tqdm


# аул Новая Адыгея, Тахтамукайский район, Республика Адыгея
LATITUDE  = 45.020131   
LONGITUDE = 38.932607

TILT  = 45 
AZIMUTH = 0

END_DATE   = date.today().replace(day=1) - pd.Timedelta(days=1)  
START_DATE = END_DATE - relativedelta(years=10) + relativedelta(days=1)

print(f"Период загрузки: {START_DATE} → {END_DATE}")
print(f"Координаты: lat={LATITUDE}, lon={LONGITUDE}")


HOURLY_VARS = [
    "global_tilted_irradiance",      
    "shortwave_radiation",           
    "direct_normal_irradiance",      
    "diffuse_radiation",             
    "temperature_2m",               
    "cloud_cover",                   
    "wind_speed_10m",                 
]


def make_year_chunks(start: date, end: date):
    """Генерирует пары (chunk_start, chunk_end) по ~1 году."""
    chunks = []
    cursor = start
    while cursor <= end:
        chunk_end = min(cursor + relativedelta(years=1) - relativedelta(days=1), end)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + relativedelta(days=1)
    return chunks


cache_session = requests_cache.CachedSession(".weather_cache", expire_after=-1)
retry_session = retry(cache_session, retries=5, backoff_factor=0.3)
om = openmeteo_requests.Client(session=retry_session)

chunks = make_year_chunks(START_DATE, END_DATE)
print(f"\nЗагрузка {len(chunks)} блоков данных...")

dfs = []

for chunk_start, chunk_end in tqdm(chunks, unit="год"):
    params = {
        "latitude":         LATITUDE,
        "longitude":        LONGITUDE,
        "start_date":       str(chunk_start),
        "end_date":         str(chunk_end),
        "hourly":           HOURLY_VARS,
        "tilt":             TILT,
        "azimuth":          AZIMUTH,
        "wind_speed_unit":  "ms",
        "timezone":         "UTC",
    }

    responses = om.weather_api(
        "https://archive-api.open-meteo.com/v1/archive",
        params=params
    )
    response = responses[0]

    hourly = response.Hourly()

    times = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left",
    )

    chunk_df = pd.DataFrame({"datetime_utc": times})

    for i, var_name in enumerate(HOURLY_VARS):
        chunk_df[var_name] = hourly.Variables(i).ValuesAsNumpy()

    dfs.append(chunk_df)


df = pd.concat(dfs, ignore_index=True)
df = df.sort_values("datetime_utc").reset_index(drop=True)
df['datetime_utc'] = df['datetime_utc'].dt.tz_localize(None)

df.rename(columns={
    "global_tilted_irradiance": "GTI_W_m2",
    "shortwave_radiation":      "GHI_W_m2",
    "direct_normal_irradiance": "DNI_W_m2",
    "diffuse_radiation":        "DHI_W_m2",
    "temperature_2m":           "temp_C",
    "cloud_cover":              "cloud_pct",
    "wind_speed_10m":           "wind_m_s",
}, inplace=True)

tag = f"{LATITUDE}_{LONGITUDE}".replace(".", "_")

# CSV
csv_path = f"weather_data_{tag}.csv"
df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"\nCSV сохранён: {csv_path}  ({len(df):,} строк)")

# XLSX 
xlsx_path = f"weather_data_{tag}.xlsx"
with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
    df.to_excel(writer, index=False, sheet_name="weather")
    ws = writer.sheets["weather"]
    for col in ws.columns:
        max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_len + 2
print(f"XLSX сохранён: {xlsx_path}")

print("\n Сводка по данным ")
print(f"Период:     {df['datetime_utc'].min()}  -  {df['datetime_utc'].max()}")
print(f"Строк:      {len(df):,}")
print(f"Пропусков (GTI): {df['GTI_W_m2'].isna().sum()}")
print("\nПервые строки:")
print(df.head(3).to_string())