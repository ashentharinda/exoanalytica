from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import lombscargle, find_peaks

INPUT = Path("phase2_6_pi_men_model_comparison_residuals.csv")

df = pd.read_csv(INPUT)
df = df.dropna(
    subset=["bjd", "instrument_epoch", "model_b_residual_ms"]
).copy()

df["bjd"] = pd.to_numeric(df["bjd"], errors="coerce")
df["model_b_residual_ms"] = pd.to_numeric(
    df["model_b_residual_ms"], errors="coerce"
)
df = df.dropna(
    subset=["bjd", "model_b_residual_ms"]
).sort_values("bjd")

baseline = df["bjd"].max() - df["bjd"].min()

freq = np.arange(
    1.0 / 1000.0,
    1.0 / 2.0,
    1.0 / (10.0 * baseline)
)

def spectral_window(t):
    t = t - t.min()
    return np.abs(
        np.mean(
            np.exp(-2j * np.pi * np.outer(freq, t)),
            axis=1
        )
    ) ** 2

def periodogram(t, y):
    t = t - t.min()
    y = y - np.mean(y)

    return lombscargle(
        t,
        y,
        2 * np.pi * freq,
        precenter=False,
        normalize=True
    )

def top_peaks(power, count=15):
    indices, _ = find_peaks(power)

    if len(indices) == 0:
        indices = np.array([np.argmax(power)])

    ranked = indices[np.argsort(power[indices])[::-1]]
    selected = []

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

results = []
reports = []

for epoch in ["HARPS_PRE", "HARPS_POST", "FULL"]:

    if epoch == "FULL":
        part = df.copy()
    else:
        part = df[
            df["instrument_epoch"].astype(str).str.upper() == epoch
        ].copy()

    t = part["bjd"].to_numpy(dtype=float)
    y = part["model_b_residual_ms"].to_numpy(dtype=float)

    if len(part) < 20:
        print(f"Skipping {epoch}: insufficient data")
        continue

    window = spectral_window(t)
    power = periodogram(t, y)

    indices = top_peaks(power)

    print(f"\n===== {epoch} =====")
    print(f"Observations: {len(part)}")
    print(f"Baseline: {np.ptp(t):.3f} days")

    reports.append(
        f"\n{epoch}\nObservations: {len(part)}"
        f"\nBaseline: {np.ptp(t):.3f} days"
    )

    for rank, idx in enumerate(indices, 1):

        row = {
            "epoch": epoch,
            "rank": rank,
            "period_days": 1.0 / freq[idx],
            "residual_power": power[idx],
            "epoch_window_power": window[idx],
            "observations": len(part),
            "baseline_days": np.ptp(t),
        }

        results.append(row)

        line = (
            f"{rank:2d}. P={row['period_days']:.3f} d | "
            f"Residual={power[idx]:.6f} | "
            f"Window={window[idx]:.6f}"
        )

        print(line)
        reports.append(line)

output = pd.DataFrame(results)

output.to_csv(
    "phase2_6_pi_men_epoch_specific_alias_analysis.csv",
    index=False
)

Path(
    "phase2_6_pi_men_epoch_specific_alias_report.txt"
).write_text(
    "\n".join(reports),
    encoding="utf-8"
)

print("\n===== ANALYSIS COMPLETE =====")
print("Output: phase2_6_pi_men_epoch_specific_alias_analysis.csv")
print("Report: phase2_6_pi_men_epoch_specific_alias_report.txt")
