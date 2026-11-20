from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr, theilslopes


ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT / "experiments"
    / "HD115617_night_level_correlated_noise_v1"
    / "nightly_innovation_summary.csv"
)

OUTPUT = (
    ROOT / "experiments"
    / "HD115617_night_level_influence_robustness_v1"
)

TARGET = "HD115617"

PAIRS = [
    ("mean_BIS_span", "mean_innovation", "BIS mean"),
    ("median_BIS_span", "median_innovation", "BIS median"),
    ("mean_FWHM", "mean_innovation", "FWHM mean"),
    ("median_FWHM", "median_innovation", "FWHM median"),
]


def correlations(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]

    result = {
        "n": int(len(x)),
        "pearson": np.nan,
        "spearman": np.nan,
        "theil_sen_slope": np.nan,
        "theil_sen_intercept": np.nan,
    }

    if len(x) < 3:
        return result

    if np.std(x) > 0 and np.std(y) > 0:
        result["pearson"] = float(pearsonr(x, y).statistic)
        result["spearman"] = float(spearmanr(x, y).statistic)

    if len(np.unique(x)) >= 2:
        fit = theilslopes(y, x)
        result["theil_sen_slope"] = float(fit.slope)
        result["theil_sen_intercept"] = float(fit.intercept)

    return result


def robust_zscore(series):
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    median = np.nanmedian(values)
    mad = np.nanmedian(np.abs(values - median))

    if not np.isfinite(mad) or mad == 0:
        return np.full(len(values), np.nan)

    return 0.67448975 * (values - median) / mad


def main():
    if OUTPUT.exists():
        raise FileExistsError(f"Output exists: {OUTPUT}")

    if not INPUT.exists():
        raise FileNotFoundError(INPUT)

    OUTPUT.mkdir(parents=True, exist_ok=False)

    df = pd.read_csv(INPUT)

    required = {
        "utc_night",
        "mean_BJD",
        "observation_count",
        "mean_innovation",
        "median_innovation",
        "mean_BIS_span",
        "median_BIS_span",
        "mean_FWHM",
        "median_FWHM",
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    for col in required - {"utc_night"}:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=["utc_night", "mean_BJD", "mean_innovation"])
    df = df.sort_values("mean_BJD").reset_index(drop=True)

    if df["utc_night"].duplicated().any():
        raise ValueError("Duplicate UTC nights detected.")

    print("===== NIGHT-LEVEL INFLUENCE & ROBUSTNESS AUDIT V1 =====")
    print(f"Target: {TARGET}")
    print(f"UTC nights: {len(df)}")

    # -------------------------------------------------
    # 1. FULL-SAMPLE ASSOCIATIONS
    # -------------------------------------------------

    full_rows = []

    for xcol, ycol, label in PAIRS:
        result = correlations(df[xcol], df[ycol])
        full_rows.append({
            "indicator": label,
            "x_column": xcol,
            "y_column": ycol,
            **result,
        })

    full = pd.DataFrame(full_rows)
    full.to_csv(OUTPUT / "full_sample_associations.csv", index=False)

    # -------------------------------------------------
    # 2. LEAVE-ONE-NIGHT-OUT INFLUENCE
    # -------------------------------------------------

    influence_rows = []

    for xcol, ycol, label in PAIRS:
        base = correlations(df[xcol], df[ycol])

        for index, row in df.iterrows():
            reduced = df.drop(index=index)
            result = correlations(reduced[xcol], reduced[ycol])

            influence_rows.append({
                "indicator": label,
                "removed_utc_night": row["utc_night"],
                "removed_observation_count": int(row["observation_count"]),
                "removed_mean_innovation": row["mean_innovation"],
                "base_pearson": base["pearson"],
                "loo_pearson": result["pearson"],
                "delta_pearson": result["pearson"] - base["pearson"],
                "base_spearman": base["spearman"],
                "loo_spearman": result["spearman"],
                "delta_spearman": result["spearman"] - base["spearman"],
                "base_theil_sen_slope": base["theil_sen_slope"],
                "loo_theil_sen_slope": result["theil_sen_slope"],
            })

    influence = pd.DataFrame(influence_rows)

    influence.to_csv(
        OUTPUT / "leave_one_night_out_influence.csv",
        index=False,
    )

    # -------------------------------------------------
    # 3. EXTREME NIGHT FLAGS USING ROBUST MAD Z-SCORES
    # -------------------------------------------------

    flag_columns = [
        "mean_innovation",
        "median_innovation",
        "mean_BIS_span",
        "mean_FWHM",
    ]

    for col in flag_columns:
        df[f"{col}_robust_z"] = robust_zscore(df[col])

    flag_mask = np.zeros(len(df), dtype=bool)

    for col in flag_columns:
        flag_mask |= df[f"{col}_robust_z"].abs().gt(3.5).fillna(False).to_numpy()

    extremes = df.loc[flag_mask].copy()

    extremes.to_csv(
        OUTPUT / "extreme_night_flags.csv",
        index=False,
    )

    # -------------------------------------------------
    # 4. SENSITIVITY EXCLUDING ONE FLAGGED NIGHT AT A TIME
    # -------------------------------------------------

    sensitivity_rows = []

    for xcol, ycol, label in PAIRS:
        base = correlations(df[xcol], df[ycol])

        if extremes.empty:
            sensitivity_rows.append({
                "indicator": label,
                "excluded_night": "NONE",
                "pearson": base["pearson"],
                "spearman": base["spearman"],
            })

        for index, row in extremes.iterrows():
            reduced = df.drop(index=index)
            result = correlations(reduced[xcol], reduced[ycol])

            sensitivity_rows.append({
                "indicator": label,
                "excluded_night": row["utc_night"],
                "pearson": result["pearson"],
                "spearman": result["spearman"],
            })

    pd.DataFrame(sensitivity_rows).to_csv(
        OUTPUT / "extreme_night_sensitivity.csv",
        index=False,
    )

    # -------------------------------------------------
    # 5. ROBUST TIME-TREND ANALYSIS
    # -------------------------------------------------

    time_rows = []

    for col in ["mean_innovation", "median_innovation"]:
        valid = df[["mean_BJD", col]].dropna()

        result = correlations(valid["mean_BJD"], valid[col])

        time_rows.append({
            "innovation_measure": col,
            **result,
        })

    pd.DataFrame(time_rows).to_csv(
        OUTPUT / "innovation_time_trend.csv",
        index=False,
    )

    # -------------------------------------------------
    # 6. MOST INFLUENTIAL NIGHTS
    # -------------------------------------------------

    top_rows = []

    for label in influence["indicator"].unique():
        subset = influence[influence["indicator"] == label]

        top = subset.reindex(
            subset["delta_pearson"].abs()
            .sort_values(ascending=False)
            .index
        ).head(10)

        for _, row in top.iterrows():
            top_rows.append(row.to_dict())

    pd.DataFrame(top_rows).to_csv(
        OUTPUT / "top_influential_nights.csv",
        index=False,
    )

    # -------------------------------------------------
    # 7. REPORT
    # -------------------------------------------------

    lines = [
        "NIGHT-LEVEL INFLUENCE & ROBUSTNESS AUDIT V1",
        "=" * 65,
        f"Target: {TARGET}",
        f"UTC nights: {len(df)}",
        "",
        "FULL-SAMPLE ASSOCIATIONS",
        "-" * 65,
    ]

    for _, row in full.iterrows():
        lines.append(
            f"{row['indicator']}: "
            f"N={row['n']}, "
            f"Pearson={row['pearson']}, "
            f"Spearman={row['spearman']}, "
            f"Theil-Sen slope={row['theil_sen_slope']}"
        )

    lines += [
        "",
        "EXTREME NIGHT FLAGS",
        "-" * 65,
        f"Flagged nights: {len(extremes)}",
        "Flag rule: absolute robust MAD z-score > 3.5 "
        "for at least one selected nightly variable.",
    ]

    if len(extremes):
        for _, row in extremes.iterrows():
            lines.append(
                f"{row['utc_night']}: "
                f"innovation={row['mean_innovation']}, "
                f"BIS={row['mean_BIS_span']}, "
                f"FWHM={row['mean_FWHM']}"
            )

    lines += [
        "",
        "MOST INFLUENTIAL NIGHTS",
        "-" * 65,
    ]

    for _, row in pd.DataFrame(top_rows).iterrows():
        lines.append(
            f"{row['indicator']} | {row['removed_utc_night']} | "
            f"Pearson delta={row['delta_pearson']} | "
            f"Spearman delta={row['delta_spearman']}"
        )

    lines += [
        "",
        "SCIENTIFIC LIMITATIONS",
        "-" * 65,
        "1. Leave-one-night-out analysis is an influence diagnostic, "
        "not a significance test.",
        "2. Robust MAD flags identify unusual values, not bad observations.",
        "3. Excluding flagged nights is sensitivity analysis only; "
        "no observations are deleted from the source data.",
        "4. Theil-Sen slope is a robust descriptive association, "
        "not a causal model.",
        "5. Time-trend correlation does not establish instrumental drift "
        "or stellar activity.",
        "6. No Keplerian or OU model was refitted.",
        "7. No planet confirmation or rejection is made.",
    ]

    report = "\n".join(lines)

    (OUTPUT / "report.txt").write_text(report, encoding="utf-8")

    metadata = {
        "experiment": "Night-Level Influence & Robustness Audit V1",
        "target": TARGET,
        "utc_nights": int(len(df)),
        "flagged_nights": int(len(extremes)),
        "robust_flag_threshold": 3.5,
        "source_observations_modified": False,
        "observations_deleted": 0,
        "model_refitted": False,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
    }

    (OUTPUT / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("")
    print("===== FULL-SAMPLE ASSOCIATIONS =====")
    print(full.to_string(index=False))

    print("")
    print("===== EXTREME NIGHT FLAGS =====")
    print(f"Flagged nights: {len(extremes)}")

    print("")
    print("===== AUDIT COMPLETE =====")
    print(f"Output: {OUTPUT}")
    print(report)


if __name__ == "__main__":
    main()
