from pathlib import Path
import json
import sys
import time
import platform
import warnings

import numpy as np
import pandas as pd
import astropy
from astropy.timeseries import LombScargle
from scipy.signal import find_peaks

warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parents[5]
STAGE_DIR = ROOT / "research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection"

INPUT_FILE = (
    STAGE_DIR / "experiments/HD115617_keplerian_validation_v1/residuals.csv"
)
OUTPUT_DIR = (
    STAGE_DIR / "experiments/HD115617_residual_injection_recovery_v1"
)

TARGET_PERIODS = {
    "P11_579": 11.579225,
    "P16_439": 16.439498,
}

AMPLITUDES = [1.0, 2.0, 3.0]
PHASES_DEG = [0, 90, 180, 270]
RECOVERY_TOLERANCE = 0.01
LOCAL_SEARCH_WIDTH = 0.05
OVERSAMPLING = 5


def load_residuals():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(INPUT_FILE)

    df = pd.read_csv(INPUT_FILE)

    required = [
        "model",
        "BJD",
        "residual_rv_mps",
        "total_sigma_mps",
    ]

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[df["model"] == "PLUS_BOTH"].copy()

    for col in ["BJD", "residual_rv_mps", "total_sigma_mps"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=required[1:])
    df = df[df["total_sigma_mps"] > 0]
    df = df.sort_values("BJD").reset_index(drop=True)

    if len(df) < 100:
        raise ValueError(f"Too few valid PLUS_BOTH rows: {len(df)}")

    if df["BJD"].duplicated().any():
        raise ValueError("Duplicate BJD timestamps detected.")

    t = df["BJD"].to_numpy(dtype=float)
    y = df["residual_rv_mps"].to_numpy(dtype=float)
    dy = df["total_sigma_mps"].to_numpy(dtype=float)

    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(y)):
        raise ValueError("Non-finite time or RV values detected.")

    return df, t, y, dy


def build_frequency_grid(t):
    baseline = float(np.max(t) - np.min(t))
    if baseline <= 0:
        raise ValueError("Invalid time baseline.")

    f_min = 1.0 / 100.0
    f_max = 1.0 / 2.0
    df = 1.0 / (baseline * OVERSAMPLING)

    frequency = np.arange(f_min, f_max, df)

    if len(frequency) < 100:
        raise ValueError("Frequency grid is unexpectedly small.")

    return frequency, baseline, df


def calculate_periodogram(t, y, dy, frequency):
    ls = LombScargle(
        t,
        y,
        dy=dy,
        fit_mean=True,
        center_data=True,
        nterms=1,
    )

    power = ls.power(
        frequency,
        method="fastchi2",
        normalization="standard",
    )

    return np.asarray(power, dtype=float)


def extract_top_peaks(frequency, power, count=25):
    peaks, _ = find_peaks(power, distance=3)

    if len(peaks) == 0:
        peaks = np.array([int(np.nanargmax(power))])

    peaks = peaks[np.argsort(power[peaks])[::-1][:count]]

    rows = []
    for rank, idx in enumerate(peaks, start=1):
        rows.append({
            "rank": rank,
            "frequency_per_day": float(frequency[idx]),
            "period_days": float(1.0 / frequency[idx]),
            "power": float(power[idx]),
        })

    return rows


def injected_signal(t, period, amplitude, phase_deg, reference_time):
    phase = np.deg2rad(phase_deg)
    return amplitude * np.sin(
        2.0 * np.pi * (t - reference_time) / period + phase
    )


def evaluate_target(frequency, power, target_period):
    target_frequency = 1.0 / target_period

    mask = (
        np.abs(frequency - target_frequency)
        <= target_frequency * LOCAL_SEARCH_WIDTH
    )

    if not np.any(mask):
        return {
            "local_peak_period_days": np.nan,
            "local_peak_power": np.nan,
            "exact_period_power": np.nan,
            "recovered_within_1pct": False,
            "global_peak_is_target": False,
        }

    local_indices = np.where(mask)[0]
    local_idx = local_indices[np.argmax(power[mask])]
    global_idx = int(np.nanargmax(power))

    local_period = float(1.0 / frequency[local_idx])
    relative_error = abs(local_period - target_period) / target_period

    exact_idx = int(np.argmin(np.abs(frequency - target_frequency)))

    global_period = float(1.0 / frequency[global_idx])
    global_error = abs(global_period - target_period) / target_period

    return {
        "local_peak_period_days": local_period,
        "local_peak_power": float(power[local_idx]),
        "exact_period_power": float(power[exact_idx]),
        "recovered_within_1pct": bool(
            relative_error <= RECOVERY_TOLERANCE
        ),
        "global_peak_is_target": bool(
            global_error <= RECOVERY_TOLERANCE
        ),
    }


def main():
    start = time.time()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "recovered_periodograms").mkdir(
        parents=True, exist_ok=True
    )

    print("\n===== RESIDUAL INJECTION & RECOVERY V1 =====")

    df, t, residual, dy = load_residuals()

    reference_time = float(np.median(t))
    frequency, baseline, frequency_step = build_frequency_grid(t)

    print(f"Target: HD115617")
    print(f"Model: PLUS_BOTH")
    print(f"Valid observations: {len(t)}")
    print(f"Baseline: {baseline:.6f} days")
    print(f"Frequency bins: {len(frequency)}")
    print(f"Frequency method: Astropy fastchi2")

    # ---------------------------------------------------------
    # BASELINE: no additional injected signal
    # ---------------------------------------------------------

    print("\n===== BASELINE PERIODOGRAM =====")

    baseline_power = calculate_periodogram(
        t, residual, dy, frequency
    )

    baseline_peaks = extract_top_peaks(
        frequency, baseline_power, count=25
    )

    pd.DataFrame(baseline_peaks).to_csv(
        OUTPUT_DIR / "baseline_periodogram_top25.csv",
        index=False,
    )

    baseline_global = baseline_peaks[0]

    print(
        f"Baseline global peak: "
        f"{baseline_global['period_days']:.6f} days"
    )

    # ---------------------------------------------------------
    # INJECTION TRIALS
    # ---------------------------------------------------------

    trial_specs = []

    for amplitude in AMPLITUDES:
        for phase in PHASES_DEG:
            trial_specs.append({
                "scenario": "P11_ONLY",
                "amplitude_mps": amplitude,
                "phase_11_deg": phase,
                "phase_16_deg": None,
            })

            trial_specs.append({
                "scenario": "P16_ONLY",
                "amplitude_mps": amplitude,
                "phase_11_deg": None,
                "phase_16_deg": phase,
            })

        for phase_11 in PHASES_DEG:
            for phase_16 in PHASES_DEG:
                trial_specs.append({
                    "scenario": "BOTH",
                    "amplitude_mps": amplitude,
                    "phase_11_deg": phase_11,
                    "phase_16_deg": phase_16,
                })

    recovery_rows = []
    trial_count = len(trial_specs)

    print(f"\n===== INJECTION TRIALS: {trial_count} =====")

    for trial_number, spec in enumerate(trial_specs, start=1):
        injected = np.zeros_like(residual)

        if spec["scenario"] in ("P11_ONLY", "BOTH"):
            injected += injected_signal(
                t,
                TARGET_PERIODS["P11_579"],
                spec["amplitude_mps"],
                spec["phase_11_deg"],
                reference_time,
            )

        if spec["scenario"] in ("P16_ONLY", "BOTH"):
            injected += injected_signal(
                t,
                TARGET_PERIODS["P16_439"],
                spec["amplitude_mps"],
                spec["phase_16_deg"],
                reference_time,
            )

        synthetic_residual = residual + injected

        power = calculate_periodogram(
            t, synthetic_residual, dy, frequency
        )

        global_idx = int(np.nanargmax(power))
        global_period = float(1.0 / frequency[global_idx])
        global_power = float(power[global_idx])

        for target_name, target_period in TARGET_PERIODS.items():
            result = evaluate_target(
                frequency, power, target_period
            )

            injected_into_target = (
                spec["scenario"] == "BOTH"
                or (
                    spec["scenario"] == "P11_ONLY"
                    and target_name == "P11_579"
                )
                or (
                    spec["scenario"] == "P16_ONLY"
                    and target_name == "P16_439"
                )
            )

            recovery_rows.append({
                "trial": trial_number,
                "scenario": spec["scenario"],
                "amplitude_mps": spec["amplitude_mps"],
                "target": target_name,
                "target_period_days": target_period,
                "injected_into_target": injected_into_target,
                "phase_11_deg": spec["phase_11_deg"],
                "phase_16_deg": spec["phase_16_deg"],
                "global_peak_period_days": global_period,
                "global_peak_power": global_power,
                **result,
            })

        if trial_number % 10 == 0 or trial_number == trial_count:
            print(f"Completed {trial_number}/{trial_count}")

    recovery_df = pd.DataFrame(recovery_rows)

    recovery_df.to_csv(
        OUTPUT_DIR / "recovery_results.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # SUMMARY: only trials where each target was injected
    # ---------------------------------------------------------

    injected_df = recovery_df[
        recovery_df["injected_into_target"]
    ].copy()

    summary = (
        injected_df.groupby(
            ["scenario", "amplitude_mps", "target"],
            dropna=False,
        )
        .agg(
            trials=("trial", "count"),
            local_recovery_rate=("recovered_within_1pct", "mean"),
            global_detection_rate=("global_peak_is_target", "mean"),
            mean_local_power=("local_peak_power", "mean"),
            mean_exact_period_power=("exact_period_power", "mean"),
        )
        .reset_index()
    )

    summary["local_recovery_percent"] = (
        summary["local_recovery_rate"] * 100.0
    )
    summary["global_detection_percent"] = (
        summary["global_detection_rate"] * 100.0
    )

    summary.to_csv(
        OUTPUT_DIR / "injection_summary.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # REPORT AND METADATA
    # ---------------------------------------------------------

    report = [
        "HD115617 RESIDUAL INJECTION & RECOVERY TEST V1",
        "=" * 58,
        "",
        "Purpose:",
        "Explore recovery of 11.579d and 16.439d signals",
        "using the actual PLUS_BOTH residual timestamps.",
        "",
        "Input:",
        str(INPUT_FILE),
        f"Valid observations: {len(t)}",
        f"First BJD: {np.min(t):.8f}",
        f"Last BJD: {np.max(t):.8f}",
        f"Baseline days: {baseline:.8f}",
        f"Frequency bins: {len(frequency)}",
        "",
        "Residual model: PLUS_BOTH",
        "Measurement weights: total_sigma_mps",
        "Injection waveform: circular sinusoidal signals",
        f"Injected amplitudes (m/s): {AMPLITUDES}",
        f"Injected phases (degrees): {PHASES_DEG}",
        f"Local search width: +/- {LOCAL_SEARCH_WIDTH * 100:.1f}%",
        f"Recovery tolerance: {RECOVERY_TOLERANCE * 100:.1f}%",
        "",
        "Baseline top 5 peaks:",
    ]

    for peak in baseline_peaks[:5]:
        report.append(
            f"  {peak['rank']}. {peak['period_days']:.6f} d "
            f"(power={peak['power']:.6f})"
        )

    report += [
        "",
        "Injection recovery summary:",
    ]

    for _, row in summary.iterrows():
        report.append(
            f"  {row['scenario']} | {row['target']} | "
            f"K={row['amplitude_mps']:.1f} m/s | "
            f"local recovery={row['local_recovery_percent']:.1f}% | "
            f"global detection={row['global_detection_percent']:.1f}%"
        )

    report += [
        "",
        "Interpretation limitations:",
        "- Synthetic circular sinusoids, not full Keplerian injections.",
        "- Residuals are conditional on the previously fitted PLUS_BOTH model.",
        "- Periods were identified from the same observational dataset.",
        "- This is an exploratory recovery and alias diagnostic.",
        "- Recovery does not establish planetary origin.",
        "- Activity and correlated noise may affect detectability.",
        "",
        f"Runtime seconds: {time.time() - start:.2f}",
    ]

    (OUTPUT_DIR / "report.txt").write_text(
        "\n".join(report), encoding="utf-8"
    )

    metadata = {
        "experiment": "HD115617 Residual Injection and Recovery v1",
        "target": "HD115617",
        "input_file": str(INPUT_FILE),
        "residual_model": "PLUS_BOTH",
        "observations": int(len(t)),
        "first_bjd": float(np.min(t)),
        "last_bjd": float(np.max(t)),
        "baseline_days": baseline,
        "frequency_bins": int(len(frequency)),
        "frequency_step_per_day": float(frequency_step),
        "target_periods_days": TARGET_PERIODS,
        "amplitudes_mps": AMPLITUDES,
        "phases_degrees": PHASES_DEG,
        "trial_count": trial_count,
        "recovery_tolerance_fraction": RECOVERY_TOLERANCE,
        "local_search_width_fraction": LOCAL_SEARCH_WIDTH,
        "periodogram_method": "Astropy LombScargle fastchi2",
        "injection_type": "circular sinusoidal",
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "astropy": astropy.__version__,
        "runtime_seconds": time.time() - start,
        "validation_status": "exploratory; not planet confirmation",
    }

    (OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\n===== OUTPUT FILES =====")
    for path in sorted(OUTPUT_DIR.iterdir()):
        if path.is_file():
            print(f"{path.name}: {path.stat().st_size:,} bytes")

    print("\n===== INJECTION SUMMARY =====")
    print(summary.to_string(index=False))

    print("\n===== COMPLETE =====")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
