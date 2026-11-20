from __future__ import annotations

import argparse
import json
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from astropy.timeseries import LombScargle


ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT
    / "experiments"
    / "HD115617_keplerian_validation_v1"
    / "residuals.csv"
)

OUTPUT = (
    ROOT
    / "experiments"
    / "HD115617_false_alarm_alias_validation_v1"
)

CANDIDATES = {
    "P11_579225": 11.579225,
    "P16_439498": 16.439498,
}

FREQ_MIN = 0.01
FREQ_MAX = 0.50
FREQ_BINS = 12120
LOCAL_PERIOD_TOLERANCE = 0.05


def build_frequency_grid():
    return np.linspace(
        FREQ_MIN,
        FREQ_MAX,
        FREQ_BINS,
        endpoint=False,
    )


def calculate_periodogram(t, residuals, errors, frequencies):
    model = LombScargle(
        t,
        residuals,
        dy=errors,
        fit_mean=True,
        center_data=True,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        power = model.power(
            frequencies,
            method="fastchi2",
            normalization="standard",
        )

    return np.asarray(power, dtype=float)


def candidate_masks(frequencies):
    periods = 1.0 / frequencies
    masks = {}

    for name, candidate_period in CANDIDATES.items():
        masks[name] = (
            np.abs(periods / candidate_period - 1.0)
            <= LOCAL_PERIOD_TOLERANCE
        )

    return masks


def summarize_power(power, masks):
    result = {
        "global_max_power": float(np.nanmax(power)),
        "global_peak_period_days": float(
            1.0 / np.linspace(
                FREQ_MIN,
                FREQ_MAX,
                FREQ_BINS,
                endpoint=False,
            )[np.nanargmax(power)]
        ),
    }

    for name, mask in masks.items():
        if not np.any(mask):
            result[f"{name}_local_max_power"] = float("nan")
            result[f"{name}_local_peak_period_days"] = float("nan")
            continue

        local_power = power[mask]
        local_frequency = frequencies_global[mask]
        index = int(np.nanargmax(local_power))

        result[f"{name}_local_max_power"] = float(
            local_power[index]
        )
        result[f"{name}_local_peak_period_days"] = float(
            1.0 / local_frequency[index]
        )

    return result


def empirical_fap(simulated, observed):
    simulated = np.asarray(simulated, dtype=float)
    simulated = simulated[np.isfinite(simulated)]

    if len(simulated) == 0:
        return float("nan")

    exceedances = int(np.sum(simulated >= observed))

    return float(
        (exceedances + 1) / (len(simulated) + 1)
    )


def run_block_sign_flip(
    t,
    residuals,
    errors,
    frequencies,
    masks,
    block_nights,
    simulations,
    rng,
):
    night_ids = np.floor(t).astype(np.int64)
    unique_nights = np.unique(night_ids)

    night_position = {
        night: index
        for index, night in enumerate(unique_nights)
    }

    night_indices = np.array(
        [night_position[night] for night in night_ids],
        dtype=int,
    )

    block_ids = night_indices // block_nights
    unique_blocks = np.unique(block_ids)

    rows = []

    print("\n===== NIGHTLY BLOCK SIGN-FLIP =====")
    print("Unique observing nights:", len(unique_nights))
    print("Block size (observing nights):", block_nights)
    print("Number of blocks:", len(unique_blocks))

    start = time.time()

    for iteration in range(simulations):
        signs = rng.choice(
            np.array([-1.0, 1.0]),
            size=len(unique_blocks),
        )

        sign_lookup = dict(zip(unique_blocks, signs))
        row_signs = np.array(
            [sign_lookup[b] for b in block_ids],
            dtype=float,
        )

        simulated_residuals = residuals * row_signs

        power = calculate_periodogram(
            t,
            simulated_residuals,
            errors,
            frequencies,
        )

        summary = summarize_power(power, masks)
        summary["simulation"] = iteration + 1
        rows.append(summary)

        if (iteration + 1) % 25 == 0:
            elapsed = time.time() - start
            print(
                f"Block bootstrap: {iteration + 1}/{simulations} "
                f"| elapsed={elapsed:.1f}s"
            )

    return pd.DataFrame(rows)


def run_random_permutation(
    t,
    standardized_residuals,
    errors,
    frequencies,
    masks,
    simulations,
    rng,
):
    rows = []

    print("\n===== RANDOM RESIDUAL PERMUTATION =====")

    start = time.time()

    for iteration in range(simulations):
        shuffled = rng.permutation(standardized_residuals)

        simulated_residuals = shuffled * errors

        power = calculate_periodogram(
            t,
            simulated_residuals,
            errors,
            frequencies,
        )

        summary = summarize_power(power, masks)
        summary["simulation"] = iteration + 1
        rows.append(summary)

        if (iteration + 1) % 25 == 0:
            elapsed = time.time() - start
            print(
                f"Permutation: {iteration + 1}/{simulations} "
                f"| elapsed={elapsed:.1f}s"
            )

    return pd.DataFrame(rows)


def write_report(
    path,
    observed,
    block_results,
    permutation_results,
    simulations,
    block_nights,
):
    lines = []

    lines.append("HD115617 FALSE-ALARM & ALIAS VALIDATION V1")
    lines.append("=" * 65)
    lines.append("")
    lines.append("Simulation count per method: " + str(simulations))
    lines.append("Block size in observing nights: " + str(block_nights))
    lines.append("Local period window: +/- 5 percent")
    lines.append("")

    lines.append("OBSERVED RESIDUAL PERIODOGRAM")
    lines.append("-" * 65)

    for key, value in observed.items():
        lines.append(f"{key}: {value}")

    lines.append("")

    for method_name, results in [
        ("NIGHTLY BLOCK SIGN-FLIP", block_results),
        ("RANDOM PERMUTATION", permutation_results),
    ]:
        lines.append(method_name)
        lines.append("-" * 65)

        lines.append(
            "Global FAP: "
            + str(
                empirical_fap(
                    results["global_max_power"],
                    observed["global_max_power"],
                )
            )
        )

        lines.append("")

        for candidate_name in CANDIDATES:
            column = f"{candidate_name}_local_max_power"

            fap = empirical_fap(
                results[column],
                observed[column],
            )

            lines.append(f"{candidate_name} local FAP: {fap}")

        lines.append("")

    lines.append("SCIENTIFIC LIMITATIONS")
    lines.append("-" * 65)
    lines.append(
        "1. Results are conditional on PLUS_BOTH residuals."
    )
    lines.append(
        "2. Candidate periods were selected using the same dataset."
    )
    lines.append(
        "3. Block sign-flip assumes approximate sign symmetry under "
        "the null and preserves structure only within each assigned "
        "block of observing nights."
    )
    lines.append(
        "4. Random permutation destroys temporal dependence and is "
        "a comparison method only."
    )
    lines.append(
        "5. Neither method independently confirms a planetary signal."
    )
    lines.append(
        "6. Local FAP uses the maximum power in a +/-5 percent "
        "period window around each candidate."
    )
    lines.append(
        "7. Global FAP uses the maximum power across the full "
        "0.01-0.50 cycles/day frequency grid."
    )
    lines.append("")
    lines.append(
        "These exploratory empirical FAP estimates should not be "
        "interpreted as final planet-validation probabilities."
    )

    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--simulations",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--block-nights",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261121,
    )

    args = parser.parse_args()

    if args.simulations < 1:
        raise ValueError("Simulations must be >= 1.")

    if args.block_nights < 1:
        raise ValueError("Block nights must be >= 1.")

    if not INPUT.exists():
        raise FileNotFoundError(f"Input not found: {INPUT}")

    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("===== INPUT VALIDATION =====")
    print("Input:", INPUT)

    df = pd.read_csv(INPUT)

    required = [
        "model",
        "BJD",
        "residual_rv_mps",
        "total_sigma_mps",
    ]

    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df[df["model"] == "PLUS_BOTH"].copy()

    for column in [
        "BJD",
        "residual_rv_mps",
        "total_sigma_mps",
    ]:
        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )

    df = df.replace([np.inf, -np.inf], np.nan)

    df = df.dropna(
        subset=[
            "BJD",
            "residual_rv_mps",
            "total_sigma_mps",
        ]
    )

    df = df[df["total_sigma_mps"] > 0]
    df = df.sort_values("BJD").reset_index(drop=True)

    if len(df) < 100:
        raise ValueError("Insufficient valid observations.")

    t = df["BJD"].to_numpy(dtype=float)
    residuals = df["residual_rv_mps"].to_numpy(dtype=float)
    errors = df["total_sigma_mps"].to_numpy(dtype=float)

    standardized = residuals / errors

    print("Valid observations:", len(df))
    print("Unique observing nights:", df["BJD"].astype(int).nunique())
    print("Residual standard deviation:", float(np.std(residuals)))
    print("Standardized residual standard deviation:", float(np.std(standardized)))

    global frequencies_global
    frequencies_global = build_frequency_grid()

    masks = candidate_masks(frequencies_global)

    print("\n===== OBSERVED PERIODOGRAM =====")

    observed_power = calculate_periodogram(
        t,
        residuals,
        errors,
        frequencies_global,
    )

    observed = summarize_power(
        observed_power,
        masks,
    )

    for key, value in observed.items():
        print(f"{key}: {value}")

    rng_block = np.random.default_rng(args.seed)
    rng_permutation = np.random.default_rng(args.seed + 1)

    block_results = run_block_sign_flip(
        t,
        residuals,
        errors,
        frequencies_global,
        masks,
        args.block_nights,
        args.simulations,
        rng_block,
    )

    permutation_results = run_random_permutation(
        t,
        standardized,
        errors,
        frequencies_global,
        masks,
        args.simulations,
        rng_permutation,
    )

    block_path = OUTPUT / "nightly_block_bootstrap_results.csv"
    permutation_path = OUTPUT / "random_permutation_results.csv"
    observed_path = OUTPUT / "observed_periodogram_summary.json"
    report_path = OUTPUT / "false_alarm_alias_report.txt"
    metadata_path = OUTPUT / "run_metadata.json"

    block_results.to_csv(block_path, index=False)
    permutation_results.to_csv(permutation_path, index=False)

    observed_path.write_text(
        json.dumps(observed, indent=2),
        encoding="utf-8",
    )

    write_report(
        report_path,
        observed,
        block_results,
        permutation_results,
        args.simulations,
        args.block_nights,
    )

    metadata = {
        "experiment": "HD115617 False-Alarm & Alias Validation v1",
        "input_file": str(INPUT),
        "model": "PLUS_BOTH",
        "valid_observations": int(len(df)),
        "unique_observing_nights": int(
            df["BJD"].astype(int).nunique()
        ),
        "simulations_per_method": int(args.simulations),
        "block_nights": int(args.block_nights),
        "random_seed_block": int(args.seed),
        "random_seed_permutation": int(args.seed + 1),
        "frequency_min_cycles_per_day": FREQ_MIN,
        "frequency_max_cycles_per_day": FREQ_MAX,
        "frequency_bins": FREQ_BINS,
        "candidate_periods_days": CANDIDATES,
        "local_period_tolerance_fraction": LOCAL_PERIOD_TOLERANCE,
        "method_primary": "3-observing-night block-wise residual sign flip",
        "method_comparison": "standardized residual random permutation",
        "limitations": [
            "Conditional PLUS_BOTH residual analysis",
            "Candidate periods selected using the same dataset",
            "Block sign-flip assumes approximate sign symmetry",
            "Random permutation destroys temporal dependence",
            "Exploratory empirical FAP, not independent planet confirmation",
        ],
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\n===== OUTPUT FILES =====")
    for path in [
        block_path,
        permutation_path,
        observed_path,
        report_path,
        metadata_path,
    ]:
        print(path)

    print("\n===== FALSE-ALARM SUMMARY =====")

    for method_name, results in [
        ("BLOCK SIGN-FLIP", block_results),
        ("RANDOM PERMUTATION", permutation_results),
    ]:
        global_fap = empirical_fap(
            results["global_max_power"],
            observed["global_max_power"],
        )

        print(f"\n{method_name}")
        print("Global FAP:", global_fap)

        for candidate_name in CANDIDATES:
            column = f"{candidate_name}_local_max_power"

            print(
                candidate_name,
                "local FAP:",
                empirical_fap(
                    results[column],
                    observed[column],
                ),
            )

    print("\nVALIDATION RUN COMPLETED.")


if __name__ == "__main__":
    main()
