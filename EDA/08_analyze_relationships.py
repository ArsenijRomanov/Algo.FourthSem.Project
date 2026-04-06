"""
08_analyze_relationships.py

Связи между признаками с отдельным анализом GTI.
"""

from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

try:
    import pvlib
except ImportError as exc:
    raise ImportError("Не найден пакет pvlib. Установите его: pip install pvlib") from exc

DATA_PATH = Path("weather_msk.csv")
DATETIME_COL = "datetime_msk"
TIMEZONE = "Europe/Moscow"
LATITUDE = 45.020131
LONGITUDE = 38.932607
DAY_THRESHOLD_DEG = 0.0

NUMERIC_COLUMNS = [
    "GTI_W_m2",
    "GHI_W_m2",
    "DNI_W_m2",
    "DHI_W_m2",
    "temp_C",
    "cloud_pct",
    "wind_m_s",
]
RADIATION_COLUMNS = ["GTI_W_m2", "GHI_W_m2", "DNI_W_m2", "DHI_W_m2"]

def add_solar_position(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df[DATETIME_COL] = pd.to_datetime(df[DATETIME_COL], errors="coerce")
    dt_local = df[DATETIME_COL].dt.tz_localize(
        TIMEZONE,
        ambiguous="NaT",
        nonexistent="shift_forward",
    )
    solar_pos = pvlib.solarposition.get_solarposition(
        time=dt_local,
        latitude=LATITUDE,
        longitude=LONGITUDE,
        method="nrel_numpy",
    )
    df["solar_zenith_deg"] = solar_pos["apparent_zenith"].values
    df["solar_elevation_deg"] = solar_pos["apparent_elevation"].values
    df["solar_azimuth_deg"] = solar_pos["azimuth"].values
    df["is_day"] = df["solar_elevation_deg"] > DAY_THRESHOLD_DEG
    return df

OUTPUT_DIR = Path("08_relationships")
ALL_CORR_COLUMNS = NUMERIC_COLUMNS + ["GTI_to_GHI_ratio", "GTI_minus_GHI"]

SCATTER_PAIRS = [
    ("cloud_pct", "GTI_W_m2"),
    ("cloud_pct", "GHI_W_m2"),
    ("cloud_pct", "DNI_W_m2"),
    ("cloud_pct", "DHI_W_m2"),
    ("temp_C", "GTI_W_m2"),
    ("temp_C", "GHI_W_m2"),
    ("GHI_W_m2", "GTI_W_m2"),
    ("DNI_W_m2", "GTI_W_m2"),
    ("DHI_W_m2", "GTI_W_m2"),
    ("wind_m_s", "temp_C"),
    ("wind_m_s", "GTI_W_m2"),
]
BINNED_PAIRS = [
    ("cloud_pct", "GTI_W_m2"),
    ("cloud_pct", "GHI_W_m2"),
    ("cloud_pct", "DNI_W_m2"),
    ("cloud_pct", "DHI_W_m2"),
    ("temp_C", "GTI_W_m2"),
    ("temp_C", "GHI_W_m2"),
    ("wind_m_s", "GTI_W_m2"),
]
SCATTER_SAMPLE_SIZE = 20000
SCATTER_ALPHA = 0.08
SCATTER_SIZE = 8
N_BINS = 20

def make_output_dirs(base_dir: Path) -> dict[str, Path]:
    tables_dir = base_dir / "tables"
    corr_dir = base_dir / "correlations"
    scatter_dir = base_dir / "scatter"
    binned_dir = base_dir / "binned"
    for directory in [base_dir, tables_dir, corr_dir, scatter_dir, binned_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    return {"tables": tables_dir, "correlations": corr_dir, "scatter": scatter_dir, "binned": binned_dir}

def save_table(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, encoding="utf-8-sig")

def compute_correlation_tables(df: pd.DataFrame, cols: list[str]):
    return df[cols].corr(method="pearson").round(4), df[cols].corr(method="spearman").round(4)

def plot_correlation_heatmap(corr: pd.DataFrame, title: str, out_path: Path) -> None:
    plt.figure(figsize=(9, 7))
    plt.imshow(corr.values, aspect="auto")
    plt.colorbar()
    plt.xticks(range(len(corr.columns)), corr.columns, rotation=45, ha="right")
    plt.yticks(range(len(corr.index)), corr.index)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()

def get_scatter_sample(df: pd.DataFrame, columns: list[str], sample_size: int) -> pd.DataFrame:
    work_df = df[columns].dropna()
    if len(work_df) <= sample_size:
        return work_df
    return work_df.sample(n=sample_size, random_state=42)

def plot_scatter_pair(df: pd.DataFrame, x_col: str, y_col: str, out_path: Path, title_suffix: str) -> None:
    sample_df = get_scatter_sample(df, [x_col, y_col], SCATTER_SAMPLE_SIZE)
    plt.figure(figsize=(8, 5))
    plt.scatter(sample_df[x_col], sample_df[y_col], alpha=SCATTER_ALPHA, s=SCATTER_SIZE)
    plt.xlabel(x_col)
    plt.ylabel(y_col)
    plt.title(f"{y_col} vs {x_col} ({title_suffix})")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()

def plot_binned_relationship(df: pd.DataFrame, x_col: str, y_col: str, out_path: Path, title_suffix: str) -> None:
    work_df = df[[x_col, y_col]].dropna().copy()
    if work_df.empty or work_df[x_col].nunique() < 2:
        return
    work_df["x_bin"] = pd.cut(work_df[x_col], bins=N_BINS, include_lowest=True, duplicates="drop")
    grouped = work_df.groupby("x_bin", observed=True)[y_col].agg(["mean", "count"]).reset_index()
    grouped["bin_center"] = grouped["x_bin"].apply(lambda interval: interval.mid)
    plt.figure(figsize=(8, 5))
    plt.plot(grouped["bin_center"], grouped["mean"], marker="o")
    plt.xlabel(x_col)
    plt.ylabel(f"mean({y_col})")
    plt.title(f"Binned mean: {y_col} vs {x_col} ({title_suffix})")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()
    grouped.to_csv(out_path.with_suffix(".csv"), index=False, encoding="utf-8-sig")

def main() -> None:
    print("=== Анализ взаимосвязей признаков ===")
    dirs = make_output_dirs(OUTPUT_DIR)
    df = pd.read_csv(DATA_PATH)
    required_cols = [DATETIME_COL] + NUMERIC_COLUMNS
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_cols}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = add_solar_position(df)

    df["GTI_to_GHI_ratio"] = np.where(df["GHI_W_m2"] > 0, df["GTI_W_m2"] / df["GHI_W_m2"], np.nan)
    df["GTI_minus_GHI"] = df["GTI_W_m2"] - df["GHI_W_m2"]
    day_df = df[df["is_day"]].copy()

    print(f"Всего строк: {len(df):,}")
    print(f"Дневных строк: {len(day_df):,}")
    print(f"Доля дневных строк: {len(day_df) / len(df):.4f}")
    print()

    pearson_all, spearman_all = compute_correlation_tables(df, ALL_CORR_COLUMNS)
    save_table(pearson_all, dirs["tables"] / "08_pearson_corr_all_data.csv")
    save_table(spearman_all, dirs["tables"] / "08_spearman_corr_all_data.csv")
    plot_correlation_heatmap(pearson_all, "Pearson correlation (all data)", dirs["correlations"] / "08_pearson_corr_all_data.png")
    plot_correlation_heatmap(spearman_all, "Spearman correlation (all data)", dirs["correlations"] / "08_spearman_corr_all_data.png")

    pearson_day, spearman_day = compute_correlation_tables(day_df, ALL_CORR_COLUMNS)
    save_table(pearson_day, dirs["tables"] / "08_pearson_corr_daytime_data.csv")
    save_table(spearman_day, dirs["tables"] / "08_spearman_corr_daytime_data.csv")
    plot_correlation_heatmap(pearson_day, "Pearson correlation (daytime data)", dirs["correlations"] / "08_pearson_corr_daytime_data.png")
    plot_correlation_heatmap(spearman_day, "Spearman correlation (daytime data)", dirs["correlations"] / "08_spearman_corr_daytime_data.png")

    print("Матрица корреляции Пирсона (daytime):")
    print(pearson_day.to_string())
    print()

    for x_col, y_col in SCATTER_PAIRS:
        plot_scatter_pair(day_df, x_col, y_col, dirs["scatter"] / f"08_daytime_scatter_{y_col}_vs_{x_col}.png", "daytime")

    for x_col, y_col in BINNED_PAIRS:
        plot_binned_relationship(day_df, x_col, y_col, dirs["binned"] / f"08_daytime_binned_{y_col}_vs_{x_col}.png", "daytime")

    print("Готово. Все результаты сохранены в папку 08_relationships.")

if __name__ == "__main__":
    main()
