from pathlib import Path
import json
import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

ROOT = Path("research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection")
INPUT = ROOT / "data/input/harps_rv_observations_18_targets.csv"
ORIGINAL_PERIODogram = ROOT / "experiments/HD115617_gls_v1/periodogram.csv"
OUT = ROOT / "experiments/HD115617_prewhitening_38d_v1"

TARGET = "HD115617"
P0 = 38.05111474761596

CHECK_PERIODS = [
    38.05111474761596,
    34.42341626,
    42.53349026,
    4.21421445,
    123.66612293,
    185.96409463,
    34.78653247,
]

def stop(message):
    raise SystemExit(f"\nERROR: {message}")

def find_column(df, required):
    for name in required:
        if name in df.columns:
            return name
    stop(f"Required column not found. Expected one of: {required}")

def main():
    if not INPUT.exists():
        stop(f"Input CSV not found: {INPUT}")

    if not ORIGINAL_PERIODogram.exists():
        stop(f"Original periodogram not found: {ORIGINAL_PERIODogram}")

    if OUT.exists():
        stop(f"Output folder already exists: {OUT}. Refusing to overwrite.")

    print("Loading original HARPS observations...")
    df = pd.read_csv(INPUT, low_memory=False)

    # Identify target rows using text columns.
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    target_mask = pd.Series(False, index=df.index)

    for column in text_columns:
        target_mask |= (
            df[column].astype(str).str.strip().str.upper() == TARGET
        )

    target_df = df.loc[target_mask].copy()

    if target_df.empty:
        print("Available columns:")
        print(list(df.columns))
        stop(f"No rows matching {TARGET} were found in text columns.")

    time_col = find_column(target_df, ["drs_bjd"])
    rv_col = find_column(target_df, ["rv_mps"])
    error_col = find_column(target_df, ["drs_dvrms"])

    for col in [time_col, rv_col, error_col]:
        target_df[col] = pd.to_numeric(target_df[col], errors="coerce")

    valid = (
        np.isfinite(target_df[time_col])
        & np.isfinite(target_df[rv_col])
        & np.isfinite(target_df[error_col])
        & (target_df[error_col] > 0)
    )
    target_df = target_df.loc[valid].copy()

    target_df = target_df.sort_values(time_col)

    t = target_df[time_col].to_numpy(dtype=float)
    y = target_df[rv_col].to_numpy(dtype=float)
    dy = target_df[error_col].to_numpy(dtype=float)

    if len(t) < 20:
        stop(f"Insufficient valid observations: {len(t)}")

    print(f"Target: {TARGET}")
    print(f"Valid observations: {len(t)}")
    print(f"Time baseline: {np.ptp(t):.6f} days")

    # Reuse the exact frequency grid from the original GLS experiment.
    original_grid = pd.read_csv(ORIGINAL_PERIODogram)

    frequency_col = next(
        (c for c in original_grid.columns
         if "frequency" in c.lower()),
        None
    )

    if frequency_col:
        frequency = pd.to_numeric(
            original_grid[frequency_col], errors="coerce"
        ).dropna().to_numpy(dtype=float)
    else:
        period_col = next(
            (c for c in original_grid.columns
             if "period" in c.lower()),
            None
        )
        if not period_col:
            stop("Could not identify frequency or period column in original periodogram.")

        periods = pd.to_numeric(
            original_grid[period_col], errors="coerce"
        ).dropna().to_numpy(dtype=float)
        frequency = 1.0 / periods

    frequency = np.unique(frequency[np.isfinite(frequency) & (frequency > 0)])
    frequency.sort()

    if len(frequency) < 100:
        stop(f"Unexpected frequency grid size: {len(frequency)}")

    print(f"Using original GLS frequency grid: {len(frequency)} samples")

    # Fit a weighted sinusoid at the fixed 38.051-day period.
    # Include a constant offset because HARPS RV values have a large zero-point.
    t0 = t.min()
    phase = 2.0 * np.pi * (t - t0) / P0

    design = np.column_stack([
        np.ones(len(t)),
        np.sin(phase),
        np.cos(phase),
    ])

    weighted_design = design / dy[:, None]
    weighted_y = y / dy

    coefficients, *_ = np.linalg.lstsq(
        weighted_design, weighted_y, rcond=None
    )

    fitted_model = design @ coefficients
    residuals = y - fitted_model

    offset, sin_coefficient, cos_coefficient = coefficients
    semi_amplitude = float(
        np.hypot(sin_coefficient, cos_coefficient)
    )

    # Calculate weighted chi-square before and after fitting.
    weighted_mean = np.average(y, weights=1.0 / dy**2)
    chi2_before = float(np.sum(((y - weighted_mean) / dy)**2))
    chi2_after = float(np.sum((residuals / dy)**2))

    # Original and residual GLS using identical timestamps, uncertainties,
    # frequency grid and model settings.
    original_ls = LombScargle(
        t, y, dy=dy,
        fit_mean=True,
        center_data=True,
        nterms=1
    )
    residual_ls = LombScargle(
        t, residuals, dy=dy,
        fit_mean=True,
        center_data=True,
        nterms=1
    )

    original_power = original_ls.power(
        frequency, method="fast", normalization="standard"
    )
    residual_power = residual_ls.power(
        frequency, method="fast", normalization="standard"
    )

    comparison = []

    for period in CHECK_PERIODS:
        f = 1.0 / period
        index = int(np.argmin(np.abs(frequency - f)))

        before = float(original_power[index])
        after = float(residual_power[index])

        comparison.append({
            "requested_period_days": period,
            "nearest_grid_period_days": float(1.0 / frequency[index]),
            "original_power": before,
            "residual_power": after,
            "power_ratio_residual_to_original": (
                after / before if before > 0 else None
            ),
            "power_reduction_percent": (
                100.0 * (1.0 - after / before) if before > 0 else None
            ),
        })

    comparison_df = pd.DataFrame(comparison)

    # Identify the strongest residual peaks.
    peak_indices = np.argsort(residual_power)[::-1][:20]
    peaks = pd.DataFrame({
        "rank": np.arange(1, len(peak_indices) + 1),
        "frequency_per_day": frequency[peak_indices],
        "period_days": 1.0 / frequency[peak_indices],
        "residual_gls_power": residual_power[peak_indices],
    })

    OUT.mkdir(parents=True)

    comparison_df.to_csv(OUT / "period_comparison.csv", index=False)
    peaks.to_csv(OUT / "residual_top20_peaks.csv", index=False)

    pd.DataFrame({
        "bjd": t,
        "rv_mps": y,
        "uncertainty_mps": dy,
        "fitted_38d_model_mps": fitted_model,
        "residual_rv_mps": residuals,
    }).to_csv(OUT / "fitted_model_and_residuals.csv", index=False)

    pd.DataFrame({
        "frequency_per_day": frequency,
        "period_days": 1.0 / frequency,
        "original_gls_power": original_power,
        "residual_gls_power": residual_power,
    }).to_csv(OUT / "residual_periodogram.csv", index=False)

    metrics = {
        "target": TARGET,
        "model": "constant_offset_plus_fixed_period_sinusoid",
        "period_days": P0,
        "observations": int(len(t)),
        "baseline_days": float(np.ptp(t)),
        "frequency_samples": int(len(frequency)),
        "offset_mps": float(offset),
        "sin_coefficient_mps": float(sin_coefficient),
        "cos_coefficient_mps": float(cos_coefficient),
        "semi_amplitude_mps": semi_amplitude,
        "residual_rms_mps": float(np.sqrt(np.mean(residuals**2))),
        "weighted_chi2_before": chi2_before,
        "weighted_chi2_after": chi2_after,
        "weighted_chi2_reduction_percent": (
            100.0 * (1.0 - chi2_after / chi2_before)
            if chi2_before > 0 else None
        ),
        "warning": (
            "Fixed-period sinusoidal pre-whitening is diagnostic only. "
            "It does not establish a Keplerian planet or prove that nearby "
            "periodogram peaks are aliases."
        ),
    }

    with open(OUT / "prewhitening_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    report = [
        "HD115617 — 38-day RV pre-whitening experiment",
        "=" * 55,
        f"Observations: {len(t)}",
        f"Baseline: {np.ptp(t):.6f} days",
        f"Fixed period: {P0:.8f} days",
        f"Fitted semi-amplitude: {semi_amplitude:.6f} m/s",
        f"Residual RMS: {metrics['residual_rms_mps']:.6f} m/s",
        f"Weighted chi-square before: {chi2_before:.6f}",
        f"Weighted chi-square after: {chi2_after:.6f}",
        "",
        "PERIOD COMPARISON",
        comparison_df.to_string(index=False),
        "",
        "TOP RESIDUAL PEAKS",
        peaks.to_string(index=False),
        "",
        "Interpretation caution:",
        metrics["warning"],
    ]

    (OUT / "prewhitening_report.txt").write_text(
        "\n".join(report), encoding="utf-8"
    )

    print("\n===== PRE-WHITENING METRICS =====")
    print(json.dumps(metrics, indent=2))

    print("\n===== PERIOD COMPARISON =====")
    print(comparison_df.to_string(index=False))

    print("\n===== TOP RESIDUAL PEAKS =====")
    print(peaks.to_string(index=False))

    print(f"\nReport saved: {OUT / 'prewhitening_report.txt'}")
    print(f"Output folder: {OUT}")

if __name__ == "__main__":
    main()
