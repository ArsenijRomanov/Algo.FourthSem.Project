"""
09_detect_anomalies.py

Что делает скрипт:
- загружает weather_msk.csv;
- рассчитывает солнечную геометрию через pvlib;
- выделяет дневные часы по высоте Солнца;
- ищет аномалии несколькими способами:
  1) нарушения физических ограничений;
  2) радиация ночью;
  3) выбросы по IQR;
  4) аномалии по rolling z-score;
  5) опционально Isolation Forest;
- сохраняет:
  - таблицу всех аномалий;
  - сводку по типам аномалий;
  - датасет с флагами;
  - очищенный датасет;
- складывает всё в папку 09_anomalies.

Что проверяется:
- нет ли физически невозможных значений;
- нет ли радиации в часы, когда Солнце под горизонтом;
- нет ли резких локальных скачков;
- нет ли статистически нетипичных наблюдений;
- какие аномалии лучше пометить, а какие можно удалить или интерполировать.

Важно:
- файл weather_msk.csv должен лежать рядом со скриптом;
- столбец времени должен называться datetime_msk;
- время трактуется как Europe/Moscow;
- для работы нужен пакет pvlib;
- Isolation Forest можно отключить, если не нужен.
"""

from pathlib import Path
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    import pvlib
except ImportError as exc:
    raise ImportError(
        "Не найден пакет pvlib. Установите его: pip install pvlib"
    ) from exc

# Isolation Forest опционален
try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except Exception:
    SKLEARN_AVAILABLE = False


DATA_PATH = Path("weather_msk.csv")
OUTPUT_DIR = Path("09_anomalies")

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

USE_ISOLATION_FOREST = True
IFOREST_CONTAMINATION = 0.005

IQR_MULTIPLIER = 1.5
ROLLING_WINDOW = 24
ROLLING_Z_THRESHOLD = 4.0

NIGHT_RADIATION_THRESHOLD = 1.0


def make_output_dirs(base_dir: Path) -> dict[str, Path]:
    tables_dir = base_dir / "tables"
    data_dir = base_dir / "data"
    plots_dir = base_dir / "plots"

    for directory in [base_dir, tables_dir, data_dir, plots_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    return {"tables": tables_dir, "data": data_dir, "plots": plots_dir}


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


def detect_physical_limit_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    anomalies = []

    rules = {
        "GHI_negative": df["GHI_W_m2"] < 0,
        "DNI_negative": df["DNI_W_m2"] < 0,
        "DHI_negative": df["DHI_W_m2"] < 0,
        "cloud_out_of_range_low": df["cloud_pct"] < 0,
        "cloud_out_of_range_high": df["cloud_pct"] > 100,
        "wind_negative": df["wind_m_s"] < 0,
    }

    for anomaly_type, mask in rules.items():
        temp = df.loc[mask].copy()
        if not temp.empty:
            temp["anomaly_type"] = anomaly_type
            anomalies.append(temp)

    if anomalies:
        return pd.concat(anomalies, ignore_index=True)

    return pd.DataFrame(columns=list(df.columns) + ["anomaly_type"])


def detect_night_radiation_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    mask = (
        (~df["is_day"]) &
        (
            (df["GHI_W_m2"] > NIGHT_RADIATION_THRESHOLD) |
            (df["DNI_W_m2"] > NIGHT_RADIATION_THRESHOLD) |
            (df["DHI_W_m2"] > NIGHT_RADIATION_THRESHOLD)
        )
    )

    result = df.loc[mask].copy()
    if not result.empty:
        result["anomaly_type"] = "radiation_at_night"
    return result


def detect_iqr_anomalies(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    anomalies = []

    for col in columns:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1

        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr

        mask = (df[col] < lower) | (df[col] > upper)
        temp = df.loc[mask].copy()

        if not temp.empty:
            temp["anomaly_type"] = f"iqr_outlier_{col}"
            anomalies.append(temp)

    if anomalies:
        return pd.concat(anomalies, ignore_index=True)

    return pd.DataFrame(columns=list(df.columns) + ["anomaly_type"])


def detect_rolling_zscore_anomalies(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    anomalies = []

    ordered_df = df.sort_values(DATETIME_COL).copy()

    for col in columns:
        rolling_mean = ordered_df[col].rolling(window=ROLLING_WINDOW, center=True, min_periods=12).mean()
        rolling_std = ordered_df[col].rolling(window=ROLLING_WINDOW, center=True, min_periods=12).std()

        z = (ordered_df[col] - rolling_mean) / rolling_std
        mask = z.abs() > ROLLING_Z_THRESHOLD

        temp = ordered_df.loc[mask].copy()
        if not temp.empty:
            temp["anomaly_type"] = f"rolling_zscore_{col}"
            temp["rolling_zscore"] = z.loc[mask].values
            anomalies.append(temp)

    if anomalies:
        return pd.concat(anomalies, ignore_index=True)

    return pd.DataFrame(columns=list(df.columns) + ["anomaly_type", "rolling_zscore"])


def detect_isolation_forest_anomalies(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if not USE_ISOLATION_FOREST or not SKLEARN_AVAILABLE:
        return pd.DataFrame(columns=list(df.columns) + ["anomaly_type", "iforest_score"])

    work_df = df[columns].dropna().copy()
    if work_df.empty:
        return pd.DataFrame(columns=list(df.columns) + ["anomaly_type", "iforest_score"])

    model = IsolationForest(
        contamination=IFOREST_CONTAMINATION,
        random_state=42,
        n_estimators=200,
    )
    preds = model.fit_predict(work_df)
    scores = model.decision_function(work_df)

    mask = preds == -1
    idx = work_df.index[mask]

    result = df.loc[idx].copy()
    if not result.empty:
        result["anomaly_type"] = "isolation_forest"
        result["iforest_score"] = scores[mask]

    return result


def plot_anomaly_counts(summary_df: pd.DataFrame, out_path: Path) -> None:
    plt.figure(figsize=(10, 5))
    plt.bar(summary_df["anomaly_type"], summary_df["count"])
    plt.xticks(rotation=45, ha="right")
    plt.ylabel("Count")
    plt.title("Anomaly counts by type")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close()


def main() -> None:
    print("=== Выявление и обработка аномалий ===")
    print(f"Файл: {DATA_PATH}")
    print(f"Папка результатов: {OUTPUT_DIR}")
    print()

    dirs = make_output_dirs(OUTPUT_DIR)

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Файл {DATA_PATH} не найден. Убедитесь, что он лежит рядом со скриптом."
        )

    df = pd.read_csv(DATA_PATH)

    required_cols = [DATETIME_COL] + NUMERIC_COLUMNS
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"В файле отсутствуют столбцы: {missing_cols}")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        df = add_solar_position(df)

    df = df.sort_values(DATETIME_COL).reset_index(drop=True)

    physical = detect_physical_limit_anomalies(df)
    night_rad = detect_night_radiation_anomalies(df)
    iqr = detect_iqr_anomalies(df, NUMERIC_COLUMNS)
    rolling = detect_rolling_zscore_anomalies(df, NUMERIC_COLUMNS)
    iforest = detect_isolation_forest_anomalies(df, NUMERIC_COLUMNS)

    anomaly_frames = [x for x in [physical, night_rad, iqr, rolling, iforest] if not x.empty]

    if anomaly_frames:
        all_anomalies = pd.concat(anomaly_frames, ignore_index=True)
    else:
        all_anomalies = pd.DataFrame(columns=list(df.columns) + ["anomaly_type"])

    summary = (
        all_anomalies["anomaly_type"]
        .value_counts(dropna=False)
        .rename_axis("anomaly_type")
        .reset_index(name="count")
    )

    # Флаги в основном датасете
    flagged_df = df.copy()
    flagged_df["has_any_anomaly"] = False
    flagged_df["anomaly_count"] = 0

    if not all_anomalies.empty:
        counts_by_time = (
            all_anomalies.groupby(DATETIME_COL)
            .size()
            .rename("anomaly_count")
            .reset_index()
        )

        flagged_df = flagged_df.merge(counts_by_time, on=DATETIME_COL, how="left", suffixes=("", "_new"))
        flagged_df["anomaly_count"] = flagged_df["anomaly_count_new"].fillna(0).astype(int)
        flagged_df = flagged_df.drop(columns=["anomaly_count_new"])
        flagged_df["has_any_anomaly"] = flagged_df["anomaly_count"] > 0

    # Очищенный датасет: убираем только строки с нарушениями физики и радиацией ночью
    hard_types = {
        "GHI_negative",
        "DNI_negative",
        "DHI_negative",
        "cloud_out_of_range_low",
        "cloud_out_of_range_high",
        "wind_negative",
        "radiation_at_night",
    }

    if not all_anomalies.empty:
        hard_times = all_anomalies.loc[all_anomalies["anomaly_type"].isin(hard_types), DATETIME_COL].drop_duplicates()
        cleaned_df = flagged_df.loc[~flagged_df[DATETIME_COL].isin(hard_times)].copy()
    else:
        cleaned_df = flagged_df.copy()

    # Сохранение
    save_path_anomalies = dirs["tables"] / "09_all_anomalies.csv"
    save_path_summary = dirs["tables"] / "09_anomaly_summary.csv"
    save_path_flagged = dirs["data"] / "09_data_with_flags.csv"
    save_path_clean = dirs["data"] / "09_cleaned_data.csv"

    all_anomalies.to_csv(save_path_anomalies, index=False, encoding="utf-8-sig")
    summary.to_csv(save_path_summary, index=False, encoding="utf-8-sig")
    flagged_df.to_csv(save_path_flagged, index=False, encoding="utf-8-sig")
    cleaned_df.to_csv(save_path_clean, index=False, encoding="utf-8-sig")

    if not summary.empty:
        plot_anomaly_counts(summary, dirs["plots"] / "09_anomaly_counts.png")

    print(f"Всего строк в исходном датасете: {len(df):,}")
    print(f"Найдено строк аномалий (с учётом повторов по типам): {len(all_anomalies):,}")
    print(f"Строк в очищенном датасете: {len(cleaned_df):,}")
    print()

    if not summary.empty:
        print("Сводка по аномалиям:")
        print(summary.to_string(index=False))
    else:
        print("Аномалии не найдены.")

    print()
    print(f"Сохранена таблица аномалий: {save_path_anomalies}")
    print(f"Сохранена сводка: {save_path_summary}")
    print(f"Сохранён датасет с флагами: {save_path_flagged}")
    print(f"Сохранён очищенный датасет: {save_path_clean}")
    print("Готово. Все результаты сохранены в папку 09_anomalies.")


if __name__ == "__main__":
    main()
