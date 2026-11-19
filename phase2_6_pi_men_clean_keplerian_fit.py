import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution
from scipy.optimize import least_squares

df = pd.read_csv("phase2_6_pi_men_harps_timeseries.csv")

# Diagnostic quality filter only
df = df[
    (df["drs_snr"] > 0) &
    np.isfinite(df["bjd"]) &
    np.isfinite(df["rv_relative_ms"]) &
    np.isfinite(df["rv_error_ms"]) &
    (df["rv_error_ms"] > 0)
].copy()

t = df["bjd"].to_numpy()
t = t - t.min()

y = df["rv_relative_ms"].to_numpy()
dy = df["rv_error_ms"].to_numpy()

def kepler_rv(params):
    P, K, e, omega, M0, gamma = params

    M = 2*np.pi*t/P + M0
    M = (M + np.pi) % (2*np.pi) - np.pi

    E = M.copy()

    for _ in range(100):
        delta = (E - e*np.sin(E) - M) / (1 - e*np.cos(E))
        E -= delta
        if np.max(np.abs(delta)) < 1e-11:
            break

    nu = 2*np.arctan2(
        np.sqrt(1+e)*np.sin(E/2),
        np.sqrt(1-e)*np.cos(E/2)
    )

    return gamma + K*(np.cos(nu+omega) + e*np.cos(omega))

def objective(p):
    P, K, e, omega, M0, gamma, jitter = p

    model = kepler_rv(p[:6])
    sigma2 = dy**2 + jitter**2
    residual = y - model

    return 0.5*np.sum(
        residual**2/sigma2 + np.log(2*np.pi*sigma2)
    )

bounds = [
    (1500, 2600),       # Period days
    (1, 300),           # Semi-amplitude m/s
    (0, 0.90),          # Eccentricity
    (-np.pi, np.pi),    # Omega
    (-np.pi, np.pi),    # Mean anomaly
    (-500, 500),        # Gamma
    (0.1, 100)          # Jitter m/s
]

print("Optimizing clean-data Keplerian model...")
print("Observations:", len(df))

result = differential_evolution(
    objective,
    bounds,
    seed=42,
    maxiter=700,
    popsize=12,
    tol=1e-7,
    polish=True,
    workers=1
)

p = result.x
model = kepler_rv(p[:6])
residual = y - model

print("\n===== CLEAN PI MEN B KEPLERIAN FIT =====")
print("Optimization success:", result.success)
print("Period (days):", p[0])
print("K (m/s):", p[1])
print("Eccentricity:", p[2])
print("Omega (rad):", p[3])
print("M0 (rad):", p[4])
print("Gamma (m/s):", p[5])
print("Estimated jitter (m/s):", p[6])
print("Residual RMS (m/s):", np.sqrt(np.mean(residual**2)))
print("Residual median (m/s):", np.median(residual))
print("Objective:", result.fun)

print("\n===== RESIDUAL SUMMARY =====")
print(pd.Series(residual).describe().to_string())

out = df.copy()
out["keplerian_model_ms"] = model
out["residual_ms"] = residual
out.to_csv("phase2_6_pi_men_clean_keplerian_residuals.csv", index=False)

print("\nResidual CSV saved.")
print("===== FIT COMPLETE =====")
