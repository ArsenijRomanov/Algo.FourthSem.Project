"""
Скрипт 1. Проверка структуры временного ряда.

Что делает:
- загружает файл weather_msk.csv;
- приводит столбец datetime_msk к типу datetime;
- проверяет сортировку по времени;
- проверяет дубликаты timestamp;
- проверяет равномерность шага по времени;
- ищет пропуски по времени в почасовом ряду;
- выводит краткую сводку по периоду наблюдений.

Что именно проверяется:
- число строк;
- минимальная и максимальная дата;
- есть ли дубликаты временных меток;
- есть ли нарушения монотонности времени;
- все ли интервалы между соседними строками равны 1 часу;
- какие часы отсутствуют в ряду, если пропуски есть.

Важно:
- временной столбец уже называется datetime_msk и хранит локальное время МСК;
- в этом скрипте оно используется как локальное время из файла.
"""

from pathlib import Path
import pandas as pd


# Путь к входному файлу
DATA_PATH = Path("weather_msk.csv")

# Имя временного столбца
TIME_COL = "datetime_msk"

# Ожидаемый шаг временного ряда
EXPECTED_FREQ = "1h"


def main() -> None:
    # Загружаем данные
    df = pd.read_csv(DATA_PATH)

    # Переводим временной столбец в datetime
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")

    # Базовая информация о размере ряда
    print("=== Проверка структуры временного ряда ===")
    print(f"Файл: {DATA_PATH}")
    print(f"Число строк: {len(df):,}")
    print(f"Минимальная дата: {df[TIME_COL].min()}")
    print(f"Максимальная дата: {df[TIME_COL].max()}")
    print()

    # Проверяем, есть ли ошибки парсинга даты
    invalid_dates = df[TIME_COL].isna().sum()
    print(f"Некорректно распознанных дат: {invalid_dates}")

    # Проверяем, отсортирован ли ряд по времени
    is_sorted = df[TIME_COL].is_monotonic_increasing
    print(f"Ряд отсортирован по времени: {is_sorted}")

    # Ищем дубликаты временных меток
    duplicate_mask = df.duplicated(subset=[TIME_COL], keep=False)
    duplicate_count = duplicate_mask.sum()
    print(f"Количество строк с дубликатами timestamp: {duplicate_count}")

    if duplicate_count > 0:
        print("Примеры дубликатов:")
        print(df.loc[duplicate_mask, [TIME_COL]].head(10).to_string(index=False))
    print()

    # Для корректной проверки интервалов создаём отсортированную версию
    df_sorted = df.sort_values(TIME_COL).reset_index(drop=True)

    # Разности между соседними временными метками
    time_diff = df_sorted[TIME_COL].diff()
    freq_counts = time_diff.value_counts(dropna=True).sort_index()

    print("Распределение интервалов между соседними строками:")
    if len(freq_counts) > 0:
        print(freq_counts.to_string())
    else:
        print("Недостаточно данных для расчёта интервалов.")
    print()

    # Проверяем, все ли шаги равны 1 часу
    expected_delta = pd.Timedelta(EXPECTED_FREQ)
    bad_steps = df_sorted.loc[(time_diff.notna()) & (time_diff != expected_delta), [TIME_COL]].copy()
    print(f"Количество интервалов, отличных от {EXPECTED_FREQ}: {len(bad_steps)}")

    # Строим эталонный полный почасовой индекс и ищем пропуски
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

    # Выводим краткий итог
    print("=== Итог ===")
    if invalid_dates == 0 and is_sorted and duplicate_count == 0 and len(missing_timestamps) == 0 and len(bad_steps) == 0:
        print("Временной ряд выглядит корректным: без дублей, пропусков и нарушений шага.")
    else:
        print("Найдены проблемы структуры ряда. Смотри сводку выше.")


if __name__ == "__main__":
    main()
