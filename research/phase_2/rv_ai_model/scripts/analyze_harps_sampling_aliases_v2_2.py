from pathlib import Path
import json
import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_widths

BASE = Path.cwd()

INPUT = BASE / "reports/harps_rv_bjd_day_sampling_v2_1.csv"
OUT = BASE / "reports"
SCRIPT_DIR = BASE / "scripts"

OUT.mkdir(parents=True, exist_ok=True)

ALIAS_OUT = OUT / "harps_rv_precise_alias_powers_v2_2.csv"
PEAK_OUT = OUT / "harps_rv_local_sampling_peaks_v2_2.csv"
REPORT_OUT = OUT / "harps_rv_sampling_alias_report_v2_2.txt"
MANIFEST_OUT = BASE / "data/manifests/harps_rv_sampling_v2_2.json"

OVERSAMPLING = 5
WINDOW_HALF_WIDTH = 0.008
CHUNK_SIZE = 32
MIN_PROMINENCE = 0.001

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

df = pd.read_csv(INPUT)

required = ["tel_object", "representative_bjd"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

df["representative_bjd"] = pd.to_numeric(
    df["representative_bjd"], errors="coerce"
)
df = df.dropna(subset=["tel_object", "representative_bjd"])
df = df[np.isfinite(df["representative_bjd"])].copy()

# Exact frequencies for direct comparison.
aliases = {
    "solar_day": 1.0,
    "sidereal_day": 1.0027379093,
    "half_solar_day": 2.0,
    "half_sidereal_day": 2.0054758186,
    "two_day": 0.5,
    "one_month": 1.0 / 29.53059,
    "one_year": 1.0 / 365.25,
}

# Continuous local search regions.
regions = {
    "two_day_region": (0.5, 0.005),
    "daily_region": (1.0, 0.008),
    "half_day_region": (2.0, 0.008),
    "monthly_region": (1.0 / 29.53059, 0.005),
    "yearly_region": (1.0 / 365.25, 0.005),
}

alias_rows = []
peak_rows = []
report_lines = [
    "HARPS RV SAMPLING ALIAS ANALYSIS V2.2",
    "=" * 72,
    "",
    "Input: one median BJD timestamp per target and BJD-day.",
    "No RV values are used in the spectral-window calculation.",
    "",
    "Exact alias frequencies:",
]

for name, freq in aliases.items():
    report_lines.append(f"{name}: {freq:.10f} cycles/day")

report_lines.extend([
    "",
    "LOCAL PEAK SEARCH",
    f"Frequency oversampling: {OVERSAMPLING}",
    f"Local region half-width: {WINDOW_HALF_WIDTH} cycles/day",
    f"Minimum peak prominence: {MIN_PROMINENCE}",
    "",
])

for target, group in df.groupby("tel_object", sort=True):

    times = np.sort(
        group["representative_bjd"].to_numpy(dtype=float)
    )

    times = np.unique(times)

    if len(times) < 3:
        print(f"SKIP {target}: insufficient sampling points")
        continue

    baseline = float(times[-1] - times[0])

    if baseline <= 0:
        continue

    # Center timestamps to improve numerical stability.
    centered = times - np.mean(times)
    n = len(centered)

    def window_power(frequencies):
        frequencies = np.asarray(frequencies, dtype=float)
        powers = np.empty(len(frequencies), dtype=float)

        for start in range(0, len(frequencies), CHUNK_SIZE):
            freq = frequencies[start:start + CHUNK_SIZE]
            phase = 2.0 * np.pi * freq[:, None] * centered[None, :]
            powers[start:start + len(freq)] = (
                np.abs(np.exp(1j * phase).mean(axis=1)) ** 2
            )

        return powers

    # --------------------------------------------------------
    # Exact alias evaluation
    # --------------------------------------------------------
    for alias_name, frequency in aliases.items():

        power = float(window_power([frequency])[0])

        alias_rows.append({
            "tel_object": target,
            "alias": alias_name,
            "frequency_cycles_per_day": frequency,
            "period_days": 1.0 / frequency,
            "window_power": power,
            "sampling_points": n,
            "baseline_days": baseline,
        })

    # --------------------------------------------------------
    # Local maxima in focused frequency regions
    # --------------------------------------------------------
    frequency_step = 1.0 / (OVERSAMPLING * baseline)
    target_peaks = []

    for region_name, (center, half_width) in regions.items():

        low = max(0.0001, center - half_width)
        high = center + half_width

        frequencies = np.arange(
            low,
            high + frequency_step * 0.5,
            frequency_step
        )

        if len(frequencies) < 3:
            continue

        powers = window_power(frequencies)

        peak_indices, properties = find_peaks(
            powers,
            prominence=MIN_PROMINENCE
        )

        if len(peak_indices) == 0:
            continue

        widths = peak_widths(
            powers,
            peak_indices,
            rel_height=0.5
        )[0]

        prominences = properties["prominences"]

        for j, peak_index in enumerate(peak_indices):

            frequency = float(frequencies[peak_index])
            power = float(powers[peak_index])
            width_frequency = float(widths[j] * frequency_step)

            target_peaks.append({
                "tel_object": target,
                "region": region_name,
                "frequency_cycles_per_day": frequency,
                "period_days": 1.0 / frequency,
                "window_power": power,
                "prominence": float(prominences[j]),
                "width_at_half_prominence_cycles_per_day": width_frequency,
                "sampling_points": n,
                "baseline_days": baseline,
            })

    # Deduplicate peaks from overlapping or nearby search regions.
    target_peaks.sort(
        key=lambda x: x["window_power"],
        reverse=True
    )

    unique_peaks = []

    for peak in target_peaks:
        duplicate = any(
            abs(
                peak["frequency_cycles_per_day"]
                - existing["frequency_cycles_per_day"]
            ) < 3.0 * frequency_step
            for existing in unique_peaks
        )

        if not duplicate:
            unique_peaks.append(peak)

    unique_peaks = unique_peaks[:20]

    for rank, peak in enumerate(unique_peaks, start=1):
        peak["peak_rank"] = rank
        peak_rows.append(peak)

    print(
        f"Processed {target}: "
        f"{n} sampling points, "
        f"{len(unique_peaks)} unique local peaks, "
        f"baseline={baseline:.1f} days"
    )

alias_df = pd.DataFrame(alias_rows)
peak_df = pd.DataFrame(peak_rows)

alias_df.to_csv(ALIAS_OUT, index=False)
peak_df.to_csv(PEAK_OUT, index=False)

# ------------------------------------------------------------
# Human-readable report
# ------------------------------------------------------------
report_lines.extend([
    "EXACT ALIAS POWER COMPARISON",
    "-" * 72,
])

for target, group in alias_df.groupby("tel_object", sort=True):

    values = {
        row["alias"]: row["window_power"]
        for _, row in group.iterrows()
    }

    report_lines.append(
        f"{target}: "
        f"solar={values.get('solar_day', np.nan):.5f}, "
        f"sidereal={values.get('sidereal_day', np.nan):.5f}, "
        f"yearly={values.get('one_year', np.nan):.5f}, "
        f"monthly={values.get('one_month', np.nan):.5f}"
    )

report_lines.extend([
    "",
    "STRONGEST UNIQUE LOCAL PEAKS",
    "-" * 72,
])

for target, group in peak_df.groupby("tel_object", sort=True):

    report_lines.append(f"\n{target}")

    for _, row in group.head(5).iterrows():
        report_lines.append(
            f"Rank {int(row['peak_rank'])}: "
            f"f={row['frequency_cycles_per_day']:.9f} c/d, "
            f"P={row['period_days']:.7f} d, "
            f"power={row['window_power']:.5f}, "
            f"prominence={row['prominence']:.5f}, "
            f"width={row['width_at_half_prominence_cycles_per_day']:.9f}"
        )

report_lines.extend([
    "",
    "INTERPRETATION LIMITATIONS",
    "- Sampling-window peaks are not planetary detections.",
    "- Peak width is measured at half prominence, not absolute half power.",
    "- Frequency-grid resolution depends on the target baseline.",
    "- Exact solar and sidereal aliases are evaluated separately.",
    "- No RV outlier removal or periodogram analysis was performed.",
    "- No raw observations or previous outputs were modified.",
    "",
    "OUTPUT FILES",
    str(ALIAS_OUT),
    str(PEAK_OUT),
    str(REPORT_OUT),
    str(MANIFEST_OUT),
    "",
    "COMPLETED - INPUT DATA UNCHANGED",
])

REPORT_OUT.write_text(
    "\n".join(report_lines),
    encoding="utf-8"
)

manifest = {
    "dataset": "harps_rv_sampling_alias_analysis",
    "version": "2.2.0",
    "input": str(INPUT.relative_to(BASE)),
    "targets": int(alias_df["tel_object"].nunique()),
    "sampling_points": int(df.shape[0]),
    "oversampling": OVERSAMPLING,
    "local_region_half_width": WINDOW_HALF_WIDTH,
    "minimum_peak_prominence": MIN_PROMINENCE,
    "exact_aliases": aliases,
    "outputs": [
        str(ALIAS_OUT.relative_to(BASE)),
        str(PEAK_OUT.relative_to(BASE)),
        str(REPORT_OUT.relative_to(BASE)),
    ],
    "raw_observations_modified": False,
    "planet_detection_performed": False,
}

MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
MANIFEST_OUT.write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8"
)

print("\n===== V2.2 SUMMARY =====")
print("Targets:", alias_df["tel_object"].nunique())
print("Exact alias records:", len(alias_df))
print("Unique local peaks:", len(peak_df))
print("\nSaved:", REPORT_OUT)
print("\nCOMPLETED - INPUT DATA UNCHANGED")
