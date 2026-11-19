import numpy as np
import pandas as pd
from pathlib import Path
from scipy.signal import lombscargle, find_peaks

INPUT = Path("phase2_6_pi_men_model_comparison_residuals.csv")

df = pd.read_csv(INPUT)

required = [
    "bjd",
    "model_b_residual_ms",
    "rv_error_ms",
    "instrument_epoch"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df = df[
    np.isfinite(df["bjd"]) &
    np.isfinite(df["model_b_residual_ms"]) &
    np.isfinite(df["rv_error_ms"]) &
    (df["rv_error_ms"] > 0)
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

# Frequency grid
baseline = np.ptp(df["bjd"].to_numpy())
min_period = 2.0
max_period = min(1000.0, baseline)

frequencies = np.linspace(
    1.0 / max_period,
    1.0 / min_period,
    4000
)

angular_frequencies = 2 * np.pi * frequencies

def calculate_periodogram(times, values):
    times = np.asarray(times, dtype=float)
    values = np.asarray(values, dtype=float)

    values = values - np.mean(values)

    if len(times) < 20 or np.ptp(times) < 30:
        return None

    power = lombscargle(
        times,
        values,
        angular_frequencies,
        normalize=True
    )

    return power

def extract_peaks(power, label):
    if power is None:
        return []

    peak_indices, _ = find_peaks(power, distance=8)

    if len(peak_indices) == 0:
        peak_indices = np.array([np.argmax(power)])

    peak_indices = sorted(
        peak_indices,
        key=lambda i: power[i],
        reverse=True
    )

    results = []

    for idx in peak_indices[:10]:
        results.append({
            "dataset": label,
            "period_days": 1.0 / frequencies[idx],
            "power": power[idx]
        })

    return results

times = df["bjd"].to_numpy()
residuals = df["model_b_residual_ms"].to_numpy()

print("\n===== RESIDUAL SIGNAL VERIFICATION =====")
print("Observations:", len(df))
print("Baseline days:", baseline)
print("Frequency grid:", len(frequencies))

# Full dataset periodogram
full_power = calculate_periodogram(times, residuals)

# PRE and POST periodograms
pre = df[df["instrument_epoch"] == "HARPS_PRE"]
post = df[df["instrument_epoch"] == "HARPS_POST"]

pre_power = calculate_periodogram(
    pre["bjd"].to_numpy(),
    pre["model_b_residual_ms"].to_numpy()
)

post_power = calculate_periodogram(
    post["bjd"].to_numpy(),
    post["model_b_residual_ms"].to_numpy()
)

peak_rows = []
peak_rows += extract_peaks(full_power, "FULL")
peak_rows += extract_peaks(pre_power, "HARPS_PRE")
peak_rows += extract_peaks(post_power, "HARPS_POST")

peak_table = pd.DataFrame(peak_rows)

# Sampling window function
window_values = np.ones(len(times))

window_power = lombscargle(
    times,
    window_values,
    angular_frequencies,
    normalize=True
)

window_rows = extract_peaks(window_power, "SAMPLING_WINDOW")
window_table = pd.DataFrame(window_rows)

# Permutation FAP for the strongest full-dataset peak.
# This is an exploratory unweighted permutation test.
rng = np.random.default_rng(42)
observed_max = float(np.max(full_power))

bootstrap_count = 300
exceedances = 0

print("\nRunning permutation FAP test...")
print("Bootstrap iterations:", bootstrap_count)

for i in range(bootstrap_count):
    shuffled = rng.permutation(residuals)
    shuffled -= np.mean(shuffled)

    simulated_power = lombscargle(
        times,
        shuffled,
        angular_frequencies,
        normalize=True
    )

    if np.max(simulated_power) >= observed_max:
        exceedances += 1

    if (i + 1) % 50 == 0:
        print(f"Completed {i+1}/{bootstrap_count}")

fap = (exceedances + 1) / (bootstrap_count + 1)

# Correlations with available activity indicators
indicator_rows = []

indicator_candidates = [
    c for c in df.columns
    if any(token in c.lower() for token in [
        "bis", "fwhm", "contrast", "activity", "ha"
    ])
]

for col in indicator_candidates:
    values = pd.to_numeric(df[col], errors="coerce")
    valid = np.isfinite(values) & np.isfinite(residuals)

    if valid.sum() < 20 or values[valid].nunique() < 2:
        continue

    pearson = np.corrcoef(
        residuals[valid],
        values[valid]
    )[0, 1]

    spearman = pd.Series(residuals[valid]).corr(
        pd.Series(values[valid]),
        method="spearman"
    )

    indicator_rows.append({
        "indicator": col,
        "valid_count": int(valid.sum()),
        "pearson_r": pearson,
        "spearman_r": spearman
    })

indicator_table = pd.DataFrame(indicator_rows)

# Save outputs
peak_file = Path("phase2_6_pi_men_epoch_periodograms.csv")
window_file = Path("phase2_6_pi_men_sampling_window_peaks.csv")
indicator_file = Path("phase2_6_pi_men_activity_correlations.csv")
report_file = Path("phase2_6_pi_men_residual_verification_report.txt")

peak_table.to_csv(peak_file, index=False)
window_table.to_csv(window_file, index=False)
indicator_table.to_csv(indicator_file, index=False)

lines = [
    "PI MEN RESIDUAL SIGNAL VERIFICATION",
    "=" * 65,
    f"Observations: {len(df)}",
    f"HARPS PRE observations: {len(pre)}",
    f"HARPS POST observations: {len(post)}",
    f"Baseline days: {baseline:.6f}",
    f"Frequency grid points: {len(frequencies)}",
    "",
    "FULL DATA RESIDUAL PERIODOGRAM",
]

for _, row in peak_table[peak_table["dataset"] == "FULL"].iterrows():
    lines.append(
        f"Period: {row['period_days']:.6f} d | "
        f"Power: {row['power']:.8f}"
    )

lines.extend(["", "HARPS PRE PERIODOGRAM"])

for _, row in peak_table[peak_table["dataset"] == "HARPS_PRE"].iterrows():
    lines.append(
        f"Period: {row['period_days']:.6f} d | "
        f"Power: {row['power']:.8f}"
    )

lines.extend(["", "HARPS POST PERIODOGRAM"])

for _, row in peak_table[peak_table["dataset"] == "HARPS_POST"].iterrows():
    lines.append(
        f"Period: {row['period_days']:.6f} d | "
        f"Power: {row['power']:.8f}"
    )

lines.extend([
    "",
    "SAMPLING WINDOW PEAKS"
])

for _, row in window_table.iterrows():
    lines.append(
        f"Period: {row['period_days']:.6f} d | "
        f"Power: {row['power']:.8f}"
    )

lines.extend([
    "",
    "PERMUTATION FALSE ALARM PROBABILITY",
    f"Observed maximum power: {observed_max:.8f}",
    f"Bootstrap iterations: {bootstrap_count}",
    f"Exceedances: {exceedances}",
    f"Estimated permutation FAP: {fap:.8f}",
    "",
    "ACTIVITY INDICATOR CORRELATIONS"
])

if len(indicator_table):
    for _, row in indicator_table.iterrows():
        lines.append(
            f"{row['indicator']}: "
            f"n={row['valid_count']}, "
            f"Pearson={row['pearson_r']:.6f}, "
            f"Spearman={row['spearman_r']:.6f}"
        )
else:
    lines.append("No usable activity indicator columns detected.")

lines.extend([
    "",
    "SCIENTIFIC LIMITATIONS",
    "- Periodograms are unweighted exploratory diagnostics.",
    "- PRE and POST have different time coverage and sampling.",
    "- Permutation FAP is approximate and assumes exchangeable residuals.",
    "- A low FAP does not establish a planetary origin.",
    "- Sampling-window peaks require direct alias investigation.",
    "- Activity correlations do not establish causation.",
    "- No additional planet detection is claimed."
])

report_file.write_text("\n".join(lines), encoding="utf-8")

print("\n===== TOP PERIODS BY DATASET =====")
print(peak_table.to_string(index=False))

print("\n===== SAMPLING WINDOW PEAKS =====")
print(window_table.to_string(index=False))

print("\n===== PERMUTATION FAP =====")
print(f"Observed maximum power: {observed_max:.6f}")
print(f"Estimated FAP: {fap:.6f}")

print("\n===== ACTIVITY CORRELATIONS =====")
if len(indicator_table):
    print(indicator_table.to_string(index=False))
else:
    print("No usable indicators detected.")

print("\nSaved:", peak_file.resolve())
print("Saved:", window_file.resolve())
print("Saved:", indicator_file.resolve())
print("Report:", report_file.resolve())
print("\n===== RESIDUAL VERIFICATION COMPLETE =====")
