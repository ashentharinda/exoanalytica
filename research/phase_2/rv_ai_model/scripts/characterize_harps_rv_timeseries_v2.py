from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path.cwd()

INPUT = BASE / "data/interim/harps_rv_observations_18_targets.csv"
SCRIPT_DIR = BASE / "scripts"
REPORT_DIR = BASE / "reports"

SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_SCRIPT = SCRIPT_DIR / "characterize_harps_rv_timeseries_v2.py"

CADENCE_OUT = REPORT_DIR / "harps_rv_cadence_summary_v2.csv"
GAPS_OUT = REPORT_DIR / "harps_rv_time_gaps_v2.csv"
WINDOW_OUT = REPORT_DIR / "harps_rv_spectral_window_v2.csv"
REPORT_OUT = REPORT_DIR / "harps_rv_timeseries_characterization_v2.txt"

# ------------------------------------------------------------
# Load raw observations
# ------------------------------------------------------------
if not INPUT.exists():
    raise FileNotFoundError(INPUT)

df = pd.read_csv(INPUT)

required = ["tel_object", "drs_bjd", "rv_mps"]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["drs_bjd"] = pd.to_numeric(df["drs_bjd"], errors="coerce")
df["rv_mps"] = pd.to_numeric(df["rv_mps"], errors="coerce")

df = df.dropna(subset=["tel_object", "drs_bjd"]).copy()

print("=" * 72)
print("PHASE 2 - STAGE 4")
print("RV TIME-SERIES CHARACTERIZATION V2")
print("=" * 72)

print("Raw input observations:", len(df))
print("Targets:", df["tel_object"].nunique())

# ------------------------------------------------------------
# Cadence and time-gap characterization
# ------------------------------------------------------------
cadence_rows = []
gap_rows = []
window_rows = []

alias_frequencies = {
    "half_day": 2.0,
    "one_day": 1.0,
    "two_day": 0.5,
    "one_year": 1.0 / 365.25,
    "one_month": 1.0 / 29.53059,
}

for target, group in df.groupby("tel_object", sort=True):

    times = np.sort(group["drs_bjd"].to_numpy(dtype=float))
    times = times[np.isfinite(times)]

    if len(times) < 3:
        print(f"SKIP {target}: insufficient timestamps")
        continue

    gaps = np.diff(times)
    positive_gaps = gaps[gaps > 0]

    if len(positive_gaps) == 0:
        print(f"SKIP {target}: no positive time gaps")
        continue

    baseline = float(times[-1] - times[0])

    median_gap = float(np.median(positive_gaps))
    mean_gap = float(np.mean(positive_gaps))

    q25, q75, q90, q95 = np.percentile(
        positive_gaps, [25, 75, 90, 95]
    )

    cadence_rows.append({
        "tel_object": target,
        "observation_count": len(times),
        "unique_timestamp_count": len(np.unique(times)),
        "baseline_days": baseline,
        "baseline_years": baseline / 365.25,
        "positive_gap_count": len(positive_gaps),
        "median_gap_days": median_gap,
        "mean_gap_days": mean_gap,
        "gap_q25_days": q25,
        "gap_q75_days": q75,
        "gap_q90_days": q90,
        "gap_q95_days": q95,
        "maximum_gap_days": float(np.max(positive_gaps)),
        "gaps_over_7_days": int(np.sum(positive_gaps > 7)),
        "gaps_over_30_days": int(np.sum(positive_gaps > 30)),
        "gaps_over_90_days": int(np.sum(positive_gaps > 90)),
    })

    for threshold in [1, 7, 30, 90, 180, 365]:
        gap_rows.append({
            "tel_object": target,
            "gap_threshold_days": threshold,
            "gap_count": int(np.sum(positive_gaps > threshold)),
            "gap_fraction": float(
                np.mean(positive_gaps > threshold)
            ),
        })

    # --------------------------------------------------------
    # Spectral window function
    #
    # W(f) = |sum(exp(2*pi*i*f*t)) / N|^2
    #
    # This examines the sampling timestamps only.
    # It is NOT a planet periodogram.
    # --------------------------------------------------------
    centered_times = times - times.mean()
    n = len(centered_times)

    for alias_name, frequency in alias_frequencies.items():
        phase = 2.0 * np.pi * frequency * centered_times
        power = abs(np.mean(np.exp(1j * phase))) ** 2

        window_rows.append({
            "tel_object": target,
            "feature": alias_name,
            "frequency_cycles_per_day": frequency,
            "period_days": 1.0 / frequency,
            "window_power": float(power),
        })

    # Exploratory frequency grid
    f_min = max(1.0 / baseline, 0.001)
    f_max = 5.0

    if f_min >= f_max:
        continue

    frequencies = np.linspace(f_min, f_max, 1024)
    powers = np.empty(len(frequencies), dtype=float)

    # Chunking limits temporary memory use.
    for start in range(0, len(frequencies), 64):
        freq_chunk = frequencies[start:start + 64]

        phase = (
            2.0 * np.pi
            * freq_chunk[:, None]
            * centered_times[None, :]
        )

        powers[start:start + len(freq_chunk)] = (
            np.abs(np.exp(1j * phase).mean(axis=1)) ** 2
        )

    # Exclude the very lowest frequencies from the peak shortlist.
    eligible = np.where(frequencies >= max(f_min, 0.01))[0]

    if len(eligible):
        top_indices = eligible[
            np.argsort(powers[eligible])[-5:][::-1]
        ]

        for rank, index in enumerate(top_indices, start=1):
            frequency = float(frequencies[index])

            window_rows.append({
                "tel_object": target,
                "feature": f"grid_peak_{rank}",
                "frequency_cycles_per_day": frequency,
                "period_days": 1.0 / frequency,
                "window_power": float(powers[index]),
            })

    print(
        f"Processed {target}: "
        f"{len(times)} timestamps, "
        f"baseline={baseline:.2f} days"
    )

# ------------------------------------------------------------
# Save outputs
# ------------------------------------------------------------
cadence = pd.DataFrame(cadence_rows)
gaps_df = pd.DataFrame(gap_rows)
window_df = pd.DataFrame(window_rows)

cadence.to_csv(CADENCE_OUT, index=False)
gaps_df.to_csv(GAPS_OUT, index=False)
window_df.to_csv(WINDOW_OUT, index=False)

# ------------------------------------------------------------
# Human-readable report
# ------------------------------------------------------------
lines = [
    "PHASE 2 - STAGE 4: RV TIME-SERIES CHARACTERIZATION V2",
    "=" * 68,
    "",
    f"Input observations: {len(df)}",
    f"Targets processed: {len(cadence)}",
    "",
    "CADENCE METHOD",
    "- Original drs_bjd timestamps used.",
    "- Positive consecutive timestamp differences used.",
    "- Duplicate timestamps are not counted as positive gaps.",
    "",
    "SPECTRAL WINDOW METHOD",
    "- Sampling timestamps only; no RV values used.",
    "- W(f) = |mean(exp(2*pi*i*f*t))|^2.",
    "- Alias frequencies evaluated at 0.5, 1, 2 cycles/day,",
    "  one month and one year.",
    "- Exploratory frequency grid: 0.001 to 5 cycles/day,",
    "  with target-specific lower frequency limit.",
    "- Grid peaks are sampling aliases, NOT detected planets.",
    "",
    "IMPORTANT LIMITATIONS",
    "- No RV outlier removal was performed.",
    "- No planet period detection was performed.",
    "- No stellar activity correction was performed.",
    "- No instrumental offset correction was performed.",
    "- A strong window peak indicates sampling structure,",
    "  not an astrophysical signal.",
    "",
    "TARGET CADENCE SUMMARY",
    "",
]

if not cadence.empty:
    for _, row in cadence.iterrows():
        lines.append(
            f"{row['tel_object']}: "
            f"N={int(row['observation_count'])}, "
            f"baseline={row['baseline_days']:.2f} d, "
            f"median gap={row['median_gap_days']:.4f} d, "
            f"max gap={row['maximum_gap_days']:.2f} d, "
            f">30d gaps={int(row['gaps_over_30_days'])}"
        )

lines.extend([
    "",
    "OUTPUTS",
    str(CADENCE_OUT),
    str(GAPS_OUT),
    str(WINDOW_OUT),
    "",
    "RAW INPUT DATA UNCHANGED",
])

REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

# ------------------------------------------------------------
# Completion summary
# ------------------------------------------------------------
print("\n===== OUTPUT SUMMARY =====")
print("Targets processed:", len(cadence))
print("Cadence rows:", len(cadence))
print("Gap rows:", len(gaps_df))
print("Window rows:", len(window_df))

print("\nSaved:")
print(CADENCE_OUT)
print(GAPS_OUT)
print(WINDOW_OUT)
print(REPORT_OUT)

print("\nCOMPLETED - RAW DATA UNCHANGED")
