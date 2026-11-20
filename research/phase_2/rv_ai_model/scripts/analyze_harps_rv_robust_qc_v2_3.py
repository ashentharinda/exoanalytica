from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path.cwd()

INPUT = BASE / "data/interim/harps_rv_observations_18_targets.csv"
REPORTS = BASE / "reports"

SUMMARY_OUT = REPORTS / "harps_rv_robust_qc_summary_v2_3.csv"
FLAGS_OUT = REPORTS / "harps_rv_robust_qc_flagged_v2_3.csv"
REPORT_OUT = REPORTS / "harps_rv_robust_qc_report_v2_3.txt"
MANIFEST_OUT = BASE / "data/manifests/harps_rv_robust_qc_v2_3.json"

REPORTS.mkdir(parents=True, exist_ok=True)
MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT)
required = [
    "tel_object", "date_obs", "drs_bjd", "drs_ccf_rvc",
    "drs_ccf_rv", "rv_mps", "drs_dvrms", "drs_snr",
    "drs_ccf_fwhm"
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

numeric = [
    "drs_bjd", "drs_ccf_rvc", "drs_ccf_rv", "rv_mps",
    "drs_dvrms", "drs_snr", "drs_ccf_fwhm"
]
for col in numeric:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Verify the documented RV conversion without changing source values.
conversion_error = (
    df["rv_mps"] - df["drs_ccf_rvc"] * 1000.0
).abs()

df["rv_conversion_error_mps"] = conversion_error
df["rv_field_difference_mps"] = (
    (df["drs_ccf_rvc"] - df["drs_ccf_rv"]) * 1000.0
).abs()

df["rv_abs_mps"] = df["rv_mps"].abs()

# Target-centred robust statistics.
summary_rows = []
flag_frames = []

for target, group in df.groupby("tel_object", sort=True):
    g = group.copy()
    rv = g["rv_mps"].to_numpy(dtype=float)
    valid = np.isfinite(rv)

    if valid.sum():
        median = float(np.median(rv[valid]))
        mad = float(np.median(np.abs(rv[valid] - median)))
        robust_sigma = 1.4826 * mad

        # Fallback scales are diagnostic only.
        scale_method = "MAD"
        if not np.isfinite(robust_sigma) or robust_sigma <= 0:
            q25, q75 = np.nanpercentile(rv[valid], [25, 75])
            robust_sigma = float((q75 - q25) / 1.349)
            scale_method = "IQR_fallback"

        if not np.isfinite(robust_sigma) or robust_sigma <= 0:
            robust_sigma = float(np.nanstd(rv[valid]))
            scale_method = "STD_fallback"

        if np.isfinite(robust_sigma) and robust_sigma > 0:
            g["rv_robust_z"] = (
                g["rv_mps"] - median
            ) / robust_sigma
        else:
            g["rv_robust_z"] = np.nan
            scale_method = "unavailable"

        abs_dev = np.abs(rv[valid] - median)
        q01, q50, q99 = np.percentile(rv[valid], [1, 50, 99])
        rv_min = float(np.min(rv[valid]))
        rv_max = float(np.max(rv[valid]))
        max_abs_dev = float(np.max(abs_dev))
    else:
        median = mad = robust_sigma = np.nan
        q01 = q50 = q99 = rv_min = rv_max = max_abs_dev = np.nan
        scale_method = "unavailable"
        g["rv_robust_z"] = np.nan

    g["flag_rv_robust_z_gt_5"] = g["rv_robust_z"].abs() > 5
    g["flag_rv_robust_z_gt_10"] = g["rv_robust_z"].abs() > 10
    g["flag_extreme_absolute_rv"] = g["rv_abs_mps"] > 100000
    g["flag_high_rv_uncertainty"] = g["drs_dvrms"] > 5
    g["flag_invalid_rv_uncertainty"] = (
        ~np.isfinite(g["drs_dvrms"]) | (g["drs_dvrms"] <= 0)
    )
    g["flag_zero_or_invalid_snr"] = (
        ~np.isfinite(g["drs_snr"]) | (g["drs_snr"] <= 0)
    )
    g["flag_invalid_fwhm"] = (
        ~np.isfinite(g["drs_ccf_fwhm"]) | (g["drs_ccf_fwhm"] <= 0)
    )
    g["flag_rv_field_difference_gt_10"] = (
        g["rv_field_difference_mps"] > 10
    )

    flag_cols = [c for c in g.columns if c.startswith("flag_")]
    g["any_review_flag"] = g[flag_cols].any(axis=1)

    flag_frames.append(g.loc[g["any_review_flag"]].copy())

    summary_rows.append({
        "tel_object": target,
        "observations": len(g),
        "valid_rv_count": int(valid.sum()),
        "rv_median_mps": median,
        "rv_mad_mps": mad,
        "rv_robust_sigma_mps": robust_sigma,
        "robust_scale_method": scale_method,
        "rv_p01_mps": q01,
        "rv_p50_mps": q50,
        "rv_p99_mps": q99,
        "rv_min_mps": rv_min,
        "rv_max_mps": rv_max,
        "max_abs_deviation_from_median_mps": max_abs_dev,
        "robust_z_gt_5_count": int(g["flag_rv_robust_z_gt_5"].sum()),
        "robust_z_gt_10_count": int(g["flag_rv_robust_z_gt_10"].sum()),
        "extreme_absolute_rv_count": int(g["flag_extreme_absolute_rv"].sum()),
        "high_uncertainty_count": int(g["flag_high_rv_uncertainty"].sum()),
        "invalid_uncertainty_count": int(g["flag_invalid_rv_uncertainty"].sum()),
        "zero_or_invalid_snr_count": int(g["flag_zero_or_invalid_snr"].sum()),
        "invalid_fwhm_count": int(g["flag_invalid_fwhm"].sum()),
        "rv_field_difference_gt_10_count": int(
            g["flag_rv_field_difference_gt_10"].sum()
        ),
        "any_review_flag_count": int(g["any_review_flag"].sum()),
    })

summary = pd.DataFrame(summary_rows)
flagged = (
    pd.concat(flag_frames, ignore_index=True)
    if flag_frames else pd.DataFrame()
)

summary.to_csv(SUMMARY_OUT, index=False)
flagged.to_csv(FLAGS_OUT, index=False)

lines = [
    "HARPS RV ROBUST QUALITY CONTROL V2.3",
    "=" * 72,
    "",
    f"Input observations: {len(df)}",
    f"Targets: {df['tel_object'].nunique()}",
    f"Flagged observations: {len(flagged)}",
    "",
    "RV conversion verification:",
    f"Maximum absolute conversion error (m/s): {conversion_error.max():.12g}",
    f"Rows with conversion error > 1e-6 m/s: {(conversion_error > 1e-6).sum()}",
    "",
    "Target-level summary:",
    summary.to_string(index=False),
    "",
    "IMPORTANT INTERPRETATION LIMITATIONS:",
    "- Robust-z thresholds are exploratory review flags, not rejection criteria.",
    "- A large RV deviation is not automatically an instrumental error or false signal.",
    "- Target-centred MAD can be affected by trends, activity, and contaminated data.",
    "- RV field differences are review flags; the two catalogue fields have different corrections.",
    "- No observations were deleted or automatically rejected.",
    "- No planet detection or Keplerian fitting was performed.",
    "",
    "RAW INPUT DATA UNCHANGED.",
]

REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

manifest = {
    "version": "2.3",
    "input": str(INPUT.relative_to(BASE)),
    "outputs": [
        str(SUMMARY_OUT.relative_to(BASE)),
        str(FLAGS_OUT.relative_to(BASE)),
        str(REPORT_OUT.relative_to(BASE)),
    ],
    "observations": int(len(df)),
    "targets": int(df["tel_object"].nunique()),
    "flagged_observations": int(len(flagged)),
    "rv_conversion_max_error_mps": float(conversion_error.max()),
    "raw_input_modified": False,
    "automatic_observation_rejection": False,
    "purpose": "Exploratory target-centred RV robust quality control",
}
MANIFEST_OUT.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

print("\n===== RV ROBUST QC V2.3 =====")
print(f"Observations: {len(df)}")
print(f"Targets: {df['tel_object'].nunique()}")
print(f"Flagged observations: {len(flagged)}")
print(f"RV conversion max error: {conversion_error.max():.12g} m/s")
print("\n===== TARGET SUMMARY =====")
print(summary[[
    "tel_object", "observations", "rv_median_mps",
    "rv_robust_sigma_mps", "robust_z_gt_5_count",
    "extreme_absolute_rv_count", "any_review_flag_count"
]].to_string(index=False))

print("\nSaved:")
print(SUMMARY_OUT)
print(FLAGS_OUT)
print(REPORT_OUT)
print(MANIFEST_OUT)
print("\nCOMPLETED - RAW INPUT DATA UNCHANGED")
