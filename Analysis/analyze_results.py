#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# -----------------------------
# Helpers
# -----------------------------

def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dump_json(data: Any, path: Path) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, encoding="utf-8-sig")


def safe_div(numerator: float, denominator: float) -> float:
    if abs(float(denominator)) < 1e-12:
        return 0.0
    return float(numerator) / float(denominator)


def percent(value: float) -> float:
    return float(value) * 100.0


# -----------------------------
# Config
# -----------------------------

@dataclass
class PathsConfig:
    results_root: str
    output_dir: str


@dataclass
class StudyMappingConfig:
    coldstandby_single_dir: str
    coldstandby_mc_dir: str
    hybrid_single_dir: str
    hybrid_mc_dir: str


@dataclass
class EconomicAssumptions:
    currency: str
    project_horizon_years: int
    discount_rate: float
    fuel_price_usd_per_l: float
    hybrid_capex_usd: float
    annual_om_baseline_usd: float
    annual_om_hybrid_usd: float


@dataclass
class OutageLossModel:
    mode: str
    loss_usd_per_down_hour: float
    also_count_partial_unserved_hours: bool
    loss_usd_per_unserved_kwh: float


@dataclass
class AnalysisOptions:
    use_mc_for_final_economics: bool
    use_single_run_for_time_series_plots: bool
    simple_payback: bool
    discounted_payback: bool
    compute_npv: bool
    compute_pi: bool
    compute_irr: bool


@dataclass
class ReportOutputs:
    save_csv: bool
    save_json: bool
    save_png: bool
    save_markdown_summary: bool


@dataclass
class AppConfig:
    paths: PathsConfig
    study_mapping: StudyMappingConfig
    economic_assumptions: EconomicAssumptions
    outage_loss_model: OutageLossModel
    analysis_options: AnalysisOptions
    report_outputs: ReportOutputs

    @staticmethod
    def from_dict(raw: dict[str, Any]) -> "AppConfig":
        return AppConfig(
            paths=PathsConfig(**raw["paths"]),
            study_mapping=StudyMappingConfig(**raw["study_mapping"]),
            economic_assumptions=EconomicAssumptions(**raw["economic_assumptions"]),
            outage_loss_model=OutageLossModel(**raw["outage_loss_model"]),
            analysis_options=AnalysisOptions(**raw["analysis_options"]),
            report_outputs=ReportOutputs(**raw["report_outputs"]),
        )


# -----------------------------
# Study discovery
# -----------------------------

@dataclass
class StudyPaths:
    cold_single_summary: Path
    cold_single_hours: Path
    cold_mc_summaries: Path
    hybrid_single_summary: Path
    hybrid_single_hours: Path
    hybrid_mc_summaries: Path


def resolve_config_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (base / path).resolve()


def find_single_file(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.glob(pattern))
    if not matches:
        raise FileNotFoundError(f"Не найден файл по шаблону {pattern!r} в {directory}")
    if len(matches) > 1:
        raise RuntimeError(
            f"По шаблону {pattern!r} найдено несколько файлов в {directory}:\n" + "\n".join(str(m) for m in matches)
        )
    return matches[0]


def discover_studies(results_root: Path, mapping: StudyMappingConfig) -> StudyPaths:
    cold_single_dir = results_root / mapping.coldstandby_single_dir
    cold_mc_dir = results_root / mapping.coldstandby_mc_dir
    hybrid_single_dir = results_root / mapping.hybrid_single_dir
    hybrid_mc_dir = results_root / mapping.hybrid_mc_dir

    return StudyPaths(
        cold_single_summary=find_single_file(cold_single_dir, "coldstandby_summary_seed_*.json"),
        cold_single_hours=find_single_file(cold_single_dir, "coldstandby_hours_seed_*.csv"),
        cold_mc_summaries=find_single_file(cold_mc_dir, "coldstandby_montecarlo_summaries.json"),
        hybrid_single_summary=find_single_file(hybrid_single_dir, "hybrid_summary_seed_*.json"),
        hybrid_single_hours=find_single_file(hybrid_single_dir, "hybrid_hours_seed_*.csv"),
        hybrid_mc_summaries=find_single_file(hybrid_mc_dir, "hybrid_montecarlo_summaries.json"),
    )


# -----------------------------
# Reading source files
# -----------------------------

def read_summary(path: Path) -> dict[str, Any]:
    return load_json(path)


def read_mc_summaries(path: Path) -> pd.DataFrame:
    return pd.DataFrame(load_json(path))


def read_hourly_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "TimestampMsk" not in df.columns:
        raise ValueError(f"В файле {path} нет колонки TimestampMsk")
    df["TimestampMsk"] = pd.to_datetime(df["TimestampMsk"])
    return df.sort_values("TimestampMsk").reset_index(drop=True)


# -----------------------------
# Derived metrics from hourly runs
# -----------------------------

def compute_load_from_hybrid_hours(df: pd.DataFrame) -> pd.Series:
    return (
        df.get("CoveredByPvKWh", 0.0)
        + df.get("CoveredByBatteryKWh", 0.0)
        + df.get("CoveredByDieselKWh", 0.0)
        + df.get("UnservedEnergyKWh", 0.0)
    )


def compute_load_from_cold_hours(df: pd.DataFrame) -> pd.Series:
    return df.get("CoveredByDieselKWh", 0.0) + df.get("UnservedEnergyKWh", 0.0)


def enrich_hybrid_hours_with_curtailment(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "CurtailmentKWh" not in out.columns:
        out["CurtailmentKWh"] = (
            out.get("EPvKWh", 0.0).astype(float)
            - out.get("CoveredByPvKWh", 0.0).astype(float)
            - out.get("ChargeKWh", 0.0).astype(float)
        ).clip(lower=0.0)
    else:
        out["CurtailmentKWh"] = out["CurtailmentKWh"].astype(float)

    out["HoursBatteryFullWithPv"] = (
        out.get("IsFull", False).astype(bool)
        & (out.get("EPvKWh", 0.0).astype(float) > 0.0)
    ).astype(int)
    return out


def assign_project_years(df: pd.DataFrame, timestamp_col: str = "TimestampMsk") -> pd.DataFrame:
    out = df.copy()
    start = out[timestamp_col].min()
    out["ProjectYear"] = 0
    current_start = start
    year = 1
    last_ts = out[timestamp_col].max() + pd.Timedelta(hours=1)

    while current_start < last_ts:
        next_start = current_start + pd.DateOffset(years=1)
        mask = (out[timestamp_col] >= current_start) & (out[timestamp_col] < next_start)
        out.loc[mask, "ProjectYear"] = year
        current_start = next_start
        year += 1

    out["ProjectYear"] = out["ProjectYear"].astype(int)
    return out


def compute_outage_cost(df: pd.DataFrame, model: OutageLossModel) -> pd.Series:
    if model.mode == "per_down_hour":
        if model.also_count_partial_unserved_hours:
            outage_hours = (df.get("UnservedEnergyKWh", 0.0).astype(float) > 0.0).astype(int)
        else:
            outage_hours = df.get("SystemDown", False).astype(bool).astype(int)
        return outage_hours.astype(float) * float(model.loss_usd_per_down_hour)

    if model.mode == "per_unserved_kwh":
        return df.get("UnservedEnergyKWh", 0.0).astype(float) * float(model.loss_usd_per_unserved_kwh)

    raise ValueError(
        "outage_loss_model.mode должен быть 'per_down_hour' или 'per_unserved_kwh'"
    )


def build_yearly_metrics(
    hybrid_hours: pd.DataFrame,
    cold_hours: pd.DataFrame,
    econ: EconomicAssumptions,
    outage_model: OutageLossModel,
) -> pd.DataFrame:
    h = assign_project_years(enrich_hybrid_hours_with_curtailment(hybrid_hours))
    c = assign_project_years(cold_hours)

    h = h.copy()
    c = c.copy()
    h["LoadKWh"] = compute_load_from_hybrid_hours(h)
    c["LoadKWh"] = compute_load_from_cold_hours(c)
    h["OutageCostUsd"] = compute_outage_cost(h, outage_model)
    c["OutageCostUsd"] = compute_outage_cost(c, outage_model)

    hybrid_yearly = h.groupby("ProjectYear", as_index=False).agg(
        Hours=("TimestampMsk", "size"),
        LoadKWh=("LoadKWh", "sum"),
        PvGenerationKWh=("EPvKWh", "sum"),
        PvToLoadKWh=("CoveredByPvKWh", "sum"),
        BatteryToLoadKWh=("CoveredByBatteryKWh", "sum"),
        DieselToLoadKWh=("CoveredByDieselKWh", "sum"),
        FuelUsedL=("FuelUsedL", "sum"),
        UnservedEnergyKWh=("UnservedEnergyKWh", "sum"),
        SystemDownHours=("SystemDown", lambda s: int(s.astype(bool).sum())),
        Availability=("LoadFullyCovered", "mean"),
        OutageCostUsd=("OutageCostUsd", "sum"),
        AvgSocKWh=("SocKWh", "mean"),
        CurtailmentKWh=("CurtailmentKWh", "sum"),
        HoursBatteryFullWithPv=("HoursBatteryFullWithPv", "sum"),
    )
    hybrid_yearly["CurtailmentPctOfPv"] = np.where(
        hybrid_yearly["PvGenerationKWh"] > 0.0,
        hybrid_yearly["CurtailmentKWh"] / hybrid_yearly["PvGenerationKWh"],
        0.0,
    )

    cold_yearly = c.groupby("ProjectYear", as_index=False).agg(
        Hours=("TimestampMsk", "size"),
        LoadKWh=("LoadKWh", "sum"),
        DieselToLoadKWh=("CoveredByDieselKWh", "sum"),
        PrimaryFuelUsedL=("PrimaryFuelUsedL", "sum"),
        ReserveFuelUsedL=("ReserveFuelUsedL", "sum"),
        UnservedEnergyKWh=("UnservedEnergyKWh", "sum"),
        SystemDownHours=("SystemDown", lambda s: int(s.astype(bool).sum())),
        Availability=("LoadFullyCovered", "mean"),
        OutageCostUsd=("OutageCostUsd", "sum"),
        PrimaryRunHours=("ActiveDiesel", lambda s: int((s == "Primary").sum())),
        ReserveRunHours=("ActiveDiesel", lambda s: int((s == "Reserve").sum())),
    )
    cold_yearly["FuelUsedL"] = cold_yearly["PrimaryFuelUsedL"] + cold_yearly["ReserveFuelUsedL"]
    cold_yearly = cold_yearly.drop(columns=["PrimaryFuelUsedL", "ReserveFuelUsedL"])

    out = hybrid_yearly.merge(cold_yearly, on="ProjectYear", suffixes=("_Hybrid", "_Cold"), how="inner")
    out["FuelCostHybridUsd"] = out["FuelUsedL_Hybrid"] * econ.fuel_price_usd_per_l
    out["FuelCostColdUsd"] = out["FuelUsedL_Cold"] * econ.fuel_price_usd_per_l
    out["AnnualOmHybridUsd"] = float(econ.annual_om_hybrid_usd)
    out["AnnualOmColdUsd"] = float(econ.annual_om_baseline_usd)
    out["OperatingCostHybridUsd"] = out["FuelCostHybridUsd"] + out["AnnualOmHybridUsd"] + out["OutageCostUsd_Hybrid"]
    out["OperatingCostColdUsd"] = out["FuelCostColdUsd"] + out["AnnualOmColdUsd"] + out["OutageCostUsd_Cold"]
    out["IncrementalNetBenefitUsd"] = out["OperatingCostColdUsd"] - out["OperatingCostHybridUsd"]
    out["DiscountFactor"] = out["ProjectYear"].apply(lambda y: 1.0 / ((1.0 + econ.discount_rate) ** y))
    out["DiscountedNetBenefitUsd"] = out["IncrementalNetBenefitUsd"] * out["DiscountFactor"]
    out["CumulativeDiscountedUsd"] = -float(econ.hybrid_capex_usd) + out["DiscountedNetBenefitUsd"].cumsum()
    out["CumulativeUndiscountedUsd"] = -float(econ.hybrid_capex_usd) + out["IncrementalNetBenefitUsd"].cumsum()
    return out


# -----------------------------
# Profiles and events
# -----------------------------

def build_monthly_profiles(hybrid_hours: pd.DataFrame, cold_hours: pd.DataFrame) -> pd.DataFrame:
    h = enrich_hybrid_hours_with_curtailment(hybrid_hours)
    c = cold_hours.copy()
    h["Month"] = h["TimestampMsk"].dt.month
    c["Month"] = c["TimestampMsk"].dt.month
    h["LoadKWh"] = compute_load_from_hybrid_hours(h)
    c["LoadKWh"] = compute_load_from_cold_hours(c)

    hybrid_monthly = h.groupby("Month", as_index=False).agg(
        Scenario=("TimestampMsk", lambda _: "Hybrid"),
        LoadKWh=("LoadKWh", "mean"),
        PvGenerationKWh=("EPvKWh", "sum"),
        PvToLoadKWh=("CoveredByPvKWh", "sum"),
        BatteryToLoadKWh=("CoveredByBatteryKWh", "sum"),
        DieselToLoadKWh=("CoveredByDieselKWh", "sum"),
        FuelUsedL=("FuelUsedL", "sum"),
        UnservedEnergyKWh=("UnservedEnergyKWh", "sum"),
        AvgSocKWh=("SocKWh", "mean"),
        DownHours=("SystemDown", lambda s: int(s.astype(bool).sum())),
        CurtailmentKWh=("CurtailmentKWh", "sum"),
        HoursBatteryFullWithPv=("HoursBatteryFullWithPv", "sum"),
    )
    hybrid_monthly["LoadKWh"] = h.groupby("Month")["LoadKWh"].sum().values / h.groupby("Month")["TimestampMsk"].nunique().values * h.groupby("Month")["TimestampMsk"].nunique().values

    cold_monthly = c.groupby("Month", as_index=False).agg(
        Scenario=("TimestampMsk", lambda _: "ColdStandby"),
        LoadKWh=("LoadKWh", "mean"),
        PvGenerationKWh=("TimestampMsk", lambda _: 0.0),
        PvToLoadKWh=("TimestampMsk", lambda _: 0.0),
        BatteryToLoadKWh=("TimestampMsk", lambda _: 0.0),
        DieselToLoadKWh=("CoveredByDieselKWh", "sum"),
        PrimaryFuelUsedL=("PrimaryFuelUsedL", "sum"),
        ReserveFuelUsedL=("ReserveFuelUsedL", "sum"),
        UnservedEnergyKWh=("UnservedEnergyKWh", "sum"),
        AvgSocKWh=("TimestampMsk", lambda _: np.nan),
        DownHours=("SystemDown", lambda s: int(s.astype(bool).sum())),
        CurtailmentKWh=("TimestampMsk", lambda _: 0.0),
        HoursBatteryFullWithPv=("TimestampMsk", lambda _: 0),
    )
    cold_monthly["FuelUsedL"] = cold_monthly["PrimaryFuelUsedL"] + cold_monthly["ReserveFuelUsedL"]
    cold_monthly = cold_monthly.drop(columns=["PrimaryFuelUsedL", "ReserveFuelUsedL"])
    cold_monthly["LoadKWh"] = c.groupby("Month")["LoadKWh"].sum().values / c.groupby("Month")["TimestampMsk"].nunique().values * c.groupby("Month")["TimestampMsk"].nunique().values
    hybrid_monthly["CurtailmentPctOfPv"] = np.where(
        hybrid_monthly["PvGenerationKWh"] > 0.0,
        hybrid_monthly["CurtailmentKWh"] / hybrid_monthly["PvGenerationKWh"],
        0.0,
    )
    cold_monthly["CurtailmentPctOfPv"] = 0.0

    out = pd.concat([hybrid_monthly, cold_monthly], ignore_index=True)
    out = out.sort_values(["Scenario", "Month"]).reset_index(drop=True)
    return out


def build_hourly_profiles(hybrid_hours: pd.DataFrame, cold_hours: pd.DataFrame) -> pd.DataFrame:
    h = enrich_hybrid_hours_with_curtailment(hybrid_hours)
    c = cold_hours.copy()
    h["Hour"] = h["TimestampMsk"].dt.hour
    c["Hour"] = c["TimestampMsk"].dt.hour

    hybrid_profile = h.groupby("Hour", as_index=False).agg(
        Scenario=("TimestampMsk", lambda _: "Hybrid"),
        PvGenerationKWh=("EPvKWh", "mean"),
        PvToLoadKWh=("CoveredByPvKWh", "mean"),
        BatteryToLoadKWh=("CoveredByBatteryKWh", "mean"),
        DieselToLoadKWh=("CoveredByDieselKWh", "mean"),
        FuelUsedL=("FuelUsedL", "mean"),
        UnservedEnergyKWh=("UnservedEnergyKWh", "mean"),
        AvgSocKWh=("SocKWh", "mean"),
        CurtailmentKWh=("CurtailmentKWh", "mean"),
        HoursBatteryFullWithPvShare=("HoursBatteryFullWithPv", "mean"),
    )
    cold_profile = c.groupby("Hour", as_index=False).agg(
        Scenario=("TimestampMsk", lambda _: "ColdStandby"),
        PvGenerationKWh=("TimestampMsk", lambda _: 0.0),
        PvToLoadKWh=("TimestampMsk", lambda _: 0.0),
        BatteryToLoadKWh=("TimestampMsk", lambda _: 0.0),
        DieselToLoadKWh=("CoveredByDieselKWh", "mean"),
        PrimaryFuelUsedL=("PrimaryFuelUsedL", "mean"),
        ReserveFuelUsedL=("ReserveFuelUsedL", "mean"),
        UnservedEnergyKWh=("UnservedEnergyKWh", "mean"),
        AvgSocKWh=("TimestampMsk", lambda _: np.nan),
        CurtailmentKWh=("TimestampMsk", lambda _: 0.0),
        HoursBatteryFullWithPvShare=("TimestampMsk", lambda _: 0.0),
    )
    cold_profile["FuelUsedL"] = cold_profile["PrimaryFuelUsedL"] + cold_profile["ReserveFuelUsedL"]
    cold_profile = cold_profile.drop(columns=["PrimaryFuelUsedL", "ReserveFuelUsedL"])

    return pd.concat([hybrid_profile, cold_profile], ignore_index=True).sort_values(["Scenario", "Hour"]).reset_index(drop=True)


def extract_system_down_events(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    if "SystemDown" not in df.columns:
        return pd.DataFrame(columns=["Scenario", "EventId", "Start", "End", "DurationHours", "UnservedEnergyKWh"])

    work = df[["TimestampMsk", "SystemDown", "UnservedEnergyKWh"]].copy()
    work["SystemDown"] = work["SystemDown"].astype(bool)

    events: list[dict[str, Any]] = []
    event_id = 0
    in_event = False
    start = None
    duration = 0
    unserved = 0.0
    prev_ts = None

    for row in work.itertuples(index=False):
        ts = row.TimestampMsk
        down = bool(row.SystemDown)
        ue = float(row.UnservedEnergyKWh)

        if down and not in_event:
            in_event = True
            start = ts
            duration = 1
            unserved = ue
        elif down and in_event:
            duration += 1
            unserved += ue
        elif not down and in_event:
            event_id += 1
            events.append({
                "Scenario": scenario,
                "EventId": event_id,
                "Start": start,
                "End": prev_ts,
                "DurationHours": duration,
                "UnservedEnergyKWh": unserved,
            })
            in_event = False
            start = None
            duration = 0
            unserved = 0.0
        prev_ts = ts

    if in_event:
        event_id += 1
        events.append({
            "Scenario": scenario,
            "EventId": event_id,
            "Start": start,
            "End": prev_ts,
            "DurationHours": duration,
            "UnservedEnergyKWh": unserved,
        })

    return pd.DataFrame(events)


# -----------------------------
# Single-run summary table
# -----------------------------

def build_single_run_comparison(
    hybrid_summary: dict[str, Any],
    cold_summary: dict[str, Any],
    econ: EconomicAssumptions,
    yearly_cashflows: pd.DataFrame,
) -> pd.DataFrame:
    hybrid_load = float(hybrid_summary.get("TotalLoadKWh", 0.0))
    cold_load = float(cold_summary.get("TotalLoadKWh", 0.0))

    rows = [
        {
            "Scenario": "Hybrid",
            "TotalLoadKWh": hybrid_load,
            "TotalPvGenerationKWh": float(hybrid_summary.get("TotalPvGenerationKWh", 0.0)),
            "PvToLoadKWh": float(hybrid_summary.get("PvToLoadKWh", 0.0)),
            "BatteryToLoadKWh": float(hybrid_summary.get("BatteryToLoadKWh", 0.0)),
            "DieselToLoadKWh": float(hybrid_summary.get("DieselToLoadKWh", 0.0)),
            "FuelUsedL": float(hybrid_summary.get("FuelUsedL", 0.0)),
            "FuelCostUsd": float(hybrid_summary.get("FuelUsedL", 0.0)) * econ.fuel_price_usd_per_l,
            "UnservedEnergyKWh": float(hybrid_summary.get("UnservedEnergyKWh", 0.0)),
            "SystemDownHours": int(hybrid_summary.get("SystemDownHours", 0)),
            "Availability": float(hybrid_summary.get("Availability", 0.0)),
            "AvailabilityPct": percent(float(hybrid_summary.get("Availability", 0.0))),
            "RenewableCoveragePct": percent(safe_div(
                float(hybrid_summary.get("PvToLoadKWh", 0.0)) + float(hybrid_summary.get("BatteryToLoadKWh", 0.0)),
                hybrid_load,
            )),
            "CurtailmentKWh": float(hybrid_summary.get(
                "CurtailmentKWh",
                yearly_cashflows["CurtailmentKWh_Hybrid"].sum() if "CurtailmentKWh_Hybrid" in yearly_cashflows.columns
                else yearly_cashflows["CurtailmentKWh"].sum() if "CurtailmentKWh" in yearly_cashflows.columns
                else 0.0,
            )),
            "CurtailmentPctOfPv": percent(safe_div(
                float(hybrid_summary.get(
                    "CurtailmentKWh",
                    yearly_cashflows["CurtailmentKWh_Hybrid"].sum() if "CurtailmentKWh_Hybrid" in yearly_cashflows.columns
                    else yearly_cashflows["CurtailmentKWh"].sum() if "CurtailmentKWh" in yearly_cashflows.columns
                    else 0.0,
                )),
                float(hybrid_summary.get("TotalPvGenerationKWh", 0.0)),
            )),
            "HoursBatteryFullWithPv": float(yearly_cashflows["HoursBatteryFullWithPv_Hybrid"].sum()) if "HoursBatteryFullWithPv_Hybrid" in yearly_cashflows.columns else float(yearly_cashflows["HoursBatteryFullWithPv"].sum()) if "HoursBatteryFullWithPv" in yearly_cashflows.columns else 0.0,
            "AnnualOmUsd": float(econ.annual_om_hybrid_usd),
            "OutageCostUsd": float(yearly_cashflows["OutageCostUsd_Hybrid"].sum()),
            "OperatingCostUsd": float(yearly_cashflows["OperatingCostHybridUsd"].sum()),
        },
        {
            "Scenario": "ColdStandby",
            "TotalLoadKWh": cold_load,
            "TotalPvGenerationKWh": 0.0,
            "PvToLoadKWh": 0.0,
            "BatteryToLoadKWh": 0.0,
            "DieselToLoadKWh": float(cold_summary.get("DieselToLoadKWh", 0.0)),
            "FuelUsedL": float(cold_summary.get("FuelUsedL", 0.0)),
            "FuelCostUsd": float(cold_summary.get("FuelUsedL", 0.0)) * econ.fuel_price_usd_per_l,
            "UnservedEnergyKWh": float(cold_summary.get("UnservedEnergyKWh", 0.0)),
            "SystemDownHours": int(cold_summary.get("SystemDownHours", 0)),
            "Availability": float(cold_summary.get("Availability", 0.0)),
            "AvailabilityPct": percent(float(cold_summary.get("Availability", 0.0))),
            "RenewableCoveragePct": 0.0,
            "CurtailmentKWh": 0.0,
            "CurtailmentPctOfPv": 0.0,
            "HoursBatteryFullWithPv": 0.0,
            "AnnualOmUsd": float(econ.annual_om_baseline_usd),
            "OutageCostUsd": float(yearly_cashflows["OutageCostUsd_Cold"].sum()),
            "OperatingCostUsd": float(yearly_cashflows["OperatingCostColdUsd"].sum()),
        },
    ]
    return pd.DataFrame(rows)


# -----------------------------
# Monte Carlo summaries
# -----------------------------

def summarize_mc_metrics(df: pd.DataFrame, scenario: str) -> pd.DataFrame:
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
    rows: list[dict[str, Any]] = []
    for col in numeric_cols:
        s = df[col].astype(float)
        rows.append({
            "Scenario": scenario,
            "Metric": col,
            "Mean": float(s.mean()),
            "Std": float(s.std(ddof=1)),
            "Min": float(s.min()),
            "P05": float(s.quantile(0.05)),
            "Median": float(s.median()),
            "P95": float(s.quantile(0.95)),
            "Max": float(s.max()),
        })
    return pd.DataFrame(rows)


def paired_mc_deltas(hybrid_mc: pd.DataFrame, cold_mc: pd.DataFrame) -> pd.DataFrame:
    preferred_direction = {
        "FuelUsedL": "lower_is_better",
        "UnservedEnergyKWh": "lower_is_better",
        "SystemDownHours": "lower_is_better",
        "Availability": "higher_is_better",
        "TotalDieselEnergyKWh": "lower_is_better",
    }

    common_metrics = [
        c for c in sorted(set(hybrid_mc.columns).intersection(cold_mc.columns))
        if pd.api.types.is_numeric_dtype(hybrid_mc[c]) and pd.api.types.is_numeric_dtype(cold_mc[c])
    ]

    n = min(len(hybrid_mc), len(cold_mc))
    h = hybrid_mc.iloc[:n].reset_index(drop=True)
    c = cold_mc.iloc[:n].reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    for metric in common_metrics:
        delta = h[metric].astype(float) - c[metric].astype(float)
        direction = preferred_direction.get(metric, "n/a")
        if direction == "lower_is_better":
            probability_hybrid_better = float((delta < 0).mean())
        elif direction == "higher_is_better":
            probability_hybrid_better = float((delta > 0).mean())
        else:
            probability_hybrid_better = math.nan

        rows.append({
            "Metric": metric,
            "DirectionForHybrid": direction,
            "MeanDelta_HybridMinusCold": float(delta.mean()),
            "P05Delta": float(delta.quantile(0.05)),
            "MedianDelta": float(delta.median()),
            "P95Delta": float(delta.quantile(0.95)),
            "ProbabilityHybridBetter": probability_hybrid_better,
        })
    return pd.DataFrame(rows)


# -----------------------------
# Economics
# -----------------------------

def npv(rate: float, cashflows: list[float]) -> float:
    return float(sum(cf / ((1.0 + rate) ** t) for t, cf in enumerate(cashflows)))


def irr(cashflows: list[float]) -> float | None:
    def f(rate: float) -> float:
        return npv(rate, cashflows)

    grid = np.concatenate([
        np.linspace(-0.99, 1.00, 500),
        np.linspace(1.05, 10.0, 500),
    ])
    values = []
    for rate in grid:
        try:
            values.append(f(float(rate)))
        except Exception:
            values.append(np.nan)

    for i in range(1, len(grid)):
        a, b = float(grid[i - 1]), float(grid[i])
        fa, fb = values[i - 1], values[i]
        if not np.isfinite(fa) or not np.isfinite(fb):
            continue
        if fa == 0.0:
            return a
        if fb == 0.0:
            return b
        if fa * fb > 0:
            continue

        left, right = a, b
        f_left, f_right = fa, fb
        for _ in range(100):
            mid = (left + right) / 2.0
            f_mid = f(mid)
            if abs(f_mid) < 1e-10:
                return mid
            if f_left * f_mid <= 0:
                right = mid
                f_right = f_mid
            else:
                left = mid
                f_left = f_mid
        return (left + right) / 2.0
    return None


def payback_period(cashflows: list[float], discount_rate: float | None = None) -> float | None:
    cumulative = cashflows[0]
    for t in range(1, len(cashflows)):
        cf = cashflows[t]
        if discount_rate is not None:
            cf = cf / ((1.0 + discount_rate) ** t)
        previous = cumulative
        cumulative += cf
        if cumulative >= 0:
            if cf <= 0:
                return float(t)
            return float((t - 1) + abs(previous) / cf)
    return None


def economic_kpis_from_cashflows(
    annual_benefits: list[float],
    econ: EconomicAssumptions,
    options: AnalysisOptions,
) -> dict[str, Any]:
    cashflows = [-float(econ.hybrid_capex_usd)] + [float(x) for x in annual_benefits]
    future_pv = sum(cf / ((1.0 + econ.discount_rate) ** t) for t, cf in enumerate(cashflows) if t > 0)

    result: dict[str, Any] = {
        "InitialInvestmentUsd": float(econ.hybrid_capex_usd),
        "DiscountRate": float(econ.discount_rate),
        "ProjectHorizonYears": int(len(annual_benefits)),
        "MeanAnnualNetBenefitUsd": float(np.mean(annual_benefits)) if annual_benefits else 0.0,
        "Cashflows": cashflows,
    }

    if options.compute_npv:
        result["NPV"] = float(npv(econ.discount_rate, cashflows))
    if options.compute_pi:
        result["PI"] = safe_div(future_pv, econ.hybrid_capex_usd)
    if options.compute_irr:
        result["IRR"] = irr(cashflows)
    if options.simple_payback:
        result["SimplePaybackYears"] = payback_period(cashflows, discount_rate=None)
    if options.discounted_payback:
        result["DiscountedPaybackYears"] = payback_period(cashflows, discount_rate=econ.discount_rate)
    return result


def normalize_weights(values: list[float], horizon_years: int) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if len(arr) == 0:
        return np.full(horizon_years, 1.0 / horizon_years)
    if len(arr) >= horizon_years:
        arr = arr[:horizon_years]
    else:
        repeats = int(math.ceil(horizon_years / len(arr)))
        arr = np.tile(arr, repeats)[:horizon_years]

    arr = np.clip(arr, 0.0, None)
    total = float(arr.sum())
    if total <= 0.0:
        return np.full(horizon_years, 1.0 / horizon_years)
    return arr / total


def build_mc_yearly_shape_weights(yearly_df: pd.DataFrame, horizon_years: int) -> dict[str, np.ndarray]:
    return {
        "cold_fuel": normalize_weights(yearly_df["FuelCostColdUsd"].tolist(), horizon_years),
        "hybrid_fuel": normalize_weights(yearly_df["FuelCostHybridUsd"].tolist(), horizon_years),
        "cold_outage": normalize_weights(yearly_df["OutageCostUsd_Cold"].tolist(), horizon_years),
        "hybrid_outage": normalize_weights(yearly_df["OutageCostUsd_Hybrid"].tolist(), horizon_years),
    }


def build_single_run_cashflow_table(yearly_df: pd.DataFrame, econ: EconomicAssumptions) -> pd.DataFrame:
    cashflow_df = yearly_df[[
        "ProjectYear",
        "FuelCostColdUsd",
        "FuelCostHybridUsd",
        "AnnualOmColdUsd",
        "AnnualOmHybridUsd",
        "OutageCostUsd_Cold",
        "OutageCostUsd_Hybrid",
        "OperatingCostColdUsd",
        "OperatingCostHybridUsd",
        "IncrementalNetBenefitUsd",
        "DiscountFactor",
        "DiscountedNetBenefitUsd",
        "CumulativeDiscountedUsd",
        "CumulativeUndiscountedUsd",
    ]].copy()
    cashflow_df.insert(1, "InitialInvestmentUsd", 0.0)
    cashflow_df.loc[cashflow_df.index[0], "InitialInvestmentUsd"] = -float(econ.hybrid_capex_usd)
    return cashflow_df


def build_mc_economics(
    hybrid_mc: pd.DataFrame,
    cold_mc: pd.DataFrame,
    econ: EconomicAssumptions,
    outage_model: OutageLossModel,
    options: AnalysisOptions,
    yearly_shape_source: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    horizon = int(econ.project_horizon_years)
    weights = build_mc_yearly_shape_weights(yearly_shape_source, horizon)

    n = min(len(hybrid_mc), len(cold_mc))
    h = hybrid_mc.iloc[:n].reset_index(drop=True)
    c = cold_mc.iloc[:n].reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    kpi_rows: list[dict[str, Any]] = []

    for run in range(n):
        cold_fuel_total = float(c.loc[run, "FuelUsedL"]) * econ.fuel_price_usd_per_l
        hybrid_fuel_total = float(h.loc[run, "FuelUsedL"]) * econ.fuel_price_usd_per_l

        if outage_model.mode == "per_down_hour":
            cold_outage_total = float(c.loc[run, "SystemDownHours"]) * float(outage_model.loss_usd_per_down_hour)
            hybrid_outage_total = float(h.loc[run, "SystemDownHours"]) * float(outage_model.loss_usd_per_down_hour)
        elif outage_model.mode == "per_unserved_kwh":
            cold_outage_total = float(c.loc[run, "UnservedEnergyKWh"]) * float(outage_model.loss_usd_per_unserved_kwh)
            hybrid_outage_total = float(h.loc[run, "UnservedEnergyKWh"]) * float(outage_model.loss_usd_per_unserved_kwh)
        else:
            raise ValueError("Неподдерживаемый режим outage_loss_model.mode")

        annual_benefits: list[float] = []
        for year_idx in range(horizon):
            cold_year_cost = (
                cold_fuel_total * weights["cold_fuel"][year_idx]
                + float(econ.annual_om_baseline_usd)
                + cold_outage_total * weights["cold_outage"][year_idx]
            )
            hybrid_year_cost = (
                hybrid_fuel_total * weights["hybrid_fuel"][year_idx]
                + float(econ.annual_om_hybrid_usd)
                + hybrid_outage_total * weights["hybrid_outage"][year_idx]
            )
            annual_benefits.append(cold_year_cost - hybrid_year_cost)

        kpis = economic_kpis_from_cashflows(annual_benefits, econ, options)
        row = {
            "Run": run + 1,
            "ColdFuelCostUsd": cold_fuel_total,
            "HybridFuelCostUsd": hybrid_fuel_total,
            "ColdOutageCostUsd": cold_outage_total,
            "HybridOutageCostUsd": hybrid_outage_total,
            "MeanAnnualNetBenefitUsd": kpis["MeanAnnualNetBenefitUsd"],
            "NPV": kpis.get("NPV"),
            "PI": kpis.get("PI"),
            "IRR": kpis.get("IRR"),
            "SimplePaybackYears": kpis.get("SimplePaybackYears"),
            "DiscountedPaybackYears": kpis.get("DiscountedPaybackYears"),
        }
        rows.append(row)
        kpi_rows.append(kpis)

    runs_df = pd.DataFrame(rows)

    summary_rows: list[dict[str, Any]] = []
    for metric in [
        "MeanAnnualNetBenefitUsd",
        "NPV",
        "PI",
        "IRR",
        "SimplePaybackYears",
        "DiscountedPaybackYears",
    ]:
        if metric not in runs_df.columns:
            continue
        s = runs_df[metric].dropna().astype(float)
        if s.empty:
            continue
        summary_rows.append({
            "Metric": metric,
            "Mean": float(s.mean()),
            "Std": float(s.std(ddof=1)),
            "Min": float(s.min()),
            "P05": float(s.quantile(0.05)),
            "Median": float(s.median()),
            "P95": float(s.quantile(0.95)),
            "Max": float(s.max()),
        })

    summary_df = pd.DataFrame(summary_rows)
    final_kpis = {
        "Method": "MonteCarlo" if options.use_mc_for_final_economics else "SingleRun",
        "Runs": int(len(runs_df)),
    }
    for _, row in summary_df.iterrows():
        final_kpis[row["Metric"]] = {
            "Mean": row["Mean"],
            "Median": row["Median"],
            "P05": row["P05"],
            "P95": row["P95"],
        }
    return runs_df, summary_df, final_kpis


# -----------------------------
# Plotting
# -----------------------------

def plot_single_run_fuel_and_downhours(single_df: pd.DataFrame, output: Path) -> None:
    fig, ax1 = plt.subplots(figsize=(10, 6))
    x = np.arange(len(single_df))
    width = 0.35

    ax1.bar(x - width / 2, single_df["FuelUsedL"], width=width, label="Fuel used, L")
    ax1.set_ylabel("Fuel used, L")
    ax1.set_xticks(x)
    ax1.set_xticklabels(single_df["Scenario"])

    ax2 = ax1.twinx()
    ax2.bar(x + width / 2, single_df["SystemDownHours"], width=width, label="Down hours")
    ax2.set_ylabel("System down hours")

    ax1.set_title("Single-run comparison: fuel use and downtime")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_monthly_energy_balance(monthly_df: pd.DataFrame, output: Path) -> None:
    df = monthly_df[monthly_df["Scenario"] == "Hybrid"].sort_values("Month")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df["Month"], df["PvToLoadKWh"], marker="o", label="PV -> load")
    ax.plot(df["Month"], df["BatteryToLoadKWh"], marker="o", label="Battery -> load")
    ax.plot(df["Month"], df["DieselToLoadKWh"], marker="o", label="Diesel -> load")
    if "CurtailmentKWh" in df.columns:
        ax.plot(df["Month"], df["CurtailmentKWh"], marker="o", label="Curtailment")
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Month")
    ax.set_ylabel("Energy, kWh")
    ax.set_title("Hybrid monthly mean energy balance")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_monthly_fuel_comparison(monthly_df: pd.DataFrame, output: Path) -> None:
    pivot = monthly_df.pivot(index="Month", columns="Scenario", values="FuelUsedL").reset_index()
    fig, ax = plt.subplots(figsize=(10, 6))
    for scenario in [c for c in pivot.columns if c != "Month"]:
        ax.plot(pivot["Month"], pivot[scenario], marker="o", label=scenario)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("Month")
    ax.set_ylabel("Fuel used, L")
    ax.set_title("Monthly fuel use comparison")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_hourly_fuel_profile(hourly_df: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    for scenario in sorted(hourly_df["Scenario"].unique()):
        part = hourly_df[hourly_df["Scenario"] == scenario].sort_values("Hour")
        ax.plot(part["Hour"], part["FuelUsedL"], marker="o", label=scenario)
    ax.set_xticks(range(0, 24, 2))
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Mean fuel used, L/hour")
    ax.set_title("Mean hourly fuel use")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_hybrid_soc_sample(hybrid_hours: pd.DataFrame, output: Path) -> None:
    days = 30
    sample = hybrid_hours.iloc[: days * 24].copy()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(sample["TimestampMsk"], sample["SocKWh"])
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("SOC, kWh")
    ax.set_title("Hybrid battery SOC, first 30 days")
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_mc_histograms(hybrid_mc: pd.DataFrame, cold_mc: pd.DataFrame, output: Path, metric: str, title: str) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(cold_mc[metric].astype(float), bins=30, alpha=0.6, label="ColdStandby")
    ax.hist(hybrid_mc[metric].astype(float), bins=30, alpha=0.6, label="Hybrid")
    ax.set_title(title)
    ax.set_xlabel(metric)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_cashflows(cashflow_df: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(cashflow_df["ProjectYear"], cashflow_df["IncrementalNetBenefitUsd"], marker="o", label="Net benefit")
    ax.plot(cashflow_df["ProjectYear"], cashflow_df["CumulativeDiscountedUsd"], marker="o", label="Cumulative discounted")
    ax.axhline(0.0, linewidth=1)
    ax.set_xlabel("Project year")
    ax.set_ylabel("USD")
    ax.set_title("Project cash flows from single run")
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


def plot_mc_npv_distribution(mc_runs_df: pd.DataFrame, output: Path) -> None:
    if "NPV" not in mc_runs_df.columns or mc_runs_df["NPV"].dropna().empty:
        return
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(mc_runs_df["NPV"].dropna().astype(float), bins=30)
    ax.set_title("Monte Carlo NPV distribution")
    ax.set_xlabel("NPV, USD")
    fig.tight_layout()
    fig.savefig(output, dpi=150)
    plt.close(fig)


# -----------------------------
# Markdown report
# -----------------------------

def render_markdown_report(
    output: Path,
    config: AppConfig,
    single_df: pd.DataFrame,
    yearly_df: pd.DataFrame,
    single_run_kpis: dict[str, Any],
    mc_final_kpis: dict[str, Any],
    mc_delta_df: pd.DataFrame,
) -> None:
    econ = config.economic_assumptions
    hybrid_row = single_df[single_df["Scenario"] == "Hybrid"].iloc[0]
    cold_row = single_df[single_df["Scenario"] == "ColdStandby"].iloc[0]

    lines: list[str] = []
    lines.append("# Анализ результатов моделирования")
    lines.append("")
    lines.append("## 1. Исходная логика расчёта")
    lines.append("")
    lines.append(
        "Скрипт сравнивает две схемы энергоснабжения: базовую схему с холодным резервом и гибридную схему PV + АКБ + дизель. "
        "Для экономики строится инкрементальный денежный поток: ежегодная выгода гибрида определяется как разность между годовыми затратами базовой схемы и годовыми затратами гибридной схемы."
    )
    lines.append("")
    lines.append("## 2. Single run")
    lines.append("")
    lines.append(f"- Горизонт моделирования: **{econ.project_horizon_years} лет**")
    lines.append(f"- Топливо, cold standby: **{cold_row['FuelUsedL']:.2f} л**")
    lines.append(f"- Топливо, hybrid: **{hybrid_row['FuelUsedL']:.2f} л**")
    lines.append(f"- Экономия топлива: **{cold_row['FuelUsedL'] - hybrid_row['FuelUsedL']:.2f} л**")
    lines.append(f"- Availability, cold standby: **{cold_row['AvailabilityPct']:.4f}%**")
    lines.append(f"- Availability, hybrid: **{hybrid_row['AvailabilityPct']:.4f}%**")
    lines.append(f"- Down hours, cold standby: **{int(cold_row['SystemDownHours'])} ч**")
    lines.append(f"- Down hours, hybrid: **{int(hybrid_row['SystemDownHours'])} ч**")
    lines.append(f"- Unserved energy, cold standby: **{cold_row['UnservedEnergyKWh']:.4f} кВт·ч**")
    lines.append(f"- Unserved energy, hybrid: **{hybrid_row['UnservedEnergyKWh']:.4f} кВт·ч**")
    if "CurtailmentKWh" in hybrid_row:
        lines.append(f"- Curtailment, hybrid: **{hybrid_row['CurtailmentKWh']:.4f} кВт·ч**")
    if "CurtailmentPctOfPv" in hybrid_row:
        lines.append(f"- Curtailment share of PV, hybrid: **{hybrid_row['CurtailmentPctOfPv']:.4f}%**")
    if "HoursBatteryFullWithPv" in hybrid_row:
        lines.append(f"- Hours battery full with PV available, hybrid: **{hybrid_row['HoursBatteryFullWithPv']:.0f} ч**")
    lines.append("")
    lines.append("## 3. Экономика по почасовому single run")
    lines.append("")
    lines.append(f"- CAPEX гибридной схемы: **{econ.hybrid_capex_usd:.2f} {econ.currency}**")
    lines.append(f"- Ставка дисконтирования: **{econ.discount_rate:.2%}**")
    lines.append(f"- Среднегодовой net benefit: **{single_run_kpis['MeanAnnualNetBenefitUsd']:.2f} {econ.currency}/год**")
    if "NPV" in single_run_kpis:
        lines.append(f"- NPV: **{single_run_kpis['NPV']:.2f} {econ.currency}**")
    if "PI" in single_run_kpis:
        lines.append(f"- PI: **{single_run_kpis['PI']:.4f}**")
    if "IRR" in single_run_kpis:
        irr_value = single_run_kpis["IRR"]
        lines.append(f"- IRR: **{irr_value:.4%}**" if irr_value is not None else "- IRR: **не определён**")
    if "SimplePaybackYears" in single_run_kpis:
        value = single_run_kpis["SimplePaybackYears"]
        lines.append(f"- PP: **{value:.4f} года**" if value is not None else "- PP: **не окупается**")
    if "DiscountedPaybackYears" in single_run_kpis:
        value = single_run_kpis["DiscountedPaybackYears"]
        lines.append(f"- DPP: **{value:.4f} года**" if value is not None else "- DPP: **не окупается**")
    lines.append("")
    lines.append("## 4. Monte Carlo")
    lines.append("")
    for metric in ["FuelUsedL", "SystemDownHours", "UnservedEnergyKWh", "Availability"]:
        row = mc_delta_df[mc_delta_df["Metric"] == metric]
        if row.empty:
            continue
        row = row.iloc[0]
        p = row["ProbabilityHybridBetter"]
        if pd.notna(p):
            lines.append(f"- {metric}: вероятность, что hybrid лучше = **{p:.2%}**")
    lines.append("")
    lines.append("## 5. Финальные KPI")
    lines.append("")
    lines.append(f"- Метод итоговой экономики: **{mc_final_kpis['Method']}**")
    if mc_final_kpis["Method"] == "MonteCarlo":
        for metric in ["NPV", "PI", "IRR", "SimplePaybackYears", "DiscountedPaybackYears"]:
            if metric not in mc_final_kpis:
                continue
            stats = mc_final_kpis[metric]
            lines.append(
                f"- {metric}: mean=**{stats['Mean']:.4f}**, median=**{stats['Median']:.4f}**, "
                f"p05=**{stats['P05']:.4f}**, p95=**{stats['P95']:.4f}**"
            )
    else:
        for metric in ["NPV", "PI", "IRR", "SimplePaybackYears", "DiscountedPaybackYears"]:
            if metric not in single_run_kpis:
                continue
            value = single_run_kpis[metric]
            if value is None:
                lines.append(f"- {metric}: **не определён**")
            else:
                lines.append(f"- {metric}: **{value:.4f}**")
    lines.append("")
    lines.append("## 6. Вывод")
    lines.append("")
    final_npv = None
    if mc_final_kpis["Method"] == "MonteCarlo" and "NPV" in mc_final_kpis:
        final_npv = mc_final_kpis["NPV"]["Mean"]
    elif "NPV" in single_run_kpis:
        final_npv = single_run_kpis["NPV"]

    if final_npv is not None and final_npv > 0:
        lines.append("При текущих допущениях замена резервного дизель-генератора на гибридную схему экономически эффективна.")
    elif final_npv is not None:
        lines.append("При текущих допущениях гибридная схема не показывает положительную экономическую эффективность.")
    else:
        lines.append("Финальный вывод по NPV не удалось сформировать, потому что метрика не была рассчитана.")

    output.write_text("\n".join(lines), encoding="utf-8")


# -----------------------------
# Main
# -----------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Анализ результатов моделирования cold-standby и hybrid систем")
    parser.add_argument("--config", required=True, help="Путь к analysis_config.json")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve()
    raw_config = load_json(config_path)
    config = AppConfig.from_dict(raw_config)

    config_dir = config_path.parent
    results_root = resolve_config_path(config_dir, config.paths.results_root)
    output_dir = resolve_config_path(config_dir, config.paths.output_dir)
    charts_dir = output_dir / "charts"
    ensure_dir(output_dir)
    ensure_dir(charts_dir)

    studies = discover_studies(results_root, config.study_mapping)

    hybrid_summary = read_summary(studies.hybrid_single_summary)
    cold_summary = read_summary(studies.cold_single_summary)
    hybrid_hours = read_hourly_csv(studies.hybrid_single_hours)
    cold_hours = read_hourly_csv(studies.cold_single_hours)
    hybrid_mc = read_mc_summaries(studies.hybrid_mc_summaries)
    cold_mc = read_mc_summaries(studies.cold_mc_summaries)

    yearly_df = build_yearly_metrics(
        hybrid_hours=hybrid_hours,
        cold_hours=cold_hours,
        econ=config.economic_assumptions,
        outage_model=config.outage_loss_model,
    )
    single_df = build_single_run_comparison(
        hybrid_summary=hybrid_summary,
        cold_summary=cold_summary,
        econ=config.economic_assumptions,
        yearly_cashflows=yearly_df,
    )
    monthly_df = build_monthly_profiles(hybrid_hours, cold_hours)
    hourly_df = build_hourly_profiles(hybrid_hours, cold_hours)
    events_df = pd.concat([
        extract_system_down_events(hybrid_hours, "Hybrid"),
        extract_system_down_events(cold_hours, "ColdStandby"),
    ], ignore_index=True)

    mc_summary_df = pd.concat([
        summarize_mc_metrics(hybrid_mc, "Hybrid"),
        summarize_mc_metrics(cold_mc, "ColdStandby"),
    ], ignore_index=True)
    mc_delta_df = paired_mc_deltas(hybrid_mc, cold_mc)

    single_run_kpis = economic_kpis_from_cashflows(
        annual_benefits=yearly_df["IncrementalNetBenefitUsd"].astype(float).tolist(),
        econ=config.economic_assumptions,
        options=config.analysis_options,
    )
    single_run_cashflow_df = build_single_run_cashflow_table(yearly_df, config.economic_assumptions)

    mc_runs_df, mc_summary_econ_df, mc_final_kpis = build_mc_economics(
        hybrid_mc=hybrid_mc,
        cold_mc=cold_mc,
        econ=config.economic_assumptions,
        outage_model=config.outage_loss_model,
        options=config.analysis_options,
        yearly_shape_source=yearly_df,
    )

    final_economic_kpis: dict[str, Any]
    if config.analysis_options.use_mc_for_final_economics:
        final_economic_kpis = mc_final_kpis
    else:
        final_economic_kpis = {"Method": "SingleRun", **single_run_kpis}

    if config.report_outputs.save_csv:
        save_csv(single_df, output_dir / "01_single_run_comparison.csv")
        save_csv(yearly_df, output_dir / "02_single_run_yearly_metrics.csv")
        save_csv(monthly_df, output_dir / "03_monthly_profiles.csv")
        save_csv(hourly_df, output_dir / "04_hourly_profiles.csv")
        save_csv(events_df, output_dir / "05_system_down_events.csv")
        save_csv(mc_summary_df, output_dir / "06_montecarlo_metric_summary.csv")
        save_csv(mc_delta_df, output_dir / "07_montecarlo_paired_deltas.csv")
        save_csv(single_run_cashflow_df, output_dir / "08_single_run_economic_cashflows.csv")
        save_csv(mc_runs_df, output_dir / "09_montecarlo_economics_runs.csv")
        save_csv(mc_summary_econ_df, output_dir / "10_montecarlo_economics_summary.csv")

    if config.report_outputs.save_json:
        dump_json(single_run_kpis, output_dir / "single_run_economic_kpis.json")
        dump_json(final_economic_kpis, output_dir / "final_economic_kpis.json")
        dump_json({
            "config": raw_config,
            "resolved_results_root": str(results_root),
            "resolved_output_dir": str(output_dir),
            "files": {
                "cold_single_summary": str(studies.cold_single_summary),
                "cold_single_hours": str(studies.cold_single_hours),
                "cold_mc_summaries": str(studies.cold_mc_summaries),
                "hybrid_single_summary": str(studies.hybrid_single_summary),
                "hybrid_single_hours": str(studies.hybrid_single_hours),
                "hybrid_mc_summaries": str(studies.hybrid_mc_summaries),
            },
        }, output_dir / "run_metadata.json")

    if config.report_outputs.save_png:
        plot_single_run_fuel_and_downhours(single_df, charts_dir / "single_run_fuel_and_downtime.png")
        plot_monthly_energy_balance(monthly_df, charts_dir / "hybrid_monthly_energy_balance.png")
        plot_monthly_fuel_comparison(monthly_df, charts_dir / "monthly_fuel_comparison.png")
        plot_hourly_fuel_profile(hourly_df, charts_dir / "hourly_fuel_profile.png")
        plot_hybrid_soc_sample(hybrid_hours, charts_dir / "hybrid_soc_first_30_days.png")
        plot_mc_histograms(hybrid_mc, cold_mc, charts_dir / "mc_fuel_distribution.png", "FuelUsedL", "Monte Carlo fuel use distribution")
        plot_mc_histograms(hybrid_mc, cold_mc, charts_dir / "mc_downtime_distribution.png", "SystemDownHours", "Monte Carlo downtime distribution")
        plot_cashflows(single_run_cashflow_df, charts_dir / "single_run_cashflows.png")
        plot_mc_npv_distribution(mc_runs_df, charts_dir / "mc_npv_distribution.png")

    if config.report_outputs.save_markdown_summary:
        render_markdown_report(
            output=output_dir / "analysis_summary.md",
            config=config,
            single_df=single_df,
            yearly_df=yearly_df,
            single_run_kpis=single_run_kpis,
            mc_final_kpis=final_economic_kpis,
            mc_delta_df=mc_delta_df,
        )

    print(f"Готово. Результаты сохранены в: {output_dir}")


if __name__ == "__main__":
    main()
