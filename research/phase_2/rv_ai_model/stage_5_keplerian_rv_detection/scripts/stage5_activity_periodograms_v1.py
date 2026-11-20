from pathlib import Path
import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle
from scipy.signal import find_peaks

ROOT = Path("research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection")

INPUT = ROOT / "data/input/harps_rv_observations_18_targets.csv"
GLS_DIR = ROOT / "experiments/HD115617_gls_v1"
GLS_GRID = GLS_DIR / "periodogram.csv"

OUT = ROOT / "experiments/HD115617_activity_v1"

if OUT.exists():
    raise FileExistsError(
        f"Output directory already exists: {OUT}. Nothing overwritten."
    )

if not INPUT.exists() or not GLS_GRID.exists():
    raise FileNotFoundError("Required input or original GLS grid is missing.")

df = pd.read_csv(INPUT)

target = df.loc[
    df["tel_object"].astype(str).str.contains(
        "HD115617", case=False, na=False
    )
].copy()

if len(target) != 1213:
    raise ValueError(f"Expected 1213 observations; found {len(target)}")

time = pd.to_numeric(target["drs_bjd"], errors="coerce").to_numpy()
time = time - np.nanmin(time)

grid = pd.read_csv(GLS_GRID)

freq_col = next(
    (c for c in grid.columns if c.lower() in
     ["frequency_per_day", "frequency", "frequency_day"]),
    None
)

if freq_col is None:
    raise ValueError(f"Frequency column not found: {grid.columns.tolist()}")

frequency = pd.to_numeric(
    grid[freq_col], errors="coerce"
).to_numpy()

frequency = frequency[np.isfinite(frequency) & (frequency > 0)]
frequency = np.unique(frequency)

if len(frequency) < 100:
    raise ValueError("Insufficient frequency grid.")

indicators = [
    "drs_bis_span",
    "drs_ccf_fwhm",
    "drs_ccf_contrast",
    "drs_ccf_noise",
]

OUT.mkdir(parents=True)

summary = []
candidate_periods = [
    4.2142, 38.0511, 42.5335,
    123.6661, 185.9641
]

print("\n===== ACTIVITY PERIODogram DIAGNOSTICS =====")
print("Target: HD115617")
print("Observations:", len(target))
print("Frequency samples:", len(frequency))

for column in indicators:
    y = pd.to_numeric(
        target[column], errors="coerce"
    ).to_numpy()

    valid = np.isfinite(time) & np.isfinite(y)

    if valid.sum() < 100:
        print("SKIPPED:", column, "- insufficient valid observations")
        continue

    t = time[valid]
    values = y[valid]

    # Remove only the constant offset. No clipping or outlier rejection.
    values = values - np.mean(values)

    ls = LombScargle(
        t,
        values,
        fit_mean=True,
        center_data=True,
        nterms=1
    )

    power = ls.power(
        frequency,
        method="fast",
        normalization="standard"
    )

    periods = 1.0 / frequency

    result = pd.DataFrame({
        "frequency_per_day": frequency,
        "period_days": periods,
        "power": power
    }).sort_values("frequency_per_day")

    result.to_csv(
        OUT / f"{column}_periodogram.csv",
        index=False
    )

    peaks, _ = find_peaks(power)

    peak_table = pd.DataFrame({
        "frequency_per_day": frequency[peaks],
        "period_days": periods[peaks],
        "power": power[peaks]
    }).sort_values("power", ascending=False).head(15)

    peak_table.insert(
        0, "rank", range(1, len(peak_table) + 1)
    )

    peak_table.to_csv(
        OUT / f"{column}_top_peaks.csv",
        index=False
    )

    max_idx = np.argmax(power)

    row = {
        "indicator": column,
        "valid_observations": int(valid.sum()),
        "highest_period_days": float(periods[max_idx]),
        "highest_power": float(power[max_idx])
    }

    for p in candidate_periods:
        idx = np.argmin(np.abs(frequency - 1.0 / p))
        row[f"power_near_{p}_days"] = float(power[idx])

    summary.append(row)

    print(f"\n{column}")
    print("Highest period:", f"{periods[max_idx]:.6f} days")
    print("Highest power:", f"{power[max_idx]:.8f}")

summary_df = pd.DataFrame(summary)
summary_df.to_csv(OUT / "activity_comparison_summary.csv", index=False)

print("\n===== CANDIDATE PERIOD COMPARISON =====")
print(summary_df.to_string(index=False))

print("\n===== OUTPUT DIRECTORY =====")
print(OUT.resolve())

print("\nACTIVITY PERIODogram DIAGNOSTICS COMPLETED")
