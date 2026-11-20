from pathlib import Path
import json
import sys
import hashlib
import warnings

import numpy as np
import pandas as pd

from astropy.timeseries import LombScargle
from scipy.signal import find_peaks


ROOT = Path(
    r"D:\exoanalytica\research\phase_2\rv_ai_model\stage_5_keplerian_rv_detection"
)

TARGET = "HD115617"
VERSION = "1.0"

INPUT = ROOT / "data" / "input"
RAW_FILE = INPUT / "harps_rv_observations_18_targets.csv"
QC_FILE = INPUT / "harps_rv_observation_qc_v1.csv"

EXP = ROOT / "experiments" / f"{TARGET}_gls_v1"
EXP.mkdir(parents=True, exist_ok=True)

OUTPUT_PERIODS = EXP / "periodogram.csv"
OUTPUT_PEAKS = EXP / "periodogram_peaks.csv"
OUTPUT_REPORT = EXP / "gls_report.txt"
OUTPUT_CONFIG = EXP / "experiment_config.json"
OUTPUT_RESULT = EXP / "gls_result.json"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stop(message):
    raise RuntimeError(message)


def main():
    print("=" * 65)
    print("EXOANALYTICA - STAGE 5 GLS SEARCH ENGINE V1")
    print("=" * 65)

    if not RAW_FILE.exists():
        stop(f"Missing input: {RAW_FILE}")

    if not QC_FILE.exists():
        stop(f"Missing QC input: {QC_FILE}")

    print("\n[1] Loading original observations...")

    raw = pd.read_csv(RAW_FILE)
    qc = pd.read_csv(QC_FILE)

    required = [
        "tel_object",
        "drs_bjd",
        "rv_mps",
        "drs_dvrms",
    ]

    missing = [c for c in required if c not in raw.columns]
    if missing:
        stop(f"Missing raw columns: {missing}")

    if "source_row_index" not in qc.columns:
        stop("QC file has no source_row_index column.")

    if len(raw) != len(qc):
        stop("Raw/QC row counts differ. Alignment cannot be assumed.")

    if not qc["source_row_index"].is_unique:
        stop("QC source_row_index is not unique.")

    # Verify raw/QC row alignment before using QC flags.
    raw_check = raw[["tel_object", "drs_bjd", "rv_mps"]].copy()
    raw_check["source_row_index"] = np.arange(len(raw))

    aligned = raw_check.merge(
        qc[["source_row_index", "tel_object", "drs_bjd", "rv_mps"]],
        on="source_row_index",
        suffixes=("_raw", "_qc"),
        validate="one_to_one",
    )

    if not (
        aligned["tel_object_raw"].astype(str)
        == aligned["tel_object_qc"].astype(str)
    ).all():
        stop("Raw/QC target alignment failed.")

    for column in ["drs_bjd", "rv_mps"]:
        a = pd.to_numeric(aligned[f"{column}_raw"], errors="coerce")
        b = pd.to_numeric(aligned[f"{column}_qc"], errors="coerce")

        if not np.allclose(a, b, rtol=1e-10, atol=1e-8, equal_nan=True):
            stop(f"Raw/QC numeric alignment failed: {column}")

    print("Raw/QC row alignment: PASS")

    raw["source_row_index"] = np.arange(len(raw))

    target = raw.loc[
        raw["tel_object"].astype(str).str.strip() == TARGET
    ].copy()

    if target.empty:
        stop(f"No observations found for {TARGET}")

    print(f"Target observations loaded: {len(target)}")

    print("\n[2] Validating numeric measurements...")

    for column in ["drs_bjd", "rv_mps", "drs_dvrms"]:
        target[column] = pd.to_numeric(
            target[column], errors="coerce"
        )

    valid_mask = (
        np.isfinite(target["drs_bjd"])
        & np.isfinite(target["rv_mps"])
        & np.isfinite(target["drs_dvrms"])
        & (target["drs_dvrms"] > 0)
    )

    invalid_count = int((~valid_mask).sum())

    # Only remove numerically unusable measurements.
    # QC review flags are NOT automatic rejection criteria.
    data = target.loc[valid_mask].copy()
    data = data.sort_values("drs_bjd").reset_index(drop=True)

    if len(data) < 20:
        stop("Insufficient valid observations for GLS.")

    t_absolute = data["drs_bjd"].to_numpy(dtype=float)
    y = data["rv_mps"].to_numpy(dtype=float)
    dy = data["drs_dvrms"].to_numpy(dtype=float)

    baseline = float(np.max(t_absolute) - np.min(t_absolute))

    if baseline <= 0:
        stop("Invalid time baseline.")

    t_reference = float(np.min(t_absolute))
    t = t_absolute - t_reference

    minimum_period = 2.0
    maximum_period = baseline / 2.0

    if maximum_period <= minimum_period:
        stop("Time baseline is too short for configured period range.")

    minimum_frequency = 1.0 / maximum_period
    maximum_frequency = 1.0 / minimum_period

    print(f"Valid observations: {len(data)}")
    print(f"Numerically invalid rows excluded: {invalid_count}")
    print(f"Time baseline: {baseline:.6f} days")
    print(f"Period search: {minimum_period:.6f} to {maximum_period:.6f} days")

    print("\n[3] Reviewing QC flags (no automatic rejection)...")

    qc_target = qc.loc[
        qc["tel_object"].astype(str).str.strip() == TARGET
    ].copy()

    flag_columns = [
        c for c in qc_target.columns
        if c.startswith("flag_")
    ]

    qc_flag_counts = {}

    for column in flag_columns:
        values = (
            qc_target[column]
            .astype(str)
            .str.strip()
            .str.lower()
        )
        qc_flag_counts[column] = int(
            values.isin(["true", "1", "yes"]).sum()
        )

    print(f"QC review flag columns: {len(flag_columns)}")
    print("QC flags are retained as review metadata.")

    print("\n[4] Running weighted Generalized Lomb-Scargle...")

    model = LombScargle(
        t,
        y,
        dy=dy,
        fit_mean=True,
        center_data=True,
        nterms=1,
        normalization="standard",
    )

    frequency, power = model.autopower(
        minimum_frequency=minimum_frequency,
        maximum_frequency=maximum_frequency,
        samples_per_peak=10,
        method="fast",
        normalization="standard",
    )

    if len(frequency) == 0 or not np.all(np.isfinite(power)):
        stop("Periodogram contains invalid results.")

    periods = 1.0 / frequency

    periodogram = pd.DataFrame({
        "frequency_per_day": frequency,
        "period_days": periods,
        "power": power,
    })

    periodogram.to_csv(OUTPUT_PERIODS, index=False)

    print(f"Periodogram frequency samples: {len(frequency)}")

    print("\n[5] Identifying local periodogram peaks...")

    peak_indices, _ = find_peaks(power)

    if len(peak_indices) == 0:
        peak_indices = np.array([int(np.argmax(power))])

    peak_indices = sorted(
        peak_indices,
        key=lambda i: power[i],
        reverse=True,
    )[:20]

    peaks = periodogram.iloc[peak_indices].copy()
    peaks.insert(0, "rank", np.arange(1, len(peaks) + 1))
    peaks = peaks.sort_values("rank")

    peaks.to_csv(OUTPUT_PEAKS, index=False)

    best_index = int(np.argmax(power))
    best_frequency = float(frequency[best_index])
    best_period = float(1.0 / best_frequency)
    best_power = float(power[best_index])

    print(f"Highest-power period: {best_period:.8f} days")
    print(f"Highest GLS power: {best_power:.8f}")

    print("\n[6] Estimating false alarm probability...")

    fap = None
    fap_warning = None

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fap_value = model.false_alarm_probability(
                best_power,
                method="baluev",
            )

        if np.isfinite(fap_value):
            fap = float(fap_value)

    except Exception as exc:
        fap_warning = str(exc)

    print(f"Approximate Baluev FAP: {fap}")

    print("\n[7] Recording reproducibility metadata...")

    config = {
        "project": "ExoAnalytica",
        "stage": 5,
        "experiment": f"{TARGET}_gls_v1",
        "version": VERSION,
        "target": TARGET,
        "input_file": str(RAW_FILE),
        "input_sha256": sha256(RAW_FILE),
        "qc_file": str(QC_FILE),
        "qc_sha256": sha256(QC_FILE),
        "time_column": "drs_bjd",
        "rv_column": "rv_mps",
        "uncertainty_column": "drs_dvrms",
        "uncertainty_unit": "m/s",
        "period_min_days": minimum_period,
        "period_max_days": maximum_period,
        "samples_per_peak": 10,
        "normalization": "standard",
        "fit_mean": True,
        "center_data": True,
        "nterms": 1,
        "method": "fast",
        "qc_policy": "retain review-flagged observations",
        "numerical_invalid_rows_excluded": invalid_count,
        "valid_observations": int(len(data)),
        "baseline_days": baseline,
    }

    result = {
        "target": TARGET,
        "status": "COMPLETED",
        "valid_observations": int(len(data)),
        "baseline_days": baseline,
        "period_search_min_days": minimum_period,
        "period_search_max_days": maximum_period,
        "frequency_samples": int(len(frequency)),
        "best_period_days": best_period,
        "best_frequency_per_day": best_frequency,
        "best_power": best_power,
        "approximate_baluev_fap": fap,
        "fap_warning": fap_warning,
        "qc_flag_counts": qc_flag_counts,
        "interpretation": (
            "Exploratory GLS result only. A periodogram peak is not "
            "a confirmed planet detection. Keplerian fitting, alias "
            "analysis, residual analysis and independent validation "
            "are still required."
        ),
    }

    OUTPUT_CONFIG.write_text(
        json.dumps(config, indent=2),
        encoding="utf-8",
    )

    OUTPUT_RESULT.write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )

    report_lines = [
        "EXOANALYTICA - STAGE 5 GLS PILOT",
        "=" * 55,
        f"Target: {TARGET}",
        f"Status: {result['status']}",
        f"Valid observations: {len(data)}",
        f"Numerically invalid rows excluded: {invalid_count}",
        f"Baseline days: {baseline:.6f}",
        f"Search period range: {minimum_period:.6f} - {maximum_period:.6f}",
        f"Frequency samples: {len(frequency)}",
        "",
        f"Highest-power period (days): {best_period:.10f}",
        f"Highest GLS power: {best_power:.10f}",
        f"Approximate Baluev FAP: {fap}",
        "",
        "TOP LOCAL PERIODICITY PEAKS",
        "-" * 55,
    ]

    for row in peaks.itertuples(index=False):
        report_lines.append(
            f"Rank {row.rank}: period={row.period_days:.8f} d, "
            f"frequency={row.frequency_per_day:.8f}/d, "
            f"power={row.power:.8f}"
        )

    report_lines.extend([
        "",
        "QC FLAG COUNTS (review only; no automatic rejection)",
    ])

    for name, count in qc_flag_counts.items():
        report_lines.append(f"{name}: {count}")

    report_lines.extend([
        "",
        "SCIENTIFIC LIMITATION",
        result["interpretation"],
        "",
        "No planet confirmation is claimed by this experiment.",
    ])

    OUTPUT_REPORT.write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    print("\n[8] OUTPUT FILES")
    for path in [
        OUTPUT_PERIODS,
        OUTPUT_PEAKS,
        OUTPUT_CONFIG,
        OUTPUT_RESULT,
        OUTPUT_REPORT,
    ]:
        print(f"Created: {path}")

    print("\n" + "=" * 65)
    print("GLS PILOT COMPLETED")
    print("=" * 65)
    print(f"Best period: {best_period:.8f} days")
    print(f"Best power: {best_power:.8f}")
    print(f"Approximate FAP: {fap}")
    print("Interpretation: exploratory candidate periodicity only.")


if __name__ == "__main__":
    main()
