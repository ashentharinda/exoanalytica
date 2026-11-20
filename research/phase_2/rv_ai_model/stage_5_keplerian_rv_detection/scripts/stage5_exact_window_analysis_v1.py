from pathlib import Path
import json
import hashlib
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "input" / "harps_rv_observations_18_targets.csv"
GLS = ROOT / "experiments" / "HD115617_gls_v1" / "periodogram.csv"
OUT = ROOT / "experiments" / "HD115617_window_exact_v1"

TARGET = "HD115617"
P0 = 38.05111474761596
P_ALIAS_SHORT = 34.423416264370736
P_ALIAS_LONG = 42.53349025958792
P_ANNUAL = 365.25
P_OBSERVED_WINDOW = 366.5616089

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def find_column(df, candidates, label):
    for name in candidates:
        if name in df.columns:
            return name
    raise ValueError(
        f"Cannot find {label} column. Available columns: {list(df.columns)}"
    )

def window_power(times, frequencies):
    # Shift timestamps to reduce numerical phase size.
    t = np.asarray(times, dtype=float)
    t = t - np.min(t)
    frequencies = np.asarray(frequencies, dtype=float)

    result = np.empty(len(frequencies), dtype=float)
    chunk_size = 500

    for start in range(0, len(frequencies), chunk_size):
        stop = min(start + chunk_size, len(frequencies))
        phase = 2.0 * np.pi * np.outer(frequencies[start:stop], t)
        z = np.exp(-1j * phase).mean(axis=1)
        result[start:stop] = np.abs(z) ** 2

    return result

def main():
    if not INPUT.exists():
        raise FileNotFoundError(INPUT)
    if not GLS.exists():
        raise FileNotFoundError(GLS)
    if OUT.exists():
        raise FileExistsError(
            f"Output already exists; refusing to overwrite: {OUT}"
        )

    raw = pd.read_csv(INPUT)
    gls = pd.read_csv(GLS)

    target_col = find_column(raw, ["tel_object"], "target")
    time_col = find_column(raw, ["drs_bjd"], "BJD timestamp")
    freq_col = find_column(
        gls, ["frequency", "frequency_per_day", "freq"], "GLS frequency"
    )

    target = raw.loc[raw[target_col].astype(str) == TARGET].copy()
    target[time_col] = pd.to_numeric(target[time_col], errors="coerce")
    target = target.dropna(subset=[time_col])

    times = target[time_col].to_numpy(dtype=float)
    times = np.unique(times)

    if len(times) < 100:
        raise RuntimeError(
            f"Unexpected timestamp count for {TARGET}: {len(times)}"
        )

    frequencies = pd.to_numeric(
        gls[freq_col], errors="coerce"
    ).dropna().to_numpy(dtype=float)
    frequencies = np.unique(frequencies[frequencies > 0])

    if len(frequencies) == 0:
        raise RuntimeError("GLS frequency grid is empty.")

    f0 = 1.0 / P0
    f_annual = 1.0 / P_ANNUAL
    f_observed_annual = 1.0 / P_OBSERVED_WINDOW

    candidates = [
        ("central_38d_signal", f0),
        ("annual_plus_sideband", f0 + f_annual),
        ("annual_minus_sideband", abs(f0 - f_annual)),
        ("observed_window_plus_sideband", f0 + f_observed_annual),
        ("observed_window_minus_sideband", abs(f0 - f_observed_annual)),
        ("observed_34_423d_peak", 1.0 / P_ALIAS_SHORT),
        ("observed_42_533d_peak", 1.0 / P_ALIAS_LONG),
        ("annual_window_frequency", f_annual),
        ("observed_annual_window_frequency", f_observed_annual),
    ]

    offsets = []
    for label, period in [
        ("34.423d_peak_offset_from_38d", P_ALIAS_SHORT),
        ("42.533d_peak_offset_from_38d", P_ALIAS_LONG),
    ]:
        delta = abs((1.0 / period) - f0)
        offsets.append((label, delta))

    all_frequencies = list(frequencies)
    all_frequencies.extend(f for _, f in candidates)
    all_frequencies.extend(f for _, f in offsets)

    unique_frequencies = np.unique(
        np.asarray(all_frequencies, dtype=float)
    )
    powers = window_power(times, unique_frequencies)

    window_df = pd.DataFrame({
        "frequency_per_day": unique_frequencies,
        "period_days": 1.0 / unique_frequencies,
        "window_power": powers,
    })

    lookup = dict(zip(unique_frequencies, powers))
    rows = []

    for label, freq in candidates + offsets:
        rows.append({
            "measurement": label,
            "frequency_per_day": freq,
            "equivalent_period_days": 1.0 / freq,
            "window_power": lookup[freq],
        })

    checks_df = pd.DataFrame(rows)

    OUT.mkdir(parents=True, exist_ok=False)
    window_df.to_csv(OUT / "exact_window_periodogram.csv", index=False)
    checks_df.to_csv(OUT / "alias_frequency_checks.csv", index=False)

    report = {
        "target": TARGET,
        "method": "Squared modulus of normalized complex sampling window",
        "timestamp_column": time_col,
        "unique_original_timestamps": int(len(times)),
        "time_baseline_days": float(times.max() - times.min()),
        "gls_frequency_samples": int(len(frequencies)),
        "central_period_days": P0,
        "annual_period_days_assumed": P_ANNUAL,
        "observed_annual_window_period_days": P_OBSERVED_WINDOW,
        "input_sha256": sha256(INPUT),
        "gls_periodogram_sha256": sha256(GLS),
        "interpretation": (
            "Sampling-window diagnostics only. A high window power at a "
            "frequency separation can support an alias hypothesis, but "
            "does not by itself establish that an RV peak is an alias."
        ),
    }

    (OUT / "analysis_metadata.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print("\n===== EXACT SPECTRAL WINDOW ANALYSIS =====")
    print(f"Target: {TARGET}")
    print(f"Unique original timestamps: {len(times)}")
    print(f"Time baseline: {times.max() - times.min():.6f} days")
    print(f"GLS grid samples: {len(frequencies)}")
    print(f"Window grid rows: {len(window_df)}")
    print(f"Output: {OUT}")

    print("\n===== ALIAS FREQUENCY CHECKS =====")
    print(checks_df.to_string(index=False, float_format=lambda x: f"{x:.10g}"))

    print("\nCompleted. No source data or production files were modified.")

if __name__ == "__main__":
    main()
