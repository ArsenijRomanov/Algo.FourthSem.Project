"""
07_analyze_diurnal_profiles.py

Суточные профили с учётом GTI и разницы GTI-GHI.
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

DATA_PATH = Path("weather_msk.csv")
OUTPUT_DIR = Path("07_diurnal_profiles")
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
    df["hour"] = df[DATETIME_COL].dt.hour
    df["month"] = df[DATETIME_COL].dt.month
    df["month_label"] = pd.Categorical(df["month"].map(dict(zip(MONTH_ORDER, MONTH_LABELS))), categories=MONTH_LABELS, ordered=True)
    df["season"] = pd.Categorical(df["month"].map(SEASON_MAP), categories=SEASON_ORDER, ordered=True)
    return df

def save_table(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, encoding="utf-8-sig")

def plot_profiles(df: pd.DataFrame, group_col: str, group_order: list[str|int], output_dir: Path, prefix: str) -> None:
    hours = list(range(24))
    for col in NUMERIC_COLUMNS + ["GTI_minus_GHI"]:
        plt.figure(figsize=(12, 6))
        for group in group_order:
            series = df.loc[df[group_col] == group].groupby("hour", observed=True)[col].mean().reindex(hours)
            plt.plot(hours, series.values, label=str(group))
        plt.title(f"{prefix}: {col}")
        plt.xlabel("Hour of day")
        plt.ylabel(col)
        plt.xticks(hours)
        plt.legend(ncol=3, fontsize=8)
        plt.tight_layout()
        plt.savefig(output_dir / f"07_{prefix}_{col}.png", dpi=150)
        plt.close()

def plot_heatmaps_like_tables(df: pd.DataFrame, output_dir: Path) -> None:
    for col in NUMERIC_COLUMNS + ["GTI_minus_GHI"]:
        month_hour = df.pivot_table(values=col, index="month", columns="hour", aggfunc="mean", observed=True).reindex(MONTH_ORDER).round(4)
        season_hour = df.pivot_table(values=col, index="season", columns="hour", aggfunc="mean", observed=True).reindex(SEASON_ORDER).round(4)
        save_table(month_hour, output_dir / f"07_month_hour_table_{col}.csv")
        save_table(season_hour, output_dir / f"07_season_hour_table_{col}.csv")

def main() -> None:
    print("=== Анализ суточных профилей ===")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(DATA_PATH)
    required_cols = [DATETIME_COL] + NUMERIC_COLUMNS
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_cols}")

    df = add_calendar_columns(df)
    df["GTI_minus_GHI"] = df["GTI_W_m2"] - df["GHI_W_m2"]

    hourly_all = df.groupby("hour", observed=True)[NUMERIC_COLUMNS + ["GTI_minus_GHI"]].mean().round(4)
    save_table(hourly_all, OUTPUT_DIR / "07_hourly_mean_all_data.csv")
    print(hourly_all.to_string())
    print()

    plot_heatmaps_like_tables(df, OUTPUT_DIR)
    plot_profiles(df, "season", SEASON_ORDER, OUTPUT_DIR, "seasonal_hourly_profile")
    plot_profiles(df, "month", MONTH_ORDER, OUTPUT_DIR, "monthly_hourly_profile")

    print("Готово. Все результаты сохранены в папку 07_diurnal_profiles.")

if __name__ == "__main__":
    main()
