from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd

SOURCE = DATA_DIR / "phase2_6_pi_men_instrument_audit.csv"
OUTPUT = DATA_DIR / "phase2_6_pi_men_corrected_dataset.csv"
REPORT = REPORTS_DIR / "phase2_6_pi_men_corrected_dataset.txt"

SLOPE = 0.48  # m/s/year

df = pd.read_csv(SOURCE)
df["date_utc"] = pd.to_datetime(
    df["date_obs"], errors="coerce", utc=True
)

# Published rejected observations:
# 7 affected by poor wavelength solution
# 2 affected by telescope guiding failure
paper_reject = df["published_rejection_window"].astype(bool)
guiding_reject = df["snr_zero_flag"].astype(bool)

df["exclusion_reason"] = ""
df.loc[paper_reject, "exclusion_reason"] = (
    "Published rejection: poor wavelength solution"
)
df.loc[guiding_reject, "exclusion_reason"] = (
    "Published rejection: telescope guiding failure"
)

# Exclude only the nine identified observations.
clean = df.loc[
    ~(paper_reject | guiding_reject)
].copy()

# Retain valid measurements only.
valid = (
    np.isfinite(clean["bjd"]) &
    np.isfinite(clean["rv_relative_ms"]) &
    np.isfinite(clean["rv_error_ms"]) &
    (clean["rv_error_ms"] > 0)
)

clean = clean.loc[valid].copy()

# Apply approximate secular acceleration correction.
# Reference epoch is the first retained observation.
reference_bjd = clean["bjd"].min()

clean["years_from_reference"] = (
    clean["bjd"] - reference_bjd
) / 365.25

clean["secular_acceleration_ms"] = (
    SLOPE * clean["years_from_reference"]
)

clean["rv_corrected_ms"] = (
    clean["rv_relative_ms"] -
    clean["secular_acceleration_ms"]
)

clean = clean.sort_values("bjd").reset_index(drop=True)

# Save clean dataset separately.
clean.to_csv(OUTPUT, index=False)

# Build report.
lines = [
    "PI MEN CORRECTED DATASET PREPARATION",
    "=" * 65,
    f"Source rows: {len(df)}",
    f"Published wavelength-solution exclusions: {int(paper_reject.sum())}",
    f"Published guiding-failure exclusions: {int(guiding_reject.sum())}",
    f"Total exclusions: {int((paper_reject | guiding_reject).sum())}",
    f"Retained valid observations: {len(clean)}",
    "",
    f"Reference BJD: {reference_bjd:.8f}",
    f"Secular acceleration: {SLOPE:.4f} m/s/year",
    f"Time baseline (years): {clean['years_from_reference'].max():.6f}",
    f"Maximum applied correction (m/s): {clean['secular_acceleration_ms'].max():.6f}",
    "",
    "INSTRUMENT EPOCH COUNTS",
    "-" * 65,
    clean["instrument_epoch"].value_counts().to_string(),
    "",
    "CORRECTED RV SUMMARY",
    "-" * 65,
    clean["rv_corrected_ms"].describe().to_string(),
    "",
    "IMPORTANT LIMITATIONS",
    "-" * 65,
    "1. Original source CSV was not modified.",
    "2. PRE and POST zero-point offsets have not yet been fitted.",
    "3. Secular acceleration is an approximate published correction.",
    "4. ESO DRS RVs are not identical to HARPS-TERRA RVs.",
    "5. This is data preparation, not an orbital validation.",
    "",
    f"Output CSV: {OUTPUT.resolve()}",
]

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print("\n===== CORRECTED DATASET PREPARATION COMPLETE =====")
