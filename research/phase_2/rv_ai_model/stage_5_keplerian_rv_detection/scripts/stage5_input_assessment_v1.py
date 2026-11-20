from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path(
    r"D:\exoanalytica\research\phase_2\rv_ai_model"
    r"\stage_5_keplerian_rv_detection"
)

INPUT = BASE / "data" / "input"
REPORTS = BASE / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

raw = pd.read_csv(INPUT / "harps_rv_observations_18_targets.csv")
qc = pd.read_csv(INPUT / "harps_rv_observation_qc_v1.csv")
robust = pd.read_csv(INPUT / "harps_rv_robust_qc_flagged_v2_3.csv")

idx = pd.to_numeric(qc["source_row_index"], errors="coerce")

if (
    idx.isna().any()
    or (idx != np.floor(idx)).any()
    or not idx.between(0, len(raw) - 1).all()
    or idx.nunique() != len(raw)
    or len(raw) != len(qc)
):
    raise ValueError("Invalid source row provenance")

aligned = raw.iloc[idx.astype(int).to_numpy()].reset_index(drop=True)
qc = qc.reset_index(drop=True)

for col in ["tel_object"]:
    if not aligned[col].fillna("").equals(qc[col].fillna("")):
        raise ValueError(f"Alignment mismatch: {col}")

for col in ["drs_bjd", "rv_mps"]:
    a = pd.to_numeric(aligned[col], errors="coerce").to_numpy(float)
    b = pd.to_numeric(qc[col], errors="coerce").to_numpy(float)

    same_nan = np.isnan(a) & np.isnan(b)
    finite = np.isfinite(a) & np.isfinite(b)

    close = np.zeros(len(a), dtype=bool)
    close[finite] = np.isclose(
        a[finite], b[finite], rtol=1e-12, atol=1e-9
    )

    if not np.all(same_nan | close):
        raise ValueError(f"Alignment mismatch: {col}")

def read_flag(series):
    return series.astype(str).str.strip().str.lower().isin(
        ["true", "1", "yes"]
    )

t = pd.to_numeric(raw["drs_bjd"], errors="coerce")
rv = pd.to_numeric(raw["rv_mps"], errors="coerce")
err = pd.to_numeric(raw["drs_dvrms"], errors="coerce")

valid_time = np.isfinite(t)
valid_rv = np.isfinite(rv)
valid_error = np.isfinite(err) & (err > 0)
valid_core = valid_time & valid_rv & valid_error

qc_flags = [
    "flag_invalid_rv",
    "flag_invalid_uncertainty",
    "flag_extreme_rv_review",
    "flag_extreme_bis_review",
    "flag_low_or_zero_snr",
    "flag_invalid_fwhm",
    "flag_rv_field_disagreement"
]

for col in qc_flags:
    qc[col] = read_flag(qc[col])

rows = []

for target, indices in raw.groupby("tel_object").groups.items():
    idx_array = np.asarray(list(indices), dtype=int)
    q = qc.iloc[idx_array]
    target_times = t.iloc[idx_array]
    target_valid = valid_core[idx_array]

    valid_times = target_times[target_valid]

    baseline = (
        float(valid_times.max() - valid_times.min())
        if len(valid_times) else np.nan
    )

    row = {
        "tel_object": target,
        "raw_observations": len(idx_array),
        "valid_bjd": int(valid_time[idx_array].sum()),
        "valid_rv": int(valid_rv[idx_array].sum()),
        "valid_positive_uncertainty": int(valid_error[idx_array].sum()),
        "valid_core_observations": int(target_valid.sum()),
        "valid_time_baseline_days": baseline,
        "robust_qc_flagged_rows": int(
            (robust["tel_object"] == target).sum()
        )
    }

    for col in qc_flags:
        row[col] = int(q[col].sum())

    rows.append(row)

summary = pd.DataFrame(rows).sort_values("tel_object")

csv_path = REPORTS / "stage5_input_assessment_v1.csv"
summary.to_csv(csv_path, index=False)

report = {
    "stage": 5,
    "version": "1.0",
    "raw_observations": len(raw),
    "qc_observations": len(qc),
    "targets": int(raw["tel_object"].nunique()),
    "row_alignment": "PASS",
    "source_indices_unique": True,
    "valid_core_observations": int(valid_core.sum()),
    "observations_removed": 0,
    "automatic_outlier_rejection": False,
    "time_column": "drs_bjd",
    "rv_column": "rv_mps",
    "uncertainty_column": "drs_dvrms",
    "uncertainty_unit": "m/s",
    "summary_file": csv_path.name
}

json_path = REPORTS / "stage5_input_assessment_v1.json"
json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("\n===== STAGE 5 INPUT ASSESSMENT =====")
print(json.dumps(report, indent=2))
print("\n===== TARGET SUMMARY =====")
print(summary.to_string(index=False))
print("\nAssessment completed. No observations removed.")
