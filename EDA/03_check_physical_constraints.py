"""
Скрипт 3. Проверка физических ограничений с учётом GTI.
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

TEMP_MIN_REASONABLE = -60
TEMP_MAX_REASONABLE = 60
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

    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_required}")

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("=== Проверка физических ограничений ===")
    print(f"Файл: {DATA_PATH}")
    print()

    violations = {
        "GTI_W_m2 < 0": df["GTI_W_m2"] < 0,
        "GHI_W_m2 < 0": df["GHI_W_m2"] < 0,
        "DNI_W_m2 < 0": df["DNI_W_m2"] < 0,
        "DHI_W_m2 < 0": df["DHI_W_m2"] < 0,
        "cloud_pct < 0": df["cloud_pct"] < 0,
        "cloud_pct > 100": df["cloud_pct"] > 100,
        "wind_m_s < 0": df["wind_m_s"] < 0,
        f"temp_C < {TEMP_MIN_REASONABLE}": df["temp_C"] < TEMP_MIN_REASONABLE,
        f"temp_C > {TEMP_MAX_REASONABLE}": df["temp_C"] > TEMP_MAX_REASONABLE,
    }

    summary_rows = [{"rule": name, "violations_count": int(mask.sum())} for name, mask in violations.items()]
    summary_df = pd.DataFrame(summary_rows)
    print("Сводка по нарушениям:")
    print(summary_df.to_string(index=False))
    print()

    cols_to_show = [TIME_COL] + NUMERIC_COLS
    for rule_name, mask in violations.items():
        if int(mask.sum()) > 0:
            print(f"Примеры для правила: {rule_name}")
            print(df.loc[mask, cols_to_show].head(10).to_string(index=False))
            print()

    print("Описательная статистика:")
    print(df[NUMERIC_COLS].describe().to_string())
    print()

    total_violations = int(sum(mask.sum() for mask in violations.values()))
    print("=== Итог ===")
    if total_violations == 0:
        print("Нарушений базовых физических ограничений не обнаружено.")
    else:
        print("Обнаружены значения, выходящие за допустимые пределы. Смотри примеры выше.")

if __name__ == "__main__":
    main()
