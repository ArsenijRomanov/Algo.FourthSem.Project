"""
Скрипт 4. Проверка согласованности радиационных признаков с учётом GTI.
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

import numpy as np

def main() -> None:
    df = pd.read_csv(DATA_PATH)

    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_required}")

    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")
    for col in ["GTI_W_m2", "GHI_W_m2", "DNI_W_m2", "DHI_W_m2", "cloud_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("=== Проверка согласованности радиационных признаков ===")
    print(f"Файл: {DATA_PATH}")
    print()

    day_mask = df["GHI_W_m2"] > 0
    night_mask = df["GHI_W_m2"] == 0

    print(f"Дневных часов (по правилу GHI > 0): {int(day_mask.sum()):,}")
    print(f"Ночных часов (по правилу GHI == 0): {int(night_mask.sum()):,}")
    print()

    ghi_zero_dni_positive = (df["GHI_W_m2"] == 0) & (df["DNI_W_m2"] > 0)
    ghi_zero_dhi_positive = (df["GHI_W_m2"] == 0) & (df["DHI_W_m2"] > 0)
    ghi_zero_gti_positive = (df["GHI_W_m2"] == 0) & (df["GTI_W_m2"] > 0)

    print("Подозрительные или диагностические случаи:")
    print(f"GHI == 0 и DNI > 0: {int(ghi_zero_dni_positive.sum())}")
    print(f"GHI == 0 и DHI > 0: {int(ghi_zero_dhi_positive.sum())}")
    print(f"GHI == 0 и GTI > 0: {int(ghi_zero_gti_positive.sum())}")
    print()

    df_day = df.loc[day_mask].copy()
    df_day["DHI_to_GHI_ratio"] = np.where(df_day["GHI_W_m2"] > 0, df_day["DHI_W_m2"] / df_day["GHI_W_m2"], np.nan)
    df_day["GTI_to_GHI_ratio"] = np.where(df_day["GHI_W_m2"] > 0, df_day["GTI_W_m2"] / df_day["GHI_W_m2"], np.nan)

    print("Статистика по отношению DHI/GHI в дневные часы:")
    print(df_day["DHI_to_GHI_ratio"].describe().to_string())
    print()

    print("Статистика по отношению GTI/GHI в дневные часы:")
    print(df_day["GTI_to_GHI_ratio"].describe().to_string())
    print()

    high_dhi_ratio_mask = df_day["DHI_to_GHI_ratio"] > 1.0
    gti_gt_ghi_mask = df_day["GTI_W_m2"] > df_day["GHI_W_m2"]
    print(f"Дневных часов, где DHI/GHI > 1: {int(high_dhi_ratio_mask.sum())}")
    print(f"Дневных часов, где GTI > GHI: {int(gti_gt_ghi_mask.sum())}")
    print()

    suspicious_mask = (
        ghi_zero_dni_positive
        | ghi_zero_dhi_positive
        | ghi_zero_gti_positive
        | high_dhi_ratio_mask.reindex(df.index, fill_value=False)
    )
    suspicious_rows = df.loc[suspicious_mask, [TIME_COL, "GTI_W_m2", "GHI_W_m2", "DNI_W_m2", "DHI_W_m2", "cloud_pct"]]
    if not suspicious_rows.empty:
        print("Примеры диагностических строк:")
        print(suspicious_rows.head(15).to_string(index=False))
        print()

    print("=== Итог ===")
    if int(ghi_zero_dni_positive.sum() + ghi_zero_dhi_positive.sum() + ghi_zero_gti_positive.sum()) == 0:
        print("Грубых противоречий между GTI, GHI, DNI и DHI не обнаружено.")
    else:
        print("Есть диагностические комбинации радиационных признаков. Их стоит изучить отдельно.")

if __name__ == "__main__":
    main()
