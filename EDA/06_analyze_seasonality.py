"""
06_analyze_seasonality.py

Что делает скрипт:
- загружает weather_msk.csv;
- преобразует datetime_msk в datetime;
- добавляет календарные признаки:
  - year
  - month
  - season
- считает месячные и годовые агрегаты по основным метеопризнакам;
- строит графики сезонности:
  - средние значения по месяцам за весь период;
  - годовые средние значения;
  - boxplot по месяцам;
- сохраняет все таблицы и графики в папку 06_seasonality.

Что проверяется:
1. Как меняются GHI, DNI, DHI по месяцам;
2. Как меняются температура, облачность и ветер по месяцам;
3. Насколько устойчивы показатели от года к году;
4. Есть ли выраженная сезонность солнечного ресурса;
5. В какие месяцы ресурс минимален и максимален.

Важно:
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
OUTPUT_DIR = Path("06_seasonality")

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
    Добавляет календарные признаки для анализа сезонности.
    """
    df = df.copy()
    df[DATETIME_COL] = pd.to_datetime(df[DATETIME_COL], errors="coerce")

    df["year"] = df[DATETIME_COL].dt.year
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


def plot_monthly_means(monthly_means: pd.DataFrame, output_dir: Path) -> None:
    """
    Строит линейные графики средних значений по месяцам.
    """
    for col in NUMERIC_COLUMNS:
        plt.figure(figsize=(9, 5))
        plt.plot(MONTH_LABELS, monthly_means[col].reindex(MONTH_ORDER).values, marker="o")
        plt.title(f"Monthly mean: {col}")
        plt.xlabel("Month")
        plt.ylabel(col)
        plt.tight_layout()

        out_path = output_dir / f"06_monthly_mean_{col}.png"
        plt.savefig(out_path, dpi=150)
        plt.close()

        print(f"Сохранён график: {out_path}")


def plot_yearly_means(yearly_means: pd.DataFrame, output_dir: Path) -> None:
    """
    Строит линейные графики средних значений по годам.
    """
    years = yearly_means.index.astype(str).tolist()

    for col in NUMERIC_COLUMNS:
        plt.figure(figsize=(10, 5))
        plt.plot(years, yearly_means[col].values, marker="o")
        plt.title(f"Yearly mean: {col}")
        plt.xlabel("Year")
        plt.ylabel(col)
        plt.xticks(rotation=45)
        plt.tight_layout()

        out_path = output_dir / f"06_yearly_mean_{col}.png"
        plt.savefig(out_path, dpi=150)
        plt.close()

        print(f"Сохранён график: {out_path}")


def plot_monthly_boxplots(df: pd.DataFrame, output_dir: Path) -> None:
    """
    Строит boxplot по месяцам для каждого признака.
    """
    for col in NUMERIC_COLUMNS:
        month_data = [df.loc[df["month"] == month, col].dropna().values for month in MONTH_ORDER]

        plt.figure(figsize=(11, 5))
        plt.boxplot(month_data, tick_labels=MONTH_LABELS)
        plt.title(f"Monthly boxplot: {col}")
        plt.xlabel("Month")
        plt.ylabel(col)
        plt.tight_layout()

        out_path = output_dir / f"06_monthly_boxplot_{col}.png"
        plt.savefig(out_path, dpi=150)
        plt.close()

        print(f"Сохранён график: {out_path}")


def plot_season_means(season_means: pd.DataFrame, output_dir: Path) -> None:
    """
    Строит столбчатые графики средних значений по сезонам.
    """
    for col in NUMERIC_COLUMNS:
        plt.figure(figsize=(8, 5))
        plt.bar(SEASON_ORDER, season_means[col].reindex(SEASON_ORDER).values)
        plt.title(f"Season mean: {col}")
        plt.xlabel("Season")
        plt.ylabel(col)
        plt.tight_layout()

        out_path = output_dir / f"06_season_mean_{col}.png"
        plt.savefig(out_path, dpi=150)
        plt.close()

        print(f"Сохранён график: {out_path}")


def main() -> None:
    print("=== Анализ сезонности ===")
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
    # Таблицы агрегатов
    # =========================
    monthly_means = df.groupby("month", observed=True)[NUMERIC_COLUMNS].mean().round(4)
    monthly_medians = df.groupby("month", observed=True)[NUMERIC_COLUMNS].median().round(4)
    yearly_means = df.groupby("year", observed=True)[NUMERIC_COLUMNS].mean().round(4)
    season_means = df.groupby("season", observed=True)[NUMERIC_COLUMNS].mean().round(4)

    save_table(monthly_means, OUTPUT_DIR / "06_monthly_means.csv")
    save_table(monthly_medians, OUTPUT_DIR / "06_monthly_medians.csv")
    save_table(yearly_means, OUTPUT_DIR / "06_yearly_means.csv")
    save_table(season_means, OUTPUT_DIR / "06_season_means.csv")
    print()

    print("Средние значения по месяцам:")
    print(monthly_means.to_string())
    print()
    print("Средние значения по сезонам:")
    print(season_means.to_string())
    print()

    # =========================
    # Графики
    # =========================
    plot_monthly_means(monthly_means, OUTPUT_DIR)
    print()
    plot_yearly_means(yearly_means, OUTPUT_DIR)
    print()
    plot_monthly_boxplots(df, OUTPUT_DIR)
    print()
    plot_season_means(season_means, OUTPUT_DIR)
    print()

    print("Готово. Все результаты сохранены в папку 06_seasonality.")


if __name__ == "__main__":
    main()
