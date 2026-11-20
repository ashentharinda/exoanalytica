from pathlib import Path
import json
import warnings

import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from astropy.timeseries import LombScargle

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input" / "harps_rv_observations_18_targets.csv"
OUT = ROOT / "experiments" / "HD115617_activity_aware_comparison_v1"

TARGET = "HD115617"

PERIODS = {
    "signal_4d": 4.21421445,
    "signal_38d": 38.0511147476,
    "signal_123d": 123.666123,
    "signal_185d": 184.576303,
}

def stop(message):
    raise RuntimeError(message)

def find_column(df, candidates):
    lower = {str(c).lower(): c for c in df.columns}
    for name in candidates:
        if name.lower() in lower:
            return lower[name.lower()]
    return None

def weighted_fit(X, y, sigma):
    w = 1.0 / sigma
    Xw = X * w[:, None]
    yw = y * w
    beta, _, rank, _ = np.linalg.lstsq(Xw, yw, rcond=None)
    residual = y - X @ beta
    return beta, residual, rank

def huber_fit(X, y, sigma):
    # Robust sensitivity analysis; not the primary model comparison.
    Xw = X / sigma[:, None]
    yw = y / sigma

    initial = np.linalg.lstsq(Xw, yw, rcond=None)[0]

    result = least_squares(
        lambda beta: (X @ beta - y) / sigma,
        initial,
        loss="huber",
        f_scale=1.345,
        max_nfev=10000
    )
    return result.x, y - X @ result.x, result.success

def make_design(t, periods, bis_z=None):
    columns = [np.ones(len(t))]
    names = ["intercept"]

    for name, period in periods.items():
        angle = 2.0 * np.pi * t / period
        columns.extend([np.sin(angle), np.cos(angle)])
        names.extend([f"{name}_sin", f"{name}_cos"])

    if bis_z is not None:
        columns.append(bis_z)
        names.append("standardized_BIS_span")

    return np.column_stack(columns), names

def metrics(name, X, y, sigma, t, bis_z, periods):
    beta, residual, rank = weighted_fit(X, y, sigma)

    chi2 = float(np.sum((residual / sigma) ** 2))
    n = len(y)
    k = X.shape[1]

    # Gaussian likelihood with supplied measurement uncertainties.
    log_likelihood_term = float(np.sum(np.log(2.0 * np.pi * sigma**2)))
    aic = chi2 + log_likelihood_term + 2 * k
    bic = chi2 + log_likelihood_term + k * np.log(n)

    # Huber fit as an influence/outlier sensitivity diagnostic.
    robust_beta, robust_residual, robust_ok = huber_fit(X, y, sigma)
    robust_chi2 = float(np.sum((robust_residual / sigma) ** 2))

    return {
        "model": name,
        "n_observations": n,
        "parameters": k,
        "design_rank": int(rank),
        "weighted_chi2": chi2,
        "reduced_chi2": chi2 / max(n-k, 1),
        "AIC": float(aic),
        "BIC": float(bic),
        "Huber_weighted_chi2": robust_chi2,
        "Huber_fit_success": bool(robust_ok),
        "residual_rms_mps": float(np.sqrt(np.mean(residual**2))),
        "coefficients": {
            key: float(value) for key, value in zip(
                ["intercept"] +
                [f"{p}_{part}" for p in periods for part in ("sin", "cos")] +
                (["standardized_BIS_span"] if X.shape[1] > 1 + 2*len(periods) else []),
                beta
            )
        },
        "_residual": residual,
        "_robust_residual": robust_residual,
    }

def residual_periodogram(t, residual, sigma):
    baseline = float(np.max(t) - np.min(t))
    min_period = 2.0
    max_period = baseline / 2.0

    if max_period <= min_period:
        stop("Insufficient time baseline for the requested GLS search.")

    frequency = np.linspace(
        1.0 / max_period,
        1.0 / min_period,
        int(np.ceil((1.0/min_period - 1.0/max_period) * baseline * 10)) + 1
    )

    gls = LombScargle(
        t, residual, dy=sigma,
        fit_mean=True,
        center_data=True,
        nterms=1
    )
    power = gls.power(frequency, method="fast")

    best = int(np.nanargmax(power))
    return {
        "strongest_residual_period_days": float(1.0 / frequency[best]),
        "strongest_residual_gls_power": float(power[best]),
    }

def main():
    if not INPUT.exists():
        stop(f"Input file not found: {INPUT}")

    if OUT.exists():
        stop(f"Output folder already exists; refusing to overwrite: {OUT}")

    df = pd.read_csv(INPUT)
    print("Input rows:", len(df))
    print("Input columns:", list(df.columns))

    target_col = find_column(
        df, ["target_name", "target", "object_name", "star_name", "object"]
    )

    if target_col is not None:
        selected = df[
            df[target_col].astype(str).str.upper().str.contains(TARGET, na=False)
        ].copy()
    else:
        selected = pd.DataFrame()

    # Fallback: search all text columns for the target identifier.
    if selected.empty:
        for col in df.select_dtypes(include=["object"]).columns:
            candidate = df[
                df[col].astype(str).str.upper().str.contains(TARGET, na=False)
            ]
            if not candidate.empty:
                selected = candidate.copy()
                target_col = col
                break

    if selected.empty:
        stop(
            f"Could not identify {TARGET} in the CSV. "
            "Inspect the printed column names and target identifiers."
        )

    time_col = find_column(selected, ["drs_bjd"])
    rv_col = find_column(selected, ["rv_mps"])
    err_col = find_column(selected, ["drs_dvrms"])
    bis_col = find_column(selected, ["drs_bis_span"])

    missing = [
        label for label, col in [
            ("drs_bjd", time_col),
            ("rv_mps", rv_col),
            ("drs_dvrms", err_col),
            ("drs_bis_span", bis_col),
        ] if col is None
    ]
    if missing:
        stop("Missing required columns: " + ", ".join(missing))

    for col in [time_col, rv_col, err_col, bis_col]:
        selected[col] = pd.to_numeric(selected[col], errors="coerce")

    selected = selected.replace([np.inf, -np.inf], np.nan)
    selected = selected.dropna(
        subset=[time_col, rv_col, err_col, bis_col]
    ).copy()

    selected = selected[
        (selected[err_col] > 0)
    ].sort_values(time_col).reset_index(drop=True)

    if len(selected) < 100:
        stop(f"Too few valid observations after numeric checks: {len(selected)}")

    t = selected[time_col].to_numpy(dtype=float)
    y = selected[rv_col].to_numpy(dtype=float)
    sigma = selected[err_col].to_numpy(dtype=float)
    bis = selected[bis_col].to_numpy(dtype=float)

    if np.std(bis) == 0:
        stop("BIS span has zero variation; cannot fit the activity term.")

    # Center and standardize BIS Span for numerical stability.
    bis_z = (bis - np.mean(bis)) / np.std(bis, ddof=1)

    periods_a = {
        "signal_4d": PERIODS["signal_4d"],
        "signal_38d": PERIODS["signal_38d"],
    }
    periods_c = {
        **periods_a,
        "signal_123d": PERIODS["signal_123d"],
        "signal_185d": PERIODS["signal_185d"],
    }

    XA, _ = make_design(t, periods_a)
    XB, _ = make_design(t, periods_a, bis_z)
    XC, _ = make_design(t, periods_c, bis_z)

    print("\n===== DATA VALIDATION =====")
    print("Target:", TARGET)
    print("Rows used:", len(t))
    print("Time baseline (days):", float(np.ptp(t)))
    print("RV median (m/s):", float(np.median(y)))
    print("RV uncertainty median (m/s):", float(np.median(sigma)))
    print("BIS span standard deviation:", float(np.std(bis, ddof=1)))

    models = [
        ("A_planets_4d_38d", XA, periods_a),
        ("B_planets_plus_BIS", XB, periods_a),
        ("C_BIS_plus_123d_185d", XC, periods_c),
    ]

    results = []
    residual_rows = []

    for name, X, periods in models:
        result = metrics(name, X, y, sigma, t, bis_z, periods)
        residual = result.pop("_residual")
        robust_residual = result.pop("_robust_residual")

        result.update(residual_periodogram(t, residual, sigma))
        result["Huber_residual_rms_mps"] = float(
            np.sqrt(np.mean(robust_residual**2))
        )

        results.append(result)

        for i in range(len(t)):
            residual_rows.append({
                "model": name,
                "drs_bjd": float(t[i]),
                "residual_mps": float(residual[i]),
                "huber_residual_mps": float(robust_residual[i]),
            })

    comparison = pd.DataFrame(results)
    comparison["delta_BIC_from_best"] = (
        comparison["BIC"] - comparison["BIC"].min()
    )
    comparison["delta_AIC_from_best"] = (
        comparison["AIC"] - comparison["AIC"].min()
    )

    OUT.mkdir(parents=True, exist_ok=False)

    comparison.to_csv(OUT / "model_comparison.csv", index=False)
    pd.DataFrame(residual_rows).to_csv(
        OUT / "model_residuals.csv", index=False
    )

    metadata = {
        "target": TARGET,
        "input_file": str(INPUT),
        "rows_used": len(t),
        "time_baseline_days": float(np.ptp(t)),
        "periods_days": PERIODS,
        "BIS_span_centered_and_standardized": True,
        "primary_fit": "weighted_least_squares",
        "robust_sensitivity": "Huber loss, f_scale=1.345",
        "models": [
            "A: constant + 4.214d + 38.051d sinusoids",
            "B: Model A + standardized BIS span linear term",
            "C: Model B + 123.666d + 184.576d sinusoids",
        ],
        "caution": (
            "Fixed-period sinusoidal diagnostic, not a full Keplerian fit. "
            "In-sample model improvement does not establish planetary origin "
            "or prove stellar activity causation. Correlated noise and "
            "sampling effects remain possible."
        ),
    }

    with open(OUT / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    report = []
    report.append("HD115617 ACTIVITY-AWARE MODEL COMPARISON")
    report.append("=" * 58)
    report.append(f"Observations used: {len(t)}")
    report.append(f"Time baseline: {np.ptp(t):.3f} days")
    report.append("")
    report.append(comparison[
        [
            "model", "weighted_chi2", "reduced_chi2",
            "AIC", "BIC", "delta_BIC_from_best",
            "strongest_residual_period_days",
            "strongest_residual_gls_power",
            "Huber_weighted_chi2",
        ]
    ].to_string(index=False))
    report.append("")
    report.append("INTERPRETATION NOTES")
    report.append("- Lower AIC/BIC indicates better relative fit under the assumed model.")
    report.append("- Model B tests a linear BIS-span contribution.")
    report.append("- Model C tests whether 123d/185d sinusoids add explanatory power.")
    report.append("- Huber results are a robustness sensitivity check.")
    report.append("- These in-sample comparisons do not prove planet or activity origin.")
    report.append("- Correlated stellar noise and the sampling window remain important.")
    report.append("- This is not a full Keplerian orbital fit.")
    (OUT / "report.txt").write_text("\n".join(report), encoding="utf-8")

    print("\n===== MODEL COMPARISON =====")
    print(comparison[
        [
            "model", "weighted_chi2", "reduced_chi2",
            "AIC", "BIC", "delta_BIC_from_best",
            "strongest_residual_period_days",
            "strongest_residual_gls_power",
        ]
    ].to_string(index=False))

    print("\n===== OUTPUT =====")
    print(OUT.resolve())
    print("Report:", (OUT / "report.txt").resolve())
    print("Comparison:", (OUT / "model_comparison.csv").resolve())
    print("Residuals:", (OUT / "model_residuals.csv").resolve())
    print("\nCompleted. Original input data was not modified.")

if __name__ == "__main__":
    main()
