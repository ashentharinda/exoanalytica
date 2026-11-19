from pathlib import Path
import numpy as np
import pandas as pd
from scipy.signal import lombscargle, find_peaks
from scipy.stats import pearsonr, spearmanr

INPUT = Path("phase2_6_pi_men_model_comparison_residuals.csv")

df = pd.read_csv(INPUT)

indicators = [
    "drs_bis_rv",
    "drs_ccf_fwhm",
    "drs_ccf_contrast"
]

required = [
    "bjd",
    "instrument_epoch",
    "model_b_residual_ms",
    *indicators
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

for col in ["bjd", "model_b_residual_ms", *indicators]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

periods = {
    "pi_Men_c": 6.267852,
    "pi_Men_d": 124.64,
    "activity_184d": 184.0
}

baseline = df["bjd"].max() - df["bjd"].min()

freq = np.arange(
    1.0 / 1000.0,
    1.0 / 2.0,
    1.0 / (10.0 * baseline)
)

rows = []
report = []

epochs = ["FULL", "HARPS_PRE", "HARPS_POST"]

for epoch in epochs:

    if epoch == "FULL":
        part = df.copy()
    else:
        part = df[
            df["instrument_epoch"].astype(str).str.upper() == epoch
        ].copy()

    part = part.dropna(
        subset=["bjd", "model_b_residual_ms", *indicators]
    )

    if len(part) < 30:
        continue

    t = part["bjd"].to_numpy(dtype=float)
    t = t - t.min()

    residual = part["model_b_residual_ms"].to_numpy(dtype=float)
    residual = residual - np.mean(residual)

    report.append("")
    report.append("=" * 65)
    report.append(f"{epoch} | N={len(part)}")
    report.append("=" * 65)

    print(f"\n===== {epoch} | N={len(part)} =====")

    for indicator in indicators:

        values = part[indicator].to_numpy(dtype=float)
        values = values - np.mean(values)

        power = lombscargle(
            t,
            values,
            2 * np.pi * freq,
            precenter=False,
            normalize=True
        )

        peak_mask = (
            (1.0 / freq >= 150.0) &
            (1.0 / freq <= 220.0)
        )

        candidate_indices = np.where(peak_mask)[0]
        best_idx = candidate_indices[
            np.argmax(power[peak_mask])
        ]

        best_period = 1.0 / freq[best_idx]
        best_power = power[best_idx]

        # Exact-period indicator powers.
        exact_powers = {}

        for name, period in periods.items():
            exact_freq = 1.0 / period

            exact_power = lombscargle(
                t,
                values,
                np.array([2 * np.pi * exact_freq]),
                precenter=False,
                normalize=True
            )[0]

            exact_powers[name] = float(exact_power)

        # Residual-indicator correlation.
        pearson = pearsonr(residual, values)
        spearman = spearmanr(residual, values)

        row = {
            "epoch": epoch,
            "indicator": indicator,
            "observations": len(part),
            "best_150_220d_period": best_period,
            "best_150_220d_power": best_power,
            "power_6.267852d": exact_powers["pi_Men_c"],
            "power_124.64d": exact_powers["pi_Men_d"],
            "power_184d": exact_powers["activity_184d"],
            "pearson_r": pearson.statistic,
            "pearson_p": pearson.pvalue,
            "spearman_r": spearman.statistic,
            "spearman_p": spearman.pvalue
        }

        rows.append(row)

        line = (
            f"{indicator}: "
            f"best 150-220d={best_period:.3f}d "
            f"(power={best_power:.5f}) | "
            f"P184 power={exact_powers['activity_184d']:.5f} | "
            f"Pearson r={pearson.statistic:.4f}"
        )

        print(line)
        report.append(line)

output = pd.DataFrame(rows)

output.to_csv(
    "phase2_6_pi_men_activity_indicator_validation.csv",
    index=False
)

Path(
    "phase2_6_pi_men_activity_indicator_report.txt"
).write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\n===== ACTIVITY VALIDATION COMPLETE =====")
print("CSV: phase2_6_pi_men_activity_indicator_validation.csv")
print("REPORT: phase2_6_pi_men_activity_indicator_report.txt")
