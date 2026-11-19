from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd

INPUT = RESULTS_DIR / "phase2_6_pi_men_model_comparison_residuals.csv"

df = pd.read_csv(INPUT)

indicators = [
    "drs_bis_rv",
    "drs_ccf_fwhm",
    "drs_ccf_contrast"
]

required = ["bjd", "instrument_epoch"] + indicators

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

for col in ["bjd"] + indicators:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=required).copy()
df = df.sort_values("bjd")

def fit_linear_model(t, y, period=None):
    """
    Baseline: intercept + linear trend.
    Periodic model: intercept + linear trend + sine + cosine.
    """
    t = np.asarray(t, dtype=float)
    y = np.asarray(y, dtype=float)

    t0 = t - np.mean(t)
    scale = max(np.ptp(t0), 1.0)
    x = t0 / scale

    columns = [
        np.ones(len(t)),
        x
    ]

    if period is not None:
        angle = 2 * np.pi * t0 / period
        columns.extend([
            np.sin(angle),
            np.cos(angle)
        ])

    X = np.column_stack(columns)

    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    residual = y - X @ beta

    rss = float(np.sum(residual ** 2))
    n = len(y)
    k = X.shape[1]

    rss_safe = max(rss, 1e-30)
    bic = n * np.log(rss_safe / n) + k * np.log(n)

    amplitude = np.nan

    if period is not None:
        amplitude = float(np.hypot(beta[2], beta[3]))

    return {
        "rss": rss,
        "bic": bic,
        "amplitude": amplitude
    }

rows = []
report = []

for epoch in ["FULL", "HARPS_PRE", "HARPS_POST"]:

    if epoch == "FULL":
        part = df.copy()
    else:
        part = df[
            df["instrument_epoch"].astype(str).str.upper() == epoch
        ].copy()

    if len(part) < 30:
        continue

    t = part["bjd"].to_numpy(dtype=float)
    t = t - t.min()

    report.append("")
    report.append("=" * 70)
    report.append(f"{epoch} | N={len(part)} | Baseline={np.ptp(t):.2f} days")
    report.append("=" * 70)

    print(f"\n===== {epoch} | N={len(part)} =====")

    for indicator in indicators:

        y = part[indicator].to_numpy(dtype=float)

        # Remove only non-finite values.
        valid = np.isfinite(t) & np.isfinite(y)
        tv = t[valid]
        yv = y[valid]

        if len(yv) < 30:
            continue

        null = fit_linear_model(tv, yv)

        # Dense frequency scan over 150–220 days.
        fmin = 1.0 / 220.0
        fmax = 1.0 / 150.0
        step = 1.0 / (10.0 * np.ptp(tv))

        frequencies = np.arange(fmin, fmax, step)

        if len(frequencies) < 2:
            frequencies = np.linspace(fmin, fmax, 1000)

        candidates = []

        for frequency in frequencies:
            period = 1.0 / frequency
            model = fit_linear_model(tv, yv, period)

            delta_bic = null["bic"] - model["bic"]

            candidates.append({
                "period": period,
                "delta_bic": delta_bic,
                "amplitude": model["amplitude"],
                "rss": model["rss"]
            })

        best = max(candidates, key=lambda x: x["delta_bic"])

        fixed = fit_linear_model(tv, yv, 184.0)
        fixed_delta_bic = null["bic"] - fixed["bic"]

        row = {
            "epoch": epoch,
            "indicator": indicator,
            "observations": len(yv),
            "baseline_days": float(np.ptp(tv)),
            "best_period_150_220d": best["period"],
            "best_period_delta_BIC": best["delta_bic"],
            "best_period_amplitude": best["amplitude"],
            "fixed_184d_delta_BIC": fixed_delta_bic,
            "fixed_184d_amplitude": fixed["amplitude"],
            "null_BIC": null["bic"]
        }

        rows.append(row)

        line = (
            f"{indicator}: "
            f"Best P={best['period']:.3f} d | "
            f"Best DeltaBIC={best['delta_bic']:.3f} | "
            f"Amplitude={best['amplitude']:.5f} | "
            f"184d DeltaBIC={fixed_delta_bic:.3f}"
        )

        print(line)
        report.append(line)

output = pd.DataFrame(rows)

output.to_csv(
    RESULTS_DIR / "phase2_6_pi_men_detrended_activity_validation.csv",
    index=False
)

REPORTS_DIR / "phase2_6_pi_men_detrended_activity_report.txt".write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\n===== DETRENDED ACTIVITY VALIDATION COMPLETE =====")
print("CSV: phase2_6_pi_men_detrended_activity_validation.csv")
print("REPORT: phase2_6_pi_men_detrended_activity_report.txt")
