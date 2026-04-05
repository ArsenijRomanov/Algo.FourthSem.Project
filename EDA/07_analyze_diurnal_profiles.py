"""
07_analyze_diurnal_profiles.py

Что делает скрипт:
- загружает weather_msk.csv;
- преобразует datetime_msk в datetime;
- добавляет календарные признаки:
  - hour
  - month
  - season
- строит средние почасовые профили:
  - по месяцам;
  - по сезонам;
- строит отдельные графики суточных профилей для каждого признака;
- сохраняет таблицы и графики в папку 07_diurnal_profiles.

Что проверяется:
1. Как меняются GHI, DNI и DHI в течение суток;
2. В какие часы наблюдается максимум солнечного ресурса;
3. Как меняются температура, облачность и ветер в течение суток;
4. Чем отличаются суточные профили по сезонам и месяцам;
5. Насколько важна почасовая структура для будущей модели энергобаланса.

Важно:
- файл weather_msk.csv должен лежать рядом со скриптом;
- столбец времени должен называться datetime_msk;
- скрипт не изменяет исходные данные;
- цвета специально не задаются.
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


# =========================
# Настройки
# =========================
DATA_PATH = Path("weather_msk.csv")
OUTPUT_DIR = Path("07_diurnal_profiles")

DATETIME_COL = "datetime_msk"

NUMERIC_COLUMNS = [
    "GHI_W_m2",
    "DNI_W_m2",
    "DHI_W_m2",
    "temp_C",
    "cloud_pct",
    "wind_m_s",
]

MONTH_ORDER = list(range(1, 13))
MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

SEASON_MAP = {
    12: "winter",
    1: "winter",
    2: "winter",
    3: "spring",
    4: "spring",
    5: "spring",
    6: "summer",
    7: "summer",
    8: "summer",
    9: "autumn",
    10: "autumn",
    11: "autumn",
}
SEASON_ORDER = ["winter", "spring", "summer", "autumn"]


def add_calendar_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет календарные признаки для суточных профилей.
    """
    df = df.copy()
    df[DATETIME_COL] = pd.to_datetime(df[DATETIME_COL], errors="coerce")

    df["hour"] = df[DATETIME_COL].dt.hour
    df["month"] = df[DATETIME_COL].dt.month
    df["month_label"] = pd.Categorical(
        df["month"].map(dict(zip(MONTH_ORDER, MONTH_LABELS))),
        categories=MONTH_LABELS,
        ordered=True,
    )
    df["season"] = pd.Categorical(
        df["month"].map(SEASON_MAP),
        categories=SEASON_ORDER,
        ordered=True,
    )
    return df


def save_table(df: pd.DataFrame, path: Path) -> None:
    """
    Сохраняет таблицу в CSV.
    """
    df.to_csv(path, encoding="utf-8-sig")
    print(f"Сохранена таблица: {path}")


def plot_seasonal_hourly_profiles(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Строит средние почасовые профили по сезонам для каждого признака.
    """
    hours = list(range(24))

    for col in NUMERIC_COLUMNS:
        plt.figure(figsize=(10, 5))

        for season in SEASON_ORDER:
            season_series = (
                df.loc[df["season"] == season]
                .groupby("hour", observed=True)[col]
                .mean()
                .reindex(hours)
            )
            plt.plot(hours, season_series.values, marker="o", label=season)

        plt.title(f"Seasonal hourly profile: {col}")
        plt.xlabel("Hour of day")
        plt.ylabel(col)
        plt.xticks(hours)
        plt.legend()
        plt.tight_layout()

        out_path = output_dir / f"07_seasonal_hourly_profile_{col}.png"
        plt.savefig(out_path, dpi=150)
        plt.close()

        print(f"Сохранён график: {out_path}")


def plot_monthly_hourly_profiles(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Строит средние почасовые профили по месяцам для каждого признака.
    """
    hours = list(range(24))

    for col in NUMERIC_COLUMNS:
        plt.figure(figsize=(12, 6))

        for month, label in zip(MONTH_ORDER, MONTH_LABELS):
            month_series = (
                df.loc[df["month"] == month]
                .groupby("hour", observed=True)[col]
                .mean()
                .reindex(hours)
            )
            plt.plot(hours, month_series.values, label=label)

        plt.title(f"Monthly hourly profile: {col}")
        plt.xlabel("Hour of day")
        plt.ylabel(col)
        plt.xticks(hours)
        plt.legend(ncol=3, fontsize=8)
        plt.tight_layout()

        out_path = output_dir / f"07_monthly_hourly_profile_{col}.png"
        plt.savefig(out_path, dpi=150)
        plt.close()

        print(f"Сохранён график: {out_path}")


def plot_heatmaps_like_tables(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Сохраняет таблицы вида месяц x час и сезон x час для каждого признака.
    Эти таблицы потом удобно использовать для тепловых карт или отчёта.
    """
    for col in NUMERIC_COLUMNS:
        month_hour = (
            df.pivot_table(
                values=col,
                index="month",
                columns="hour",
                aggfunc="mean",
                observed=True,
            )
            .reindex(MONTH_ORDER)
            .round(4)
        )
        season_hour = (
            df.pivot_table(
                values=col,
                index="season",
                columns="hour",
                aggfunc="mean",
                observed=True,
            )
            .reindex(SEASON_ORDER)
            .round(4)
        )

        save_table(month_hour, output_dir / f"07_month_hour_table_{col}.csv")
        save_table(season_hour, output_dir / f"07_season_hour_table_{col}.csv")


def main() -> None:
    print("=== Анализ суточных профилей ===")
    print(f"Файл: {DATA_PATH}")
    print(f"Папка результатов: {OUTPUT_DIR}")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Файл {DATA_PATH} не найден. Убедитесь, что он лежит рядом со скриптом."
        )

    df = pd.read_csv(DATA_PATH)

    required_cols = [DATETIME_COL] + NUMERIC_COLUMNS
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_cols}")

    df = add_calendar_columns(df)

    print(f"Число строк: {len(df):,}")
    print(f"Период: {df[DATETIME_COL].min()} — {df[DATETIME_COL].max()}")
    print()

    # =========================
    # Таблицы средних почасовых профилей
    # =========================
    hourly_all = df.groupby("hour", observed=True)[NUMERIC_COLUMNS].mean().round(4)
    save_table(hourly_all, OUTPUT_DIR / "07_hourly_mean_all_data.csv")
    print("Средние почасовые профили по всем данным:")
    print(hourly_all.to_string())
    print()

    plot_heatmaps_like_tables(df, OUTPUT_DIR)
    print()

    # =========================
    # Графики
    # =========================
    plot_seasonal_hourly_profiles(df, OUTPUT_DIR)
    print()
    plot_monthly_hourly_profiles(df, OUTPUT_DIR)
    print()

    print("Готово. Все результаты сохранены в папку 07_diurnal_profiles.")


if __name__ == "__main__":
    main()
