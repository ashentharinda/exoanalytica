from pathlib import Path
import json
import sys
import platform
import time
import warnings

import numpy as np
import pandas as pd
import scipy
from scipy.optimize import minimize
from scipy.linalg import cholesky, solve_triangular

warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parents[1]
INPUT_RESIDUALS = (
    ROOT / "experiments" /
    "HD115617_keplerian_validation_v1" / "residuals.csv"
)
INPUT_RAW = ROOT / "data" / "input" / "harps_rv_observations_18_targets.csv"
OUTPUT = ROOT / "experiments" / "HD115617_correlated_noise_validation_v1"

TARGET = "HD115617"
MODEL = "PLUS_BOTH"


def fail(message):
    raise RuntimeError(message)


def load_data():
    if not INPUT_RESIDUALS.exists():
        fail(f"Missing residuals file: {INPUT_RESIDUALS}")

    if not INPUT_RAW.exists():
        fail(f"Missing raw observations file: {INPUT_RAW}")

    residuals = pd.read_csv(INPUT_RESIDUALS)
    raw = pd.read_csv(INPUT_RAW)

    required_residual = [
        "model", "BJD", "residual_rv_mps",
        "measurement_error_mps", "fitted_jitter_mps",
        "total_sigma_mps"
    ]
    required_raw = ["tel_object", "drs_bjd", "date_obs"]

    for col in required_residual:
        if col not in residuals.columns:
            fail(f"Missing residual column: {col}")

    for col in required_raw:
        if col not in raw.columns:
            fail(f"Missing raw input column: {col}")

    data = residuals.loc[
        residuals["model"].astype(str) == MODEL
    ].copy()

    data["BJD"] = pd.to_numeric(data["BJD"], errors="coerce")
    numeric = [
        "residual_rv_mps",
        "measurement_error_mps",
        "fitted_jitter_mps",
        "total_sigma_mps"
    ]

    for col in numeric:
        data[col] = pd.to_numeric(data[col], errors="coerce")

    data = data.dropna(subset=["BJD"] + numeric)
    data = data.sort_values("BJD").reset_index(drop=True)

    data = data[
        (data["total_sigma_mps"] > 0) &
        (data["measurement_error_mps"] > 0)
    ].copy()

    raw_target = raw[
        raw["tel_object"].astype(str).str.strip() == TARGET
    ].copy()

    raw_target["drs_bjd"] = pd.to_numeric(
        raw_target["drs_bjd"], errors="coerce"
    )
    raw_target = raw_target.dropna(subset=["drs_bjd"])

    # Exact timestamp mapping was verified in the preceding audit.
    date_map = dict(zip(raw_target["drs_bjd"], raw_target["date_obs"]))
    data["date_obs"] = data["BJD"].map(date_map)

    if len(data) != 1213:
        print(
            f"WARNING: Expected 1213 residual rows; found {len(data)}."
        )

    if data["date_obs"].isna().any():
        fail(
            "Some residual BJD timestamps could not be mapped to "
            "original HARPS date_obs values. Stopping."
        )

    t = data["BJD"].to_numpy(dtype=float)
    y = data["residual_rv_mps"].to_numpy(dtype=float)
    sigma = data["total_sigma_mps"].to_numpy(dtype=float)

    if len(t) < 20:
        fail("Insufficient observations.")

    if np.any(np.diff(t) < 0):
        fail("BJD timestamps are not sorted.")

    return data, t, y, sigma


def gaussian_loglike_white(y, sigma):
    weights = 1.0 / sigma**2
    mu = np.sum(weights * y) / np.sum(weights)
    residual = y - mu

    variance = sigma**2
    loglike = -0.5 * np.sum(
        residual**2 / variance + np.log(2.0 * np.pi * variance)
    )

    return float(loglike), float(mu)


def ou_kalman_loglike(t, y, sigma, mu, amplitude, tau, return_details=False):
    """
    Exact irregular-time OU / continuous-time AR(1) likelihood.

    Latent covariance:
        K(i,j) = amplitude^2 * exp(-abs(t_i-t_j)/tau)

    Measurement variance:
        total_sigma_mps^2

    The OU latent process is stationary at the first observation.
    """

    if amplitude <= 0 or tau <= 0:
        return (-np.inf, None) if return_details else -np.inf

    residual = y - mu
    latent_variance = amplitude**2

    state_mean = 0.0
    state_variance = latent_variance

    loglike = 0.0
    innovations = []
    innovation_variances = []

    for i in range(len(t)):
        if i > 0:
            dt = t[i] - t[i - 1]

            if dt < 0:
                return (-np.inf, None) if return_details else -np.inf

            phi = np.exp(-dt / tau)
            state_mean = phi * state_mean
            state_variance = (
                phi**2 * state_variance
                + latent_variance * (1.0 - phi**2)
            )

        observation_variance = sigma[i]**2
        innovation_variance = state_variance + observation_variance

        if not np.isfinite(innovation_variance) or innovation_variance <= 0:
            return (-np.inf, None) if return_details else -np.inf

        innovation = residual[i] - state_mean

        loglike += -0.5 * (
            innovation**2 / innovation_variance
            + np.log(2.0 * np.pi * innovation_variance)
        )

        gain = state_variance / innovation_variance
        state_mean += gain * innovation
        state_variance *= 1.0 - gain

        innovations.append(innovation)
        innovation_variances.append(innovation_variance)

    if return_details:
        details = {
            "innovation": np.asarray(innovations),
            "innovation_variance": np.asarray(innovation_variances),
        }
        return float(loglike), details

    return float(loglike)


def fit_ou(t, y, sigma):
    """
    Fit constant mean, OU amplitude and OU timescale.
    Multiple deterministic starting points reduce local-minimum risk.
    """

    spread = max(float(np.std(y)), 0.1)
    initial_taus = [0.5, 2.0, 7.0, 30.0, 100.0, 365.0]

    bounds = [
        (-100.0, 100.0),
        (np.log(1e-4), np.log(100.0)),
        (np.log(0.01), np.log(20000.0)),
    ]

    candidates = []

    def objective(params):
        mu, log_amp, log_tau = params
        amp = np.exp(log_amp)
        tau = np.exp(log_tau)

        ll = ou_kalman_loglike(t, y, sigma, mu, amp, tau)

        if not np.isfinite(ll):
            return 1e100

        return -ll

    for tau0 in initial_taus:
        start = [
            float(np.average(y, weights=1.0 / sigma**2)),
            np.log(spread * 0.5),
            np.log(tau0),
        ]

        result = minimize(
            objective,
            start,
            method="L-BFGS-B",
            bounds=bounds,
            options={
                "maxiter": 3000,
                "ftol": 1e-11,
                "maxls": 40,
            },
        )

        if np.isfinite(result.fun):
            candidates.append(result)

    if not candidates:
        fail("All OU optimization attempts failed.")

    best = min(candidates, key=lambda r: r.fun)

    mu, log_amp, log_tau = best.x
    amplitude = float(np.exp(log_amp))
    tau = float(np.exp(log_tau))

    loglike, details = ou_kalman_loglike(
        t, y, sigma, mu, amplitude, tau, return_details=True
    )

    return {
        "mu": float(mu),
        "amplitude": amplitude,
        "tau_days": tau,
        "loglike": float(loglike),
        "success": bool(best.success),
        "optimizer_message": str(best.message),
        "iterations": int(best.nit),
        "details": details,
    }


def exponential_gp_dense_loglike(t, y, sigma, mu, amplitude, tau):
    """
    Dense covariance implementation of the same exponential kernel.
    Used as an independent likelihood cross-check at the OU optimum.
    """

    dt = np.abs(t[:, None] - t[None, :])
    covariance = amplitude**2 * np.exp(-dt / tau)
    covariance.flat[::len(t) + 1] += sigma**2

    try:
        lower = cholesky(
            covariance,
            lower=True,
            check_finite=False
        )

        residual = y - mu
        solved = solve_triangular(
            lower, residual, lower=True, check_finite=False
        )

        logdet = 2.0 * np.sum(np.log(np.diag(lower)))

        loglike = -0.5 * (
            np.dot(solved, solved)
            + logdet
            + len(t) * np.log(2.0 * np.pi)
        )

        return float(loglike)

    except Exception as exc:
        fail(f"Dense exponential GP Cholesky failed: {exc}")


def information_criteria(loglike, k, n):
    aic = 2.0 * k - 2.0 * loglike
    bic = k * np.log(n) - 2.0 * loglike
    return float(aic), float(bic)


def main():
    started = time.time()

    if OUTPUT.exists():
        fail(
            f"Output folder already exists: {OUTPUT}. "
            "Refusing to overwrite existing results."
        )

    OUTPUT.mkdir(parents=True, exist_ok=False)

    print("===== HD115617 CORRELATED-NOISE VALIDATION V1 =====")
    print("Loading residuals and original HARPS timestamp metadata...")

    data, t, y, sigma = load_data()
    n = len(y)

    print(f"Target: {TARGET}")
    print(f"Model residuals: {MODEL}")
    print(f"Observations: {n}")
    print(f"Unique UTC date_obs: {data['date_obs'].nunique()}")
    print(f"BJD baseline: {t.max() - t.min():.6f} days")
    print(f"Residual standard deviation: {np.std(y):.6f} m/s")

    print("\n===== 1. WHITE GAUSSIAN BASELINE =====")

    white_ll, white_mu = gaussian_loglike_white(y, sigma)
    white_aic, white_bic = information_criteria(
        white_ll, 1, n
    )

    print(f"White log-likelihood: {white_ll:.8f}")
    print(f"White mean: {white_mu:.8f} m/s")
    print(f"White AIC: {white_aic:.6f}")
    print(f"White BIC: {white_bic:.6f}")

    print("\n===== 2. IRREGULAR-TIME OU / AR(1) FIT =====")

    ou = fit_ou(t, y, sigma)
    ou_aic, ou_bic = information_criteria(
        ou["loglike"], 3, n
    )

    print(f"Optimizer success: {ou['success']}")
    print(f"OU log-likelihood: {ou['loglike']:.8f}")
    print(f"OU mean: {ou['mu']:.8f} m/s")
    print(f"OU amplitude: {ou['amplitude']:.8f} m/s")
    print(f"OU timescale: {ou['tau_days']:.8f} days")
    print(f"OU AIC: {ou_aic:.6f}")
    print(f"OU BIC: {ou_bic:.6f}")

    print("\n===== 3. EXPONENTIAL GP DENSE CROSS-CHECK =====")

    gp_ll = exponential_gp_dense_loglike(
        t, y, sigma,
        ou["mu"], ou["amplitude"], ou["tau_days"]
    )

    gp_aic, gp_bic = information_criteria(gp_ll, 3, n)
    likelihood_difference = abs(gp_ll - ou["loglike"])

    print(f"Dense GP log-likelihood: {gp_ll:.8f}")
    print(f"OU vs GP absolute log-likelihood difference: "
          f"{likelihood_difference:.10g}")

    print("\n===== 4. MODEL COMPARISON =====")

    rows = [
        {
            "model": "WHITE_GAUSSIAN",
            "implementation": "Independent Gaussian",
            "log_likelihood": white_ll,
            "parameter_count": 1,
            "AIC": white_aic,
            "BIC": white_bic,
        },
        {
            "model": "OU_CONTINUOUS_TIME_AR1",
            "implementation": "Irregular-time Kalman filter",
            "log_likelihood": ou["loglike"],
            "parameter_count": 3,
            "AIC": ou_aic,
            "BIC": ou_bic,
        },
        {
            "model": "EXPONENTIAL_GP_CROSSCHECK",
            "implementation": "Dense covariance Cholesky",
            "log_likelihood": gp_ll,
            "parameter_count": 3,
            "AIC": gp_aic,
            "BIC": gp_bic,
        },
    ]

    comparison = pd.DataFrame(rows)
    comparison["delta_BIC_vs_white"] = (
        comparison["BIC"] - white_bic
    )
    comparison.to_csv(
        OUTPUT / "model_comparison.csv", index=False
    )

    parameter_rows = [
        {
            "model": "WHITE_GAUSSIAN",
            "parameter": "mean_mps",
            "value": white_mu,
            "unit": "m/s",
        },
        {
            "model": "OU_CONTINUOUS_TIME_AR1",
            "parameter": "mean_mps",
            "value": ou["mu"],
            "unit": "m/s",
        },
        {
            "model": "OU_CONTINUOUS_TIME_AR1",
            "parameter": "correlated_amplitude_mps",
            "value": ou["amplitude"],
            "unit": "m/s",
        },
        {
            "model": "OU_CONTINUOUS_TIME_AR1",
            "parameter": "correlation_timescale_days",
            "value": ou["tau_days"],
            "unit": "days",
        },
    ]

    pd.DataFrame(parameter_rows).to_csv(
        OUTPUT / "fitted_parameters.csv", index=False
    )

    details = ou["details"]
    diagnostics = data[
        ["BJD", "date_obs", "residual_rv_mps",
         "measurement_error_mps", "fitted_jitter_mps",
         "total_sigma_mps"]
    ].copy()

    diagnostics["OU_innovation_mps"] = details["innovation"]
    diagnostics["OU_innovation_variance"] = (
        details["innovation_variance"]
    )
    diagnostics["OU_standardized_innovation"] = (
        diagnostics["OU_innovation_mps"] /
        np.sqrt(diagnostics["OU_innovation_variance"])
    )

    diagnostics.to_csv(
        OUTPUT / "residual_diagnostics.csv", index=False
    )

    metadata = {
        "experiment": "HD115617_correlated_noise_validation_v1",
        "target": TARGET,
        "residual_model": MODEL,
        "input_residuals": str(INPUT_RESIDUALS),
        "input_raw_observations": str(INPUT_RAW),
        "observations": int(n),
        "unique_date_obs": int(data["date_obs"].nunique()),
        "bjd_min": float(t.min()),
        "bjd_max": float(t.max()),
        "baseline_days": float(t.max() - t.min()),
        "white_log_likelihood": white_ll,
        "ou_log_likelihood": ou["loglike"],
        "dense_gp_log_likelihood": gp_ll,
        "ou_gp_abs_loglike_difference": likelihood_difference,
        "ou_optimizer_success": ou["success"],
        "ou_optimizer_message": ou["optimizer_message"],
        "ou_optimizer_iterations": ou["iterations"],
        "ou_mean_mps": ou["mu"],
        "ou_amplitude_mps": ou["amplitude"],
        "ou_timescale_days": ou["tau_days"],
        "timestamp_source": "Exact BJD matched to original drs_bjd",
        "night_metadata": "Original HARPS date_obs UTC calendar date",
        "measurement_variance": "total_sigma_mps squared",
        "correlated_process": "Stationary exponential OU covariance",
        "limitations": [
            "Conditional analysis of PLUS_BOTH residuals.",
            "Keplerian parameters were not jointly refitted.",
            "Candidate periods were previously selected using this dataset.",
            "OU and exponential-kernel GP are mathematically equivalent here.",
            "Dense GP is a likelihood implementation cross-check, not an independent noise hypothesis.",
            "AIC/BIC comparisons do not account for earlier period-selection uncertainty.",
            "Correlated noise does not identify its physical origin.",
            "No planet confirmation is implied."
        ],
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "runtime_seconds": float(time.time() - started),
    }

    with open(OUTPUT / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    report = []
    report.append("HD115617 CORRELATED-NOISE VALIDATION V1")
    report.append("=" * 55)
    report.append(f"Target: {TARGET}")
    report.append(f"Residual model: {MODEL}")
    report.append(f"Observations: {n}")
    report.append(f"Unique original UTC dates: {data['date_obs'].nunique()}")
    report.append(f"BJD baseline: {t.max() - t.min():.6f} days")
    report.append("")
    report.append("MODEL COMPARISON")
    report.append(comparison.to_string(index=False))
    report.append("")
    report.append("FITTED OU PARAMETERS")
    report.append(f"Mean: {ou['mu']:.8f} m/s")
    report.append(f"Amplitude: {ou['amplitude']:.8f} m/s")
    report.append(f"Timescale: {ou['tau_days']:.8f} days")
    report.append("")
    report.append("IMPLEMENTATION CROSS-CHECK")
    report.append(f"OU Kalman log-likelihood: {ou['loglike']:.12f}")
    report.append(f"Dense GP log-likelihood: {gp_ll:.12f}")
    report.append(f"Absolute difference: {likelihood_difference:.12g}")
    report.append("")
    report.append("INTERPRETATION GUIDANCE")
    report.append(
        "A lower BIC indicates a preferred model among the compared "
        "likelihood models, subject to the assumptions and limitations."
    )
    report.append(
        "The OU process and exponential-kernel GP are the same "
        "covariance model in this experiment. Their likelihoods should "
        "agree within numerical tolerance."
    )
    report.append(
        "A correlated-noise preference is evidence of residual temporal "
        "structure, not proof that the structure is stellar activity, "
        "instrumental noise, or a planet."
    )
    report.append(
        "The comparison is conditional on residuals from the existing "
        "PLUS_BOTH Keplerian fit. It is not a joint Keplerian-plus-GP refit."
    )
    report.append("")
    report.append("Optimizer success: " + str(ou["success"]))
    report.append("Optimizer message: " + ou["optimizer_message"])
    report.append(f"Runtime: {time.time() - started:.2f} seconds")

    (OUTPUT / "report.txt").write_text(
        "\n".join(report), encoding="utf-8"
    )

    print("\n===== OUTPUT FILES =====")
    for path in sorted(OUTPUT.iterdir()):
        print(f"{path.name} ({path.stat().st_size:,} bytes)")

    print("\n===== FINAL STATUS =====")
    print("Experiment completed.")
    print(f"Output: {OUTPUT}")
    print("No production application files were modified.")


if __name__ == "__main__":
    main()
