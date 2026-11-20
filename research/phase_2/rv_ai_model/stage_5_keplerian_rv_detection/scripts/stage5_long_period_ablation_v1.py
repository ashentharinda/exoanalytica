from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path("research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection")
INPUT = ROOT / "data/input/harps_rv_observations_18_targets.csv"
OUT = ROOT / "experiments/HD115617_long_period_ablation_v1"

GAP = 100.0
P4214 = 4.21421445
P38051 = 38.0511147476
P123 = 123.666123
P185 = 184.576303

MODELS = {
    "A": (False, False, False),
    "B": (True, False, False),
    "B_PLUS_123": (True, True, False),
    "B_PLUS_185": (True, False, True),
    "C_BOTH": (True, True, True),
}


def make_matrix(data, model, t_ref, bis_median=None, bis_std=None):
    use_bis, use_123, use_185 = MODELS[model]
    t = data["drs_bjd"].to_numpy(float)
    bis = data["drs_bis_span"].to_numpy(float)

    cols = [np.ones(len(data))]

    for period in (P4214, P38051):
        phase = 2 * np.pi * (t - t_ref) / period
        cols.extend([np.sin(phase), np.cos(phase)])

    if use_bis:
        cols.append((bis - bis_median) / bis_std)

    if use_123:
        phase = 2 * np.pi * (t - t_ref) / P123
        cols.extend([np.sin(phase), np.cos(phase)])

    if use_185:
        phase = 2 * np.pi * (t - t_ref) / P185
        cols.extend([np.sin(phase), np.cos(phase)])

    return np.column_stack(cols)


def evaluate(train, test, model, t_ref):
    use_bis = MODELS[model][0]

    bis_median = float(train["drs_bis_span"].median()) if use_bis else 0.0
    bis_std = float(train["drs_bis_span"].std(ddof=0)) if use_bis else 1.0

    if use_bis and (not np.isfinite(bis_std) or bis_std <= 0):
        raise ValueError("Invalid BIS Span standard deviation.")

    X_train = make_matrix(train, model, t_ref, bis_median, bis_std)
    X_test = make_matrix(test, model, t_ref, bis_median, bis_std)

    y_train = train["rv_mps"].to_numpy(float)
    y_test = test["rv_mps"].to_numpy(float)
    err_train = train["drs_dvrms"].to_numpy(float)
    err_test = test["drs_dvrms"].to_numpy(float)

    sw = 1.0 / err_train
    coef, _, rank, _ = np.linalg.lstsq(
        X_train * sw[:, None],
        y_train * sw,
        rcond=None,
    )

    residual = y_test - X_test @ coef
    chi2 = float(np.sum((residual / err_test) ** 2))
    weighted_rmse = float(
        np.sqrt(
            np.sum((residual / err_test) ** 2)
            / np.sum(1.0 / err_test**2)
        )
    )

    return {
        "model": model,
        "train_n": len(train),
        "test_n": len(test),
        "rank": int(rank),
        "parameters": int(X_train.shape[1]),
        "test_chi2": chi2,
        "test_weighted_rmse_mps": weighted_rmse,
        "test_median_abs_residual_mps": float(np.median(np.abs(residual))),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=False)

    df = pd.read_csv(INPUT)
    df = df[
        df["tel_object"].astype(str).str.contains(
            r"HD\s*115617|61\s*Vir",
            case=False,
            regex=True,
            na=False,
        )
    ].copy()

    required = ["drs_bjd", "rv_mps", "drs_dvrms", "drs_bis_span"]
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    original_n = len(df)
    df = df.dropna(subset=required)
    df = df[np.isfinite(df[required]).all(axis=1)]
    df = df[df["drs_dvrms"] > 0]
    df = df.sort_values("drs_bjd").reset_index(drop=True)

    if len(df) != 1213:
        raise RuntimeError(
            f"Expected 1213 valid rows based on prior validation; found {len(df)}."
        )

    gaps = np.diff(df["drs_bjd"].to_numpy(float))
    df["season_id"] = np.r_[0, np.cumsum(gaps >= GAP)]

    season_stats = df.groupby("season_id").agg(
        observations=("drs_bjd", "size"),
        start_bjd=("drs_bjd", "min"),
        end_bjd=("drs_bjd", "max"),
    )
    season_stats["span_days"] = (
        season_stats["end_bjd"] - season_stats["start_bjd"]
    )
    eligible = season_stats[
        (season_stats["observations"] >= 20)
        & (season_stats["span_days"] >= 60)
    ].index.tolist()

    t_ref = float(df["drs_bjd"].iloc[0])
    rows = []

    for held_out in eligible:
        train = df[df["season_id"] != held_out]
        test = df[df["season_id"] == held_out]

        for model in MODELS:
            result = evaluate(train, test, model, t_ref)
            result["held_out_season"] = int(held_out)
            result["season_span_days"] = float(
                test["drs_bjd"].max() - test["drs_bjd"].min()
            )
            rows.append(result)

    results = pd.DataFrame(rows)
    results.to_csv(OUT / "ablation_loso_metrics.csv", index=False)

    pivot_rmse = results.pivot(
        index="held_out_season",
        columns="model",
        values="test_weighted_rmse_mps",
    )
    pivot_chi2 = results.pivot(
        index="held_out_season",
        columns="model",
        values="test_chi2",
    )

    comparisons = []
    for sid in eligible:
        comparisons.append({
            "held_out_season": int(sid),
            "B_rmse": pivot_rmse.loc[sid, "B"],
            "B_PLUS_123_rmse": pivot_rmse.loc[sid, "B_PLUS_123"],
            "B_PLUS_185_rmse": pivot_rmse.loc[sid, "B_PLUS_185"],
            "C_BOTH_rmse": pivot_rmse.loc[sid, "C_BOTH"],
            "B_minus_123_rmse": (
                pivot_rmse.loc[sid, "B"] -
                pivot_rmse.loc[sid, "B_PLUS_123"]
            ),
            "B_minus_185_rmse": (
                pivot_rmse.loc[sid, "B"] -
                pivot_rmse.loc[sid, "B_PLUS_185"]
            ),
            "B_minus_both_rmse": (
                pivot_rmse.loc[sid, "B"] -
                pivot_rmse.loc[sid, "C_BOTH"]
            ),
            "B_minus_123_chi2": (
                pivot_chi2.loc[sid, "B"] -
                pivot_chi2.loc[sid, "B_PLUS_123"]
            ),
            "B_minus_185_chi2": (
                pivot_chi2.loc[sid, "B"] -
                pivot_chi2.loc[sid, "B_PLUS_185"]
            ),
            "B_minus_both_chi2": (
                pivot_chi2.loc[sid, "B"] -
                pivot_chi2.loc[sid, "C_BOTH"]
            ),
        })

    comp = pd.DataFrame(comparisons)
    comp.to_csv(OUT / "ablation_fold_comparison.csv", index=False)

    models = ["A", "B", "B_PLUS_123", "B_PLUS_185", "C_BOTH"]
    summary_rows = []

    for model in models:
        sub = results[results["model"] == model]
        summary_rows.append({
            "model": model,
            "folds": len(sub),
            "median_test_weighted_rmse_mps": sub[
                "test_weighted_rmse_mps"
            ].median(),
            "median_test_chi2": sub["test_chi2"].median(),
        })

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "ablation_model_summary.csv", index=False)

    report = [
        "HD115617 LONG-PERIOD ABLATION VALIDATION v1",
        "=" * 58,
        f"Original target rows: {original_n}",
        f"Valid observations: {len(df)}",
        f"Eligible LOSO seasons: {len(eligible)}",
        f"Eligible season IDs: {eligible}",
        "",
        "MODEL DEFINITIONS",
        "A: 4.214d + 38.051d",
        "B: Model A + standardized BIS Span",
        "B_PLUS_123: Model B + 123.666d",
        "B_PLUS_185: Model B + 184.576d",
        "C_BOTH: Model B + both long-period terms",
        "",
        "MEDIAN HELD-OUT METRICS",
        "-" * 58,
    ]

    for _, row in summary.iterrows():
        report.append(
            f"{row['model']}: median weighted RMSE="
            f"{row['median_test_weighted_rmse_mps']:.6f} m/s; "
            f"median chi2={row['median_test_chi2']:.3f}"
        )

    report.extend([
        "",
        "PERIOD-SPECIFIC IMPROVEMENT COUNTS",
        "-" * 58,
        f"123d improves over B: "
        f"{int((comp['B_minus_123_rmse'] > 0).sum())}/{len(comp)} folds",
        f"185d improves over B: "
        f"{int((comp['B_minus_185_rmse'] > 0).sum())}/{len(comp)} folds",
        f"Both improve over B: "
        f"{int((comp['B_minus_both_rmse'] > 0).sum())}/{len(comp)} folds",
        "",
        "MEDIAN WEIGHTED RMSE IMPROVEMENT VS MODEL B",
        f"123d only: {comp['B_minus_123_rmse'].median():.6f} m/s",
        f"185d only: {comp['B_minus_185_rmse'].median():.6f} m/s",
        f"Both: {comp['B_minus_both_rmse'].median():.6f} m/s",
        "",
        "SCIENTIFIC LIMITATIONS",
        "1. Fixed-period sinusoidal models; not full Keplerian fits.",
        "2. LOSO folds are observing blocks defined by a 100-day gap.",
        "3. Long-period signals are not fully sampled within every block.",
        "4. Predictive improvement does not prove planetary origin.",
        "5. Correlated stellar noise and instrumental systematics remain possible.",
        "6. Results depend on the selected candidate periods.",
    ])

    (OUT / "report.txt").write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )

    metadata = {
        "target": "HD115617",
        "input": str(INPUT),
        "gap_threshold_days": GAP,
        "eligible_seasons": [int(x) for x in eligible],
        "periods_days": {
            "4.214": P4214,
            "38.051": P38051,
            "123.666": P123,
            "184.576": P185,
        },
        "method": "Weighted least squares leave-one-season-out ablation",
        "models": MODELS,
    }
    (OUT / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\n===== ABLATION VALIDATION COMPLETE =====")
    print("Output:", OUT.resolve())
    print("\n===== MODEL SUMMARY =====")
    print(summary.to_string(index=False))
    print("\n===== FOLD COMPARISON =====")
    print(comp.to_string(index=False))
    print("\n===== REPORT =====")
    print((OUT / "report.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
