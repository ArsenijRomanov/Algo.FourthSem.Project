"""
Скрипт 1. Проверка структуры временного ряда с учётом GTI.

Что делает:
- загружает weather_msk.csv;
- проверяет наличие обязательных столбцов, включая GTI_W_m2;
- приводит datetime_msk к datetime;
- проверяет сортировку, дубликаты и непрерывность почасового ряда.

Важно:
- GTI_W_m2 соответствует панели с наклоном 45° и азимутом 0°.
"""

from pathlib import Path
import pandas as pd

DATA_PATH = Path("weather_msk.csv")
TIME_COL = "datetime_msk"
REQUIRED_COLUMNS = [
    "datetime_msk",
    "GTI_W_m2",
    "GHI_W_m2",
    "DNI_W_m2",
    "DHI_W_m2",
    "temp_C",
    "cloud_pct",
    "wind_m_s",
]

EXPECTED_FREQ = "1h"

def main() -> None:
    df = pd.read_csv(DATA_PATH)

    print("=== Проверка структуры временного ряда ===")
    print(f"Файл: {DATA_PATH}")
    print(f"Число строк: {len(df):,}")
    print()

    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    print(f"Присутствуют обязательные столбцы: {len(missing_required) == 0}")
    if missing_required:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_required}")
    print()

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")

    print(f"Минимальная дата: {df[TIME_COL].min()}")
    print(f"Максимальная дата: {df[TIME_COL].max()}")
    print()

    invalid_dates = int(df[TIME_COL].isna().sum())
    is_sorted = df[TIME_COL].is_monotonic_increasing
    duplicate_mask = df.duplicated(subset=[TIME_COL], keep=False)
    duplicate_count = int(duplicate_mask.sum())

    print(f"Некорректно распознанных дат: {invalid_dates}")
    print(f"Ряд отсортирован по времени: {is_sorted}")
    print(f"Количество строк с дубликатами timestamp: {duplicate_count}")
    if duplicate_count > 0:
        print(df.loc[duplicate_mask, [TIME_COL]].head(10).to_string(index=False))
    print()

    df_sorted = df.sort_values(TIME_COL).reset_index(drop=True)
    time_diff = df_sorted[TIME_COL].diff()
    freq_counts = time_diff.value_counts(dropna=True).sort_index()

    print("Распределение интервалов между соседними строками:")
    if len(freq_counts) > 0:
        print(freq_counts.to_string())
    else:
        print("Недостаточно данных для расчёта интервалов.")
    print()

    expected_delta = pd.Timedelta(EXPECTED_FREQ)
    bad_steps = df_sorted.loc[(time_diff.notna()) & (time_diff != expected_delta), [TIME_COL]].copy()
    print(f"Количество интервалов, отличных от {EXPECTED_FREQ}: {len(bad_steps)}")

    full_index = pd.date_range(
        start=df_sorted[TIME_COL].min(),
        end=df_sorted[TIME_COL].max(),
        freq=EXPECTED_FREQ,
    )
    missing_timestamps = full_index.difference(df_sorted[TIME_COL])

    print(f"Ожидаемое число часов в полном диапазоне: {len(full_index):,}")
    print(f"Фактическое число уникальных временных меток: {df_sorted[TIME_COL].nunique():,}")
    print(f"Количество отсутствующих часов: {len(missing_timestamps)}")
    if len(missing_timestamps) > 0:
        print("Первые пропущенные часы:")
        for ts in missing_timestamps[:10]:
            print(ts)
    print()

    print("=== Итог ===")
    if invalid_dates == 0 and is_sorted and duplicate_count == 0 and len(missing_timestamps) == 0 and len(bad_steps) == 0:
        print("Временной ряд выглядит корректным: без дублей, пропусков и нарушений шага.")
    else:
        print("Найдены проблемы структуры ряда. Смотри сводку выше.")

if __name__ == "__main__":
    main()
