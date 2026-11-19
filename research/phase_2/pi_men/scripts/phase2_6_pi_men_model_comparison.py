from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import numpy as np
import pandas as pd
from pathlib import Path
from scipy.optimize import differential_evolution
from scipy.signal import lombscargle

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
n = len(df)

def kepler_anomaly(M, e):
    M = (M + np.pi) % (2*np.pi) - np.pi
    E = M.copy()

    for _ in range(100):
        delta = (E - e*np.sin(E) - M) / (1 - e*np.cos(E))
        E -= delta
        if np.max(np.abs(delta)) < 1e-11:
            break

    return E

def orbital_signal(K, M0):
    M = 2*np.pi*t/P + M0
    E = kepler_anomaly(M, ECC)

    nu = 2*np.arctan2(
        np.sqrt(1+ECC)*np.sin(E/2),
        np.sqrt(1-ECC)*np.cos(E/2)
    )

    return K*(np.cos(nu+OMEGA) + ECC*np.cos(OMEGA))

def model_a(params):
    K, M0, gamma, jitter = params
    prediction = orbital_signal(K, M0) + gamma
    sigma = np.sqrt(dy**2 + jitter**2)
    return prediction, sigma

def model_b(params):
    K, M0, gamma_pre, gamma_post, jitter_pre, jitter_post = params

    gamma = np.where(is_pre, gamma_pre, gamma_post)
    jitter = np.where(is_pre, jitter_pre, jitter_post)

    prediction = orbital_signal(K, M0) + gamma
    sigma = np.sqrt(dy**2 + jitter**2)

    return prediction, sigma

def neg_log_likelihood(residual, sigma):
    return 0.5*np.sum(
        np.log(2*np.pi*sigma**2) + (residual/sigma)**2
    )

def objective_a(params):
    prediction, sigma = model_a(params)
    return neg_log_likelihood(y-prediction, sigma)

def objective_b(params):
    prediction, sigma = model_b(params)
    return neg_log_likelihood(y-prediction, sigma)

bounds_a = [
    (1, 300),
    (-np.pi, np.pi),
    (-500, 500),
    (0.1, 100)
]

bounds_b = [
    (1, 300),
    (-np.pi, np.pi),
    (-500, 500),
    (-500, 500),
    (0.1, 100),
    (0.1, 100)
]

print("\n===== PI MEN MODEL COMPARISON =====")
print("Observations:", n)
print("HARPS-PRE:", int(is_pre.sum()))
print("HARPS-POST:", int((~is_pre).sum()))

print("\nFitting Model A: shared gamma and jitter...")

fit_a = differential_evolution(
    objective_a,
    bounds_a,
    seed=42,
    maxiter=900,
    popsize=15,
    tol=1e-8,
    polish=True,
    workers=1
)

print("Model A complete.")

print("\nFitting Model B: separate PRE/POST gamma and jitter...")

fit_b = differential_evolution(
    objective_b,
    bounds_b,
    seed=42,
    maxiter=900,
    popsize=15,
    tol=1e-8,
    polish=True,
    workers=1
)

print("Model B complete.")

pred_a, sigma_a = model_a(fit_a.x)
pred_b, sigma_b = model_b(fit_b.x)

res_a = y-pred_a
res_b = y-pred_b

nll_a = fit_a.fun
nll_b = fit_b.fun

k_a = len(fit_a.x)
k_b = len(fit_b.x)

aic_a = 2*k_a + 2*nll_a
aic_b = 2*k_b + 2*nll_b

bic_a = k_a*np.log(n) + 2*nll_a
bic_b = k_b*np.log(n) + 2*nll_b

def diagnostics(residual, sigma):
    chi2 = np.sum((residual/sigma)**2)
    dof = n - len(sigma) * 0
    return {
        "rms": np.sqrt(np.mean(residual**2)),
        "median": np.median(residual),
        "std": np.std(residual, ddof=1),
        "chi2": chi2
    }

def epoch_summary(residual, epoch_mask):
    values = residual[epoch_mask]
    return {
        "count": len(values),
        "mean": np.mean(values),
        "median": np.median(values),
        "std": np.std(values, ddof=1),
        "rms": np.sqrt(np.mean(values**2))
    }

# Residual periodogram for Model B
# Search periods between 2 days and the full observing baseline.
baseline = np.ptp(t)
min_period = 2.0
max_period = baseline

frequencies = np.linspace(
    1/max_period,
    1/min_period,
    50000
)

angular_frequencies = 2*np.pi*frequencies

res_centered = res_b - np.mean(res_b)

power = lombscargle(
    t,
    res_centered,
    angular_frequencies,
    normalize=True
)

top_indices = np.argsort(power)[::-1][:10]

period_rows = []
for idx in top_indices:
    period_rows.append({
        "period_days": 1/frequencies[idx],
        "power": power[idx]
    })

period_table = pd.DataFrame(period_rows)

# Epoch diagnostics
pre_a = epoch_summary(res_a, is_pre)
post_a = epoch_summary(res_a, ~is_pre)

pre_b = epoch_summary(res_b, is_pre)
post_b = epoch_summary(res_b, ~is_pre)

# Save residual dataset
df["model_a_rv_ms"] = pred_a
df["model_a_residual_ms"] = res_a
df["model_a_sigma_ms"] = sigma_a

df["model_b_rv_ms"] = pred_b
df["model_b_residual_ms"] = res_b
df["model_b_sigma_ms"] = sigma_b

residual_file = RESULTS_DIR / "phase2_6_pi_men_model_comparison_residuals.csv"
period_file = RESULTS_DIR / "phase2_6_pi_men_residual_periodogram.csv"
report_file = REPORTS_DIR / "phase2_6_pi_men_model_comparison_report.txt"

df.to_csv(residual_file, index=False)
period_table.to_csv(period_file, index=False)

lines = [
    "PI MEN MODEL COMPARISON AND RESIDUAL VALIDATION",
    "="*65,
    f"Observations: {n}",
    f"HARPS-PRE: {int(is_pre.sum())}",
    f"HARPS-POST: {int((~is_pre).sum())}",
    "",
    "FIXED ORBITAL PARAMETERS",
    f"Period: {P} days",
    f"Eccentricity: {ECC}",
    f"Omega: {np.rad2deg(OMEGA)} degrees",
    "",
    "MODEL A: SHARED GAMMA AND JITTER",
    f"K: {fit_a.x[0]:.8f}",
    f"M0: {fit_a.x[1]:.10f}",
    f"Gamma: {fit_a.x[2]:.8f}",
    f"Jitter: {fit_a.x[3]:.8f}",
    f"Negative log likelihood: {nll_a:.8f}",
    f"AIC: {aic_a:.8f}",
    f"BIC: {bic_a:.8f}",
    f"Residual RMS: {np.sqrt(np.mean(res_a**2)):.8f}",
    f"Residual median: {np.median(res_a):.8f}",
    f"Optimizer success: {fit_a.success}",
    "",
    "MODEL B: SEPARATE PRE/POST GAMMA AND JITTER",
    f"K: {fit_b.x[0]:.8f}",
    f"M0: {fit_b.x[1]:.10f}",
    f"Gamma PRE: {fit_b.x[2]:.8f}",
    f"Gamma POST: {fit_b.x[3]:.8f}",
    f"PRE-POST offset: {fit_b.x[3]-fit_b.x[2]:.8f}",
    f"Jitter PRE: {fit_b.x[4]:.8f}",
    f"Jitter POST: {fit_b.x[5]:.8f}",
    f"Negative log likelihood: {nll_b:.8f}",
    f"AIC: {aic_b:.8f}",
    f"BIC: {bic_b:.8f}",
    f"Residual RMS: {np.sqrt(np.mean(res_b**2)):.8f}",
    f"Residual median: {np.median(res_b):.8f}",
    f"Optimizer success: {fit_b.success}",
    "",
    "MODEL COMPARISON",
    f"Delta AIC (A-B): {aic_a-aic_b:.8f}",
    f"Delta BIC (A-B): {bic_a-bic_b:.8f}",
    "Positive delta means Model B has the lower information criterion.",
    "",
    "MODEL B RESIDUALS BY INSTRUMENT EPOCH",
]

for name, stats in [
    ("PRE", pre_b),
    ("POST", post_b)
]:
    lines.extend([
        f"{name}:",
        f"  Count: {stats['count']}",
        f"  Mean: {stats['mean']:.8f}",
        f"  Median: {stats['median']:.8f}",
        f"  Std: {stats['std']:.8f}",
        f"  RMS: {stats['rms']:.8f}"
    ])

lines.extend([
    "",
    "TOP MODEL B RESIDUAL PERIODOGRAM PEAKS",
])

for _, row in period_table.iterrows():
    lines.append(
        f"Period {row['period_days']:.6f} days | "
        f"Power {row['power']:.8f}"
    )

lines.extend([
    "",
    "SCIENTIFIC LIMITATIONS",
    "- Fixed orbital parameters are exploratory inputs.",
    "- Reference epoch and omega convention require verification.",
    "- Periodogram peaks are exploratory, not planet detections.",
    "- AIC/BIC compare only these two specified models.",
    "- Secular acceleration correction is approximate.",
    "- No independent published-solution validation is claimed."
])

report_file.write_text("\n".join(lines), encoding="utf-8")

print("\n===== MODEL COMPARISON RESULTS =====")
print(f"Model A AIC: {aic_a:.6f}")
print(f"Model B AIC: {aic_b:.6f}")
print(f"Delta AIC (A-B): {aic_a-aic_b:.6f}")
print(f"Model A BIC: {bic_a:.6f}")
print(f"Model B BIC: {bic_b:.6f}")
print(f"Delta BIC (A-B): {bic_a-bic_b:.6f}")

print("\n===== MODEL B RESIDUAL RMS =====")
print(f"PRE: {pre_b['rms']:.6f} m/s")
print(f"POST: {post_b['rms']:.6f} m/s")

print("\n===== TOP RESIDUAL PERIODS =====")
print(period_table.to_string(index=False))

print("\nResidual CSV:", residual_file.resolve())
print("Periodogram CSV:", period_file.resolve())
print("Report:", report_file.resolve())
print("\n===== VALIDATION COMPLETE =====")
