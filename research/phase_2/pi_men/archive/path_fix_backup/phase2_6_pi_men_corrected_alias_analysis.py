from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import lombscargle, find_peaks

# ============================================================
# PHASE 2.6 — CORRECTED SAMPLING WINDOW & ALIAS ANALYSIS
# Read-only research diagnostic
# ============================================================

BASE = RESULTS_DIR
INPUT = BASE / "phase2_6_pi_men_model_comparison_residuals.csv"

if not INPUT.exists():
    raise FileNotFoundError(f"Input file not found: {INPUT.resolve()}")

df = pd.read_csv(INPUT)

required = [
    "bjd",
    "instrument_epoch",
    "model_b_residual_ms",
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df = df.dropna(subset=required).copy()
df["bjd"] = pd.to_numeric(df["bjd"], errors="coerce")
df["model_b_residual_ms"] = pd.to_numeric(
    df["model_b_residual_ms"], errors="coerce"
)
df = df.dropna(subset=["bjd", "model_b_residual_ms"])

df = df.sort_values("bjd").reset_index(drop=True)

# Relative time improves numerical stability.
t_all = df["bjd"].to_numpy(dtype=float)
t_all = t_all - t_all.min()

y_all = df["model_b_residual_ms"].to_numpy(dtype=float)

baseline = float(np.ptp(t_all))
n = len(df)

if n < 20 or baseline <= 0:
    raise ValueError("Insufficient observations or invalid time baseline.")

# Frequency range: periods from 2 to 1000 days.
min_period = 2.0
max_period = 1000.0

min_frequency = 1.0 / max_period
max_frequency = 1.0 / min_period

# Oversampling factor 10 relative to 1 / baseline.
frequency_step = 1.0 / (10.0 * baseline)

frequencies = np.arange(
    min_frequency,
    max_frequency,
    frequency_step
)

periods = 1.0 / frequencies

print("\n===== DATA SUMMARY =====")
print(f"Observations: {n}")
print(f"Baseline: {baseline:.3f} days")
print(f"Frequency points: {len(frequencies)}")
print(f"Frequency step: {frequency_step:.10f} cycles/day")

# ------------------------------------------------------------
# Correct Fourier spectral window:
# W(f) = |sum(exp(-2*pi*i*f*t)) / N|^2
# ------------------------------------------------------------

def calculate_window(times, freq):
    times = np.asarray(times, dtype=float)
    times = times - np.min(times)

    phase = np.exp(
        -2j * np.pi * np.outer(freq, times)
    )

    return np.abs(np.mean(phase, axis=1)) ** 2


# ------------------------------------------------------------
# Lomb-Scargle residual periodogram
# ------------------------------------------------------------

def calculate_periodogram(times, values, freq):
    times = np.asarray(times, dtype=float)
    values = np.asarray(values, dtype=float)

    times = times - np.min(times)
    values = values - np.mean(values)

    angular_frequency = 2.0 * np.pi * freq

    power = lombscargle(
        times,
        values,
        angular_frequency,
        precenter=False,
        normalize=True
    )

    return power


def get_top_peaks(freq, power, count=15):
    peak_indices, _ = find_peaks(power)

    if len(peak_indices) == 0:
        peak_indices = np.array([int(np.argmax(power))])

    ranked = peak_indices[
        np.argsort(power[peak_indices])[::-1]
    ]

    selected = []

    # Keep peaks separated by at least 0.5% in frequency.
    for idx in ranked:
        f = freq[idx]

        if all(
            abs(f - freq[old]) / f > 0.005
            for old in selected
        ):
            selected.append(idx)

        if len(selected) >= count:
            break

    return selected


# ------------------------------------------------------------
# Full-data sampling window
# ------------------------------------------------------------

window_power = calculate_window(t_all, frequencies)

window_indices = get_top_peaks(
    frequencies,
    window_power,
    count=20
)

window_rows = []

for rank, idx in enumerate(window_indices, start=1):
    window_rows.append({
        "rank": rank,
        "period_days": 1.0 / frequencies[idx],
        "frequency": frequencies[idx],
        "window_power": window_power[idx],
    })

window_df = pd.DataFrame(window_rows)

window_df.to_csv(
    RESULTS_DIR / "phase2_6_pi_men_corrected_sampling_window.csv",
    index=False
)

# ------------------------------------------------------------
# Full, PRE and POST residual periodograms
# ------------------------------------------------------------

periodogram_rows = []
peak_summary = {}

epochs = ["FULL", "PRE", "POST"]

for epoch in epochs:

    if epoch == "FULL":
        subset = df.copy()
    else:
        subset = df[
            df["instrument_epoch"].astype(str).str.upper() == epoch
        ].copy()

    if len(subset) < 20:
        print(f"Skipping {epoch}: insufficient observations.")
        continue

    times = subset["bjd"].to_numpy(dtype=float)
    times -= times.min()

    values = subset["model_b_residual_ms"].to_numpy(dtype=float)

    power = calculate_periodogram(
        times,
        values,
        frequencies
    )

    indices = get_top_peaks(
        frequencies,
        power,
        count=20
    )

    rows = []

    for rank, idx in enumerate(indices, start=1):

        period = 1.0 / frequencies[idx]

        # Compare residual peak against full-data window.
        window_idx = int(
            np.argmin(np.abs(frequencies - frequencies[idx]))
        )

        row = {
            "epoch": epoch,
            "rank": rank,
            "period_days": period,
            "frequency": frequencies[idx],
            "residual_power": power[idx],
            "full_sampling_window_power": window_power[window_idx],
            "observations": len(subset),
        }

        rows.append(row)
        periodogram_rows.append(row)

    peak_summary[epoch] = rows

    print(f"\n===== {epoch} TOP RESIDUAL PEAKS =====")

    for row in rows[:10]:
        print(
            f"{row['rank']:2d}. "
            f"P={row['period_days']:10.3f} d | "
            f"Power={row['residual_power']:.6f} | "
            f"Window={row['full_sampling_window_power']:.6f}"
        )


periodogram_df = pd.DataFrame(periodogram_rows)

periodogram_df.to_csv(
    RESULTS_DIR / "phase2_6_pi_men_corrected_residual_periodograms.csv",
    index=False
)

# ------------------------------------------------------------
# Compare known candidate periods against sampling window
# ------------------------------------------------------------

candidate_periods = [
    6.267852,
    62.0,
    73.0,
    81.0,
    105.0,
    120.0,
    125.0,
    178.0,
    182.0,
    250.0,
    364.0,
    421.0,
    889.0,
]

alias_rows = []

for candidate in candidate_periods:

    frequency = 1.0 / candidate
    idx = int(np.argmin(np.abs(frequencies - frequency)))

    alias_rows.append({
        "candidate_period_days": candidate,
        "nearest_grid_period_days": 1.0 / frequencies[idx],
        "sampling_window_power": window_power[idx],
        "full_residual_power": (
            peak_summary["FULL"][0]["residual_power"]
            if False else np.nan
        ),
    })

alias_df = pd.DataFrame(alias_rows)

# Add actual FULL residual power at each candidate frequency.
if "FULL" in peak_summary:
    full_subset = df.copy()
    full_t = full_subset["bjd"].to_numpy(dtype=float)
    full_t -= full_t.min()

    full_y = full_subset["model_b_residual_ms"].to_numpy(dtype=float)

    full_power = calculate_periodogram(
        full_t,
        full_y,
        frequencies
    )

    for i, row in alias_df.iterrows():
        idx = int(
            np.argmin(
                np.abs(
                    frequencies - 1.0 / row["candidate_period_days"]
                )
            )
        )
        alias_df.loc[i, "full_residual_power"] = full_power[idx]

alias_df.to_csv(
    RESULTS_DIR / "phase2_6_pi_men_alias_candidate_comparison.csv",
    index=False
)

# ------------------------------------------------------------
# Save report
# ------------------------------------------------------------

report = []

report.append("PHASE 2.6 — CORRECTED SAMPLING WINDOW & ALIAS ANALYSIS")
report.append("=" * 65)
report.append(f"Input: {INPUT}")
report.append(f"Observations: {n}")
report.append(f"Baseline: {baseline:.4f} days")
report.append(f"Frequency grid points: {len(frequencies)}")
report.append(f"Frequency step: {frequency_step:.10f} cycles/day")
report.append("Sampling window: complex Fourier window function")
report.append("")

report.append("CORRECTED SAMPLING WINDOW — TOP PEAKS")
report.append("-" * 65)

for row in window_rows:
    report.append(
        f"{row['rank']:2d}. "
        f"{row['period_days']:.4f} days | "
        f"Window power={row['window_power']:.6f}"
    )

for epoch in epochs:
    if epoch not in peak_summary:
        continue

    report.append("")
    report.append(f"{epoch} RESIDUAL PERIODOGRAM")
    report.append("-" * 65)

    for row in peak_summary[epoch][:15]:
        report.append(
            f"{row['rank']:2d}. "
            f"{row['period_days']:.4f} days | "
            f"Residual power={row['residual_power']:.6f} | "
            f"Window power={row['full_sampling_window_power']:.6f}"
        )

report.append("")
report.append("ALIAS CANDIDATE COMPARISON")
report.append("-" * 65)

for _, row in alias_df.iterrows():
    report.append(
        f"Candidate={row['candidate_period_days']:.3f} d | "
        f"Window={row['sampling_window_power']:.6f} | "
        f"Residual={row['full_residual_power']:.6f}"
    )

report.append("")
report.append("SCIENTIFIC LIMITATIONS")
report.append("-" * 65)
report.append(
    "A peak near a sampling-window peak may indicate an alias, "
    "but proximity alone does not prove alias contamination."
)
report.append(
    "This diagnostic does not establish a new planet or validate "
    "a residual signal."
)
report.append(
    "The PRE and POST datasets have different time coverage; "
    "their periodograms must be interpreted cautiously."
)
report.append(
    "No false-alarm probability is calculated in this script."
)

REPORTS_DIR / "phase2_6_pi_men_corrected_alias_analysis_report.txt".write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\n===== OUTPUT FILES =====")
print("phase2_6_pi_men_corrected_sampling_window.csv")
print("phase2_6_pi_men_corrected_residual_periodograms.csv")
print("phase2_6_pi_men_alias_candidate_comparison.csv")
print("phase2_6_pi_men_corrected_alias_analysis_report.txt")

print("\n===== ANALYSIS COMPLETED =====")
