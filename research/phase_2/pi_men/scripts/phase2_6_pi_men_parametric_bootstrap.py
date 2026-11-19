from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

INPUT = DATA_DIR / "phase2_6_pi_men_corrected_dataset.csv"
REPORT = REPORTS_DIR / "phase2_6_pi_men_bootstrap_report.txt"
OUTPUT = RESULTS_DIR / "phase2_6_pi_men_bootstrap_results.csv"

P_B = 2088.33
ECC = 0.6396
OMEGA = np.deg2rad(331.03)
P_C = 6.267852

N_BOOT = 200
SEED = 20261119

df = pd.read_csv(INPUT)

df = df[
    np.isfinite(df["bjd"]) &
    np.isfinite(df["rv_corrected_ms"]) &
    np.isfinite(df["rv_error_ms"]) &
    (df["rv_error_ms"] > 0) &
    df["instrument_epoch"].isin(["HARPS_PRE", "HARPS_POST"])
].copy()

df = df.sort_values("bjd").reset_index(drop=True)

t = df["bjd"].to_numpy(float).copy()
t -= t.min()

y_observed = df["rv_corrected_ms"].to_numpy(float)
dy = df["rv_error_ms"].to_numpy(float)

pre = df["instrument_epoch"].eq("HARPS_PRE").to_numpy()
post = ~pre
N = len(y_observed)

M = 2*np.pi*t/P_B
angle = 2*np.pi*t/P_C

def kepler_anomaly(M, e):
    M = (M + np.pi) % (2*np.pi) - np.pi
    E = M.copy()

    for _ in range(100):
        delta = (E - e*np.sin(E) - M)/(1-e*np.cos(E))
        E -= delta
        if np.max(np.abs(delta)) < 1e-11:
            break

    return E

def design_matrix(K, M0, model):
    mean_anomaly = M + M0
    E = kepler_anomaly(mean_anomaly, ECC)

    nu = 2*np.arctan2(
        np.sqrt(1+ECC)*np.sin(E/2),
        np.sqrt(1-ECC)*np.cos(E/2)
    )

    orbital = K*(
        np.cos(nu+OMEGA) + ECC*np.cos(OMEGA)
    )

    columns = [
        orbital,
        pre.astype(float),
        post.astype(float)
    ]

    if model == "B":
        columns += [
            np.sin(angle),
            np.cos(angle)
        ]

    elif model == "C":
        columns += [
            pre*np.sin(angle),
            pre*np.cos(angle),
            post*np.sin(angle),
            post*np.cos(angle)
        ]

    return np.column_stack(columns)

def fit_profile(data, model, start):
    # Nonlinear parameters: K, M0, PRE jitter, POST jitter.
    def evaluate(theta, return_details=False):
        K, M0, jp, jq = theta

        if jp <= 0 or jq <= 0:
            return 1e100

        variance = dy**2 + np.where(pre, jp**2, jq**2)
        weights = 1.0/variance

        X = design_matrix(K, M0, model)

        sw = np.sqrt(weights)
        Xw = X*sw[:, None]
        yw = data*sw

        beta, *_ = np.linalg.lstsq(Xw, yw, rcond=None)

        residual = data-X@beta

        nll = 0.5*np.sum(
            np.log(2*np.pi*variance) +
            residual**2/variance
        )

        if return_details:
            return {
                "nll": float(nll),
                "theta": theta.copy(),
                "beta": beta,
                "prediction": X@beta,
                "residual": residual,
                "variance": variance
            }

        return float(nll)

    result = minimize(
        evaluate,
        np.asarray(start, dtype=float),
        method="L-BFGS-B",
        bounds=[
            (1, 300),
            (-np.pi, np.pi),
            (0.1, 100),
            (0.1, 100)
        ],
        options={
            "maxiter": 1200,
            "ftol": 1e-11,
            "gtol": 1e-7,
            "maxls": 40
        }
    )

    details = evaluate(result.x, return_details=True)
    details["success"] = bool(result.success)
    details["message"] = str(result.message)
    details["optimizer_result"] = result

    return details

def amplitude(beta, sine_index, cosine_index):
    return float(np.hypot(beta[sine_index], beta[cosine_index]))

# First fit the observed dataset.
# Starting values are close to the previously reproduced solution.
initial = np.array([
    192.9,
    2.64037,
    2.88,
    2.37
])

print("Fitting observed Model B...", flush=True)
observed_B = fit_profile(y_observed, "B", initial)

print("Fitting observed Model C...", flush=True)
observed_C = fit_profile(y_observed, "C", initial)

if not observed_B["success"] or not observed_C["success"]:
    raise RuntimeError(
        "Observed-data profile fit did not converge. "
        "Do not interpret bootstrap results."
    )

observed_stat = 2*(observed_B["nll"]-observed_C["nll"])

obs_pre_amp = amplitude(observed_C["beta"], 3, 4)
obs_post_amp = amplitude(observed_C["beta"], 5, 6)
observed_amp_difference = abs(obs_pre_amp-obs_post_amp)

print("\nOBSERVED PROFILE FIT", flush=True)
print("B NLL:", observed_B["nll"])
print("C NLL:", observed_C["nll"])
print("2 delta NLL:", observed_stat)
print("PRE amplitude:", obs_pre_amp)
print("POST amplitude:", obs_post_amp)
print("Absolute amplitude difference:", observed_amp_difference)

# Generate synthetic datasets under the fitted shared-signal Model B.
rng = np.random.default_rng(SEED)

mu_null = observed_B["prediction"]
sigma_null = np.sqrt(observed_B["variance"])

records = []
failures = 0

start_B = observed_B["theta"]
start_C = observed_C["theta"]

for i in range(N_BOOT):
    simulated = mu_null + rng.normal(0, sigma_null, size=N)

    fit_B = fit_profile(simulated, "B", start_B)
    fit_C = fit_profile(simulated, "C", start_C)

    if not fit_B["success"] or not fit_C["success"]:
        failures += 1
        print(
            f"Bootstrap {i+1}/{N_BOOT}: optimizer failure",
            flush=True
        )
        continue

    statistic = 2*(fit_B["nll"]-fit_C["nll"])

    pre_amp = amplitude(fit_C["beta"], 3, 4)
    post_amp = amplitude(fit_C["beta"], 5, 6)

    records.append({
        "replicate": i+1,
        "delta_2_nll": statistic,
        "pre_amplitude_ms": pre_amp,
        "post_amplitude_ms": post_amp,
        "absolute_amplitude_difference_ms": abs(pre_amp-post_amp),
        "B_nll": fit_B["nll"],
        "C_nll": fit_C["nll"]
    })

    if (i+1) % 10 == 0:
        print(
            f"Bootstrap {i+1}/{N_BOOT}; "
            f"successful={len(records)}; failures={failures}",
            flush=True
        )

if len(records) < 100:
    raise RuntimeError(
        f"Only {len(records)} successful replicates. "
        "At least 100 are required for this exploratory report."
    )

boot = pd.DataFrame(records)
boot.to_csv(OUTPUT, index=False)

# Empirical upper-tail probability under shared-signal null.
exceed = int(np.sum(boot["delta_2_nll"] >= observed_stat))
p_empirical = (exceed+1)/(len(boot)+1)

amp_exceed = int(np.sum(
    boot["absolute_amplitude_difference_ms"] >=
    observed_amp_difference
))
p_amplitude = (amp_exceed+1)/(len(boot)+1)

lines = [
    "PI MEN C - PARAMETRIC BOOTSTRAP",
    "="*72,
    f"Input: {INPUT}",
    f"Successful bootstrap replicates: {len(boot)}",
    f"Failed replicates: {failures}",
    f"Seed: {SEED}",
    f"Fixed b period: {P_B}",
    f"Fixed b eccentricity: {ECC}",
    f"Fixed b omega degrees: {np.rad2deg(OMEGA)}",
    f"Fixed c period: {P_C}",
    "",
    "OBSERVED DATA PROFILE FIT:",
    f"Model B success: {observed_B['success']}",
    f"Model C success: {observed_C['success']}",
    f"Model B NLL: {observed_B['nll']:.8f}",
    f"Model C NLL: {observed_C['nll']:.8f}",
    f"Observed 2 delta NLL: {observed_stat:.8f}",
    f"PRE amplitude in C: {obs_pre_amp:.8f} m/s",
    f"POST amplitude in C: {obs_post_amp:.8f} m/s",
    f"Observed absolute amplitude difference: {observed_amp_difference:.8f} m/s",
    "",
    "BOOTSTRAP TEST UNDER SHARED-SIGNAL MODEL B:",
    f"Replicates >= observed likelihood improvement: {exceed}",
    f"Empirical p-value: {p_empirical:.8f}",
    "",
    "AMPLITUDE DIFFERENCE DIAGNOSTIC:",
    f"Replicates with amplitude difference >= observed: {amp_exceed}",
    f"Empirical tail fraction: {p_amplitude:.8f}",
    "",
    "BOOTSTRAP 2 DELTA NLL QUANTILES:",
    str(boot["delta_2_nll"].quantile([0.50, 0.90, 0.95, 0.99])),
    "",
    "BOOTSTRAP ABSOLUTE AMPLITUDE DIFFERENCE QUANTILES:",
    str(boot["absolute_amplitude_difference_ms"].quantile(
        [0.50, 0.90, 0.95, 0.99]
    )),
    "",
    "IMPORTANT CAVEATS:",
    "- Null simulations assume the fitted shared-signal Model B is correct.",
    "- Measurement errors and fitted epoch jitters define Gaussian noise.",
    "- b period, eccentricity, omega and c period remain fixed.",
    "- This profile optimizer must be checked against the earlier DE fits.",
    "- Correlated stellar/instrumental noise is not simulated.",
    "- Bootstrap tests B versus C, not planet existence versus no planet.",
    "- Results are exploratory and conditional on the specified model."
]

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print(f"\nBootstrap CSV: {OUTPUT.resolve()}")
print(f"Report saved: {REPORT.resolve()}")
