"""
Скрипт 2. Проверка пропусков и типов данных.

Что делает:
- загружает weather_msk.csv;
- проверяет типы столбцов;
- приводит столбец datetime_msk к datetime;
- приводит числовые признаки к numeric при необходимости;
- считает число и долю пропусков по каждому столбцу;
- показывает количество пустых строк и строк, где отсутствует хотя бы одно значение.

Что именно проверяется:
- соответствует ли тип столбца ожидаемому;
- есть ли NaN после чтения файла;
- появляются ли NaN после принудительного перевода в numeric;
- сколько строк содержат хотя бы один пропуск.

Важно:
- этот шаг нужен до любой физической интерпретации данных;
- если в колонках попались строки, пробелы или посторонние символы,
  они будут преобразованы в NaN и сразу станут видны.
"""

from pathlib import Path
import pandas as pd


DATA_PATH = Path("weather_msk.csv")
TIME_COL = "datetime_msk"
NUMERIC_COLS = [
    "GHI_W_m2",
    "DNI_W_m2",
    "DHI_W_m2",
    "temp_C",
    "cloud_pct",
    "wind_m_s",
]


def main() -> None:
    # Загружаем файл как есть
    df = pd.read_csv(DATA_PATH)

    print("=== Проверка типов и пропусков ===")
    print(f"Файл: {DATA_PATH}")
    print(f"Размер таблицы: {df.shape[0]:,} строк x {df.shape[1]} столбцов")
    print()

    # Показываем исходные типы
    print("Исходные типы столбцов:")
    print(df.dtypes.to_string())
    print()

    # Приводим время к datetime
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")

    # Приводим числовые столбцы к numeric
    # Это полезно, если в CSV случайно попались строки или некорректные символы.
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("Типы после приведения:")
    print(df.dtypes.to_string())
    print()

    # Считаем пропуски по каждому столбцу
    missing_count = df.isna().sum()
    missing_share = (missing_count / len(df) * 100).round(4)

    summary = pd.DataFrame({
        "missing_count": missing_count,
        "missing_share_pct": missing_share,
    })

    print("Пропуски по столбцам:")
    print(summary.to_string())
    print()

    # Проверяем строки, где отсутствует хотя бы одно значение
    rows_with_any_nan = df.isna().any(axis=1).sum()
    fully_empty_rows = df.isna().all(axis=1).sum()

    print(f"Строк с хотя бы одним пропуском: {rows_with_any_nan}")
    print(f"Полностью пустых строк: {fully_empty_rows}")
    print()

    # Если есть проблемные строки, выводим несколько примеров
    if rows_with_any_nan > 0:
        print("Примеры строк с пропусками:")
        print(df[df.isna().any(axis=1)].head(10).to_string(index=False))
        print()

    # Краткий итог
    print("=== Итог ===")
    if missing_count.sum() == 0:
        print("Пропусков не обнаружено.")
    else:
        print("Обнаружены пропуски. Нужна стратегия обработки перед моделированием.")


if __name__ == "__main__":
    main()
