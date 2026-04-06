"""
Скрипт 2. Проверка пропусков и типов данных с учётом GTI.
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

NUMERIC_COLS = [
    "GTI_W_m2",
    "GHI_W_m2",
    "DNI_W_m2",
    "DHI_W_m2",
    "temp_C",
    "cloud_pct",
    "wind_m_s",
]

def main() -> None:
    df = pd.read_csv(DATA_PATH)

    print("=== Проверка типов и пропусков ===")
    print(f"Файл: {DATA_PATH}")
    print(f"Размер таблицы: {df.shape[0]:,} строк x {df.shape[1]} столбцов")
    print()

    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_required}")

    print("Исходные типы столбцов:")
    print(df.dtypes.to_string())
    print()

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("Типы после приведения:")
    print(df.dtypes.to_string())
    print()

    missing_count = df.isna().sum()
    missing_share = (missing_count / len(df) * 100).round(4)
    summary = pd.DataFrame({"missing_count": missing_count, "missing_share_pct": missing_share})

    print("Пропуски по столбцам:")
    print(summary.to_string())
    print()

    rows_with_any_nan = int(df.isna().any(axis=1).sum())
    fully_empty_rows = int(df.isna().all(axis=1).sum())
    print(f"Строк с хотя бы одним пропуском: {rows_with_any_nan}")
    print(f"Полностью пустых строк: {fully_empty_rows}")
    print()

    if rows_with_any_nan > 0:
        print("Примеры строк с пропусками:")
        print(df[df.isna().any(axis=1)].head(10).to_string(index=False))
        print()

    print("=== Итог ===")
    if int(missing_count.sum()) == 0:
        print("Пропусков не обнаружено.")
    else:
        print("Обнаружены пропуски. Нужна стратегия обработки перед моделированием.")

if __name__ == "__main__":
    main()
