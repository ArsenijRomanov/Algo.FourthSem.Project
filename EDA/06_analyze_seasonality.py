"""
06_analyze_seasonality.py

Анализ сезонности с учётом GTI и с отдельной проверкой полноты лет.
"""
from pathlib import Path
import calendar
import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = Path("weather_msk.csv")
OUTPUT_DIR = Path("06_seasonality")
DATETIME_COL = "datetime_msk"

NUMERIC_COLUMNS = [
    "GTI_W_m2",
    "GHI_W_m2",
    "DNI_W_m2",
    "DHI_W_m2",
    "temp_C",
    "cloud_pct",
    "wind_m_s",
]
MONTH_ORDER = list(range(1, 13))
MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
SEASON_MAP = {12:"winter",1:"winter",2:"winter",3:"spring",4:"spring",5:"spring",6:"summer",7:"summer",8:"summer",9:"autumn",10:"autumn",11:"autumn"}
SEASON_ORDER = ["winter","spring","summer","autumn"]

def add_calendar_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[DATETIME_COL] = pd.to_datetime(df[DATETIME_COL], errors="coerce")
    df["year"] = df[DATETIME_COL].dt.year
    df["month"] = df[DATETIME_COL].dt.month
    df["month_label"] = pd.Categorical(df["month"].map(dict(zip(MONTH_ORDER, MONTH_LABELS))), categories=MONTH_LABELS, ordered=True)
    df["season"] = pd.Categorical(df["month"].map(SEASON_MAP), categories=SEASON_ORDER, ordered=True)
    return df

def save_table(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, encoding="utf-8-sig")

def expected_hours_for_year(year: int) -> int:
    return 8784 if calendar.isleap(year) else 8760

def plot_monthly_means(monthly_means: pd.DataFrame, output_dir: Path) -> None:
    for col in monthly_means.columns:
        plt.figure(figsize=(9, 5))
        plt.plot(MONTH_LABELS, monthly_means[col].reindex(MONTH_ORDER).values, marker="o")
        plt.title(f"Monthly mean: {col}")
        plt.xlabel("Month")
        plt.ylabel(col)
        plt.tight_layout()
        plt.savefig(output_dir / f"06_monthly_mean_{col}.png", dpi=150)
        plt.close()

def plot_yearly_means(yearly_means: pd.DataFrame, output_dir: Path, suffix: str) -> None:
    years = yearly_means.index.astype(str).tolist()
    for col in yearly_means.columns:
        plt.figure(figsize=(10, 5))
        plt.plot(years, yearly_means[col].values, marker="o")
        plt.title(f"Yearly mean ({suffix}): {col}")
        plt.xlabel("Year")
        plt.ylabel(col)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / f"06_yearly_mean_{suffix}_{col}.png", dpi=150)
        plt.close()

def plot_monthly_boxplots(df: pd.DataFrame, output_dir: Path) -> None:
    for col in NUMERIC_COLUMNS + ["GTI_minus_GHI"]:
        month_data = [df.loc[df["month"] == month, col].dropna().values for month in MONTH_ORDER]
        plt.figure(figsize=(11, 5))
        plt.boxplot(month_data, tick_labels=MONTH_LABELS)
        plt.title(f"Monthly boxplot: {col}")
        plt.xlabel("Month")
        plt.ylabel(col)
        plt.tight_layout()
        plt.savefig(output_dir / f"06_monthly_boxplot_{col}.png", dpi=150)
        plt.close()

def plot_season_means(season_means: pd.DataFrame, output_dir: Path) -> None:
    for col in season_means.columns:
        plt.figure(figsize=(8, 5))
        plt.bar(SEASON_ORDER, season_means[col].reindex(SEASON_ORDER).values)
        plt.title(f"Season mean: {col}")
        plt.xlabel("Season")
        plt.ylabel(col)
        plt.tight_layout()
        plt.savefig(output_dir / f"06_season_mean_{col}.png", dpi=150)
        plt.close()

def main() -> None:
    print("=== Анализ сезонности ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    required_cols = [DATETIME_COL] + NUMERIC_COLUMNS
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_cols}")

    df = add_calendar_columns(df)
    df["GTI_minus_GHI"] = df["GTI_W_m2"] - df["GHI_W_m2"]

    year_counts = df.groupby("year", observed=True).size().rename("observed_hours").to_frame()
    year_counts["expected_hours"] = [expected_hours_for_year(y) for y in year_counts.index]
    year_counts["is_full_year"] = year_counts["observed_hours"] == year_counts["expected_hours"]

    monthly_means = df.groupby("month", observed=True)[NUMERIC_COLUMNS + ["GTI_minus_GHI"]].mean().round(4)
    monthly_medians = df.groupby("month", observed=True)[NUMERIC_COLUMNS + ["GTI_minus_GHI"]].median().round(4)
    yearly_means = df.groupby("year", observed=True)[NUMERIC_COLUMNS + ["GTI_minus_GHI"]].mean().round(4)
    yearly_means_full = yearly_means.loc[year_counts["is_full_year"]]
    season_means = df.groupby("season", observed=True)[NUMERIC_COLUMNS + ["GTI_minus_GHI"]].mean().round(4)

    save_table(monthly_means, OUTPUT_DIR / "06_monthly_means.csv")
    save_table(monthly_medians, OUTPUT_DIR / "06_monthly_medians.csv")
    save_table(yearly_means, OUTPUT_DIR / "06_yearly_means_all_years.csv")
    save_table(yearly_means_full, OUTPUT_DIR / "06_yearly_means_full_years.csv")
    save_table(season_means, OUTPUT_DIR / "06_season_means.csv")
    save_table(year_counts, OUTPUT_DIR / "06_year_completeness.csv")

    print("Средние значения по месяцам:")
    print(monthly_means.to_string())
    print()
    print("Полнота лет:")
    print(year_counts.to_string())
    print()

    plot_monthly_means(monthly_means, OUTPUT_DIR)
    plot_yearly_means(yearly_means, OUTPUT_DIR, "all_years")
    if len(yearly_means_full) > 0:
        plot_yearly_means(yearly_means_full, OUTPUT_DIR, "full_years")
    plot_monthly_boxplots(df, OUTPUT_DIR)
    plot_season_means(season_means, OUTPUT_DIR)

    print("Готово. Все результаты сохранены в папку 06_seasonality.")

if __name__ == "__main__":
    main()
