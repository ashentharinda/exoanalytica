from pathlib import Path
import json
import numpy as np
import pandas as pd

from astropy.timeseries import LombScargle
from scipy.stats import spearmanr, pearsonr

ROOT = Path("research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection")
INPUT = ROOT / "data/input/harps_rv_observations_18_targets.csv"
GRID_FILE = ROOT / "experiments/HD115617_gls_v1/periodogram.csv"
OUT = ROOT / "experiments/HD115617_activity_validation_123_185_v1"

TARGET = "HD115617"
PERIOD_B = 4.21421445
PERIOD_C = 38.05111474761596

INDICATORS = [
    "drs_bis_span",
    "drs_ccf_fwhm",
    "drs_ccf_contrast",
    "drs_ccf_noise",
]

CHECK_PERIODS = [123.358, 123.666123, 184.576303, 185.964095]

def stop(message):
    raise SystemExit(f"\nERROR: {message}")

def main():
    if not INPUT.exists():
        stop(f"Input missing: {INPUT}")

    if not GRID_FILE.exists():
        stop(f"Original GLS grid missing: {GRID_FILE}")

    if OUT.exists():
        stop(f"Output exists already: {OUT}. Refusing to overwrite.")

    df = pd.read_csv(INPUT, low_memory=False)

    # Find target rows.
    text_columns = df.select_dtypes(include=["object", "string"]).columns
    mask = pd.Series(False, index=df.index)

    for column in text_columns:
        mask |= df[column].astype(str).str.strip().str.upper().eq(TARGET)

    data = df.loc[mask].copy()

    if data.empty:
        stop(f"No observations found for {TARGET}")

    required = ["drs_bjd", "rv_mps", "drs_dvrms"]
    for col in required:
        if col not in data.columns:
            stop(f"Missing required column: {col}")
        data[col] = pd.to_numeric(data[col], errors="coerce")

    valid = (
        np.isfinite(data["drs_bjd"])
        & np.isfinite(data["rv_mps"])
        & np.isfinite(data["drs_dvrms"])
        & (data["drs_dvrms"] > 0)
    )

    data = data.loc[valid].sort_values("drs_bjd").copy()

    t = data["drs_bjd"].to_numpy(float)
    y = data["rv_mps"].to_numpy(float)
    dy = data["drs_dvrms"].to_numpy(float)

    print(f"Target: {TARGET}")
    print(f"Valid RV observations: {len(t)}")
    print(f"Baseline: {np.ptp(t):.6f} days")

    # Reuse original GLS frequency grid.
    grid_df = pd.read_csv(GRID_FILE)

    fcol = next(
        (c for c in grid_df.columns if "frequency" in c.lower()),
        None
    )

    if fcol:
        frequency = pd.to_numeric(
            grid_df[fcol], errors="coerce"
        ).dropna().to_numpy(float)
    else:
        pcol = next(
            (c for c in grid_df.columns if "period" in c.lower()),
            None
        )
        if not pcol:
            stop("Cannot identify frequency/period column.")

        periods = pd.to_numeric(
            grid_df[pcol], errors="coerce"
        ).dropna().to_numpy(float)
        frequency = 1.0 / periods

    frequency = np.unique(
        frequency[np.isfinite(frequency) & (frequency > 0)]
    )
    frequency.sort()

    # Reconstruct the simultaneous 4.214d + 38.051d model.
    t0 = t.min()
    phase_b = 2 * np.pi * (t - t0) / PERIOD_B
    phase_c = 2 * np.pi * (t - t0) / PERIOD_C

    design = np.column_stack([
        np.ones(len(t)),
        np.sin(phase_b),
        np.cos(phase_b),
        np.sin(phase_c),
        np.cos(phase_c),
    ])

    coef, *_ = np.linalg.lstsq(
        design / dy[:, None],
        y / dy,
        rcond=None
    )

    residual_rv = y - design @ coef

    # RV residual periodogram.
    rv_ls = LombScargle(
        t, residual_rv, dy=dy,
        fit_mean=True, center_data=True, nterms=1
    )
    rv_power = rv_ls.power(
        frequency, method="fast", normalization="standard"
    )

    rv_peak_indices = np.argsort(rv_power)[::-1][:15]

    rv_peaks = pd.DataFrame({
        "rank": np.arange(1, len(rv_peak_indices) + 1),
        "period_days": 1.0 / frequency[rv_peak_indices],
        "gls_power": rv_power[rv_peak_indices],
    })

    indicator_rows = []
    correlation_rows = []
    peak_frames = []

    for indicator in INDICATORS:
        if indicator not in data.columns:
            print(f"WARNING: Missing indicator column: {indicator}")
            continue

        values = pd.to_numeric(
            data[indicator], errors="coerce"
        ).to_numpy(float)

        good = (
            np.isfinite(t)
            & np.isfinite(values)
            & np.isfinite(residual_rv)
        )

        ti = t[good]
        vi = values[good]
        ri = residual_rv[good]
        raw_ri = y[good]

        if len(ti) < 50:
            print(f"WARNING: Too few valid rows for {indicator}")
            continue

        # Correlation with raw RV and with the two-signal residual.
        sr_raw = spearmanr(vi, raw_ri)
        sr_resid = spearmanr(vi, ri)
        pr_raw = pearsonr(vi, raw_ri)
        pr_resid = pearsonr(vi, ri)

        correlation_rows.append({
            "indicator": indicator,
            "valid_observations": int(len(ti)),
            "spearman_raw_rv": float(sr_raw.statistic),
            "spearman_raw_pvalue": float(sr_raw.pvalue),
            "spearman_residual_rv": float(sr_resid.statistic),
            "spearman_residual_pvalue": float(sr_resid.pvalue),
            "pearson_raw_rv": float(pr_raw.statistic),
            "pearson_raw_pvalue": float(pr_raw.pvalue),
            "pearson_residual_rv": float(pr_resid.statistic),
            "pearson_residual_pvalue": float(pr_resid.pvalue),
        })

        # Unweighted indicator GLS on the same frequency grid.
        indicator_ls = LombScargle(
            ti, vi,
            fit_mean=True,
            center_data=True,
            nterms=1
        )

        indicator_power = indicator_ls.power(
            frequency, method="fast", normalization="standard"
        )

        peak_idx = int(np.argmax(indicator_power))
        strongest_period = float(1.0 / frequency[peak_idx])
        strongest_power = float(indicator_power[peak_idx])

        for period in CHECK_PERIODS:
            idx = int(np.argmin(np.abs(frequency - 1.0 / period)))
            indicator_rows.append({
                "indicator": indicator,
                "valid_observations": int(len(ti)),
                "requested_period_days": period,
                "nearest_grid_period_days": float(1.0 / frequency[idx]),
                "indicator_gls_power": float(indicator_power[idx]),
                "strongest_indicator_period_days": strongest_period,
                "strongest_indicator_power": strongest_power,
            })

        top = np.argsort(indicator_power)[::-1][:10]
        peak_frames.append(pd.DataFrame({
            "indicator": indicator,
            "rank": np.arange(1, len(top) + 1),
            "period_days": 1.0 / frequency[top],
            "gls_power": indicator_power[top],
        }))

        print(
            f"{indicator}: N={len(ti)}, "
            f"strongest period={strongest_period:.4f} d, "
            f"power={strongest_power:.5f}"
        )

    if not correlation_rows:
        stop("No usable activity indicators were found.")

    OUT.mkdir(parents=True)

    pd.DataFrame(correlation_rows).to_csv(
        OUT / "rv_activity_correlations.csv", index=False
    )

    pd.DataFrame(indicator_rows).to_csv(
        OUT / "activity_period_powers.csv", index=False
    )

    rv_peaks.to_csv(
        OUT / "joint_residual_rv_top15.csv", index=False
    )

    if peak_frames:
        pd.concat(peak_frames, ignore_index=True).to_csv(
            OUT / "activity_indicator_top10_peaks.csv", index=False
        )

    pd.DataFrame({
        "bjd": t,
        "rv_mps": y,
        "uncertainty_mps": dy,
        "joint_two_signal_residual_mps": residual_rv,
    }).to_csv(
        OUT / "joint_residual_rv.csv", index=False
    )

    summary = {
        "target": TARGET,
        "rv_observations": int(len(t)),
        "baseline_days": float(np.ptp(t)),
        "activity_indicators_analyzed": [
            row["indicator"] for row in correlation_rows
        ],
        "periods_checked_days": CHECK_PERIODS,
        "model": "4.21421445d_and_38.05111475d_fixed_period_sinusoids",
        "warning": (
            "Activity-indicator correlations and periodogram peaks are "
            "diagnostic, not proof of a stellar or planetary origin. "
            "Multiple testing, temporal evolution, sampling aliases and "
            "indicator uncertainties must be considered."
        ),
    }

    with open(OUT / "activity_validation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    report = [
        "HD115617 — Activity validation of 123d and 185d RV residuals",
        "=" * 68,
        f"RV observations: {len(t)}",
        f"Baseline: {np.ptp(t):.6f} days",
        "",
        "RV / ACTIVITY INDICATOR CORRELATIONS",
        pd.DataFrame(correlation_rows).to_string(index=False),
        "",
        "ACTIVITY INDICATOR POWER AT SELECTED PERIODS",
        pd.DataFrame(indicator_rows).to_string(index=False),
        "",
        "TOP JOINT RESIDUAL RV PEAKS",
        rv_peaks.to_string(index=False),
        "",
        "CAUTION",
        summary["warning"],
    ]

    (OUT / "activity_validation_report.txt").write_text(
        "\n".join(report), encoding="utf-8"
    )

    print("\n===== RV / ACTIVITY CORRELATIONS =====")
    print(pd.DataFrame(correlation_rows).to_string(index=False))

    print("\n===== ACTIVITY POWER AT 123 / 185 DAYS =====")
    print(pd.DataFrame(indicator_rows).to_string(index=False))

    print("\n===== RESIDUAL RV TOP PEAKS =====")
    print(rv_peaks.to_string(index=False))

    print(f"\nReport saved: {OUT / 'activity_validation_report.txt'}")
    print(f"Output folder: {OUT}")

if __name__ == "__main__":
    main()
