
"""
05_full_descriptive_statistics.py

Что делает скрипт:
- загружает weather_msk.csv;
- считает солнечную геометрию через pvlib;
- выделяет дневные часы по высоте Солнца;
- считает описательную статистику по всем данным и отдельно по дневным;
- строит гистограммы и boxplot по всем данным и отдельно по дневным;
- сохраняет результаты в папку 05_statistics со следующей структурой:

05_statistics/
├── all_data/
│   ├── tables/
│   ├── histograms/
│   └── boxplots/
└── daytime_data/
    ├── tables/
    ├── histograms/
    └── boxplots/

Что проверяется:
- диапазоны значений признаков;
- квантили распределений;
- доля нулей и отрицательных значений;
- форма распределений;
- отличие дневных распределений от распределений на всём ряде.

Важно:
- время берётся из столбца datetime_msk;
- время трактуется как Europe/Moscow;
- для работы нужен пакет pvlib.
"""

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import pandas as pd

try:
    import pvlib
except ImportError as exc:
    raise ImportError(
        "Не найден пакет pvlib. Установите его: pip install pvlib"
    ) from exc


DATA_PATH = Path("weather_msk.csv")
OUTPUT_DIR = Path("05_statistics")

DATETIME_COL = "datetime_msk"
TIMEZONE = "Europe/Moscow"

LATITUDE = 45.020131
LONGITUDE = 38.932607

DAY_THRESHOLD_DEG = 0.0

NUMERIC_COLUMNS = [
    "GHI_W_m2",
    "DNI_W_m2",
    "DHI_W_m2",
    "temp_C",
    "cloud_pct",
    "wind_m_s",
]

RADIATION_COLUMNS = ["GHI_W_m2", "DNI_W_m2", "DHI_W_m2"]
EXTRA_QUANTILES = [0.01, 0.05, 0.95, 0.99]
HIST_BINS = 50


def make_output_dirs(base_dir: Path, dataset_name: str) -> dict[str, Path]:
    """Создаёт структуру папок для конкретного набора данных."""
    dataset_dir = base_dir / dataset_name
    tables_dir = dataset_dir / "tables"
    hist_dir = dataset_dir / "histograms"
    box_dir = dataset_dir / "boxplots"

    for directory in [dataset_dir, tables_dir, hist_dir, box_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    return {
        "dataset_dir": dataset_dir,
        "tables_dir": tables_dir,
        "hist_dir": hist_dir,
        "box_dir": box_dir,
    }


def add_solar_position(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    dt = pd.to_datetime(df[DATETIME_COL], errors="coerce")
    dt_local = dt.dt.tz_localize(
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


def build_summary_table(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    stats = df[columns].describe().T
    stats = stats.rename(
        columns={
            "count": "count_non_null",
            "mean": "mean",
            "std": "std",
            "min": "min",
            "25%": "q25",
            "50%": "median",
            "75%": "q75",
            "max": "max",
        }
    )

    stats["missing_count"] = df[columns].isna().sum()
    stats["missing_share"] = df[columns].isna().mean()

    extra_quantiles = df[columns].quantile(EXTRA_QUANTILES).T
    extra_quantiles.columns = [f"q{int(q * 100):02d}" for q in EXTRA_QUANTILES]

    zero_negative_info = pd.DataFrame(index=columns)
    zero_negative_info["zero_count"] = (df[columns] == 0).sum()
    zero_negative_info["zero_share"] = (df[columns] == 0).mean()
    zero_negative_info["negative_count"] = (df[columns] < 0).sum()
    zero_negative_info["negative_share"] = (df[columns] < 0).mean()

    summary = stats.join(extra_quantiles, how="left").join(zero_negative_info, how="left")

    ordered_cols = [
        "count_non_null",
        "missing_count",
        "missing_share",
        "mean",
        "std",
        "min",
        "q01",
        "q05",
        "q25",
        "median",
        "q75",
        "q95",
        "q99",
        "max",
        "zero_count",
        "zero_share",
        "negative_count",
        "negative_share",
    ]
    return summary[[col for col in ordered_cols if col in summary.columns]]


def save_summary_tables(summary: pd.DataFrame, tables_dir: Path, prefix: str) -> None:
    full_path = tables_dir / f"{prefix}_summary.csv"
    short_path = tables_dir / f"{prefix}_report.csv"

    summary.to_csv(full_path, encoding="utf-8-sig")
    summary[["mean", "std", "min", "median", "max"]].round(4).to_csv(
        short_path, encoding="utf-8-sig"
    )

    print(f"Сохранена полная сводка: {full_path}")
    print(f"Сохранена краткая сводка: {short_path}")


def plot_histograms(df: pd.DataFrame, columns: list[str], hist_dir: Path, prefix: str) -> None:
    for col in columns:
        plt.figure(figsize=(8, 5))
        plt.hist(df[col].dropna(), bins=HIST_BINS)
        plt.title(f"Histogram: {col} ({prefix})")
        plt.xlabel(col)
        plt.ylabel("Count")
        plt.tight_layout()
        out_path = hist_dir / f"{prefix}_{col}_hist.png"
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f"Сохранена гистограмма: {out_path}")

    rows = (len(columns) + 1) // 2
    fig = plt.figure(figsize=(14, 4 * rows))
    for i, col in enumerate(columns, start=1):
        ax = fig.add_subplot(rows, 2, i)
        ax.hist(df[col].dropna(), bins=HIST_BINS)
        ax.set_title(col)
        ax.set_xlabel(col)
        ax.set_ylabel("Count")
    plt.tight_layout()
    out_path = hist_dir / f"{prefix}_all_histograms.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Сохранена сводная гистограмма: {out_path}")


def plot_boxplots(df: pd.DataFrame, columns: list[str], box_dir: Path, prefix: str) -> None:
    for col in columns:
        plt.figure(figsize=(8, 4.5))
        plt.boxplot(df[col].dropna(), vert=False)
        plt.title(f"Boxplot: {col} ({prefix})")
        plt.xlabel(col)
        plt.tight_layout()
        out_path = box_dir / f"{prefix}_{col}_boxplot.png"
        plt.savefig(out_path, dpi=150)
        plt.close()
        print(f"Сохранён boxplot: {out_path}")

    rows = (len(columns) + 1) // 2
    fig = plt.figure(figsize=(14, 4 * rows))
    for i, col in enumerate(columns, start=1):
        ax = fig.add_subplot(rows, 2, i)
        ax.boxplot(df[col].dropna(), vert=False)
        ax.set_title(col)
        ax.set_xlabel(col)
    plt.tight_layout()
    out_path = box_dir / f"{prefix}_all_boxplots.png"
    plt.savefig(out_path, dpi=150)
    plt.close()
    print(f"Сохранён сводный boxplot: {out_path}")


def main() -> None:
    print("=== Полная описательная статистика и графики ===")
    print(f"Файл: {DATA_PATH}")
    print(f"Папка результатов: {OUTPUT_DIR}")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Файл {DATA_PATH} не найден. Убедитесь, что он лежит рядом со скриптом."
        )

    df = pd.read_csv(DATA_PATH)

    required = [DATETIME_COL] + NUMERIC_COLUMNS
    missing_cols = [col for col in required if col not in df.columns]
    if missing_cols:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_cols}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = add_solar_position(df)

    day_df = df[df["is_day"]].copy()

    print("=== Краткий отчёт по выделению дневного времени ===")
    print(f"Всего строк: {len(df):,}")
    print(f"Дневных строк: {len(day_df):,}")
    print(f"Доля дневных строк: {len(day_df) / len(df):.4f}")
    print()
    print("Диапазон solar_elevation_deg:")
    print(df["solar_elevation_deg"].describe().round(4).to_string())
    print()

    # Общий обогащённый датасет сохраняем в корень папки 05_statistics
    enriched_path = OUTPUT_DIR / "05_enriched_with_solar_position.csv"
    df.to_csv(enriched_path, index=False, encoding="utf-8-sig")
    print(f"Сохранён датасет с солнечной геометрией: {enriched_path}")
    print()

    all_dirs = make_output_dirs(OUTPUT_DIR, "all_data")
    day_dirs = make_output_dirs(OUTPUT_DIR, "daytime_data")

    # Все данные
    summary_all = build_summary_table(df, NUMERIC_COLUMNS)
    print("=== Статистика по всем данным ===")
    print(summary_all.round(4).to_string())
    print()

    save_summary_tables(summary_all, all_dirs["tables_dir"], "05_all_data")
    plot_histograms(df, NUMERIC_COLUMNS, all_dirs["hist_dir"], "05_all_data")
    print()
    plot_boxplots(df, NUMERIC_COLUMNS, all_dirs["box_dir"], "05_all_data")
    print()

    # Дневные данные
    summary_day = build_summary_table(day_df, NUMERIC_COLUMNS)
    print("=== Статистика по дневным данным ===")
    print(summary_day.round(4).to_string())
    print()

    save_summary_tables(summary_day, day_dirs["tables_dir"], "05_daytime_data")
    plot_histograms(day_df, NUMERIC_COLUMNS, day_dirs["hist_dir"], "05_daytime_data")
    print()
    plot_boxplots(day_df, NUMERIC_COLUMNS, day_dirs["box_dir"], "05_daytime_data")
    print()

    print("=== Краткий вывод по радиации в дневное время ===")
    print(
        summary_day.loc[
            RADIATION_COLUMNS,
            ["mean", "std", "min", "median", "max", "zero_share", "negative_share"],
        ].round(4).to_string()
    )
    print()
    print("Готово. Все результаты сохранены в папке 05_statistics с раздельной структурой.")


if __name__ == "__main__":
    main()
