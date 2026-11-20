from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path.cwd()

INPUT = BASE / "data/interim/harps_rv_observations_18_targets.csv"
OUT = BASE / "reports"
SCRIPT_DIR = BASE / "scripts"

OUT.mkdir(parents=True, exist_ok=True)

CADENCE_OUT = OUT / "harps_rv_cadence_summary_v2_1.csv"
DAILY_OUT = OUT / "harps_rv_bjd_day_sampling_v2_1.csv"
SESSION_OUT = OUT / "harps_rv_observing_sessions_v2_1.csv"
WINDOW_OUT = OUT / "harps_rv_spectral_window_v2_1.csv"
REPORT_OUT = OUT / "harps_rv_timeseries_characterization_v2_1.txt"
MANIFEST_OUT = BASE / "data/manifests/harps_rv_timeseries_v2_1.json"

# Exploratory session boundary, not a universal observing-night definition.
SESSION_GAP_DAYS = 0.5

# Frequency grid oversampling relative to the nominal 1 / baseline spacing.
OVERSAMPLING = 5
MAX_FREQUENCY = 5.0
CHUNK_SIZE = 16

ALIAS_FREQUENCIES = {
    "half_day": 2.0,
    "one_day": 1.0,
    "two_day": 0.5,
    "one_month": 1.0 / 29.53059,
    "one_year": 1.0 / 365.25,
}

if not INPUT.exists():
    raise FileNotFoundError(INPUT)

df = pd.read_csv(INPUT)

required = ["tel_object", "drs_bjd", "rv_mps"]
missing = [c for c in required if c not in df.columns]
if missing:
    raise ValueError(f"Missing required columns: {missing}")

df["drs_bjd"] = pd.to_numeric(df["drs_bjd"], errors="coerce")
df["rv_mps"] = pd.to_numeric(df["rv_mps"], errors="coerce")

df = df.dropna(subset=["tel_object", "drs_bjd"]).copy()
df = df[np.isfinite(df["drs_bjd"])].copy()

# ------------------------------------------------------------
# BJD-day representatives
# ------------------------------------------------------------
df["bjd_day"] = np.floor(df["drs_bjd"]).astype("int64")

daily = (
    df.groupby(["tel_object", "bjd_day"], as_index=False)
      .agg(
          representative_bjd=("drs_bjd", "median"),
          observations_in_bjd_day=("drs_bjd", "size"),
          rv_median_mps=("rv_mps", "median"),
          rv_valid_count=("rv_mps", "count"),
      )
      .sort_values(["tel_object", "representative_bjd"])
      .reset_index(drop=True)
)

daily["bjd_day_method"] = "floor(drs_bjd); representative timestamp=median(drs_bjd)"

# ------------------------------------------------------------
# Per-target cadence, sessions and spectral window
# ------------------------------------------------------------
cadence_rows = []
session_rows = []
window_rows = []

for target, group in daily.groupby("tel_object", sort=True):

    times = np.sort(
        group["representative_bjd"].to_numpy(dtype=float)
    )

    if len(times) < 3:
        print(f"SKIP {target}: fewer than 3 BJD-day representatives")
        continue

    gaps = np.diff(times)
    positive_gaps = gaps[gaps > 0]

    if len(positive_gaps) == 0:
        print(f"SKIP {target}: no positive BJD-day gaps")
        continue

    baseline = float(times[-1] - times[0])

    # --------------------------------------------------------
    # Session grouping using the declared 0.5-day threshold
    # --------------------------------------------------------
    session_ids = np.zeros(len(times), dtype=int)

    if len(gaps):
        session_ids[1:] = np.cumsum(
            gaps > SESSION_GAP_DAYS
        )

    session_count = int(session_ids.max()) + 1

    session_times = []

    for sid in range(session_count):
        selected = times[session_ids == sid]

        session_times.append(float(np.median(selected)))

        session_rows.append({
            "tel_object": target,
            "session_id": sid + 1,
            "session_start_bjd": float(selected.min()),
            "session_end_bjd": float(selected.max()),
            "session_mid_bjd": float(np.median(selected)),
            "bjd_day_count": int(len(selected)),
            "session_span_days": float(selected.max() - selected.min()),
            "session_gap_threshold_days": SESSION_GAP_DAYS,
        })

    session_times = np.asarray(session_times, dtype=float)
    session_gaps = np.diff(session_times)
    session_gaps = session_gaps[session_gaps > 0]

    q25, q50, q75, q90, q95 = np.percentile(
        positive_gaps, [25, 50, 75, 90, 95]
    )

    cadence_rows.append({
        "tel_object": target,
        "raw_observation_count": int(
            df.loc[df["tel_object"] == target].shape[0]
        ),
        "bjd_day_count": int(len(times)),
        "baseline_days": baseline,
        "baseline_years": baseline / 365.25,
        "intra_bjd_day_observations": int(
            group["observations_in_bjd_day"].sum() - len(group)
        ),
        "bjd_day_gap_q25_days": float(q25),
        "bjd_day_gap_median_days": float(q50),
        "bjd_day_gap_q75_days": float(q75),
        "bjd_day_gap_q90_days": float(q90),
        "bjd_day_gap_q95_days": float(q95),
        "maximum_bjd_day_gap_days": float(np.max(positive_gaps)),
        "bjd_day_gaps_over_7d": int(np.sum(positive_gaps > 7)),
        "bjd_day_gaps_over_30d": int(np.sum(positive_gaps > 30)),
        "bjd_day_gaps_over_90d": int(np.sum(positive_gaps > 90)),
        "session_gap_threshold_days": SESSION_GAP_DAYS,
        "session_count": session_count,
        "median_session_gap_days": (
            float(np.median(session_gaps))
            if len(session_gaps) else np.nan
        ),
        "maximum_session_gap_days": (
            float(np.max(session_gaps))
            if len(session_gaps) else np.nan
        ),
    })

    # --------------------------------------------------------
    # Sampling-only spectral window
    # --------------------------------------------------------
    centered = times - np.mean(times)
    n = len(centered)

    for alias_name, frequency in ALIAS_FREQUENCIES.items():
        power = abs(
            np.mean(
                np.exp(2j * np.pi * frequency * centered)
            )
        ) ** 2

        window_rows.append({
            "tel_object": target,
            "feature": alias_name,
            "frequency_cycles_per_day": frequency,
            "period_days": 1.0 / frequency,
            "window_power": float(power),
            "sampling_points": n,
            "sampling_basis": "one median BJD timestamp per BJD-day",
        })

    # Frequency resolution approximately 1/(baseline * oversampling).
    f_min = max(1.0 / baseline, 0.001)
    f_max = MAX_FREQUENCY

    if f_min < f_max:
        dfrequency = 1.0 / (baseline * OVERSAMPLING)

        count = int(
            np.floor((f_max - f_min) / dfrequency)
        ) + 1

        frequencies = f_min + np.arange(count) * dfrequency
        powers = np.empty(len(frequencies), dtype=float)

        for start in range(0, len(frequencies), CHUNK_SIZE):
            freq = frequencies[start:start + CHUNK_SIZE]

            phase = (
                2.0 * np.pi
                * freq[:, None]
                * centered[None, :]
            )

            powers[start:start + len(freq)] = (
                np.abs(np.exp(1j * phase).mean(axis=1)) ** 2
            )

        # Record strongest grid values as exploratory sampling peaks.
        top = np.argsort(powers)[-10:][::-1]

        for rank, index in enumerate(top, start=1):
            frequency = float(frequencies[index])

            window_rows.append({
                "tel_object": target,
                "feature": f"grid_peak_{rank}",
                "frequency_cycles_per_day": frequency,
                "period_days": 1.0 / frequency,
                "window_power": float(powers[index]),
                "sampling_points": n,
                "sampling_basis": "one median BJD timestamp per BJD-day",
            })

    print(
        f"Processed {target}: "
        f"{len(times)} BJD-days, "
        f"{session_count} sessions, "
        f"baseline={baseline:.1f} days"
    )

# ------------------------------------------------------------
# Save v2.1 outputs
# ------------------------------------------------------------
cadence_df = pd.DataFrame(cadence_rows)
session_df = pd.DataFrame(session_rows)
window_df = pd.DataFrame(window_rows)

daily.to_csv(DAILY_OUT, index=False)
cadence_df.to_csv(CADENCE_OUT, index=False)
session_df.to_csv(SESSION_OUT, index=False)
window_df.to_csv(WINDOW_OUT, index=False)

# ------------------------------------------------------------
# Report
# ------------------------------------------------------------
lines = [
    "PHASE 2 - STAGE 4: RV TIME-SERIES CHARACTERIZATION V2.1",
    "=" * 72,
    "",
    f"Raw observations: {len(df)}",
    f"Targets processed: {len(cadence_df)}",
    f"BJD-day representatives: {len(daily)}",
    f"Observing sessions: {len(session_df)}",
    "",
    "BJD-DAY REPRESENTATIVE METHOD",
    "- Group key: tel_object + floor(drs_bjd).",
    "- One representative timestamp per BJD-day: median(drs_bjd).",
    "- BJD-day is a numerical grouping unit, not a confirmed UTC night.",
    "- Multiple exposures on one BJD-day do not increase window sample count.",
    "",
    "SESSION METHOD",
    f"- Session boundary: gap > {SESSION_GAP_DAYS} days.",
    "- This is an exploratory observing-block definition.",
    "- It is not a universal astronomical night definition.",
    "",
    "SPECTRAL WINDOW",
    "- Uses sampling timestamps only; RV values are not used.",
    "- W(f) = |mean(exp(2*pi*i*f*t))|^2.",
    "- Alias frequencies include daily, half-daily, monthly and yearly.",
    f"- Grid range: {MAX_FREQUENCY} cycles/day maximum.",
    f"- Frequency oversampling factor: {OVERSAMPLING}.",
    "- Strong peaks indicate sampling structure, not planets.",
    "",
    "LIMITATIONS",
    "- No RV outlier removal.",
    "- No planet period detection.",
    "- No activity or instrumental correction.",
    "- BJD-day grouping can combine/split calendar observing dates.",
    "- The session threshold is exploratory and must be sensitivity-tested.",
    "",
    "TARGET SUMMARY",
    "",
]

for _, row in cadence_df.iterrows():
    lines.append(
        f"{row['tel_object']}: "
        f"Nraw={int(row['raw_observation_count'])}, "
        f"BJD-days={int(row['bjd_day_count'])}, "
        f"sessions={int(row['session_count'])}, "
        f"baseline={row['baseline_days']:.1f}d, "
        f"median gap={row['bjd_day_gap_median_days']:.3f}d, "
        f"max gap={row['maximum_bjd_day_gap_days']:.1f}d"
    )

lines.extend([
    "",
    "OUTPUT FILES",
    str(DAILY_OUT),
    str(CADENCE_OUT),
    str(SESSION_OUT),
    str(WINDOW_OUT),
    str(MANIFEST_OUT),
    "",
    "RAW INPUT DATA UNCHANGED",
])

REPORT_OUT.write_text("\n".join(lines), encoding="utf-8")

manifest = {
    "dataset": "harps_rv_timeseries_characterization_v2_1",
    "version": "2.1.0",
    "input": str(INPUT.relative_to(BASE)),
    "raw_observations": int(len(df)),
    "target_count": int(cadence_df["tel_object"].nunique()),
    "bjd_day_count": int(len(daily)),
    "session_count": int(len(session_df)),
    "bjd_day_grouping": "tel_object + floor(drs_bjd)",
    "representative_timestamp": "median(drs_bjd)",
    "session_gap_threshold_days": SESSION_GAP_DAYS,
    "session_threshold_is_exploratory": True,
    "spectral_window_uses_rv_values": False,
    "frequency_oversampling": OVERSAMPLING,
    "maximum_frequency_cycles_per_day": MAX_FREQUENCY,
    "outputs": [
        str(DAILY_OUT.relative_to(BASE)),
        str(CADENCE_OUT.relative_to(BASE)),
        str(SESSION_OUT.relative_to(BASE)),
        str(WINDOW_OUT.relative_to(BASE)),
        str(REPORT_OUT.relative_to(BASE)),
    ],
    "raw_data_modified": False,
    "planet_detection_performed": False,
}

MANIFEST_OUT.parent.mkdir(parents=True, exist_ok=True)
MANIFEST_OUT.write_text(
    json.dumps(manifest, indent=2),
    encoding="utf-8"
)

print("\n===== V2.1 OUTPUT SUMMARY =====")
print("Targets:", len(cadence_df))
print("BJD-day representatives:", len(daily))
print("Sessions:", len(session_df))
print("Spectral window rows:", len(window_df))

print("\n===== REPORT =====")
print(REPORT_OUT.read_text(encoding="utf-8"))

print("\nCOMPLETED - RAW DATA UNCHANGED")
