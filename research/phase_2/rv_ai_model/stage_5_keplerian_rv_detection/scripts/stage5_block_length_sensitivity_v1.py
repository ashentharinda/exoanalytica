from pathlib import Path
import importlib.util
import json
import time

import numpy as np
import pandas as pd


BASE_SCRIPT = (
    Path(__file__).resolve().parent
    / "stage5_false_alarm_alias_validation_v1.py"
)

spec = importlib.util.spec_from_file_location(
    "fap_base",
    BASE_SCRIPT,
)

base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


SIMULATIONS = 500
BLOCK_LENGTHS = [1, 3, 5, 10]
SEED = 20261121

OUTPUT = base.OUTPUT / "block_length_sensitivity_v1"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    print("===== BLOCK-LENGTH SENSITIVITY VALIDATION V1 =====")
    print("Input:", base.INPUT)
    print("Output:", OUTPUT)

    if not base.INPUT.exists():
        raise FileNotFoundError(base.INPUT)

    df = pd.read_csv(base.INPUT)

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

    t = df["BJD"].to_numpy(dtype=float)
    residuals = df["residual_rv_mps"].to_numpy(dtype=float)
    errors = df["total_sigma_mps"].to_numpy(dtype=float)

    frequencies = base.build_frequency_grid()
    masks = base.candidate_masks(frequencies)

    base.frequencies_global = frequencies

    print("Valid observations:", len(df))
    print("Unique observing nights:", df["BJD"].astype(int).nunique())
    print("Simulation count per block length:", SIMULATIONS)
    print("Block lengths:", BLOCK_LENGTHS)

    print("\n===== OBSERVED PERIODOGRAM =====")

    observed_power = base.calculate_periodogram(
        t,
        residuals,
        errors,
        frequencies,
    )

    observed = base.summarize_power(
        observed_power,
        masks,
    )

    for key, value in observed.items():
        print(f"{key}: {value}")

    (OUTPUT / "observed_periodogram_summary.json").write_text(
        json.dumps(observed, indent=2),
        encoding="utf-8",
    )

    summaries = []
    started = time.time()

    for block_nights in BLOCK_LENGTHS:
        print("\n" + "=" * 65)
        print(f"STARTING BLOCK LENGTH: {block_nights} NIGHT(S)")
        print("=" * 65)

        rng = np.random.default_rng(SEED + block_nights)

        results = base.run_block_sign_flip(
            t=t,
            residuals=residuals,
            errors=errors,
            frequencies=frequencies,
            masks=masks,
            block_nights=block_nights,
            simulations=SIMULATIONS,
            rng=rng,
        )

        output_file = (
            OUTPUT
            / f"block_{block_nights}_nights_results.csv"
        )

        results.to_csv(output_file, index=False)

        summary = {
            "block_nights": block_nights,
            "simulations": SIMULATIONS,
            "global_fap": base.empirical_fap(
                results["global_max_power"],
                observed["global_max_power"],
            ),
            "global_null_95": float(
                results["global_max_power"].quantile(0.95)
            ),
            "global_null_99": float(
                results["global_max_power"].quantile(0.99)
            ),
        }

        for candidate in base.CANDIDATES:
            column = f"{candidate}_local_max_power"

            summary[f"{candidate}_local_fap"] = (
                base.empirical_fap(
                    results[column],
                    observed[column],
                )
            )

            summary[f"{candidate}_null_95"] = float(
                results[column].quantile(0.95)
            )

            summary[f"{candidate}_null_99"] = float(
                results[column].quantile(0.99)
            )

        summaries.append(summary)

        print("\n===== BLOCK LENGTH SUMMARY =====")
        print(json.dumps(summary, indent=2))

        print("Saved:", output_file)

    summary_df = pd.DataFrame(summaries)

    summary_path = OUTPUT / "block_length_sensitivity_summary.csv"
    summary_df.to_csv(summary_path, index=False)

    metadata = {
        "experiment": "HD115617 Block-Length Sensitivity Validation v1",
        "input": str(base.INPUT),
        "model": "PLUS_BOTH",
        "valid_observations": int(len(df)),
        "unique_observing_nights": int(
            df["BJD"].astype(int).nunique()
        ),
        "block_lengths_nights": BLOCK_LENGTHS,
        "simulations_per_block_length": SIMULATIONS,
        "total_simulations": SIMULATIONS * len(BLOCK_LENGTHS),
        "random_seed_base": SEED,
        "frequency_min_cycles_per_day": base.FREQ_MIN,
        "frequency_max_cycles_per_day": base.FREQ_MAX,
        "frequency_bins": base.FREQ_BINS,
        "candidate_periods_days": base.CANDIDATES,
        "method": "Non-overlapping consecutive observing-night block sign-flip",
        "limitations": [
            "Conditional on PLUS_BOTH residuals",
            "Candidate periods were selected using the same dataset",
            "Block sign-flip assumes approximate sign symmetry",
            "Sensitivity analysis does not independently validate planets",
            "Block boundaries may affect the results",
            "This is not a conventional moving-block bootstrap",
        ],
    }

    (OUTPUT / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\n===== FINAL SENSITIVITY TABLE =====")
    print(summary_df.to_string(index=False))

    print("\n===== OUTPUT FILES =====")
    for path in sorted(OUTPUT.iterdir()):
        if path.is_file():
            print(path)

    print("\nTotal elapsed seconds:", round(time.time() - started, 2))
    print("\nBLOCK-LENGTH SENSITIVITY VALIDATION COMPLETED.")


if __name__ == "__main__":
    main()
