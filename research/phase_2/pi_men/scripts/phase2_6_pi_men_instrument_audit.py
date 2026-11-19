from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd

# ============================================================
# PI MEN HARPS INSTRUMENT & DATA QUALITY AUDIT
# Research-only. Does not modify existing project files.
# ============================================================

INPUT = DATA_DIR / "phase2_6_pi_men_harps_timeseries.csv"
OUTPUT_CSV = DATA_DIR / "phase2_6_pi_men_instrument_audit.csv"
OUTPUT_REPORT = REPORTS_DIR / "phase2_6_pi_men_instrument_audit.txt"

FIBRE_UPGRADE_DATE = pd.Timestamp("2015-06-03", tz="UTC")
REJECT_START = pd.Timestamp("2018-11-27", tz="UTC")
REJECT_END = pd.Timestamp("2018-11-29", tz="UTC")

SECULAR_ACCELERATION = 0.48  # m/s/year, approximate published value

if not INPUT.exists():
    raise FileNotFoundError(f"Input CSV not found: {INPUT.resolve()}")

df = pd.read_csv(INPUT)

required = [
    "date_obs", "bjd", "rv_ms", "rv_relative_ms",
    "rv_error_ms", "drs_snr", "ins_mode"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["date_utc"] = pd.to_datetime(
    df["date_obs"], errors="coerce", utc=True
)

for col in [
    "bjd", "rv_ms", "rv_relative_ms",
    "rv_error_ms", "drs_snr"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Instrument era classification
df["instrument_epoch"] = np.where(
    df["date_utc"] < FIBRE_UPGRADE_DATE,
    "HARPS_PRE",
    "HARPS_POST"
)

# Flag the dates rejected in the published analysis
df["published_rejection_window"] = (
    (df["date_utc"] >= REJECT_START) &
    (df["date_utc"] < REJECT_END)
)

# Diagnostic flags only; no rows are deleted
df["snr_zero_flag"] = df["drs_snr"].eq(0)

df["invalid_measurement_flag"] = (
    ~np.isfinite(df["bjd"]) |
    ~np.isfinite(df["rv_relative_ms"]) |
    ~np.isfinite(df["rv_error_ms"]) |
    (df["rv_error_ms"] <= 0)
)

# Approximate secular acceleration scale from first observation
valid_dates = df["date_utc"].dropna()

if len(valid_dates):
    first_date = valid_dates.min()
    df["years_from_first_observation"] = (
        (df["date_utc"] - first_date).dt.total_seconds()
        / (365.25 * 86400)
    )
    df["expected_secular_drift_ms"] = (
        SECULAR_ACCELERATION *
        df["years_from_first_observation"]
    )
else:
    df["years_from_first_observation"] = np.nan
    df["expected_secular_drift_ms"] = np.nan

# ------------------------------------------------------------
# Report helpers
# ------------------------------------------------------------

lines = []

def add(text=""):
    lines.append(str(text))

def section(title):
    add()
    add("=" * 72)
    add(title)
    add("=" * 72)

def summarize(group, label):
    good = group[
        np.isfinite(group["rv_relative_ms"]) &
        np.isfinite(group["rv_error_ms"]) &
        (group["rv_error_ms"] > 0)
    ]

    add(f"\n{label}")
    add("-" * 60)
    add(f"Rows: {len(group)}")
    add(f"Valid RV rows: {len(good)}")
    add(f"Median SNR: {group['drs_snr'].median():.4f}")
    add(f"Median RV error (m/s): {good['rv_error_ms'].median():.6f}")

    if len(good):
        add(f"RV median (m/s): {good['rv_relative_ms'].median():.6f}")
        add(f"RV standard deviation (m/s): {good['rv_relative_ms'].std():.6f}")
        add(f"RV minimum (m/s): {good['rv_relative_ms'].min():.6f}")
        add(f"RV maximum (m/s): {good['rv_relative_ms'].max():.6f}")

    add(f"SNR = 0 rows: {int(group['snr_zero_flag'].sum())}")
    add(f"Invalid measurement rows: {int(group['invalid_measurement_flag'].sum())}")

# ------------------------------------------------------------
# Main report
# ------------------------------------------------------------

section("PI MEN HARPS INSTRUMENT AUDIT")

add(f"Input file: {INPUT.resolve()}")
add(f"Total input rows: {len(df)}")
add(f"Fibre upgrade boundary: {FIBRE_UPGRADE_DATE}")
add(f"Published rejection window: {REJECT_START.date()} to {REJECT_END.date()}")
add("Classification is diagnostic only; no observations were removed.")

section("1. INSTRUMENT EPOCH COUNTS")

for epoch in ["HARPS_PRE", "HARPS_POST"]:
    group = df[df["instrument_epoch"] == epoch]
    summarize(group, epoch)

section("2. PUBLISHED REJECTION WINDOW")

rejected_window = df[df["published_rejection_window"]].copy()

add(f"Rows dated 2018-11-27 or 2018-11-28: {len(rejected_window)}")

if len(rejected_window):
    cols = [
        "date_obs", "bjd", "rv_ms", "rv_relative_ms",
        "rv_error_ms", "drs_snr", "ins_mode"
    ]
    add(rejected_window[cols].to_string(index=False))
else:
    add("No rows found in the published rejection window.")

section("3. ZERO-SNR OBSERVATIONS")

zero_snr = df[df["snr_zero_flag"]].copy()
add(f"Total SNR=0 rows: {len(zero_snr)}")

if len(zero_snr):
    cols = [
        "date_obs", "bjd", "rv_ms", "rv_relative_ms",
        "rv_error_ms", "drs_snr", "ins_mode"
    ]
    add(zero_snr[cols].to_string(index=False))

section("4. OBSERVATIONS BY CALENDAR YEAR")

yearly = (
    df.dropna(subset=["date_utc"])
      .assign(year=lambda x: x["date_utc"].dt.year)
      .groupby(["year", "instrument_epoch"])
      .agg(
          observations=("bjd", "count"),
          median_snr=("drs_snr", "median"),
          median_error_ms=("rv_error_ms", "median"),
          rv_std_ms=("rv_relative_ms", "std"),
          zero_snr_count=("snr_zero_flag", "sum")
      )
      .reset_index()
)

add(yearly.to_string(index=False))

section("5. OBSERVATION MODE COUNTS")

mode_counts = (
    df["ins_mode"]
    .fillna("MISSING")
    .value_counts()
)

add(mode_counts.to_string())

section("6. SECULAR ACCELERATION SCALE")

if len(valid_dates):
    baseline_years = (
        (valid_dates.max() - valid_dates.min()).total_seconds()
        / (365.25 * 86400)
    )

    estimated_drift = SECULAR_ACCELERATION * baseline_years

    add(f"Time baseline (years): {baseline_years:.6f}")
    add(f"Approximate published acceleration: {SECULAR_ACCELERATION:.4f} m/s/year")
    add(f"Expected drift over baseline: {estimated_drift:.4f} m/s")
    add("NOTE: This is an estimated scale, not a correction applied to the data.")
else:
    add("Could not calculate baseline: no valid observation dates.")

section("7. SCIENTIFIC LIMITATIONS")

add("1. HARPS PRE and POST must be modelled with separate zero-point offsets.")
add("2. Raw PRE/POST medians are not a valid instrumental offset measurement")
add("   because planetary signals and secular acceleration also affect RV.")
add("3. The seven observations rejected in the paper should be checked")
add("   against the original ESO records and exact observation timestamps.")
add("4. This CSV contains ESO DRS RVs, not HARPS-TERRA RVs.")
add("5. No secular acceleration correction or data exclusion was applied.")
add("6. This audit does not perform a new orbital fit.")

# Save annotated audit CSV and report
df.to_csv(OUTPUT_CSV, index=False)
OUTPUT_REPORT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print("\nAnnotated CSV saved:", OUTPUT_CSV.resolve())
print("Report saved:", OUTPUT_REPORT.resolve())
print("\n===== INSTRUMENT AUDIT COMPLETE =====")
