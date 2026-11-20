from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(
    "research/phase_2/rv_ai_model/stage_5_keplerian_rv_detection"
)
INPUT = ROOT / "data/input/harps_rv_observations_18_targets.csv"
OUT = ROOT / "experiments/HD115617_seasonal_stability_v1"

TARGET = "HD115617"
GAP_THRESHOLD_DAYS = 100.0

PERIODS = {
    "p_4_214": 4.21421445,
    "p_38_051": 38.0511147476,
    "p_123_666": 123.666123,
    "p_184_576": 184.576303,
}

def design_matrix(t, bis, model, t_ref, bis_median=None, bis_std=None):
    columns = [np.ones(len(t))]
    labels = ["constant"]

    def add_period(period, prefix):
        phase = 2.0 * np.pi * (t - t_ref) / period
        columns.extend([np.sin(phase), np.cos(phase)])
        labels.extend([f"{prefix}_sin", f"{prefix}_cos"])

    add_period(PERIODS["p_4_214"], "p4214")
    add_period(PERIODS["p_38_051"], "p38051")

    if model in ("B", "C"):
        if bis_median is None or bis_std is None or bis_std <= 0:
            raise ValueError("Invalid training BIS standardization.")
        columns.append((bis - bis_median) / bis_std)
        labels.append("bis_standardized")

    if model == "C":
        add_period(PERIODS["p_123_666"], "p123666")
        add_period(PERIODS["p_184_576"], "p184576")

    return np.column_stack(columns), labels


def fit_predict(train, test, model, t_ref):
    t_train = train["drs_bjd"].to_numpy(float)
    y_train = train["rv_mps"].to_numpy(float)
    e_train = train["drs_dvrms"].to_numpy(float)
    b_train = train["drs_bis_span"].to_numpy(float)

    t_test = test["drs_bjd"].to_numpy(float)
    y_test = test["rv_mps"].to_numpy(float)
    e_test = test["drs_dvrms"].to_numpy(float)
    b_test = test["drs_bis_span"].to_numpy(float)

    bis_median = None
    bis_std = None

    if model in ("B", "C"):
        bis_median = float(np.median(b_train))
        bis_std = float(np.std(b_train))
        if not np.isfinite(bis_std) or bis_std <= 0:
            raise ValueError("BIS Span has invalid training standard deviation.")

    X_train, labels = design_matrix(
        t_train, b_train, model, t_ref, bis_median, bis_std
    )
    X_test, _ = design_matrix(
        t_test, b_test, model, t_ref, bis_median, bis_std
    )

    weights = 1.0 / np.square(e_train)
    sqrt_w = np.sqrt(weights)

    coefficients, _, rank, _ = np.linalg.lstsq(
        X_train * sqrt_w[:, None],
        y_train * sqrt_w,
        rcond=None,
    )

    prediction_train = X_train @ coefficients
    prediction_test = X_test @ coefficients

    residual_train = y_train - prediction_train
    residual_test = y_test - prediction_test

    test_chi2 = float(np.sum(np.square(residual_test / e_test)))
    test_weighted_rmse = float(
        np.sqrt(
            np.sum(np.square(residual_test) / np.square(e_test))
            / np.sum(1.0 / np.square(e_test))
        )
    )

    result = {
        "model": model,
        "train_n": len(train),
        "test_n": len(test),
        "train_rank": int(rank),
        "train_parameters": len(coefficients),
        "test_chi2": test_chi2,
        "test_weighted_rmse_mps": test_weighted_rmse,
        "test_median_abs_residual_mps": float(
            np.median(np.abs(residual_test))
        ),
        "train_rms_residual_mps": float(
            np.sqrt(np.mean(np.square(residual_train)))
        ),
    }

    if model == "C":
        coefficient_map = dict(zip(labels, coefficients))

        for prefix, period in [
            ("p123666", PERIODS["p_123_666"]),
            ("p184576", PERIODS["p_184_576"]),
        ]:
            sine = float(coefficient_map[f"{prefix}_sin"])
            cosine = float(coefficient_map[f"{prefix}_cos"])
            amplitude = float(np.hypot(sine, cosine))
            phase = float(np.degrees(np.arctan2(cosine, sine)))

            result[f"{prefix}_amplitude_mps"] = amplitude
            result[f"{prefix}_phase_deg"] = phase

    return result


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

    original_rows = len(df)
    df = df.dropna(subset=required).copy()
    df = df[
        np.isfinite(df[required]).all(axis=1)
        & (df["drs_dvrms"] > 0)
    ].copy()

    df = df.sort_values("drs_bjd").reset_index(drop=True)

    if len(df) < 100:
        raise RuntimeError("Insufficient valid observations.")

    t = df["drs_bjd"].to_numpy(float)
    gaps = np.diff(t)

    season_ids = np.r_[
        0,
        np.cumsum(gaps >= GAP_THRESHOLD_DAYS)
    ]
    df["season_id"] = season_ids

    season_rows = []
    for sid, group in df.groupby("season_id"):
        span = float(group["drs_bjd"].max() - group["drs_bjd"].min())
        n = len(group)

        eligible = n >= 20 and span >= 60.0

        season_rows.append({
            "season_id": int(sid),
            "observations": int(n),
            "start_bjd": float(group["drs_bjd"].min()),
            "end_bjd": float(group["drs_bjd"].max()),
            "span_days": span,
            "cycles_123_666d": span / PERIODS["p_123_666"],
            "cycles_184_576d": span / PERIODS["p_184_576"],
            "eligible_for_loso": bool(eligible),
        })

    seasons = pd.DataFrame(season_rows)
    seasons.to_csv(OUT / "season_summary.csv", index=False)

    eligible_ids = seasons.loc[
        seasons["eligible_for_loso"], "season_id"
    ].astype(int).tolist()

    if len(eligible_ids) < 3:
        raise RuntimeError(
            "Fewer than three eligible observing seasons. "
            "LOSO validation is not sufficiently supported."
        )

    t_ref = float(df["drs_bjd"].iloc[0])

    # Full-data diagnostic fits.
    full_rows = []
    full_data = df.copy()

    for model in ["A", "B", "C"]:
        result = fit_predict(
            full_data,
            full_data,
            model,
            t_ref,
        )
        result["fit_scope"] = "full_data_diagnostic"
        full_rows.append(result)

    pd.DataFrame(full_rows).to_csv(
        OUT / "full_data_model_metrics.csv",
        index=False,
    )

    # Leave one eligible observing season out at a time.
    fold_rows = []

    for held_out_id in eligible_ids:
        train = df[df["season_id"] != held_out_id].copy()
        test = df[df["season_id"] == held_out_id].copy()

        for model in ["A", "B", "C"]:
            result = fit_predict(train, test, model, t_ref)
            result["held_out_season"] = held_out_id
            result["test_start_bjd"] = float(test["drs_bjd"].min())
            result["test_end_bjd"] = float(test["drs_bjd"].max())
            result["test_span_days"] = float(
                test["drs_bjd"].max() - test["drs_bjd"].min()
            )
            fold_rows.append(result)

    folds = pd.DataFrame(fold_rows)
    folds.to_csv(OUT / "loso_fold_metrics.csv", index=False)

    # Compare whether adding the 123d/185d components improves
    # held-out predictions relative to Model B.
    comparison_rows = []

    for sid in eligible_ids:
        subset = folds[folds["held_out_season"] == sid]
        b = subset[subset["model"] == "B"].iloc[0]
        c = subset[subset["model"] == "C"].iloc[0]

        comparison_rows.append({
            "held_out_season": int(sid),
            "model_b_test_chi2": float(b["test_chi2"]),
            "model_c_test_chi2": float(c["test_chi2"]),
            "delta_chi2_B_minus_C": float(
                b["test_chi2"] - c["test_chi2"]
            ),
            "model_b_weighted_rmse_mps": float(
                b["test_weighted_rmse_mps"]
            ),
            "model_c_weighted_rmse_mps": float(
                c["test_weighted_rmse_mps"]
            ),
            "delta_weighted_rmse_B_minus_C_mps": float(
                b["test_weighted_rmse_mps"]
                - c["test_weighted_rmse_mps"]
            ),
            "p123666_amplitude_mps": float(
                c["p123666_amplitude_mps"]
            ),
            "p123666_phase_deg": float(c["p123666_phase_deg"]),
            "p184576_amplitude_mps": float(
                c["p184576_amplitude_mps"]
            ),
            "p184576_phase_deg": float(c["p184576_phase_deg"]),
        })

    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(
        OUT / "long_period_loso_comparison.csv",
        index=False,
    )

    report = []
    report.append("HD115617 SEASONAL STABILITY VALIDATION v1")
    report.append("=" * 58)
    report.append(f"Original target rows: {original_rows}")
    report.append(f"Valid numeric observations: {len(df)}")
    report.append(f"Excluded invalid rows: {original_rows - len(df)}")
    report.append(f"Baseline days: {t[-1] - t[0]:.6f}")
    report.append(f"Season gap threshold: {GAP_THRESHOLD_DAYS:.1f} days")
    report.append(f"Total gap-defined seasons: {len(seasons)}")
    report.append(f"Eligible LOSO seasons: {len(eligible_ids)}")
    report.append(f"Eligible season IDs: {eligible_ids}")
    report.append("")
    report.append("SEASON COVERAGE")
    report.append("-" * 58)

    for _, row in seasons.iterrows():
        report.append(
            f"Season {int(row.season_id):02d}: "
            f"N={int(row.observations)}, "
            f"span={row.span_days:.2f} d, "
            f"cycles@123.666={row.cycles_123_666d:.2f}, "
            f"cycles@184.576={row.cycles_184_576d:.2f}, "
            f"LOSO={row.eligible_for_loso}"
        )

    report.append("")
    report.append("LOSO MODEL C VS MODEL B")
    report.append("-" * 58)

    for _, row in comparison.iterrows():
        report.append(
            f"Season {int(row.held_out_season):02d}: "
            f"Delta chi2 (B-C)={row.delta_chi2_B_minus_C:.3f}, "
            f"Delta weighted RMSE (B-C)="
            f"{row.delta_weighted_rmse_B_minus_C_mps:.4f} m/s, "
            f"A123={row.p123666_amplitude_mps:.4f} m/s, "
            f"A185={row.p184576_amplitude_mps:.4f} m/s"
        )

    report.append("")
    report.append("MEDIAN HELD-OUT COMPARISON")
    report.append("-" * 58)
    report.append(
        "Median Delta chi2 (B-C): "
        f"{comparison['delta_chi2_B_minus_C'].median():.4f}"
    )
    report.append(
        "Median Delta weighted RMSE (B-C): "
        f"{comparison['delta_weighted_rmse_B_minus_C_mps'].median():.6f} m/s"
    )
    report.append(
        "Folds where Model C improves held-out weighted RMSE: "
        f"{int((comparison['delta_weighted_rmse_B_minus_C_mps'] > 0).sum())}"
        f"/{len(comparison)}"
    )

    report.append("")
    report.append("SCIENTIFIC LIMITATIONS")
    report.append("-" * 58)
    report.append(
        "1. The 100-day gap rule defines observing blocks, not guaranteed "
        "physical stellar seasons."
    )
    report.append(
        "2. Only blocks with at least 20 observations and 60 days span "
        "are used as held-out LOSO folds."
    )
    report.append(
        "3. Many individual blocks cover fewer than two cycles of the "
        "123d and 185d candidates."
    )
    report.append(
        "4. Model C uses fixed candidate periods and sinusoidal terms; "
        "this is not a full Keplerian or activity Gaussian-process model."
    )
    report.append(
        "5. Held-out improvements are predictive diagnostics, not proof "
        "that either long-period signal is planetary."
    )
    report.append(
        "6. Measurement uncertainties may not capture correlated stellar "
        "noise or all instrumental systematics."
    )
    report.append(
        "7. BIS Span is included as a linear activity proxy; this does "
        "not establish a causal activity model."
    )
    report.append(
        "8. The short and sparse seasons are retained in the season "
        "summary but not treated as independent LOSO validation folds."
    )

    (OUT / "report.txt").write_text(
        "\n".join(report) + "\n",
        encoding="utf-8",
    )

    metadata = {
        "target": TARGET,
        "input_file": str(INPUT),
        "observations_valid": int(len(df)),
        "observations_original": int(original_rows),
        "gap_threshold_days": GAP_THRESHOLD_DAYS,
        "eligible_season_ids": eligible_ids,
        "periods_days": PERIODS,
        "models": {
            "A": "constant + 4.214d + 38.051d",
            "B": "Model A + standardized BIS Span",
            "C": "Model B + 123.666d + 184.576d",
        },
        "method": "Leave-One-Eligible-Season-Out weighted least squares",
    }

    (OUT / "run_metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print("\n===== SEASONAL STABILITY VALIDATION COMPLETE =====")
    print("Target:", TARGET)
    print("Valid observations:", len(df))
    print("Total seasons:", len(seasons))
    print("Eligible LOSO seasons:", len(eligible_ids))
    print("Eligible IDs:", eligible_ids)
    print("\nOutput directory:", OUT.resolve())
    print("\nGenerated files:")
    for path in sorted(OUT.iterdir()):
        print(f" - {path.name} ({path.stat().st_size:,} bytes)")

    print("\n===== REPORT PREVIEW =====")
    print((OUT / "report.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
