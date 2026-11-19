from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution
from pathlib import Path

INPUT = DATA_DIR / "phase2_6_pi_men_corrected_dataset.csv"

P = 2088.33
ECC = 0.6396
OMEGA = np.deg2rad(331.03)

df = pd.read_csv(INPUT)

required = [
    "bjd", "rv_corrected_ms", "rv_error_ms",
    "instrument_epoch"
]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing columns: {missing}")

df = df[
    np.isfinite(df["bjd"]) &
    np.isfinite(df["rv_corrected_ms"]) &
    np.isfinite(df["rv_error_ms"]) &
    (df["rv_error_ms"] > 0) &
    df["instrument_epoch"].isin(["HARPS_PRE", "HARPS_POST"])
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

t = df["bjd"].to_numpy()
t = t - t.min()
y = df["rv_corrected_ms"].to_numpy()
dy = df["rv_error_ms"].to_numpy()

is_pre = df["instrument_epoch"].eq("HARPS_PRE").to_numpy()

def kepler_anomaly(M, e):
    M = (M + np.pi) % (2*np.pi) - np.pi
    E = M.copy()

    for _ in range(100):
        delta = (E - e*np.sin(E) - M) / (1 - e*np.cos(E))
        E -= delta
        if np.max(np.abs(delta)) < 1e-11:
            break

    return E

def model(params):
    K, M0, gamma_pre, gamma_post, jitter_pre, jitter_post = params

    M = 2*np.pi*t/P + M0
    E = kepler_anomaly(M, ECC)

    nu = 2*np.arctan2(
        np.sqrt(1+ECC)*np.sin(E/2),
        np.sqrt(1-ECC)*np.cos(E/2)
    )

    orbital = K*(np.cos(nu+OMEGA) + ECC*np.cos(OMEGA))

    gamma = np.where(is_pre, gamma_pre, gamma_post)

    return orbital + gamma

def objective(params):
    _, _, _, _, jitter_pre, jitter_post = params

    residual = y - model(params)
    jitter = np.where(is_pre, jitter_pre, jitter_post)
    variance = dy**2 + jitter**2

    return 0.5*np.sum(
        np.log(2*np.pi*variance) + residual**2/variance
    )

bounds = [
    (1, 300),
    (-np.pi, np.pi),
    (-500, 500),
    (-500, 500),
    (0.1, 100),
    (0.1, 100)
]

print("\n===== PI MEN PRE/POST KEPLERIAN FIT =====")
print("Observations:", len(df))
print("HARPS-PRE:", int(is_pre.sum()))
print("HARPS-POST:", int((~is_pre).sum()))

result = differential_evolution(
    objective,
    bounds,
    seed=42,
    maxiter=900,
    popsize=15,
    tol=1e-8,
    polish=True,
    workers=1
)

K, M0, gamma_pre, gamma_post, jitter_pre, jitter_post = result.x

prediction = model(result.x)
residual = y - prediction

jitter = np.where(is_pre, jitter_pre, jitter_post)
sigma = np.sqrt(dy**2 + jitter**2)

chi2 = np.sum((residual/sigma)**2)
reduced_chi2 = chi2/(len(df)-len(result.x))

print("\nOPTIMIZED PARAMETERS")
print(f"K (m/s): {K:.8f}")
print("Published K (m/s): 192.99")
print(f"K difference (%): {(K/192.99-1)*100:.5f}")
print(f"M0 (rad): {M0:.10f}")
print(f"Gamma PRE (m/s): {gamma_pre:.8f}")
print(f"Gamma POST (m/s): {gamma_post:.8f}")
print(f"PRE-POST offset difference (m/s): {gamma_post-gamma_pre:.8f}")
print(f"PRE jitter (m/s): {jitter_pre:.8f}")
print(f"POST jitter (m/s): {jitter_post:.8f}")

print("\nFIT DIAGNOSTICS")
print(f"Residual RMS (m/s): {np.sqrt(np.mean(residual**2)):.8f}")
print(f"Residual median (m/s): {np.median(residual):.8f}")
print(f"Weighted chi-square: {chi2:.8f}")
print(f"Reduced chi-square: {reduced_chi2:.8f}")
print(f"Optimizer success: {result.success}")
print("Optimizer message:", result.message)

df["model_rv_ms"] = prediction
df["residual_ms"] = residual
df["effective_sigma_ms"] = sigma

output = RESULTS_DIR / "phase2_6_pi_men_pre_post_residuals.csv"
report = REPORTS_DIR / "phase2_6_pi_men_pre_post_fit.txt"

df.to_csv(output, index=False)

report_lines = [
    "PI MEN PRE/POST KEPLERIAN FIT",
    "="*60,
    f"Observations: {len(df)}",
    f"HARPS-PRE: {int(is_pre.sum())}",
    f"HARPS-POST: {int((~is_pre).sum())}",
    f"K: {K:.8f}",
    f"Published K: 192.99",
    f"K difference (%): {(K/192.99-1)*100:.6f}",
    f"M0: {M0:.10f}",
    f"Gamma PRE: {gamma_pre:.8f}",
    f"Gamma POST: {gamma_post:.8f}",
    f"PRE-POST offset difference: {gamma_post-gamma_pre:.8f}",
    f"PRE jitter: {jitter_pre:.8f}",
    f"POST jitter: {jitter_post:.8f}",
    f"Residual RMS: {np.sqrt(np.mean(residual**2)):.8f}",
    f"Reduced chi-square: {reduced_chi2:.8f}",
    f"Optimizer success: {result.success}",
    "",
    "Exploratory fit only.",
    "Published epoch and omega convention require verification.",
    "ESO DRS RVs are not HARPS-TERRA RVs.",
    "PRE/POST offsets are phenomenological."
]

report.write_text("\n".join(report_lines), encoding="utf-8")

print("\nResidual CSV saved:", output.resolve())
print("Report saved:", report.resolve())
print("\n===== PRE/POST FIT COMPLETE =====")
