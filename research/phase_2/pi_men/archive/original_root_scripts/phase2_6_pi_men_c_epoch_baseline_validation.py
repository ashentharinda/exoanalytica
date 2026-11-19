from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import chi2

INPUT = Path("phase2_6_pi_men_c_incremental_residuals.csv")
OUTPUT = Path("phase2_6_pi_men_c_epoch_baseline_validation.txt")

P_C = 6.267852

JITTER = {
    "HARPS_PRE": 3.17160032,
    "HARPS_POST": 2.49151128,
}

df = pd.read_csv(INPUT)

required = [
    "bjd", "baseline_residual_ms",
    "rv_error_ms", "instrument_epoch"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df.dropna(subset=required).copy()
df = df.sort_values("bjd").reset_index(drop=True)

results = []

for epoch in ["HARPS_PRE", "HARPS_POST"]:
    sub = df[df["instrument_epoch"] == epoch]

    t = sub["bjd"].to_numpy(dtype=float)
    y = sub["baseline_residual_ms"].to_numpy(dtype=float)
    dy = sub["rv_error_ms"].to_numpy(dtype=float)

    sigma = np.sqrt(dy**2 + JITTER[epoch]**2)
    weights = 1.0 / sigma**2

    angle = 2.0 * np.pi * t / P_C

    X0 = np.ones((len(t), 1))
    X1 = np.column_stack([
        np.ones(len(t)),
        np.sin(angle),
        np.cos(angle)
    ])

    def fit(X):
        sw = np.sqrt(weights)
        Xw = X * sw[:, None]
        yw = y * sw

        beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)
        residual = y - X @ beta
        value = np.sum(weights * residual**2)
        covariance = np.linalg.inv(Xw.T @ Xw)

        return beta, residual, value, covariance

    b0, r0, chi0, cov0 = fit(X0)
    b1, r1, chi1, cov1 = fit(X1)

    amplitude = np.hypot(b1[1], b1[2])
    phase = np.arctan2(b1[2], b1[1])

    if amplitude > 0:
        grad = np.array([b1[1], b1[2]]) / amplitude
        amplitude_error = np.sqrt(
            max(0.0, grad @ cov1[1:3, 1:3] @ grad)
        )
    else:
        amplitude_error = float("nan")

    n = len(y)
    delta_chi = chi0 - chi1
    delta_bic = (chi1 + 3*np.log(n)) - (chi0 + np.log(n))

    results.append([
        epoch, n, t.max()-t.min(),
        amplitude, amplitude_error, phase,
        delta_chi, chi2.sf(max(0, delta_chi), 2),
        delta_bic,
        np.sqrt(np.mean(r0**2)),
        np.sqrt(np.mean(r1**2))
    ])

lines = [
    "PI MEN C - PRE/POST BASELINE RESIDUAL VALIDATION",
    "=" * 65,
    "Signal fitted to baseline_residual_ms.",
    "Common global relative-BJD reference used.",
    "Fixed period: 6.267852 days",
    ""
]

for r in results:
    lines += [
        "-" * 65,
        f"Epoch: {r[0]}",
        f"Observations: {r[1]}",
        f"Baseline days: {r[2]:.3f}",
        f"Amplitude: {r[3]:.6f} +/- {r[4]:.6f} m/s",
        f"Global phase: {r[5]:.6f} rad",
        f"Delta chi-square: {r[6]:.6f}",
        f"Approx p-value: {r[7]:.6g}",
        f"Delta BIC: {r[8]:.6f}",
        f"RMS null: {r[9]:.6f} m/s",
        f"RMS with c: {r[10]:.6f} m/s",
        ""
    ]

lines += [
    "CAVEATS:",
    "- Conditional fits after fixed b baseline.",
    "- Does not refit b orbital parameters.",
    "- Approximate p-values ignore correlated noise and parameter uncertainty.",
    "- Not a planet confirmation."
]

OUTPUT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print(f"\nReport saved: {OUTPUT.resolve()}")
