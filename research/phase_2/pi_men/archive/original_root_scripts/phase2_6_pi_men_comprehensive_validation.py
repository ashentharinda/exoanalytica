from pathlib import Path
import numpy as np
import pandas as pd

INPUT = Path("phase2_6_pi_men_model_comparison_residuals.csv")

P_C = 6.267852
P_D = 124.64
P_ACTIVITY = 184.0

OUTPUT_CSV = Path("phase2_6_pi_men_comprehensive_validation.csv")
OUTPUT_REPORT = Path("phase2_6_pi_men_comprehensive_validation.txt")

print("Loading residual dataset...")
df = pd.read_csv(INPUT)

required = [
    "bjd",
    "instrument_epoch",
    "model_b_residual_ms",
    "model_b_sigma_ms"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

for col in ["bjd", "model_b_residual_ms", "model_b_sigma_ms"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["instrument_epoch"] = (
    df["instrument_epoch"].astype(str).str.upper()
)

df = df.dropna(subset=required).copy()
df = df[
    np.isfinite(df["bjd"]) &
    np.isfinite(df["model_b_residual_ms"]) &
    np.isfinite(df["model_b_sigma_ms"]) &
    (df["model_b_sigma_ms"] > 0)
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

allowed = ["HARPS_PRE", "HARPS_POST"]
df = df[df["instrument_epoch"].isin(allowed)].copy()

if len(df) < 30:
    raise ValueError("Insufficient valid observations.")

print(f"Valid observations: {len(df)}")
print(df["instrument_epoch"].value_counts().to_string())

# Use one common time origin so shared planetary phases
# remain consistent between PRE and POST.
t = df["bjd"].to_numpy(dtype=float)
t = t - np.min(t)

y = df["model_b_residual_ms"].to_numpy(dtype=float)
sigma = df["model_b_sigma_ms"].to_numpy(dtype=float)
epoch = df["instrument_epoch"].to_numpy()

epoch_pre = (epoch == "HARPS_PRE").astype(float)
epoch_post = (epoch == "HARPS_POST").astype(float)

def sinusoid(period):
    angle = 2.0 * np.pi * t / period
    return (
        np.sin(angle),
        np.cos(angle)
    )

sin_c, cos_c = sinusoid(P_C)
sin_d, cos_d = sinusoid(P_D)
sin_a, cos_a = sinusoid(P_ACTIVITY)

# Separate epoch intercepts are included in every model.
BASE = [
    ("gamma_PRE", epoch_pre),
    ("gamma_POST", epoch_post)
]

SIGNALS = {
    "c": [
        ("c_sin", sin_c),
        ("c_cos", cos_c)
    ],
    "d": [
        ("d_sin", sin_d),
        ("d_cos", cos_d)
    ],
    "activity184": [
        ("activity184_sin", sin_a),
        ("activity184_cos", cos_a)
    ]
}

def fit_model(signal_names):
    columns = list(BASE)

    for name in signal_names:
        columns.extend(SIGNALS[name])

    names = [name for name, _ in columns]
    X = np.column_stack([values for _, values in columns])

    # Weighted least squares using supplied uncertainties.
    Xw = X / sigma[:, None]
    yw = y / sigma

    beta, _, _, _ = np.linalg.lstsq(Xw, yw, rcond=None)

    residual = y - X @ beta
    chi2 = float(np.sum((residual / sigma) ** 2))

    n = len(y)
    k = X.shape[1]

    try:
        covariance = np.linalg.inv(Xw.T @ Xw)
        errors = np.sqrt(np.diag(covariance))
    except np.linalg.LinAlgError:
        covariance = np.linalg.pinv(Xw.T @ Xw)
        errors = np.sqrt(np.maximum(np.diag(covariance), 0))

    # Gaussian likelihood with supplied measurement uncertainties.
    loglike = -0.5 * np.sum(
        (residual / sigma) ** 2 +
        np.log(2.0 * np.pi * sigma ** 2)
    )

    aic = 2 * k - 2 * loglike
    bic = k * np.log(n) - 2 * loglike

    if n > k + 1:
        aicc = aic + (2 * k * (k + 1)) / (n - k - 1)
    else:
        aicc = np.nan

    result = {
        "n": n,
        "k": k,
        "chi2": chi2,
        "reduced_chi2": chi2 / (n - k),
        "loglike": float(loglike),
        "AIC": float(aic),
        "AICc": float(aicc),
        "BIC": float(bic),
        "weighted_rms": float(
            np.sqrt(np.mean((residual / sigma) ** 2))
        ),
        "residual_rms_ms": float(np.sqrt(np.mean(residual ** 2))),
        "coefficients": dict(zip(names, beta)),
        "errors": dict(zip(names, errors)),
        "residuals": residual
    }

    for name, period in [
        ("c", P_C),
        ("d", P_D),
        ("activity184", P_ACTIVITY)
    ]:
        if name not in signal_names:
            continue

        a = result["coefficients"][f"{name}_sin"]
        b = result["coefficients"][f"{name}_cos"]

        ea = result["errors"][f"{name}_sin"]
        eb = result["errors"][f"{name}_cos"]

        amplitude = float(np.hypot(a, b))

        # Approximate uncertainty using coefficient covariance
        # diagonal terms; not a full nonlinear amplitude interval.
        amp_error = (
            float(np.sqrt((a*a*ea*ea + b*b*eb*eb) /
                          max(amplitude**2, 1e-30)))
        )

        result[f"{name}_amplitude_ms"] = amplitude
        result[f"{name}_amplitude_approx_error_ms"] = amp_error

    return result

models = {
    "BASE": [],
    "C_ONLY": ["c"],
    "D_ONLY": ["d"],
    "ACTIVITY184_ONLY": ["activity184"],
    "C_PLUS_D": ["c", "d"],
    "C_PLUS_D_PLUS_184": ["c", "d", "activity184"]
}

fitted = {}

for name, signals in models.items():
    fitted[name] = fit_model(signals)

baseline = fitted["BASE"]

report = []
report.append("PI MEN COMPREHENSIVE RV RESIDUAL VALIDATION")
report.append("=" * 70)
report.append(f"Input: {INPUT}")
report.append(f"Valid observations: {len(df)}")
report.append(f"PRE observations: {int(np.sum(epoch_pre))}")
report.append(f"POST observations: {int(np.sum(epoch_post))}")
report.append(f"Periods: c={P_C} d, d={P_D} d, activity={P_ACTIVITY} d")
report.append("")
report.append("MODEL COMPARISON")
report.append("-" * 70)
report.append(
    "Model | k | chi2 | reduced chi2 | AICc | BIC | "
    "Delta BIC vs BASE"
)

rows = []

for name, result in fitted.items():
    delta_bic = baseline["BIC"] - result["BIC"]

    report.append(
        f"{name} | {result['k']} | {result['chi2']:.4f} | "
        f"{result['reduced_chi2']:.5f} | "
        f"{result['AICc']:.4f} | {result['BIC']:.4f} | "
        f"{delta_bic:.4f}"
    )

    rows.append({
        "model": name,
        "observations": result["n"],
        "parameters": result["k"],
        "chi2": result["chi2"],
        "reduced_chi2": result["reduced_chi2"],
        "AIC": result["AIC"],
        "AICc": result["AICc"],
        "BIC": result["BIC"],
        "delta_BIC_vs_BASE": delta_bic,
        "residual_rms_ms": result["residual_rms_ms"]
    })

report.append("")
report.append("PLANETARY / ACTIVITY AMPLITUDES")
report.append("-" * 70)

full = fitted["C_PLUS_D_PLUS_184"]

for name in ["c", "d", "activity184"]:
    key = f"{name}_amplitude_ms"
    err_key = f"{name}_amplitude_approx_error_ms"

    report.append(
        f"{name}: K={full[key]:.5f} +/- "
        f"{full[err_key]:.5f} m/s (approximate)"
    )

# Diagnostic: fit c and d independently in each epoch.
# This tests whether the recovered amplitudes are stable.
report.append("")
report.append("EPOCH-SPECIFIC AMPLITUDE CHECK")
report.append("-" * 70)

epoch_rows = []

for epoch_name in allowed:
    mask = epoch == epoch_name

    te = t[mask]
    ye = y[mask]
    se = sigma[mask]

    columns = [
        np.ones(len(te)),
        np.sin(2 * np.pi * te / P_C),
        np.cos(2 * np.pi * te / P_C),
        np.sin(2 * np.pi * te / P_D),
        np.cos(2 * np.pi * te / P_D)
    ]

    X = np.column_stack(columns)
    Xw = X / se[:, None]
    yw = ye / se

    beta, _, _, _ = np.linalg.lstsq(Xw, yw, rcond=None)

    covariance = np.linalg.pinv(Xw.T @ Xw)
    errors = np.sqrt(np.maximum(np.diag(covariance), 0))

    kc = float(np.hypot(beta[1], beta[2]))
    kd = float(np.hypot(beta[3], beta[4]))

    ec = float(np.sqrt(
        (beta[1]**2 * errors[1]**2 +
         beta[2]**2 * errors[2]**2) /
        max(kc**2, 1e-30)
    ))

    ed = float(np.sqrt(
        (beta[3]**2 * errors[3]**2 +
         beta[4]**2 * errors[4]**2) /
        max(kd**2, 1e-30)
    ))

    report.append(
        f"{epoch_name} N={len(te)} | "
        f"c K={kc:.5f} +/- {ec:.5f} m/s | "
        f"d K={kd:.5f} +/- {ed:.5f} m/s"
    )

    epoch_rows.append({
        "model": f"EPOCH_{epoch_name}",
        "observations": len(te),
        "c_amplitude_ms": kc,
        "c_approx_error_ms": ec,
        "d_amplitude_ms": kd,
        "d_approx_error_ms": ed
    })

# Save model and epoch diagnostics together.
model_df = pd.DataFrame(rows)
epoch_df = pd.DataFrame(epoch_rows)

model_df.to_csv(OUTPUT_CSV, index=False)

epoch_output = OUTPUT_CSV.with_name(
    "phase2_6_pi_men_epoch_amplitude_check.csv"
)
epoch_df.to_csv(epoch_output, index=False)

report.append("")
report.append("IMPORTANT LIMITATIONS")
report.append("-" * 70)
report.append(
    "1. This is a conditional residual analysis after the fitted "
    "planet-b model, not a full simultaneous refit of all planets."
)
report.append(
    "2. The supplied sigma values are treated as known independent "
    "Gaussian uncertainties."
)
report.append(
    "3. Amplitude uncertainties are approximate linear covariance "
    "estimates, not full posterior credible intervals."
)
report.append(
    "4. PRE/POST amplitude fits are diagnostic and do not prove "
    "planet identity or activity origin."
)
report.append(
    "5. Fixed-period model comparisons do not account for every "
    "possible alias or period-search trial."
)
report.append(
    "6. No detection claim or false-alarm probability is made here."
)

OUTPUT_REPORT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print("\n===== VALIDATION COMPLETE =====")
print(f"Model comparison CSV: {OUTPUT_CSV}")
print(f"Epoch amplitude CSV: {epoch_output}")
print(f"Report: {OUTPUT_REPORT}")
