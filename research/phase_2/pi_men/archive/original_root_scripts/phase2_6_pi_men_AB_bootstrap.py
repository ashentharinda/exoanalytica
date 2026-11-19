from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

INPUT = Path("phase2_6_pi_men_corrected_dataset.csv")
REPORT = Path("phase2_6_pi_men_AB_bootstrap_report.txt")
OUTPUT = Path("phase2_6_pi_men_AB_bootstrap_results.csv")

P_B = 2088.33
ECC = 0.6396
OMEGA = np.deg2rad(331.03)
P_C = 6.267852

N_BOOT = 1000
SEED = 20261120

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

    return np.column_stack(columns)

def fit_profile(data, model, start):

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

    return details

# ------------------------------------------------------------
# OBSERVED DATA FIT
# ------------------------------------------------------------

initial = np.array([
    192.9,
    2.64037,
    2.88,
    2.37
])

print("Fitting observed Model A...", flush=True)
observed_A = fit_profile(y_observed, "A", initial)

print("Fitting observed Model B...", flush=True)
observed_B = fit_profile(y_observed, "B", initial)

if not observed_A["success"] or not observed_B["success"]:
    raise RuntimeError(
        "Observed profile fit failed. "
        "Do not interpret bootstrap results."
    )

observed_stat = 2*(observed_A["nll"]-observed_B["nll"])

print("\nOBSERVED PROFILE FIT")
print("Model A NLL:", observed_A["nll"])
print("Model B NLL:", observed_B["nll"])
print("Observed 2 delta NLL:", observed_stat)
print("Model A optimizer:", observed_A["message"])
print("Model B optimizer:", observed_B["message"])

# ------------------------------------------------------------
# PARAMETRIC BOOTSTRAP UNDER MODEL A
# ------------------------------------------------------------

rng = np.random.default_rng(SEED)

mu_null = observed_A["prediction"]
sigma_null = np.sqrt(observed_A["variance"])

records = []
failures = 0

start_A = observed_A["theta"]
start_B = observed_B["theta"]

for i in range(N_BOOT):

    simulated = mu_null + rng.normal(
        0,
        sigma_null,
        size=N
    )

    fit_A = fit_profile(simulated, "A", start_A)
    fit_B = fit_profile(simulated, "B", start_B)

    if not fit_A["success"] or not fit_B["success"]:
        failures += 1
        print(
            f"Bootstrap {i+1}/{N_BOOT}: optimizer failure",
            flush=True
        )
        continue

    statistic = 2*(fit_A["nll"]-fit_B["nll"])

    records.append({
        "replicate": i+1,
        "delta_2_nll": statistic,
        "A_nll": fit_A["nll"],
        "B_nll": fit_B["nll"],
        "A_K_ms": fit_A["theta"][0],
        "B_K_ms": fit_B["theta"][0]
    })

    if (i+1) % 50 == 0:
        print(
            f"Bootstrap {i+1}/{N_BOOT}; "
            f"successful={len(records)}; failures={failures}",
            flush=True
        )

if len(records) < 800:
    raise RuntimeError(
        f"Only {len(records)} successful replicates. "
        "At least 800 are required for this exploratory test."
    )

boot = pd.DataFrame(records)
boot.to_csv(OUTPUT, index=False)

# ------------------------------------------------------------
# EMPIRICAL SIGNIFICANCE
# ------------------------------------------------------------

exceed = int(
    np.sum(boot["delta_2_nll"] >= observed_stat)
)

p_empirical = (exceed+1)/(len(boot)+1)

quantiles = boot["delta_2_nll"].quantile(
    [0.50, 0.90, 0.95, 0.99]
)

lines = [
    "PI MEN C - MODEL A VS MODEL B PARAMETRIC BOOTSTRAP",
    "="*72,
    f"Input: {INPUT}",
    f"Observations: {N}",
    f"PRE observations: {int(pre.sum())}",
    f"POST observations: {int(post.sum())}",
    f"Successful replicates: {len(boot)}",
    f"Failed replicates: {failures}",
    f"Seed: {SEED}",
    f"Bootstrap requested: {N_BOOT}",
    "",
    "FIXED PARAMETERS:",
    f"b period: {P_B}",
    f"b eccentricity: {ECC}",
    f"b omega degrees: {np.rad2deg(OMEGA)}",
    f"c period: {P_C}",
    "",
    "OBSERVED DATA FIT:",
    f"Model A success: {observed_A['success']}",
    f"Model B success: {observed_B['success']}",
    f"Model A NLL: {observed_A['nll']:.8f}",
    f"Model B NLL: {observed_B['nll']:.8f}",
    f"Observed 2 delta NLL: {observed_stat:.8f}",
    "",
    "BOOTSTRAP TEST UNDER MODEL A:",
    f"Replicates >= observed improvement: {exceed}",
    f"Empirical p-value: {p_empirical:.8f}",
    "",
    "BOOTSTRAP 2 DELTA NLL QUANTILES:",
    str(quantiles),
    "",
    "IMPORTANT CAVEATS:",
    "- Null simulations assume Model A is correct.",
    "- Noise assumes independent Gaussian errors.",
    "- Measurement errors and fitted epoch jitters define the noise.",
    "- b period, eccentricity and omega remain fixed.",
    "- c period is fixed at the tested published period.",
    "- Correlated stellar/instrumental noise is not simulated.",
    "- This is a conditional test, not definitive planet confirmation.",
    "- Period-search trial factors are not included.",
    "- Results require independent scientific validation."
]

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("\n".join(lines))
print(f"\nBootstrap CSV: {OUTPUT.resolve()}")
print(f"Report saved: {REPORT.resolve()}")
