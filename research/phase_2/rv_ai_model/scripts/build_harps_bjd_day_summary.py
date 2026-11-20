from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]

RAW = BASE / "data/interim/harps_rv_observations_18_targets.csv"
OUT = BASE / "data/processed/harps_rv_bjd_day_summary_v1.csv"
PROVENANCE = BASE / "data/processed/harps_rv_bjd_day_observation_qc_v1.csv"
REPORT = BASE / "reports/harps_rv_bjd_day_qc_report_v1.txt"
MANIFEST = BASE / "data/manifests/harps_rv_bjd_day_summary_v1.json"

# Review thresholds only. These are NOT universal rejection limits.
RV_EXTREME_MPS = 100_000.0
BIS_EXTREME_MPS = 1_000_000.0
RV_FIELD_DISAGREEMENT_MPS = 10.0

for folder in [OUT.parent, PROVENANCE.parent, REPORT.parent, MANIFEST.parent]:
    folder.mkdir(parents=True, exist_ok=True)

if not RAW.exists():
    raise FileNotFoundError(f"Raw dataset not found: {RAW}")

df = pd.read_csv(RAW, low_memory=False)

required = [
    "tel_object", "date_obs", "drs_bjd",
    "drs_ccf_rvc", "rv_mps", "drs_dvrms",
    "drs_bis_span", "drs_bis_rv",
    "drs_ccf_fwhm", "drs_snr", "drs_ccf_rv"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

numeric = [
    "drs_bjd", "drs_ccf_rvc", "rv_mps", "drs_dvrms",
    "drs_bis_span", "drs_bis_rv",
    "drs_ccf_fwhm", "drs_snr", "drs_ccf_rv"
]

for col in numeric:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Preserve the original row index for observation-level provenance.
df.insert(0, "source_row_index", np.arange(len(df), dtype=np.int64))

# Independent unit-conversion verification.
df["rv_conversion_error_mps"] = (
    df["rv_mps"] - df["drs_ccf_rvc"] * 1000.0
).abs()

# BJD integer-day grouping. This is NOT assumed to be an observing-night ID.
df["bjd_day"] = np.floor(df["drs_bjd"])

# Convert BIS span to m/s. BIS mean velocity remains a separate field.
df["bis_span_mps"] = df["drs_bis_span"] * 1000.0

# Observation-level flags. Flags do not delete observations.
finite_rv = np.isfinite(df["rv_mps"])
valid_unc = np.isfinite(df["drs_dvrms"]) & (df["drs_dvrms"] > 0)

df["flag_invalid_rv"] = ~finite_rv
df["flag_invalid_uncertainty"] = ~valid_unc
df["flag_extreme_rv_review"] = (
    finite_rv & (df["rv_mps"].abs() > RV_EXTREME_MPS)
)
df["flag_extreme_bis_review"] = (
    np.isfinite(df["bis_span_mps"]) &
    (df["bis_span_mps"].abs() > BIS_EXTREME_MPS)
)
df["flag_low_or_zero_snr"] = (
    ~np.isfinite(df["drs_snr"]) | (df["drs_snr"] <= 0)
)
df["flag_invalid_fwhm"] = (
    ~np.isfinite(df["drs_ccf_fwhm"]) |
    (df["drs_ccf_fwhm"] <= 0)
)
df["flag_rv_field_disagreement"] = (
    np.isfinite(df["drs_ccf_rvc"]) &
    np.isfinite(df["drs_ccf_rv"]) &
    (
        (df["drs_ccf_rvc"] - df["drs_ccf_rv"]).abs() * 1000.0
        > RV_FIELD_DISAGREEMENT_MPS
    )
)

# Provenance output: one row per original observation.
provenance_cols = [
    "source_row_index", "tel_object", "date_obs",
    "drs_bjd", "bjd_day", "rv_mps", "drs_dvrms",
    "flag_invalid_rv", "flag_invalid_uncertainty",
    "flag_extreme_rv_review", "flag_extreme_bis_review",
    "flag_low_or_zero_snr", "flag_invalid_fwhm",
    "flag_rv_field_disagreement"
]
df[provenance_cols].to_csv(PROVENANCE, index=False)

records = []

for (target, day), group in df.groupby(
    ["tel_object", "bjd_day"], sort=True, dropna=False
):
    rv = group["rv_mps"].to_numpy(dtype=float)
    unc = group["drs_dvrms"].to_numpy(dtype=float)

    rv_valid = np.isfinite(rv)
    unc_valid = np.isfinite(unc) & (unc > 0)
    weighted_valid = rv_valid & unc_valid

    valid_rv = rv[rv_valid]

    if len(valid_rv):
        rv_median = float(np.median(valid_rv))
        mad = float(np.median(np.abs(valid_rv - rv_median)))
        mad_scatter = 1.4826 * mad
        rv_min = float(np.min(valid_rv))
        rv_max = float(np.max(valid_rv))
    else:
        rv_median = np.nan
        mad_scatter = np.nan
        rv_min = np.nan
        rv_max = np.nan

    if weighted_valid.any():
        weights = 1.0 / np.square(unc[weighted_valid])
        weighted_mean = float(
            np.sum(rv[weighted_valid] * weights) / np.sum(weights)
        )
        formal_unc = float(np.sqrt(1.0 / np.sum(weights)))
    else:
        weighted_mean = np.nan
        formal_unc = np.nan

    def finite_median(column):
        values = group[column].to_numpy(dtype=float)
        values = values[np.isfinite(values)]
        return float(np.median(values)) if len(values) else np.nan

    def finite_mean(column):
        values = group[column].to_numpy(dtype=float)
        values = values[np.isfinite(values)]
        return float(np.mean(values)) if len(values) else np.nan

    utc_dates = pd.to_datetime(
        group["date_obs"], errors="coerce", utc=True
    ).dt.strftime("%Y-%m-%d")

    records.append({
        "tel_object": target,
        "bjd_day": int(day) if pd.notna(day) else np.nan,
        "observations_in_bin": len(group),
        "valid_rv_count": int(rv_valid.sum()),
        "valid_uncertainty_count": int(unc_valid.sum()),
        "weighted_rv_count": int(weighted_valid.sum()),

        "rv_median_mps": rv_median,
        "rv_weighted_mean_mps": weighted_mean,
        "rv_formal_uncertainty_mps": formal_unc,
        "rv_mad_scatter_mps": mad_scatter,
        "rv_min_mps": rv_min,
        "rv_max_mps": rv_max,

        "rv_median_uncertainty_mps": finite_median("drs_dvrms"),

        "bis_span_median_mps": finite_median("bis_span_mps"),
        "bis_mean_velocity_median_kms": finite_median("drs_bis_rv"),
        "fwhm_median_kms": finite_median("drs_ccf_fwhm"),
        "snr_median": finite_median("drs_snr"),

        "date_obs_start_utc": utc_dates.min(),
        "date_obs_end_utc": utc_dates.max(),
        "utc_date_count": int(utc_dates.nunique()),

        "invalid_rv_count": int(group["flag_invalid_rv"].sum()),
        "invalid_uncertainty_count": int(
            group["flag_invalid_uncertainty"].sum()
        ),
        "extreme_rv_review_count": int(
            group["flag_extreme_rv_review"].sum()
        ),
        "extreme_bis_review_count": int(
            group["flag_extreme_bis_review"].sum()
        ),
        "low_or_zero_snr_count": int(
            group["flag_low_or_zero_snr"].sum()
        ),
        "invalid_fwhm_count": int(group["flag_invalid_fwhm"].sum()),
        "rv_field_disagreement_count": int(
            group["flag_rv_field_disagreement"].sum()
        ),
    })

result = pd.DataFrame(records).sort_values(
    ["tel_object", "bjd_day"]
).reset_index(drop=True)

# Group-level review indicators.
result["flag_group_rv_review"] = (
    (result["invalid_rv_count"] > 0) |
    (result["extreme_rv_review_count"] > 0)
)
result["flag_group_uncertainty_review"] = (
    result["invalid_uncertainty_count"] > 0
)
result["flag_group_bis_review"] = (
    result["extreme_bis_review_count"] > 0
)

result.to_csv(OUT, index=False)

# Report.
report = []
report.append("PHASE 2 - STAGE 4: BJD-DAY RV PROCESSING V1")
report.append("=" * 65)
report.append(f"Raw input: {RAW}")
report.append(f"Processed output: {OUT}")
report.append(f"Observation provenance: {PROVENANCE}")
report.append("")
report.append(f"Raw observations: {len(df):,}")
report.append(f"Targets: {df['tel_object'].nunique()}")
report.append(f"BJD-day groups: {len(result):,}")
report.append("")
report.append("ESTIMATOR DEFINITIONS")
report.append("- RV median: median of all finite RV observations.")
report.append("- Weighted mean: inverse-variance weighted using finite RV")
report.append("  and strictly positive finite uncertainty.")
report.append("- Formal uncertainty: sqrt(1 / sum(weights)).")
report.append("- MAD scatter: 1.4826 * median absolute deviation.")
report.append("- BIS span: drs_bis_span converted from km/s to m/s.")
report.append("- BIS mean velocity is retained separately.")
report.append("")
report.append("REVIEW FLAGS - NOT AUTOMATIC REJECTION LIMITS")
report.append(f"|RV| > {RV_EXTREME_MPS:g} m/s")
report.append(f"|BIS span| > {BIS_EXTREME_MPS:g} m/s")
report.append(
    f"|drs_ccf_rvc - drs_ccf_rv| > "
    f"{RV_FIELD_DISAGREEMENT_MPS:g} m/s"
)
report.append("")
report.append("OBSERVATION-LEVEL FLAG TOTALS")

flag_cols = [
    "flag_invalid_rv",
    "flag_invalid_uncertainty",
    "flag_extreme_rv_review",
    "flag_extreme_bis_review",
    "flag_low_or_zero_snr",
    "flag_invalid_fwhm",
    "flag_rv_field_disagreement"
]

for col in flag_cols:
    report.append(f"{col}: {int(df[col].sum())}")

report.append("")
report.append("GROUP-LEVEL REVIEW TOTALS")
for col in [
    "flag_group_rv_review",
    "flag_group_uncertainty_review",
    "flag_group_bis_review"
]:
    report.append(f"{col}: {int(result[col].sum())}")

report.append("")
report.append("UNIT CONVERSION")
report.append(
    "Maximum |rv_mps - drs_ccf_rvc * 1000|: "
    f"{df['rv_conversion_error_mps'].max():.12g} m/s"
)
report.append(
    "Rows with conversion error > 1e-6 m/s: "
    f"{int((df['rv_conversion_error_mps'] > 1e-6).sum())}"
)
report.append("")
report.append("DATA POLICY")
report.append("No raw observations were deleted.")
report.append("No automatic scientific outlier rejection was applied.")
report.append("BJD-day groups are not assumed to equal UTC observing nights.")
report.append("All observation-level source row indices are retained.")
report.append("")
report.append("COMPLETED")

REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")

manifest = {
    "dataset": "harps_rv_bjd_day_summary_v1",
    "version": "1.0.0",
    "input": str(RAW.relative_to(BASE)),
    "output": str(OUT.relative_to(BASE)),
    "provenance": str(PROVENANCE.relative_to(BASE)),
    "report": str(REPORT.relative_to(BASE)),
    "raw_observations": int(len(df)),
    "target_count": int(df["tel_object"].nunique()),
    "bjd_day_groups": int(len(result)),
    "grouping": "tel_object + floor(drs_bjd)",
    "rv_primary_estimator": "median of finite rv_mps",
    "rv_auxiliary_estimator": "inverse-variance weighted mean",
    "uncertainty_policy": "positive finite drs_dvrms only for weights",
    "raw_observations_deleted": 0,
    "automatic_outlier_rejection": False,
    "review_thresholds": {
        "absolute_rv_mps": RV_EXTREME_MPS,
        "absolute_bis_span_mps": BIS_EXTREME_MPS,
        "rv_field_disagreement_mps": RV_FIELD_DISAGREEMENT_MPS
    }
}

MANIFEST.write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8"
)

print("\n" + "=" * 65)
print("BJD-DAY PROCESSING COMPLETED")
print("=" * 65)
print(f"Raw observations: {len(df):,}")
print(f"Targets: {df['tel_object'].nunique()}")
print(f"BJD-day groups: {len(result):,}")
print(f"\nProcessed CSV: {OUT}")
print(f"Observation QC CSV: {PROVENANCE}")
print(f"QC report: {REPORT}")
print(f"Manifest: {MANIFEST}")
print("\nRAW DATA UNCHANGED")
