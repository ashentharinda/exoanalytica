from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd

INPUT = RESULTS_DIR / "phase2_6_pi_men_model_comparison_residuals.csv"
df = pd.read_csv(INPUT)

required = [
    "bjd",
    "instrument_epoch",
    "model_b_residual_ms",
    "model_b_sigma_ms"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df.dropna(subset=required).copy()

for col in ["bjd", "model_b_residual_ms", "model_b_sigma_ms"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=[
    "bjd", "model_b_residual_ms", "model_b_sigma_ms"
])

df = df[df["model_b_sigma_ms"] > 0].copy()

# Published / diagnostic periods in days.
PERIODS = {
    "pi_Men_c": 6.267852,
    "pi_Men_d": 124.64,
    "activity_184d": 184.0
}

def design_matrix(part, selected):
    t = part["bjd"].to_numpy(dtype=float)
    t = t - t.min()

    epochs = part["instrument_epoch"].astype(str).to_numpy()
    unique_epochs = sorted(set(epochs))

    columns = []
    names = []

    # Separate residual zero-point intercepts.
    for epoch in unique_epochs:
        columns.append((epochs == epoch).astype(float))
        names.append(f"offset_{epoch}")

    # Sine and cosine terms for each fixed period.
    for name in selected:
        period = PERIODS[name]
        angle = 2 * np.pi * t / period

        columns.append(np.sin(angle))
        names.append(f"{name}_sin")

        columns.append(np.cos(angle))
        names.append(f"{name}_cos")

    return np.column_stack(columns), names

def fit_model(part, selected):
    y = part["model_b_residual_ms"].to_numpy(dtype=float)
    sigma = part["model_b_sigma_ms"].to_numpy(dtype=float)

    X, names = design_matrix(part, selected)

    Xw = X / sigma[:, None]
    yw = y / sigma

    beta, _, _, _ = np.linalg.lstsq(Xw, yw, rcond=None)

    residual = y - X @ beta
    chi2 = float(np.sum((residual / sigma) ** 2))

    covariance = np.linalg.pinv(Xw.T @ Xw)

    n = len(y)
    k = X.shape[1]

    aic = chi2 + 2 * k
    bic = chi2 + k * np.log(n)

    amplitudes = {}

    for name in selected:
        i = names.index(f"{name}_sin")
        j = names.index(f"{name}_cos")

        a = beta[i]
        b = beta[j]

        amplitude = float(np.sqrt(a*a + b*b))

        if amplitude > 0:
            gradient = np.array([a, b]) / amplitude
            sub_cov = covariance[np.ix_([i, j], [i, j])]
            variance = float(gradient @ sub_cov @ gradient)
            amplitude_error = np.sqrt(max(variance, 0))
        else:
            amplitude_error = np.nan

        amplitudes[name] = (
            amplitude,
            float(amplitude_error)
        )

    return {
        "n": n,
        "k": k,
        "chi2": chi2,
        "aic": aic,
        "bic": bic,
        "amplitudes": amplitudes
    }

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

    if len(part) < 20:
        continue

    null = fit_model(part, [])

    report.append("")
    report.append("=" * 65)
    report.append(f"{epoch}: {len(part)} observations")
    report.append("=" * 65)

    report.append(
        f"Null model: chi2={null['chi2']:.4f}, "
        f"AIC={null['aic']:.4f}, BIC={null['bic']:.4f}"
    )

    model_sets = [
        ["pi_Men_c"],
        ["pi_Men_d"],
        ["activity_184d"],
        ["pi_Men_c", "pi_Men_d"],
        ["pi_Men_c", "pi_Men_d", "activity_184d"]
    ]

    for selected in model_sets:

        result = fit_model(part, selected)

        delta_aic = null["aic"] - result["aic"]
        delta_bic = null["bic"] - result["bic"]

        row = {
            "epoch": epoch,
            "model": "+".join(selected),
            "observations": result["n"],
            "chi2": result["chi2"],
            "AIC": result["aic"],
            "BIC": result["bic"],
            "delta_AIC_vs_null": delta_aic,
            "delta_BIC_vs_null": delta_bic
        }

        for name, (amp, err) in result["amplitudes"].items():
            row[f"{name}_amplitude_ms"] = amp
            row[f"{name}_amplitude_error_ms"] = err

        rows.append(row)

        report.append("")
        report.append(f"Model: {' + '.join(selected)}")
        report.append(f"Chi-square: {result['chi2']:.4f}")
        report.append(f"Delta AIC: {delta_aic:.4f}")
        report.append(f"Delta BIC: {delta_bic:.4f}")

        for name, (amp, err) in result["amplitudes"].items():
            report.append(
                f"{name}: K={amp:.5f} +/- {err:.5f} m/s"
            )

output = pd.DataFrame(rows)

output.to_csv(
    RESULTS_DIR / "phase2_6_pi_men_published_period_validation.csv",
    index=False
)

REPORTS_DIR / "phase2_6_pi_men_published_period_validation_report.txt".write_text(
    "\n".join(report),
    encoding="utf-8"
)

print("\n".join(report))
print("\n===== VALIDATION COMPLETED =====")
print("CSV: phase2_6_pi_men_published_period_validation.csv")
print("REPORT: phase2_6_pi_men_published_period_validation_report.txt")
