from pathlib import Path
from itertools import combinations
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr


ROOT = Path(__file__).resolve().parents[1]

RAW_FILE = ROOT / "data" / "input" / "harps_rv_observations_18_targets.csv"

RESIDUAL_FILE = (
    ROOT / "experiments"
    / "HD115617_correlated_noise_validation_v1"
    / "residual_diagnostics.csv"
)

OUTPUT_DIR = ROOT / "experiments" / "HD115617_night_level_correlated_noise_v1"

TARGET = "HD115617"

BLOCK_LENGTHS = [1, 3, 5, 10]


def safe_corr(x, y, method="pearson"):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]

    if len(x) < 3:
        return np.nan

    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan

    if method == "pearson":
        return float(pearsonr(x, y).statistic)

    return float(spearmanr(x, y).statistic)


def describe_pairs(x, y):
    return {
        "pair_count": int(len(x)),
        "pearson": safe_corr(x, y, "pearson"),
        "spearman": safe_corr(x, y, "spearman"),
    }


def main():
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output folder already exists: {OUTPUT_DIR}"
        )

    if not RAW_FILE.exists():
        raise FileNotFoundError(RAW_FILE)

    if not RESIDUAL_FILE.exists():
        raise FileNotFoundError(RESIDUAL_FILE)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    print("===== NIGHT-LEVEL CORRELATED NOISE INVESTIGATION V1 =====")

    raw = pd.read_csv(RAW_FILE)
    residuals = pd.read_csv(RESIDUAL_FILE)

    required_raw = {
        "tel_object",
        "date_obs",
        "drs_bjd",
        "drs_bis_span",
        "drs_ccf_fwhm",
    }

    required_residual = {
        "BJD",
        "date_obs",
        "OU_standardized_innovation",
        "OU_innovation_mps",
        "OU_innovation_variance",
    }

    missing_raw = required_raw - set(raw.columns)
    missing_residual = required_residual - set(residuals.columns)

    if missing_raw:
        raise ValueError(f"Missing raw columns: {sorted(missing_raw)}")

    if missing_residual:
        raise ValueError(
            f"Missing residual columns: {sorted(missing_residual)}"
        )

    raw = raw.loc[raw["tel_object"].astype(str) == TARGET].copy()

    residuals = residuals.copy()

    raw["drs_bjd"] = pd.to_numeric(raw["drs_bjd"], errors="coerce")
    residuals["BJD"] = pd.to_numeric(residuals["BJD"], errors="coerce")

    raw = raw.dropna(subset=["drs_bjd"])
    residuals = residuals.dropna(subset=["BJD"])

    if raw["drs_bjd"].duplicated().any():
        raise ValueError("Duplicate BJD values found in raw target data.")

    if residuals["BJD"].duplicated().any():
        raise ValueError("Duplicate BJD values found in residual data.")

    raw = raw.rename(columns={"drs_bjd": "BJD"})

    raw_columns = [
        "BJD",
        "date_obs",
        "drs_bis_span",
        "drs_ccf_fwhm",
    ]

    merged = residuals.merge(
        raw[raw_columns],
        on="BJD",
        how="inner",
        suffixes=("_residual", "_raw"),
        validate="one_to_one",
    )

    if len(merged) != len(residuals) or len(merged) != len(raw):
        raise ValueError(
            "Exact BJD matching failed. "
            f"Raw={len(raw)}, residuals={len(residuals)}, "
            f"matched={len(merged)}"
        )

    merged["date_obs_residual"] = pd.to_datetime(
        merged["date_obs_residual"],
        errors="coerce",
        utc=True,
    )

    merged["date_obs_raw"] = pd.to_datetime(
        merged["date_obs_raw"],
        errors="coerce",
        utc=True,
    )

    if merged["date_obs_residual"].isna().any():
        raise ValueError("Invalid residual date_obs timestamps found.")

    if merged["date_obs_raw"].isna().any():
        raise ValueError("Invalid raw date_obs timestamps found.")

    date_mismatches = (
        merged["date_obs_residual"].dt.date
        != merged["date_obs_raw"].dt.date
    )

    if date_mismatches.any():
        raise ValueError(
            f"UTC calendar-date mismatch in {int(date_mismatches.sum())} rows."
        )

    merged["utc_night"] = merged["date_obs_residual"].dt.strftime("%Y-%m-%d")

    numeric_columns = [
        "OU_standardized_innovation",
        "OU_innovation_mps",
        "OU_innovation_variance",
        "drs_bis_span",
        "drs_ccf_fwhm",
        "BJD",
    ]

    for column in numeric_columns:
        merged[column] = pd.to_numeric(
            merged[column],
            errors="coerce",
        )

    merged = merged.replace([np.inf, -np.inf], np.nan)

    merged = merged.dropna(
        subset=[
            "BJD",
            "utc_night",
            "OU_standardized_innovation",
        ]
    ).sort_values("BJD").reset_index(drop=True)

    if len(merged) != 1213:
        print(
            f"WARNING: Expected 1213 matched observations; "
            f"found {len(merged)}."
        )

    print(f"Matched observations: {len(merged)}")

    # ---------------------------------------------------------
    # 1. UTC NIGHT-LEVEL AGGREGATION
    # ---------------------------------------------------------

    nightly = (
        merged.groupby("utc_night", as_index=False)
        .agg(
            observation_count=("BJD", "size"),
            mean_BJD=("BJD", "mean"),
            mean_innovation=("OU_standardized_innovation", "mean"),
            median_innovation=("OU_standardized_innovation", "median"),
            std_innovation=("OU_standardized_innovation", "std"),
            mean_innovation_mps=("OU_innovation_mps", "mean"),
            mean_innovation_variance=("OU_innovation_variance", "mean"),
            mean_BIS_span=("drs_bis_span", "mean"),
            median_BIS_span=("drs_bis_span", "median"),
            mean_FWHM=("drs_ccf_fwhm", "mean"),
            median_FWHM=("drs_ccf_fwhm", "median"),
        )
        .sort_values("mean_BJD")
        .reset_index(drop=True)
    )

    nightly.to_csv(
        OUTPUT_DIR / "nightly_innovation_summary.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # 2. WITHIN-NIGHT PAIRWISE CORRELATION
    # ---------------------------------------------------------

    within_x = []
    within_y = []

    for _, group in merged.groupby("utc_night"):
        values = group["OU_standardized_innovation"].to_numpy(dtype=float)

        if len(values) < 2:
            continue

        for i, j in combinations(range(len(values)), 2):
            within_x.append(values[i])
            within_y.append(values[j])

    within_result = describe_pairs(within_x, within_y)

    # ---------------------------------------------------------
    # 3. ADJACENT UTC NIGHT CORRELATION
    # ---------------------------------------------------------

    nightly["gap_days"] = nightly["mean_BJD"].diff()

    adjacent = nightly.iloc[1:].copy()
    previous = nightly.iloc[:-1].reset_index(drop=True)

    adjacent = adjacent.reset_index(drop=True)

    adjacent["previous_night"] = previous["utc_night"]
    adjacent["previous_mean_innovation"] = previous["mean_innovation"]
    adjacent["previous_median_innovation"] = previous["median_innovation"]

    adjacent["previous_mean_BIS"] = previous["mean_BIS_span"]
    adjacent["previous_mean_FWHM"] = previous["mean_FWHM"]

    adjacent["pearson_pair_product"] = (
        adjacent["previous_mean_innovation"]
        * adjacent["mean_innovation"]
    )

    adjacent.to_csv(
        OUTPUT_DIR / "adjacent_night_pairs.csv",
        index=False,
    )

    adjacent_pearson = safe_corr(
        adjacent["previous_mean_innovation"],
        adjacent["mean_innovation"],
        "pearson",
    )

    adjacent_spearman = safe_corr(
        adjacent["previous_mean_innovation"],
        adjacent["mean_innovation"],
        "spearman",
    )

    adjacent_median_pearson = safe_corr(
        adjacent["previous_median_innovation"],
        adjacent["median_innovation"],
        "pearson",
    )

    adjacent_median_spearman = safe_corr(
        adjacent["previous_median_innovation"],
        adjacent["median_innovation"],
        "spearman",
    )

    # ---------------------------------------------------------
    # 4. NIGHTLY INNOVATION VS ACTIVITY INDICATORS
    # ---------------------------------------------------------

    association_rows = []

    indicators = [
        ("mean_BIS_span", "BIS mean"),
        ("median_BIS_span", "BIS median"),
        ("mean_FWHM", "FWHM mean"),
        ("median_FWHM", "FWHM median"),
    ]

    innovation_columns = [
        ("mean_innovation", "Nightly mean innovation"),
        ("median_innovation", "Nightly median innovation"),
    ]

    for indicator, indicator_label in indicators:
        for innovation, innovation_label in innovation_columns:
            association_rows.append({
                "indicator": indicator_label,
                "innovation_measure": innovation_label,
                "pearson": safe_corr(
                    nightly[indicator],
                    nightly[innovation],
                    "pearson",
                ),
                "spearman": safe_corr(
                    nightly[indicator],
                    nightly[innovation],
                    "spearman",
                ),
                "valid_nights": int(
                    (
                        nightly[indicator].notna()
                        & nightly[innovation].notna()
                    ).sum()
                ),
            })

    associations = pd.DataFrame(association_rows)

    associations.to_csv(
        OUTPUT_DIR / "nightly_activity_associations.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # 5. DESCRIPTIVE BLOCK-LENGTH SENSITIVITY
    # ---------------------------------------------------------

    block_rows = []

    for block_length in BLOCK_LENGTHS:
        block_means = []

        values = nightly["mean_innovation"].to_numpy(dtype=float)

        for start in range(0, len(values), block_length):
            chunk = values[start:start + block_length]
            chunk = chunk[np.isfinite(chunk)]

            if len(chunk) == block_length:
                block_means.append(float(np.mean(chunk)))

        block_means = np.asarray(block_means, dtype=float)

        if len(block_means) >= 3:
            x = block_means[:-1]
            y = block_means[1:]

            pearson = safe_corr(x, y, "pearson")
            spearman = safe_corr(x, y, "spearman")
            pair_count = len(x)
        else:
            pearson = np.nan
            spearman = np.nan
            pair_count = 0

        block_rows.append({
            "consecutive_night_block_length": block_length,
            "complete_blocks": int(len(block_means)),
            "adjacent_block_pairs": int(pair_count),
            "pearson": pearson,
            "spearman": spearman,
        })

    block_results = pd.DataFrame(block_rows)

    block_results.to_csv(
        OUTPUT_DIR / "block_length_sensitivity.csv",
        index=False,
    )

    # ---------------------------------------------------------
    # 6. REPORT
    # ---------------------------------------------------------

    report = []

    report.append("NIGHT-LEVEL CORRELATED NOISE INVESTIGATION V1")
    report.append("=" * 60)
    report.append(f"Target: {TARGET}")
    report.append(f"Matched observations: {len(merged)}")
    report.append(f"UTC observing nights: {len(nightly)}")
    report.append(
        f"Median observations per night: "
        f"{nightly['observation_count'].median():.3f}"
    )
    report.append(
        f"Maximum observations per night: "
        f"{nightly['observation_count'].max()}"
    )

    report.append("")
    report.append("EXACT MATCH VALIDATION")
    report.append("-" * 60)
    report.append("Raw drs_bjd matched to residual BJD: one-to-one")
    report.append("Raw and residual UTC calendar dates: matched")

    report.append("")
    report.append("WITHIN-NIGHT PAIRWISE INNOVATION CORRELATION")
    report.append("-" * 60)
    report.append(f"Pairs: {within_result['pair_count']}")
    report.append(f"Pearson: {within_result['pearson']}")
    report.append(f"Spearman: {within_result['spearman']}")

    report.append("")
    report.append("ADJACENT UTC-NIGHT CORRELATION")
    report.append("-" * 60)
    report.append(f"Adjacent night pairs: {len(adjacent)}")
    report.append(
        f"Median BJD gap days: {adjacent['gap_days'].median():.6f}"
    )
    report.append(f"Mean innovation Pearson: {adjacent_pearson}")
    report.append(f"Mean innovation Spearman: {adjacent_spearman}")
    report.append(f"Median innovation Pearson: {adjacent_median_pearson}")
    report.append(f"Median innovation Spearman: {adjacent_median_spearman}")

    report.append("")
    report.append("NIGHTLY ACTIVITY INDICATOR ASSOCIATIONS")
    report.append("-" * 60)

    for _, row in associations.iterrows():
        report.append(
            f"{row['indicator']} vs {row['innovation_measure']}: "
            f"Pearson={row['pearson']}, "
            f"Spearman={row['spearman']}, "
            f"N={row['valid_nights']}"
        )

    report.append("")
    report.append("DESCRIPTIVE BLOCK-LENGTH SENSITIVITY")
    report.append("-" * 60)

    for _, row in block_results.iterrows():
        report.append(
            f"Block length {int(row['consecutive_night_block_length'])} nights: "
            f"blocks={int(row['complete_blocks'])}, "
            f"pairs={int(row['adjacent_block_pairs'])}, "
            f"Pearson={row['pearson']}, "
            f"Spearman={row['spearman']}"
        )

    report.append("")
    report.append("SCIENTIFIC LIMITATIONS")
    report.append("-" * 60)
    report.append(
        "1. These are descriptive diagnostics, not formal significance tests."
    )
    report.append(
        "2. Pairwise observations and adjacent-night pairs are not independent."
    )
    report.append(
        "3. Block-length sensitivity uses consecutive non-overlapping "
        "groups of observing nights; it is not a bootstrap."
    )
    report.append(
        "4. BIS/FWHM associations do not establish a causal activity origin."
    )
    report.append(
        "5. No observations were removed and no RV model was refitted."
    )
    report.append(
        "6. OU innovations are conditional on the existing OU fit and "
        "Keplerian residuals."
    )
    report.append(
        "7. This experiment does not confirm or reject any planet candidate."
    )

    report_text = "\n".join(report)

    (OUTPUT_DIR / "report.txt").write_text(
        report_text,
        encoding="utf-8",
    )

    metadata = {
        "experiment": "Night-Level Correlated Noise Investigation V1",
        "target": TARGET,
        "observations": int(len(merged)),
        "utc_nights": int(len(nightly)),
        "raw_residual_exact_bjd_match": True,
        "utc_calendar_dates_match": True,
        "block_lengths": BLOCK_LENGTHS,
        "production_code_modified": False,
        "observations_removed": 0,
        "model_refitted": False,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }

    (OUTPUT_DIR / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("")
    print("===== INVESTIGATION COMPLETE =====")
    print(f"Output folder: {OUTPUT_DIR}")
    print(f"UTC nights: {len(nightly)}")
    print(f"Within-night Pearson: {within_result['pearson']}")
    print(f"Adjacent-night Pearson: {adjacent_pearson}")
    print(f"Adjacent-night Spearman: {adjacent_spearman}")
    print("")
    print(report_text)


if __name__ == "__main__":
    main()
