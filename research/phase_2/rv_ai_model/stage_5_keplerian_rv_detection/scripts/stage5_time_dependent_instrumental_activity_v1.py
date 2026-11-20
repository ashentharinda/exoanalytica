from pathlib import Path
import json
import sys
import traceback

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[3]

RAW = ROOT / "data/input/harps_rv_observations_18_targets.csv"
RESIDUAL = ROOT / "experiments/HD115617_correlated_noise_validation_v1/residual_diagnostics.csv"
OUT = ROOT / "experiments/HD115617_time_dependent_instrumental_activity_v1"

TARGET = "HD115617"
FOCUS_DATES = [
    "2013-06-09", "2013-06-15",
    "2017-02-26", "2017-08-08",
    "2009-08-11", "2015-06-09",
    "2016-03-17", "2008-05-31",
]

def robust_z(series):
    x = pd.to_numeric(series, errors="coerce")
    med = x.median()
    mad = (x - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        return pd.Series(np.nan, index=x.index)
    return 0.67448975 * (x - med) / mad

def association(x, y):
    pair = pd.DataFrame({"x": x, "y": y}).replace(
        [np.inf, -np.inf], np.nan
    ).dropna()

    if len(pair) < 3 or pair["x"].nunique() < 2 or pair["y"].nunique() < 2:
        return {
            "n": len(pair), "pearson": np.nan,
            "spearman": np.nan, "theil_sen_slope": np.nan
        }

    return {
        "n": len(pair),
        "pearson": float(stats.pearsonr(pair["x"], pair["y"]).statistic),
        "spearman": float(stats.spearmanr(pair["x"], pair["y"]).statistic),
        "theil_sen_slope": float(
            stats.theilslopes(pair["y"], pair["x"]).slope
        )
    }

def main():
    if OUT.exists():
        raise FileExistsError(f"Output folder already exists: {OUT}")

    if not RAW.exists() or not RESIDUAL.exists():
        raise FileNotFoundError("Required input file missing.")

    OUT.mkdir(parents=True)

    raw = pd.read_csv(RAW)
    residual = pd.read_csv(RESIDUAL)

    raw = raw.loc[raw["tel_object"].astype(str).str.strip() == TARGET].copy()
    residual = residual.loc[
        residual["BJD"].notna()
    ].copy()

    if len(raw) != 1213 or len(residual) != 1213:
        raise ValueError(
            f"Unexpected row count: raw={len(raw)}, residual={len(residual)}"
        )

    raw["drs_bjd"] = pd.to_numeric(raw["drs_bjd"], errors="raise")
    residual["BJD"] = pd.to_numeric(residual["BJD"], errors="raise")

    if raw["drs_bjd"].duplicated().any() or residual["BJD"].duplicated().any():
        raise ValueError("Duplicate BJD values detected; refusing ambiguous merge.")

    raw["date_obs"] = pd.to_datetime(raw["date_obs"], utc=True, errors="raise")
    residual["date_obs"] = pd.to_datetime(
        residual["date_obs"], utc=True, errors="raise"
    )

    merged = raw.merge(
        residual,
        left_on="drs_bjd",
        right_on="BJD",
        how="inner",
        validate="one_to_one",
        suffixes=("_raw", "_diag")
    )

    if len(merged) != 1213:
        raise ValueError(f"Only {len(merged)} exact BJD matches; expected 1213.")

    if not (merged["date_obs_raw"].values == merged["date_obs_diag"].values).all():
        raise ValueError("UTC timestamp mismatch between raw and residual data.")

    merged["utc_night"] = merged["date_obs_raw"].dt.strftime("%Y-%m-%d")
    merged["elapsed_years"] = (
        merged["drs_bjd"] - merged["drs_bjd"].min()
    ) / 365.25

    numeric = [
        "drs_ccf_fwhm", "drs_bis_span", "drs_snr",
        "rv_mps", "residual_rv_mps", "OU_innovation_mps",
        "OU_innovation_variance", "OU_standardized_innovation",
        "total_sigma_mps"
    ]

    for col in numeric:
        merged[col] = pd.to_numeric(merged[col], errors="coerce")

    # Observation-level data, preserving all original matched observations.
    merged.to_csv(OUT / "matched_observations.csv", index=False)

    # UTC-night summaries.
    nightly = merged.groupby("utc_night", as_index=False).agg(
        observation_count=("drs_bjd", "size"),
        mean_BJD=("drs_bjd", "mean"),
        mean_FWHM=("drs_ccf_fwhm", "mean"),
        median_FWHM=("drs_ccf_fwhm", "median"),
        std_FWHM=("drs_ccf_fwhm", "std"),
        mean_BIS_span=("drs_bis_span", "mean"),
        median_BIS_span=("drs_bis_span", "median"),
        std_BIS_span=("drs_bis_span", "std"),
        median_SNR=("drs_snr", "median"),
        mean_RV_residual=("residual_rv_mps", "mean"),
        median_RV_residual=("residual_rv_mps", "median"),
        mean_innovation=("OU_innovation_mps", "mean"),
        median_innovation=("OU_innovation_mps", "median"),
        mean_standardized_innovation=("OU_standardized_innovation", "mean"),
        median_standardized_innovation=("OU_standardized_innovation", "median"),
    )

    nightly["mean_BJD"] = pd.to_numeric(nightly["mean_BJD"])
    nightly["elapsed_years"] = (
        nightly["mean_BJD"] - nightly["mean_BJD"].min()
    ) / 365.25

    nightly = nightly.sort_values("mean_BJD").reset_index(drop=True)

    # Robust outlier scores are descriptive flags, not data rejection criteria.
    for col in [
        "mean_FWHM", "median_FWHM",
        "mean_BIS_span", "median_BIS_span",
        "mean_innovation", "median_innovation",
        "mean_standardized_innovation"
    ]:
        nightly[f"{col}_robust_z"] = robust_z(nightly[col])

    nightly.to_csv(OUT / "nightly_time_series.csv", index=False)

    # Long-term trend associations.
    trend_rows = []
    for col in [
        "mean_FWHM", "median_FWHM",
        "mean_BIS_span", "median_BIS_span",
        "mean_innovation", "median_innovation",
        "mean_standardized_innovation",
        "median_SNR", "observation_count"
    ]:
        result = association(nightly["elapsed_years"], nightly[col])
        trend_rows.append({"measure": col, **result})

    trends = pd.DataFrame(trend_rows)
    trends.to_csv(OUT / "long_term_trends.csv", index=False)

    # Compare five chronological time segments.
    nightly["time_bin"] = pd.cut(
        nightly["elapsed_years"],
        bins=np.linspace(
            nightly["elapsed_years"].min(),
            nightly["elapsed_years"].max(),
            6
        ),
        include_lowest=True,
        labels=["T1", "T2", "T3", "T4", "T5"]
    )

    time_bins = nightly.groupby("time_bin", observed=False).agg(
        nights=("utc_night", "count"),
        observations=("observation_count", "sum"),
        FWHM_median=("median_FWHM", "median"),
        FWHM_mean=("mean_FWHM", "mean"),
        BIS_median=("median_BIS_span", "median"),
        BIS_mean=("mean_BIS_span", "mean"),
        innovation_median=("median_innovation", "median"),
        innovation_mean=("mean_innovation", "mean"),
        standardized_innovation_median=("median_standardized_innovation", "median"),
        SNR_median=("median_SNR", "median"),
    ).reset_index()

    time_bins.to_csv(OUT / "chronological_time_bins.csv", index=False)

    # Correlations between activity indicators and OU innovations.
    activity_rows = []
    for indicator in [
        "mean_FWHM", "median_FWHM",
        "mean_BIS_span", "median_BIS_span",
        "median_SNR"
    ]:
        for innovation in [
            "mean_innovation", "median_innovation",
            "mean_standardized_innovation"
        ]:
            result = association(nightly[indicator], nightly[innovation])
            activity_rows.append({
                "indicator": indicator,
                "innovation_measure": innovation,
                **result
            })

    pd.DataFrame(activity_rows).to_csv(
        OUT / "activity_innovation_associations.csv", index=False
    )

    # Raw observations on previously identified unusual UTC nights.
    focus = merged.loc[merged["utc_night"].isin(FOCUS_DATES)].copy()
    focus = focus.sort_values(["utc_night", "drs_bjd"])
    focus.to_csv(OUT / "focus_night_raw_observations.csv", index=False)

    focus_summary = nightly.loc[
        nightly["utc_night"].isin(FOCUS_DATES)
    ].copy()
    focus_summary.to_csv(OUT / "focus_night_summary.csv", index=False)

    # Robust unusual-night flags. These are not rejected observations.
    flag_cols = [
        "mean_FWHM_robust_z", "median_FWHM_robust_z",
        "mean_BIS_span_robust_z", "median_BIS_span_robust_z",
        "mean_innovation_robust_z", "median_innovation_robust_z",
        "mean_standardized_innovation_robust_z"
    ]

    nightly["extreme_flag"] = (
        nightly[flag_cols].abs().gt(3.5).any(axis=1)
    )

    nightly.loc[nightly["extreme_flag"]].to_csv(
        OUT / "unusual_night_flags.csv", index=False
    )

    metadata = {
        "target": TARGET,
        "raw_target_observations": int(len(raw)),
        "residual_observations": int(len(residual)),
        "exact_bjd_matches": int(len(merged)),
        "utc_nights": int(nightly["utc_night"].nunique()),
        "focus_dates": FOCUS_DATES,
        "input_raw": str(RAW),
        "input_residual_diagnostics": str(RESIDUAL),
        "method": "Descriptive time-trend, chronological-bin and association analysis",
        "limitations": [
            "No instrument configuration or calibration-event metadata in supplied CSV.",
            "Correlation does not establish causation.",
            "Robust outlier flags do not justify removing observations.",
            "OU innovations are conditional on the existing fitted OU model.",
            "No Keplerian refit or planet confirmation is performed."
        ]
    }

    (OUT / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    report = [
        "HD115617 TIME-DEPENDENT INSTRUMENTAL / ACTIVITY INVESTIGATION V1",
        "=" * 68,
        f"Raw target observations: {len(raw)}",
        f"Residual observations: {len(residual)}",
        f"Exact BJD matches: {len(merged)}",
        f"UTC observing nights: {nightly['utc_night'].nunique()}",
        "",
        "LONG-TERM TRENDS",
        trends.to_string(index=False),
        "",
        "CHRONOLOGICAL TIME BINS",
        time_bins.to_string(index=False),
        "",
        "FOCUS NIGHT SUMMARY",
        focus_summary.to_string(index=False),
        "",
        "UNUSUAL NIGHT COUNT",
        str(int(nightly["extreme_flag"].sum())),
        "",
        "LIMITATIONS",
        *[f"- {x}" for x in metadata["limitations"]],
    ]

    (OUT / "report.txt").write_text("\n".join(report), encoding="utf-8")

    print("\n===== INVESTIGATION COMPLETED =====")
    print(f"Output folder: {OUT}")
    print(f"Exact BJD matches: {len(merged)}")
    print(f"UTC nights: {nightly['utc_night'].nunique()}")
    print(f"Unusual nights flagged: {nightly['extreme_flag'].sum()}")
    print("\nGenerated files:")
    for path in sorted(OUT.iterdir()):
        print(f" - {path.name}")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
