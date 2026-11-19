import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

# ============================================================
# PI MEN B — PUBLISHED ORBIT VALIDATION
# Research-only. Does not modify existing analysis scripts.
# ============================================================

INPUT = "phase2_6_pi_men_harps_timeseries.csv"
OUTPUT = "phase2_6_pi_men_published_validation_residuals.csv"
REPORT = "phase2_6_pi_men_published_validation.txt"

# Published reference values discussed in Phase 2.6.
P_REF = 2088.33
E_REF = 0.6396
OMEGA_REF_DEG = 331.03
K_REF = 192.99

OMEGA_REF = np.deg2rad(OMEGA_REF_DEG)

df = pd.read_csv(INPUT)

required = [
    "bjd", "rv_relative_ms", "rv_error_ms", "drs_snr"
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

# Diagnostic filter: exclude zero-SNR and invalid measurements.
df = df[
    (df["drs_snr"] > 0)
    & np.isfinite(df["bjd"])
    & np.isfinite(df["rv_relative_ms"])
    & np.isfinite(df["rv_error_ms"])
    & (df["rv_error_ms"] > 0)
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

t_abs = df["bjd"].to_numpy(dtype=float)
t_ref = float(t_abs.min())
t = t_abs - t_ref

y = df["rv_relative_ms"].to_numpy(dtype=float)
dy = df["rv_error_ms"].to_numpy(dtype=float)

# Fixed published P, e and omega.
# Free parameters: K, M0, gamma, jitter.
def kepler_rv(K, M0, gamma):
    M = 2.0 * np.pi * t / P_REF + M0
    M = (M + np.pi) % (2.0 * np.pi) - np.pi

    E = M.copy()

    for _ in range(150):
        delta = (
            E - E_REF * np.sin(E) - M
        ) / (
            1.0 - E_REF * np.cos(E)
        )
        E -= delta

        if np.max(np.abs(delta)) < 1e-12:
            break

    nu = 2.0 * np.arctan2(
        np.sqrt(1.0 + E_REF) * np.sin(E / 2.0),
        np.sqrt(1.0 - E_REF) * np.cos(E / 2.0)
    )

    return gamma + K * (
        np.cos(nu + OMEGA_REF)
        + E_REF * np.cos(OMEGA_REF)
    )


def objective(params):
    K, M0, gamma, jitter = params

    model = kepler_rv(K, M0, gamma)
    variance = dy**2 + jitter**2
    residual = y - model

    return 0.5 * np.sum(
        residual**2 / variance
        + np.log(2.0 * np.pi * variance)
    )


bounds = [
    (50.0, 350.0),       # K, m/s
    (-np.pi, np.pi),     # M0 at first observation
    (-500.0, 500.0),     # gamma, m/s
    (0.01, 100.0)        # jitter, m/s
]

print("Starting published-orbit validation...")
print("Input observations:", len(df))
print("Reference epoch BJD:", t_ref)
print("Fixed P:", P_REF)
print("Fixed e:", E_REF)
print("Fixed omega (deg):", OMEGA_REF_DEG)

result = differential_evolution(
    objective,
    bounds,
    seed=42,
    maxiter=800,
    popsize=15,
    tol=1e-8,
    polish=True,
    workers=1
)

K, M0, gamma, jitter = result.x

model = kepler_rv(K, M0, gamma)
residual = y - model

rms = float(np.sqrt(np.mean(residual**2)))
weighted_chi2 = float(np.sum(
    residual**2 / (dy**2 + jitter**2)
))
reduced_chi2 = weighted_chi2 / max(len(y) - 4, 1)

# Descriptive comparison only; not a formal significance test.
report_lines = [
    "===== PI MEN B PUBLISHED ORBIT VALIDATION =====",
    f"Optimization success: {result.success}",
    f"Optimizer message: {result.message}",
    f"Observations: {len(df)}",
    f"Reference epoch BJD: {t_ref:.8f}",
    "",
    "FIXED PUBLISHED PARAMETERS",
    f"Period (days): {P_REF}",
    f"Eccentricity: {E_REF}",
    f"Omega (degrees): {OMEGA_REF_DEG}",
    "",
    "OPTIMIZED PARAMETERS",
    f"K (m/s): {K:.8f}",
    f"Published K (m/s): {K_REF}",
    f"K difference (m/s): {K - K_REF:.8f}",
    f"M0 at first observation (rad): {M0:.10f}",
    f"Gamma (m/s): {gamma:.8f}",
    f"Jitter (m/s): {jitter:.8f}",
    "",
    "FIT DIAGNOSTICS",
    f"Residual RMS (m/s): {rms:.8f}",
    f"Residual median (m/s): {np.median(residual):.8f}",
    f"Weighted chi-square: {weighted_chi2:.8f}",
    f"Reduced chi-square: {reduced_chi2:.8f}",
    f"Objective: {result.fun:.8f}",
    "",
    "RESIDUAL SUMMARY",
    pd.Series(residual).describe().to_string(),
    "",
    "CAUTION",
    "Exploratory fixed-orbit fit only.",
    "Reference epoch and published parameter convention must be",
    "verified against the original publication before interpretation.",
    "This fit does not establish an independent planet validation."
]

report_text = "\n".join(report_lines)

out = df.copy()
out["published_orbit_model_ms"] = model
out["published_orbit_residual_ms"] = residual
out.to_csv(OUTPUT, index=False)

with open(REPORT, "w", encoding="utf-8") as f:
    f.write(report_text)

print("\n" + report_text)
print("\nResidual CSV saved:", OUTPUT)
print("Report saved:", REPORT)
print("===== VALIDATION COMPLETE =====")
