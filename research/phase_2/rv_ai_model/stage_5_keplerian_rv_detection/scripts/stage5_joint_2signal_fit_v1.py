from pathlib import Path
import json
import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle

ROOT = Path("research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection")
INPUT = ROOT / "data/input/harps_rv_observations_18_targets.csv"
ORIGINAL_PERIODogram = ROOT / "experiments/HD115617_gls_v1/periodogram.csv"
OUT = ROOT / "experiments/HD115617_joint_2signal_v1"

TARGET = "HD115617"

# Pilot periods from the original GLS periodogram.
PERIOD_B = 4.21421445
PERIOD_C = 38.05111474761596

CHECK_PERIODS = [
    4.21421445,
    38.05111474761596,
    34.42341626,
    42.53349026,
    123.66612293,
    185.96409463,
    34.78653247,
]

def stop(message):
    raise SystemExit(f"\nERROR: {message}")

def main():
    if not INPUT.exists():
        stop(f"Input file missing: {INPUT}")

    if not ORIGINAL_PERIODogram.exists():
        stop(f"Original periodogram missing: {ORIGINAL_PERIODogram}")

    if OUT.exists():
        stop(f"Output folder already exists: {OUT}. Refusing to overwrite.")

    print("Loading original HARPS observations...")
    df = pd.read_csv(INPUT, low_memory=False)

    # Identify the target without assuming a particular target-column name.
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    mask = pd.Series(False, index=df.index)

    for column in text_columns:
        mask |= (
            df[column].astype(str).str.strip().str.upper() == TARGET
        )

    target_df = df.loc[mask].copy()

    if target_df.empty:
        print("Available columns:", list(df.columns))
        stop(f"No observations found for {TARGET}")

    required = ["drs_bjd", "rv_mps", "drs_dvrms"]
    for column in required:
        if column not in target_df.columns:
            stop(f"Required column missing: {column}")

        target_df[column] = pd.to_numeric(
            target_df[column], errors="coerce"
        )

    valid = (
        np.isfinite(target_df["drs_bjd"])
        & np.isfinite(target_df["rv_mps"])
        & np.isfinite(target_df["drs_dvrms"])
        & (target_df["drs_dvrms"] > 0)
    )

    target_df = target_df.loc[valid].sort_values("drs_bjd")

    t = target_df["drs_bjd"].to_numpy(dtype=float)
    y = target_df["rv_mps"].to_numpy(dtype=float)
    dy = target_df["drs_dvrms"].to_numpy(dtype=float)

    if len(t) < 20:
        stop(f"Insufficient observations: {len(t)}")

    print(f"Target: {TARGET}")
    print(f"Valid observations: {len(t)}")
    print(f"Baseline: {np.ptp(t):.6f} days")

    # Reuse the exact original GLS frequency grid.
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
            stop("No frequency/period column found in original periodogram.")

        periods = pd.to_numeric(
            original_grid[period_col], errors="coerce"
        ).dropna().to_numpy(dtype=float)

        frequency = 1.0 / periods

    frequency = np.unique(
        frequency[np.isfinite(frequency) & (frequency > 0)]
    )
    frequency.sort()

    print(f"Frequency samples: {len(frequency)}")

    # Joint weighted linear model:
    # RV = offset
    #    + a1*sin(2*pi*t/P1) + b1*cos(2*pi*t/P1)
    #    + a2*sin(2*pi*t/P2) + b2*cos(2*pi*t/P2)
    #
    # Both signals are fitted simultaneously.
    t0 = t.min()

    phase_b = 2.0 * np.pi * (t - t0) / PERIOD_B
    phase_c = 2.0 * np.pi * (t - t0) / PERIOD_C

    design = np.column_stack([
        np.ones(len(t)),
        np.sin(phase_b),
        np.cos(phase_b),
        np.sin(phase_c),
        np.cos(phase_c),
    ])

    weighted_design = design / dy[:, None]
    weighted_y = y / dy

    coefficients, residual_sum, rank, singular_values = np.linalg.lstsq(
        weighted_design,
        weighted_y,
        rcond=None
    )

    fitted_model = design @ coefficients
    residuals = y - fitted_model

    offset, sin_b, cos_b, sin_c, cos_c = coefficients

    amplitude_b = float(np.hypot(sin_b, cos_b))
    amplitude_c = float(np.hypot(sin_c, cos_c))

    # Weighted chi-square comparison.
    weighted_mean = np.average(y, weights=1.0 / dy**2)

    chi2_before = float(
        np.sum(((y - weighted_mean) / dy)**2)
    )

    chi2_after = float(
        np.sum((residuals / dy)**2)
    )

    chi2_reduction = (
        100.0 * (1.0 - chi2_after / chi2_before)
        if chi2_before > 0 else None
    )

    # GLS on original data and joint-model residuals.
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
        frequency,
        method="fast",
        normalization="standard"
    )

    residual_power = residual_ls.power(
        frequency,
        method="fast",
        normalization="standard"
    )

    # Compare selected periods.
    comparisons = []

    for period in CHECK_PERIODS:
        index = int(
            np.argmin(np.abs(frequency - (1.0 / period)))
        )

        before = float(original_power[index])
        after = float(residual_power[index])

        comparisons.append({
            "requested_period_days": period,
            "nearest_grid_period_days": float(1.0 / frequency[index]),
            "original_power": before,
            "joint_residual_power": after,
            "power_ratio": after / before if before > 0 else None,
            "power_reduction_percent": (
                100.0 * (1.0 - after / before)
                if before > 0 else None
            ),
        })

    comparison_df = pd.DataFrame(comparisons)

    # Strongest remaining residual peaks.
    peak_indices = np.argsort(residual_power)[::-1][:25]

    peaks_df = pd.DataFrame({
        "rank": np.arange(1, len(peak_indices) + 1),
        "frequency_per_day": frequency[peak_indices],
        "period_days": 1.0 / frequency[peak_indices],
        "residual_gls_power": residual_power[peak_indices],
    })

    # Save experiment outputs without touching original inputs.
    OUT.mkdir(parents=True)

    comparison_df.to_csv(
        OUT / "period_comparison.csv", index=False
    )

    peaks_df.to_csv(
        OUT / "joint_residual_top25_peaks.csv", index=False
    )

    pd.DataFrame({
        "bjd": t,
        "rv_mps": y,
        "uncertainty_mps": dy,
        "joint_fitted_model_mps": fitted_model,
        "joint_residual_rv_mps": residuals,
    }).to_csv(
        OUT / "joint_model_and_residuals.csv", index=False
    )

    pd.DataFrame({
        "frequency_per_day": frequency,
        "period_days": 1.0 / frequency,
        "original_gls_power": original_power,
        "joint_residual_gls_power": residual_power,
    }).to_csv(
        OUT / "joint_residual_periodogram.csv", index=False
    )

    metrics = {
        "target": TARGET,
        "model": "constant_plus_two_fixed_period_sinusoids",
        "observations": int(len(t)),
        "baseline_days": float(np.ptp(t)),
        "frequency_samples": int(len(frequency)),
        "period_b_days": PERIOD_B,
        "period_c_days": PERIOD_C,
        "offset_mps": float(offset),
        "planet_b_sin_coefficient_mps": float(sin_b),
        "planet_b_cos_coefficient_mps": float(cos_b),
        "planet_b_semi_amplitude_mps": amplitude_b,
        "planet_c_sin_coefficient_mps": float(sin_c),
        "planet_c_cos_coefficient_mps": float(cos_c),
        "planet_c_semi_amplitude_mps": amplitude_c,
        "residual_rms_mps": float(np.sqrt(np.mean(residuals**2))),
        "weighted_chi2_before": chi2_before,
        "weighted_chi2_after": chi2_after,
        "weighted_chi2_reduction_percent": chi2_reduction,
        "design_matrix_rank": int(rank),
        "warning": (
            "This is a fixed-period joint sinusoidal diagnostic, "
            "not a full Keplerian fit. Periods, eccentricities, "
            "uncertainties and model comparison require further analysis."
        ),
    }

    with open(
        OUT / "joint_fit_metrics.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(metrics, f, indent=2)

    report = [
        "HD115617 — Joint two-signal fitting experiment",
        "=" * 60,
        f"Observations: {len(t)}",
        f"Baseline: {np.ptp(t):.6f} days",
        "",
        "SIMULTANEOUS SIGNAL MODEL",
        f"Signal B period: {PERIOD_B:.8f} days",
        f"Signal B semi-amplitude: {amplitude_b:.6f} m/s",
        f"Signal C period: {PERIOD_C:.8f} days",
        f"Signal C semi-amplitude: {amplitude_c:.6f} m/s",
        f"Constant offset: {offset:.6f} m/s",
        "",
        f"Residual RMS: {metrics['residual_rms_mps']:.6f} m/s",
        f"Weighted chi-square before: {chi2_before:.6f}",
        f"Weighted chi-square after: {chi2_after:.6f}",
        f"Weighted chi-square reduction: {chi2_reduction:.3f}%",
        "",
        "PERIOD COMPARISON",
        comparison_df.to_string(index=False),
        "",
        "TOP JOINT RESIDUAL PEAKS",
        peaks_df.to_string(index=False),
        "",
        "CAUTION",
        metrics["warning"],
    ]

    (OUT / "joint_fit_report.txt").write_text(
        "\n".join(report),
        encoding="utf-8"
    )

    print("\n===== JOINT FIT METRICS =====")
    print(json.dumps(metrics, indent=2))

    print("\n===== PERIOD COMPARISON =====")
    print(comparison_df.to_string(index=False))

    print("\n===== TOP RESIDUAL PEAKS =====")
    print(peaks_df.to_string(index=False))

    print(f"\nReport saved: {OUT / 'joint_fit_report.txt'}")
    print(f"Output folder: {OUT}")

if __name__ == "__main__":
    main()
