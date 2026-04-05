"""
Скрипт 3. Проверка физических ограничений.

Что делает:
- загружает weather_msk.csv;
- приводит столбец datetime_msk к datetime;
- проверяет, что значения признаков лежат в физически допустимых диапазонах;
- считает количество нарушений по каждому правилу;
- показывает примеры аномальных строк.

Что именно проверяется:
- GHI, DNI, DHI неотрицательны;
- cloud_pct находится в диапазоне [0, 100];
- wind_m_s неотрицателен;
- temp_C лежит в разумном климатическом диапазоне.

Важно:
- диапазон температуры здесь взят как широкий sanity-check, а не как строгий закон природы;
- если точка находится в регионе с экстремальным климатом, границы можно скорректировать.
"""

from pathlib import Path
import pandas as pd


DATA_PATH = Path("weather_msk.csv")
TIME_COL = "datetime_msk"

# Широкие физически разумные пределы для температуры воздуха.
TEMP_MIN_REASONABLE = -60
TEMP_MAX_REASONABLE = 60


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    df[TIME_COL] = pd.to_datetime(df[TIME_COL], errors="coerce")

    numeric_cols = ["GHI_W_m2", "DNI_W_m2", "DHI_W_m2", "temp_C", "cloud_pct", "wind_m_s"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    print("=== Проверка физических ограничений ===")
    print(f"Файл: {DATA_PATH}")
    print()

    # Список правил в виде: имя_проверки -> логическая маска нарушения
    violations = {
        "GHI_W_m2 < 0": df["GHI_W_m2"] < 0,
        "DNI_W_m2 < 0": df["DNI_W_m2"] < 0,
        "DHI_W_m2 < 0": df["DHI_W_m2"] < 0,
        "cloud_pct < 0": df["cloud_pct"] < 0,
        "cloud_pct > 100": df["cloud_pct"] > 100,
        "wind_m_s < 0": df["wind_m_s"] < 0,
        f"temp_C < {TEMP_MIN_REASONABLE}": df["temp_C"] < TEMP_MIN_REASONABLE,
        f"temp_C > {TEMP_MAX_REASONABLE}": df["temp_C"] > TEMP_MAX_REASONABLE,
    }

    # Сводка по числу нарушений
    summary_rows = []
    for rule_name, mask in violations.items():
        summary_rows.append({
            "rule": rule_name,
            "violations_count": int(mask.sum()),
        })

    summary_df = pd.DataFrame(summary_rows)
    print("Сводка по нарушениям:")
    print(summary_df.to_string(index=False))
    print()

    # Выводим примеры нарушений по каждому правилу
    for rule_name, mask in violations.items():
        count = int(mask.sum())
        if count > 0:
            print(f"Примеры для правила: {rule_name}")
            cols_to_show = [TIME_COL, "GHI_W_m2", "DNI_W_m2", "DHI_W_m2", "temp_C", "cloud_pct", "wind_m_s"]
            print(df.loc[mask, cols_to_show].head(10).to_string(index=False))
            print()

    # Дополнительно выводим описательную статистику как sanity-check
    print("Описательная статистика:")
    print(df[numeric_cols].describe().to_string())
    print()

    # Краткий итог
    total_violations = int(sum(mask.sum() for mask in violations.values()))
    print("=== Итог ===")
    if total_violations == 0:
        print("Нарушений базовых физических ограничений не обнаружено.")
    else:
        print("Обнаружены значения, выходящие за допустимые пределы. Смотри примеры выше.")


if __name__ == "__main__":
    main()
