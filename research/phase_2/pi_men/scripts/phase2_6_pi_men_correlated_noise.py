from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize

INPUT = DATA_DIR / "phase2_6_pi_men_corrected_dataset.csv"
REPORT = REPORTS_DIR / "phase2_6_pi_men_correlated_noise_report.txt"
OUTPUT = RESULTS_DIR / "phase2_6_pi_men_correlated_noise_results.csv"

P_B = 2088.33
ECC = 0.6396
OMEGA = np.deg2rad(331.03)
P_C = 6.267852

BLOCK_LENGTHS = [2, 3, 5, 10]
N_BOOT = 500
SEED = 20261121

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

y = df["rv_corrected_ms"].to_numpy(float)
dy = df["rv_error_ms"].to_numpy(float)

pre = df["instrument_epoch"].eq("HARPS_PRE").to_numpy()
post = ~pre
N = len(y)

M = 2*np.pi*t/P_B
angle = 2*np.pi*t/P_C

epoch_indices = {
    "PRE": np.where(pre)[0],
    "POST": np.where(post)[0]
}

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

def moving_block_sample(values, n, block_length, rng):
    """Circular moving-block bootstrap of an ordered residual series."""
    values = np.asarray(values, dtype=float)
    m = len(values)

    if m == 0:
        raise ValueError("Empty residual series")

    pieces = []

    while sum(len(piece) for piece in pieces) < n:
        start = rng.integers(0, m)
        indices = (start + np.arange(block_length)) % m
        pieces.append(values[indices])

    return np.concatenate(pieces)[:n]

def acf_values(values, max_lag=10):
    values = np.asarray(values, dtype=float)
    values = values - np.mean(values)

    denominator = np.dot(values, values)

    if denominator == 0:
        return {}

    return {
        lag: float(np.dot(values[:-lag], values[lag:])/denominator)
        for lag in range(1, min(max_lag, len(values)-1)+1)
    }

# ------------------------------------------------------------
# FIT NULL MODEL A TO OBSERVED DATA
# ------------------------------------------------------------

initial = np.array([192.9, 2.64037, 2.88, 2.37])

print("Fitting observed Model A...", flush=True)
observed_A = fit_profile(y, "A", initial)

print("Fitting observed Model B...", flush=True)
observed_B = fit_profile(y, "B", initial)

if not observed_A["success"] or not observed_B["success"]:
    raise RuntimeError("Observed profile fit failed.")

observed_stat = 2*(observed_A["nll"]-observed_B["nll"])

print("\nOBSERVED FIT")
print("Model A NLL:", observed_A["nll"])
print("Model B NLL:", observed_B["nll"])
print("Observed 2 delta NLL:", observed_stat)

# ------------------------------------------------------------
# STANDARDIZED MODEL A RESIDUALS
# ------------------------------------------------------------

sigma = np.sqrt(observed_A["variance"])
standardized = observed_A["residual"]/sigma

# Center and normalize separately within each epoch.
# This preserves within-epoch residual ordering and local structure.
epoch_residuals = {}

for name, idx in epoch_indices.items():
    values = standardized[idx].copy()
    values -= np.mean(values)

    scale = np.std(values, ddof=1)

    if not np.isfinite(scale) or scale <= 0:
        raise RuntimeError(f"Invalid residual scale for {name}")

    values /= scale
    epoch_residuals[name] = values

# Residual autocorrelation diagnostic.
acf_lines = []

for name, values in epoch_residuals.items():
    acf = acf_values(values, 10)
    acf_lines.append(f"{name} residual ACF:")
    for lag, value in acf.items():
        acf_lines.append(f"  Lag {lag}: {value:.6f}")

# ------------------------------------------------------------
# MOVING-BLOCK BOOTSTRAP
# ------------------------------------------------------------

rng = np.random.default_rng(SEED)

mu_null = observed_A["prediction"]
sigma_null = np.sqrt(observed_A["variance"])

start_A = observed_A["theta"]
start_B = observed_B["theta"]

all_records = []

for block_length in BLOCK_LENGTHS:

    print(
        f"\nStarting block length {block_length}; "
        f"{N_BOOT} replicates",
        flush=True
    )

    records = []
    failures = 0

    for i in range(N_BOOT):

        simulated_standardized = np.empty(N)

        # Resample separately within PRE and POST.
        for name, idx in epoch_indices.items():
            sampled = moving_block_sample(
                epoch_residuals[name],
                len(idx),
                block_length,
                rng
            )
            simulated_standardized[idx] = sampled

        simulated = (
            mu_null +
            sigma_null*simulated_standardized
        )

        fit_A = fit_profile(simulated, "A", start_A)
        fit_B = fit_profile(simulated, "B", start_B)

        if not fit_A["success"] or not fit_B["success"]:
            failures += 1
            continue

        statistic = 2*(fit_A["nll"]-fit_B["nll"])

        records.append({
            "block_length_observations": block_length,
            "replicate": i+1,
            "delta_2_nll": statistic,
            "A_nll": fit_A["nll"],
            "B_nll": fit_B["nll"]
        })

        if (i+1) % 50 == 0:
            print(
                f"Block {block_length}: {i+1}/{N_BOOT}; "
                f"success={len(records)}; failures={failures}",
                flush=True
            )

    if len(records) < int(0.8*N_BOOT):
        raise RuntimeError(
            f"Too few successful fits for block length {block_length}: "
            f"{len(records)}/{N_BOOT}"
        )

    block_df = pd.DataFrame(records)

    exceed = int(
        np.sum(block_df["delta_2_nll"] >= observed_stat)
    )

    p_value = (exceed+1)/(len(block_df)+1)

    all_records.extend(records)

    print(
        f"BLOCK {block_length} SUMMARY: "
        f"successful={len(records)}, "
        f"failures={failures}, "
        f"exceedances={exceed}, "
        f"p={p_value:.8f}",
        flush=True
    )

# ------------------------------------------------------------
# SAVE RESULTS
# ------------------------------------------------------------

results = pd.DataFrame(all_records)
results.to_csv(OUTPUT, index=False)

summary = []

for block_length in BLOCK_LENGTHS:
    subset = results[
        results["block_length_observations"] == block_length
    ]

    exceed = int(
        np.sum(subset["delta_2_nll"] >= observed_stat)
    )

    p_value = (exceed+1)/(len(subset)+1)

    q = subset["delta_2_nll"].quantile(
        [0.50, 0.90, 0.95, 0.99]
    )

    summary.append({
        "block_length": block_length,
        "successful": len(subset),
        "exceedances": exceed,
        "empirical_p": p_value,
        "q50": q.loc[0.50],
        "q90": q.loc[0.90],
        "q95": q.loc[0.95],
        "q99": q.loc[0.99]
    })

summary_df = pd.DataFrame(summary)

lines = [
    "PI MEN C - CORRELATED NOISE ROBUSTNESS TEST",
    "="*72,
    f"Input: {INPUT}",
    f"Observations: {N}",
    f"PRE observations: {int(pre.sum())}",
    f"POST observations: {int(post.sum())}",
    f"Bootstrap replicates per block length: {N_BOOT}",
    f"Block lengths: {BLOCK_LENGTHS}",
    f"Seed: {SEED}",
    "",
    "OBSERVED MODEL COMPARISON:",
    f"Model A NLL: {observed_A['nll']:.8f}",
    f"Model B NLL: {observed_B['nll']:.8f}",
    f"Observed 2 delta NLL: {observed_stat:.8f}",
    "",
    "STANDARDIZED RESIDUAL ACF:",
    *acf_lines,
    "",
    "MOVING-BLOCK BOOTSTRAP SUMMARY:",
    summary_df.to_string(index=False),
    "",
    "INTERPRETATION NOTES:",
    "- Blocks are consecutive observations within each instrument epoch.",
    "- PRE and POST residual sequences are resampled separately.",
    "- This preserves short-range ordering approximately, not exact time correlations.",
    "- Irregular time gaps mean block length is not a fixed number of days.",
    "- This is a residual bootstrap conditional on fitted Model A.",
    "- It does not prove the residual process is stationary.",
    "- It does not fully model long-term correlated stellar or instrumental noise.",
    "- The c period is fixed; period-search trial factors are not included.",
    "- Results are exploratory and require further validation."
]

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("\n" + "\n".join(lines))
print(f"\nCSV: {OUTPUT.resolve()}")
print(f"Report: {REPORT.resolve()}")
