"""
Скрипт 4. Проверка согласованности радиационных признаков.

Что делает:
- загружает weather_msk.csv;
- приводит столбец datetime_msk к datetime;
- анализирует совместное поведение GHI, DNI, DHI;
- ищет явно подозрительные комбинации значений;
- оценивает, есть ли радиация ночью;
- строит базовые диагностические признаки для дальнейшего EDA.

Что именно проверяется:
- случаи, когда GHI = 0, но DNI > 0;
- случаи, когда GHI = 0, но DHI > 0;
- наличие положительной радиации ночью;
- доля диффузной радиации в общей радиации в дневные часы.

Важно:
- здесь используется упрощённая проверка дня/ночи по GHI > 0;
- это не астрономически точное разделение, но для первичной диагностики подходит;
- позже для более строгой проверки лучше использовать положение солнца по координатам и времени.
"""

from pathlib import Path
import numpy as np
import pandas as pd


DATA_PATH = Path("weather_msk.csv")
TIME_COL = "datetime_msk"


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")

    for col in ["GHI_W_m2", "DNI_W_m2", "DHI_W_m2", "cloud_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("=== Проверка согласованности радиационных признаков ===")
    print(f"Файл: {DATA_PATH}")
    print()

    # Условно считаем дневными часы, когда GHI > 0.
    # Для грубой первичной проверки этого достаточно.
    day_mask = df["GHI_W_m2"] > 0
    night_mask = df["GHI_W_m2"] == 0

    print(f"Дневных часов (по правилу GHI > 0): {int(day_mask.sum()):,}")
    print(f"Ночных часов (по правилу GHI == 0): {int(night_mask.sum()):,}")
    print()

    # Подозрительные комбинации.
    # Если GHI равен нулю, а одна из компонент положительна, это повод проверить данные.
    ghi_zero_dni_positive = (df["GHI_W_m2"] == 0) & (df["DNI_W_m2"] > 0)
    ghi_zero_dhi_positive = (df["GHI_W_m2"] == 0) & (df["DHI_W_m2"] > 0)

    # Проверка наличия положительной радиации в условно ночные часы
    positive_dni_at_night = night_mask & (df["DNI_W_m2"] > 0)
    positive_dhi_at_night = night_mask & (df["DHI_W_m2"] > 0)

    print("Подозрительные случаи:")
    print(f"GHI == 0 и DNI > 0: {int(ghi_zero_dni_positive.sum())}")
    print(f"GHI == 0 и DHI > 0: {int(ghi_zero_dhi_positive.sum())}")
    print(f"Ночные часы с DNI > 0: {int(positive_dni_at_night.sum())}")
    print(f"Ночные часы с DHI > 0: {int(positive_dhi_at_night.sum())}")
    print()

    # Доля диффузной составляющей в общей радиации в дневные часы.
    # Используем защиту от деления на ноль.
    df_day = df.loc[day_mask].copy()
    df_day["DHI_to_GHI_ratio"] = np.where(
        df_day["GHI_W_m2"] > 0,
        df_day["DHI_W_m2"] / df_day["GHI_W_m2"],
        np.nan,
    )

    print("Статистика по отношению DHI/GHI в дневные часы:")
    print(df_day["DHI_to_GHI_ratio"].describe().to_string())
    print()

    # Смотрим, как часто встречаются очень большие значения отношения DHI/GHI.
    # Это не обязательно ошибка, но полезный диагностический индикатор.
    high_ratio_mask = df_day["DHI_to_GHI_ratio"] > 1.0
    print(f"Дневных часов, где DHI/GHI > 1: {int(high_ratio_mask.sum())}")
    print()

    # Выводим примеры подозрительных строк
    suspicious_mask = ghi_zero_dni_positive | ghi_zero_dhi_positive | high_ratio_mask.reindex(df.index, fill_value=False)
    suspicious_rows = df.loc[suspicious_mask, [TIME_COL, "GHI_W_m2", "DNI_W_m2", "DHI_W_m2", "cloud_pct"]]

    if not suspicious_rows.empty:
        print("Примеры подозрительных строк:")
        print(suspicious_rows.head(15).to_string(index=False))
        print()

    # Дополнительная грубая проверка: DNI при очень высокой облачности.
    # Это не строгая ошибка, а диагностическое правило.
    high_cloud_high_dni = (df["cloud_pct"] >= 95) & (df["DNI_W_m2"] > 700)
    print(f"Часов с cloud_pct >= 95 и DNI > 700: {int(high_cloud_high_dni.sum())}")
    if high_cloud_high_dni.sum() > 0:
        print(df.loc[high_cloud_high_dni, [TIME_COL, "DNI_W_m2", "cloud_pct"]].head(10).to_string(index=False))
        print()

    print("=== Итог ===")
    if int(ghi_zero_dni_positive.sum() + ghi_zero_dhi_positive.sum()) == 0:
        print("Грубых противоречий между GHI, DNI и DHI не обнаружено.")
    else:
        print("Есть подозрительные комбинации радиационных признаков. Их стоит изучить отдельно.")


if __name__ == "__main__":
    main()
