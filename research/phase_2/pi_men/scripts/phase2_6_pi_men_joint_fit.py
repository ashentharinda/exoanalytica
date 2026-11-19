from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

INPUT = DATA_DIR / "phase2_6_pi_men_corrected_dataset.csv"

P_C = 6.267852
P_D = 124.64
P_ACTIVITY = 184.0

OUTPUT = RESULTS_DIR / "phase2_6_pi_men_joint_fit_results.csv"
REPORT = REPORTS_DIR / "phase2_6_pi_men_joint_fit_report.txt"

df = pd.read_csv(INPUT)

required = [
    "bjd",
    "rv_corrected_ms",
    "rv_error_ms",
    "instrument_epoch"
]

missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

for col in ["bjd", "rv_corrected_ms", "rv_error_ms"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["instrument_epoch"] = (
    df["instrument_epoch"].astype(str).str.upper()
)

df = df.dropna(subset=required).copy()
df = df[
    np.isfinite(df["bjd"]) &
    np.isfinite(df["rv_corrected_ms"]) &
    np.isfinite(df["rv_error_ms"]) &
    (df["rv_error_ms"] > 0) &
    df["instrument_epoch"].isin(["HARPS_PRE", "HARPS_POST"])
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

if len(df) < 100:
    raise ValueError("Insufficient observations for joint fitting.")

t0 = float(df["bjd"].min())
t = df["bjd"].to_numpy(dtype=float) - t0
y = df["rv_corrected_ms"].to_numpy(dtype=float)
err = df["rv_error_ms"].to_numpy(dtype=float)
epoch = df["instrument_epoch"].to_numpy()

pre = epoch == "HARPS_PRE"
post = epoch == "HARPS_POST"

gamma_pre0 = float(np.median(y[pre]))
gamma_post0 = float(np.median(y[post]))

print(f"Observations: {len(df)}")
print(f"HARPS_PRE: {pre.sum()}")
print(f"HARPS_POST: {post.sum()}")
print(f"Baseline: {np.ptp(t):.3f} days")

def eccentricity_from_q(q):
    return 0.99 / (1.0 + np.exp(-np.clip(q, -30, 30)))

def solve_kepler(M, e):
    M = (M + np.pi) % (2.0 * np.pi) - np.pi
    E = M + e * np.sin(M)

    for _ in range(60):
        delta = (E - e * np.sin(E) - M) / (
            1.0 - e * np.cos(E)
        )
        E -= delta
        if np.max(np.abs(delta)) < 1e-11:
            break

    return E

def keplerian_rv(t, period, K, e, omega, M0):
    M = M0 + 2.0 * np.pi * t / period
    E = solve_kepler(M, e)

    nu = 2.0 * np.arctan2(
        np.sqrt(1.0 + e) * np.sin(E / 2.0),
        np.sqrt(1.0 - e) * np.cos(E / 2.0)
    )

    return K * (
        np.cos(nu + omega) + e * np.cos(omega)
    )

signals = {
    "c": P_C,
    "d": P_D,
    "activity184": P_ACTIVITY
}

def build_bounds(signal_names):
    bounds = [
        (np.log(1500), np.log(3000)),  # log P_b
        (np.log(50), np.log(400)),     # log K_b
        (-3.0, 3.0),                   # eccentricity transform
        (-4*np.pi, 4*np.pi),           # omega
        (-8*np.pi, 8*np.pi),           # M0
        (-1000, 1000),                 # gamma PRE
        (-1000, 1000),                 # gamma POST
        (np.log(0.05), np.log(50)),    # jitter PRE
        (np.log(0.05), np.log(50)),    # jitter POST
    ]

    for _ in signal_names:
        bounds.extend([(-20, 20), (-20, 20)])

    return bounds

def unpack_model(x, signal_names):
    period_b = np.exp(x[0])
    K_b = np.exp(x[1])
    eccentricity = eccentricity_from_q(x[2])
    omega = x[3]
    M0 = x[4]

    gamma_pre = x[5]
    gamma_post = x[6]

    jitter_pre = np.exp(x[7])
    jitter_post = np.exp(x[8])

    return (
        period_b, K_b, eccentricity, omega, M0,
        gamma_pre, gamma_post,
        jitter_pre, jitter_post
    )

def calculate_model(x, signal_names):
    (
        period_b, K_b, eccentricity, omega, M0,
        gamma_pre, gamma_post,
        jitter_pre, jitter_post
    ) = unpack_model(x, signal_names)

    model = keplerian_rv(
        t, period_b, K_b, eccentricity, omega, M0
    )

    model = model + np.where(pre, gamma_pre, gamma_post)

    index = 9

    for name in signal_names:
        period = signals[name]
        angle = 2.0 * np.pi * t / period

        model += (
            x[index] * np.sin(angle) +
            x[index + 1] * np.cos(angle)
        )

        index += 2

    jitter = np.where(pre, jitter_pre, jitter_post)
    variance = err**2 + jitter**2

    return model, variance

def negative_log_likelihood(x, signal_names):
    model, variance = calculate_model(x, signal_names)
    residual = y - model

    value = 0.5 * np.sum(
        residual**2 / variance + np.log(2.0 * np.pi * variance)
    )

    if not np.isfinite(value):
        return 1e100

    return float(value)

def initial_parameters(signal_names, M0):
    e0 = 0.6396
    q0 = np.log((e0 / 0.99) / (1.0 - e0 / 0.99))

    x = [
        np.log(2088.33),
        np.log(192.99),
        q0,
        np.deg2rad(331.03),
        M0,
        gamma_pre0,
        gamma_post0,
        np.log(3.0),
        np.log(3.0)
    ]

    for _ in signal_names:
        x.extend([0.0, 0.0])

    return np.asarray(x, dtype=float)

def fit_model(signal_names):
    bounds = build_bounds(signal_names)
    best = None

    # Multiple starting phases reduce the chance of a local solution.
    for start_phase in [2.64, 2.64 + np.pi, 2.64 - np.pi]:

        x0 = initial_parameters(signal_names, start_phase)

        result = minimize(
            negative_log_likelihood,
            x0,
            args=(signal_names,),
            method="L-BFGS-B",
            bounds=bounds,
            options={
                "maxiter": 6000,
                "ftol": 1e-12,
                "gtol": 1e-7,
                "maxls": 50
            }
        )

        if best is None or result.fun < best.fun:
            best = result

    model, variance = calculate_model(best.x, signal_names)
    residual = y - model

    n = len(y)
    k = len(best.x)
    loglike = -float(best.fun)

    aic = 2*k - 2*loglike
    bic = k*np.log(n) - 2*loglike
    aicc = (
        aic + 2*k*(k+1)/(n-k-1)
        if n > k+1 else np.nan
    )

    output = {
        "signals": "+".join(signal_names) if signal_names else "BASE",
        "n": n,
        "k": k,
        "success": bool(best.success),
        "message": str(best.message),
        "negative_log_likelihood": float(best.fun),
        "log_likelihood": loglike,
        "chi2": float(np.sum(residual**2 / variance)),
        "reduced_chi2": float(np.sum(residual**2 / variance)/(n-k)),
        "AIC": aic,
        "AICc": aicc,
        "BIC": bic,
        "residual_rms_ms": float(np.sqrt(np.mean(residual**2))),
        "parameters": best.x,
        "residuals": residual
    }

    return output

model_sets = [
    [],
    ["c"],
    ["d"],
    ["activity184"],
    ["c", "d"],
    ["c", "d", "activity184"]
]

results = []

print("\n===== FITTING MODELS =====")

for names in model_sets:
    label = "+".join(names) if names else "BASE"
    print(f"Fitting {label} ...")

    fit = fit_model(names)
    results.append(fit)

    print(
        f"  success={fit['success']} | "
        f"chi2={fit['chi2']:.3f} | "
        f"BIC={fit['BIC']:.3f}"
    )

base_bic = results[0]["BIC"]

report = []
report.append("PI MEN FULL SIMULTANEOUS RV MODEL")
report.append("=" * 75)
report.append(f"Input: {INPUT}")
report.append(f"Observations: {len(df)}")
report.append(f"Baseline: {np.ptp(t):.3f} days")
report.append(f"Reference BJD: {t0:.8f}")
report.append("")
report.append("MODEL COMPARISON")
report.append("-" * 75)
report.append(
    "Model | k | Success | chi2 | reduced chi2 | AICc | BIC | Delta BIC"
)

csv_rows = []

for fit in results:
    delta_bic = base_bic - fit["BIC"]

    report.append(
        f"{fit['signals']} | {fit['k']} | {fit['success']} | "
        f"{fit['chi2']:.4f} | {fit['reduced_chi2']:.5f} | "
        f"{fit['AICc']:.4f} | {fit['BIC']:.4f} | "
        f"{delta_bic:.4f}"
    )

    csv_rows.append({
        key: fit[key]
        for key in [
            "signals", "n", "k", "success",
            "negative_log_likelihood", "chi2",
            "reduced_chi2", "AIC", "AICc", "BIC",
            "residual_rms_ms"
        ]
    } | {"delta_BIC_vs_BASE": delta_bic})

full = results[-1]
x = full["parameters"]

(
    period_b, K_b, e_b, omega_b, M0_b,
    gamma_pre, gamma_post,
    jitter_pre, jitter_post
) = unpack_model(x, ["c", "d", "activity184"])

report.append("")
report.append("FULL MODEL PARAMETERS")
report.append("-" * 75)
report.append(f"Planet b period: {period_b:.8f} days")
report.append(f"Planet b K: {K_b:.6f} m/s")
report.append(f"Planet b eccentricity: {e_b:.7f}")
report.append(f"Planet b omega: {np.rad2deg(omega_b)%360:.5f} deg")
report.append(f"Planet b M0 at reference BJD: {M0_b:.7f} rad")
report.append(f"Reference BJD: {t0:.8f}")
report.append(f"Gamma PRE: {gamma_pre:.6f} m/s")
report.append(f"Gamma POST: {gamma_post:.6f} m/s")
report.append(f"Jitter PRE: {jitter_pre:.6f} m/s")
report.append(f"Jitter POST: {jitter_post:.6f} m/s")

report.append("")
report.append("SINUSOIDAL COMPONENTS")
report.append("-" * 75)

index = 9

for name in ["c", "d", "activity184"]:
    a = x[index]
    b = x[index+1]
    amplitude = float(np.hypot(a, b))
    phase = float(np.arctan2(b, a))

    report.append(
        f"{name}: period={signals[name]:.6f} d | "
        f"amplitude={amplitude:.6f} m/s | "
        f"sin coefficient={a:.6f} | "
        f"cos coefficient={b:.6f} | "
        f"phase={phase:.6f} rad"
    )

    index += 2

report.append("")
report.append("LIMITATIONS")
report.append("-" * 75)
report.append(
    "1. This is a fixed-period sinusoidal approximation for c, d "
    "and the 184-day candidate, not full Keplerian solutions for them."
)
report.append(
    "2. The 184-day term is a diagnostic candidate, not an established "
    "stellar activity or planetary signal."
)
report.append(
    "3. The approximate secular acceleration correction in the input "
    "dataset must be independently verified."
)
report.append(
    "4. HARPS DRS CCF velocities may differ from the data products "
    "used in the published orbital solution."
)
report.append(
    "5. AICc/BIC comparisons are conditional on this model family "
    "and do not replace alias analysis, bootstrap tests or posterior checks."
)
report.append(
    "6. Optimizer success and parameter stability must be inspected "
    "before interpreting the fit physically."
)

pd.DataFrame(csv_rows).to_csv(OUTPUT, index=False)
REPORT.write_text("\n".join(report), encoding="utf-8")

print("\n".join(report))
print("\n===== JOINT FIT COMPLETE =====")
print(f"CSV: {OUTPUT}")
print(f"Report: {REPORT}")
