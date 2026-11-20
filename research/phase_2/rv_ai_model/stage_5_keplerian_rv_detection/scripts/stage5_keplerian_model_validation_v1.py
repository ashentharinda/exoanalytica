from pathlib import Path
import json
import sys
import time
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import minimize

warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input" / "harps_rv_observations_18_targets.csv"
OUTPUT = ROOT / "experiments" / "HD115617_keplerian_validation_v1"

TARGET = "HD115617"
PERIODS = {
    "P_4.214d": 4.21421445,
    "P_38.051d": 38.0511147476,
    "P_123.666d": 123.666123,
    "P_184.576d": 184.576303,
}
MODELS = {
    "BASE_2": ["P_4.214d", "P_38.051d"],
    "PLUS_123": ["P_4.214d", "P_38.051d", "P_123.666d"],
    "PLUS_185": ["P_4.214d", "P_38.051d", "P_184.576d"],
    "PLUS_BOTH": ["P_4.214d", "P_38.051d", "P_123.666d", "P_184.576d"],
}

def solve_kepler(mean_anomaly, eccentricity):
    """Vectorized Newton solution of E - e sin(E) = M."""
    M = (mean_anomaly + np.pi) % (2.0 * np.pi) - np.pi
    E = M + eccentricity * np.sin(M)
    for _ in range(40):
        f = E - eccentricity * np.sin(E) - M
        fp = 1.0 - eccentricity * np.cos(E)
        step = f / fp
        E -= step
        if np.max(np.abs(step)) < 1e-11:
            break
    return E

def keplerian_rv(t, period, K, e, omega, M0, t0):
    M = M0 + 2.0 * np.pi * (t - t0) / period
    E = solve_kepler(M, e)
    nu = np.arctan2(
        np.sqrt(1.0 - e * e) * np.sin(E),
        np.cos(E) - e
    )
    return K * (np.cos(nu + omega) + e * np.cos(omega))

def unpack(theta, names):
    gamma, beta, jitter = theta[:3]
    planets = {}
    offset = 3
    for name in names:
        K, e, omega, M0 = theta[offset:offset + 4]
        planets[name] = (K, e, omega, M0)
        offset += 4
    return gamma, beta, jitter, planets

def predict(theta, names, t, t0, bis):
    gamma, beta, jitter, planets = unpack(theta, names)
    model = gamma + beta * bis
    for name, (K, e, omega, M0) in planets.items():
        model += keplerian_rv(
            t, PERIODS[name], K, e, omega, M0, t0
        )
    return model, jitter

def negative_log_likelihood(theta, names, t, y, err, t0, bis):
    model, jitter = predict(theta, names, t, t0, bis)
    variance = err * err + jitter * jitter
    residual = y - model
    return 0.5 * np.sum(
        residual * residual / variance + np.log(2.0 * np.pi * variance)
    )

def initial_linear_solution(names, t, y, err, bis, t0):
    columns = [np.ones(len(t)), bis]
    for name in names:
        phase = 2.0 * np.pi * (t - t0) / PERIODS[name]
        columns.extend([np.sin(phase), np.cos(phase)])
    design = np.column_stack(columns)
    weighted_design = design / err[:, None]
    weighted_y = y / err
    coeff, *_ = np.linalg.lstsq(weighted_design, weighted_y, rcond=None)
    return coeff

def fit_model(model_name, names, t, y, err, bis, t0):
    linear = initial_linear_solution(names, t, y, err, bis, t0)

    gamma0 = float(linear[0])
    beta0 = float(linear[1])
    planet_initials = {}
    for i, name in enumerate(names):
        a = float(linear[2 + 2 * i])
        b = float(linear[3 + 2 * i])
        K0 = max(0.05, min(30.0, float(np.hypot(a, b))))
        phase0 = float(np.arctan2(-a, b))
        planet_initials[name] = (K0, phase0)

    bounds = [
        (None, None), (-100.0, 100.0), (0.01, 30.0)
    ]
    for _ in names:
        bounds.extend([
            (0.001, 30.0),
            (0.0, 0.8),
            (-np.pi, np.pi),
            (-np.pi, np.pi),
        ])

    best = None
    starts = [
        (0.02, 0.0),
        (0.15, 0.7),
        (0.35, -0.7),
    ]

    for eccentricity_start, omega_start in starts:
        theta = [gamma0, beta0, 2.0]
        for name in names:
            K0, phase0 = planet_initials[name]
            M0 = (phase0 - omega_start + np.pi) % (2*np.pi) - np.pi
            theta.extend([K0, eccentricity_start, omega_start, M0])

        result = minimize(
            negative_log_likelihood,
            np.asarray(theta, dtype=float),
            args=(names, t, y, err, t0, bis),
            method="L-BFGS-B",
            bounds=bounds,
            options={"maxiter": 3000, "ftol": 1e-11, "maxls": 40},
        )

        if np.isfinite(result.fun) and (
            best is None or result.fun < best.fun
        ):
            best = result

    if best is None:
        raise RuntimeError(f"No finite optimizer solution for {model_name}")

    model, jitter = predict(best.x, names, t, t0, bis)
    residual = y - model
    sigma_total = np.sqrt(err * err + jitter * jitter)
    chi2 = float(np.sum((residual / sigma_total) ** 2))
    n = len(y)
    k = len(best.x)
    log_likelihood = float(-best.fun)
    bic = float(k * np.log(n) - 2.0 * log_likelihood)
    aic = float(2.0 * k - 2.0 * log_likelihood)

    metrics = {
        "model": model_name,
        "signals": ";".join(names),
        "n_observations": n,
        "n_parameters": k,
        "optimizer_success": bool(best.success),
        "optimizer_message": str(best.message),
        "negative_log_likelihood": float(best.fun),
        "log_likelihood": log_likelihood,
        "BIC": bic,
        "AIC": aic,
        "chi2_with_jitter": chi2,
        "reduced_chi2_with_jitter": chi2 / max(1, n-k),
        "residual_rms_mps": float(np.sqrt(np.mean(residual**2))),
        "weighted_residual_rms_mps": float(
            np.sqrt(np.mean((residual / sigma_total)**2))
        ),
        "fitted_jitter_mps": float(jitter),
        "BIS_coefficient_mps_per_std": float(best.x[1]),
        "fit_iterations": int(best.nit),
    }

    parameters = []
    gamma, beta, jitter, planets = unpack(best.x, names)
    parameters.append({
        "model": model_name, "parameter": "gamma",
        "value": gamma, "unit": "m/s"
    })
    parameters.append({
        "model": model_name, "parameter": "BIS_coefficient",
        "value": beta, "unit": "m/s per standardized BIS"
    })
    parameters.append({
        "model": model_name, "parameter": "jitter",
        "value": jitter, "unit": "m/s"
    })

    for name, (K, e, omega, M0) in planets.items():
        for parameter, value, unit in [
            ("period", PERIODS[name], "day"),
            ("semi_amplitude_K", K, "m/s"),
            ("eccentricity", e, "dimensionless"),
            ("omega", omega, "radian"),
            ("mean_anomaly_at_reference", M0, "radian"),
        ]:
            parameters.append({
                "model": model_name,
                "parameter": f"{name}_{parameter}",
                "value": float(value),
                "unit": unit,
            })

    residual_frame = pd.DataFrame({
        "model": model_name,
        "BJD": t,
        "observed_rv_mps": y,
        "model_rv_mps": model,
        "residual_rv_mps": residual,
        "measurement_error_mps": err,
        "fitted_jitter_mps": jitter,
        "total_sigma_mps": sigma_total,
        "standardized_BIS_span": bis,
    })
    return metrics, parameters, residual_frame

def main():
    started = time.time()
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)
    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing experiment: {OUTPUT}"
        )

    df = pd.read_csv(INPUT)
    required = ["tel_object", "drs_bjd", "rv_mps", "drs_dvrms", "drs_bis_span"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    target = df[
        df["tel_object"].astype(str).str.contains(
            TARGET, case=False, regex=False, na=False
        )
    ].copy()

    for col in ["drs_bjd", "rv_mps", "drs_dvrms", "drs_bis_span"]:
        target[col] = pd.to_numeric(target[col], errors="coerce")

    before = len(target)
    target = target.replace([np.inf, -np.inf], np.nan)
    target = target.dropna(subset=required[1:])
    target = target[target["drs_dvrms"] > 0].copy()
    target = target.sort_values("drs_bjd").reset_index(drop=True)

    if len(target) < 100:
        raise ValueError(f"Insufficient valid observations: {len(target)}")

    t = target["drs_bjd"].to_numpy(float)
    y = target["rv_mps"].to_numpy(float)
    err = target["drs_dvrms"].to_numpy(float)
    bis_raw = target["drs_bis_span"].to_numpy(float)

    bis_mean = float(np.mean(bis_raw))
    bis_std = float(np.std(bis_raw, ddof=0))
    if not np.isfinite(bis_std) or bis_std == 0:
        raise ValueError("BIS span has zero or invalid standard deviation")
    bis = (bis_raw - bis_mean) / bis_std
    t0 = float(np.median(t))

    print(f"Target: {TARGET}")
    print(f"Input rows: {before}")
    print(f"Valid rows: {len(target)}")
    print(f"Excluded invalid rows: {before-len(target)}")
    print(f"Baseline: {t.max()-t.min():.6f} days")
    print("Starting conditional fixed-period Keplerian model fits...")

    summary = []
    parameter_rows = []
    residual_frames = []

    for model_name, names in MODELS.items():
        print(f"\nFitting {model_name}: {', '.join(names)}")
        metrics, parameters, residuals = fit_model(
            model_name, names, t, y, err, bis, t0
        )
        summary.append(metrics)
        parameter_rows.extend(parameters)
        residual_frames.append(residuals)
        print(
            f"  BIC={metrics['BIC']:.3f}; "
            f"jitter={metrics['fitted_jitter_mps']:.3f} m/s; "
            f"RMS={metrics['residual_rms_mps']:.3f} m/s; "
            f"success={metrics['optimizer_success']}"
        )

    summary_df = pd.DataFrame(summary).sort_values("BIC")
    summary_df["delta_BIC"] = summary_df["BIC"] - summary_df["BIC"].min()
    parameters_df = pd.DataFrame(parameter_rows)
    residuals_df = pd.concat(residual_frames, ignore_index=True)

    OUTPUT.mkdir(parents=True, exist_ok=False)
    summary_df.to_csv(OUTPUT / "fit_summary.csv", index=False)
    parameters_df.to_csv(OUTPUT / "parameter_estimates.csv", index=False)
    residuals_df.to_csv(OUTPUT / "residuals.csv", index=False)

    metadata = {
        "experiment": "HD115617 Keplerian Model Validation v1",
        "target": TARGET,
        "input_file": str(INPUT),
        "input_rows_for_target": int(before),
        "valid_rows": int(len(target)),
        "excluded_invalid_rows": int(before-len(target)),
        "first_bjd": float(t.min()),
        "last_bjd": float(t.max()),
        "baseline_days": float(t.max()-t.min()),
        "reference_bjd": t0,
        "measurement_error_column": "drs_dvrms (m/s)",
        "activity_proxy": "drs_bis_span, standardized",
        "periods_fixed_days": PERIODS,
        "models": MODELS,
        "optimizer": "SciPy L-BFGS-B; three deterministic eccentricity/omega starts per model",
        "likelihood": "Gaussian likelihood with fitted additive jitter in quadrature",
        "eccentricity_bounds": [0.0, 0.8],
        "periods_were_selected_using_the_same_dataset": True,
        "validation_status": "conditional model comparison; not blind independent validation",
        "formal_parameter_uncertainties": "not estimated in v1",
        "runtime_seconds": round(time.time()-started, 3),
        "python": sys.version,
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    (OUTPUT / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )

    best = summary_df.iloc[0]
    report = [
        "HD115617 KEPLERIAN MODEL VALIDATION V1",
        "=" * 48,
        f"Valid observations: {len(target)}",
        f"Baseline: {t.max()-t.min():.6f} days",
        f"Reference BJD: {t0:.8f}",
        "",
        "MODEL COMPARISON (sorted by BIC)",
        summary_df.to_string(index=False),
        "",
        f"Lowest-BIC model: {best['model']}",
        "This is a relative comparison among the tested conditional models.",
        "",
        "SCIENTIFIC LIMITATIONS",
        "- Candidate periods were selected using this same dataset.",
        "- Periods were held fixed; period-search uncertainty is not included.",
        "- BIS span is a linear activity proxy, not a physical stellar activity model.",
        "- A fitted jitter term absorbs excess scatter but does not identify its cause.",
        "- Eccentric Keplerian fits can overfit; eccentricity estimates need uncertainty analysis.",
        "- BIC does not account for the prior search over candidate periods.",
        "- No formal parameter uncertainties or independent blind validation are produced.",
        "- These results do not confirm any candidate as a planet.",
        "",
        "Next: inspect parameter stability, residual structure and independent validation.",
    ]
    (OUTPUT / "report.txt").write_text("\n".join(report), encoding="utf-8")

    print("\n===== FINAL MODEL COMPARISON =====")
    print(summary_df[
        ["model", "BIC", "delta_BIC", "fitted_jitter_mps",
         "residual_rms_mps", "optimizer_success"]
    ].to_string(index=False))
    print(f"\nReports saved to: {OUTPUT}")
    print(f"Runtime: {time.time()-started:.1f} seconds")

if __name__ == "__main__":
    main()
