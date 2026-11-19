from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import numpy as np
import pandas as pd

FILE = DATA_DIR / "phase2_6_pi_men_harps_timeseries.csv"

print("===== PI MEN RV DATA DIAGNOSTICS =====")

df = pd.read_csv(FILE)

rv = df["rv_relative_ms"].to_numpy(float)
err = df["rv_error_ms"].to_numpy(float)
bjd = df["bjd"].to_numpy(float)

valid = (
    np.isfinite(rv)
    & np.isfinite(err)
    & np.isfinite(bjd)
    & (err > 0)
)

df = df.loc[valid].copy()
rv = df["rv_relative_ms"].to_numpy(float)
err = df["rv_error_ms"].to_numpy(float)

median = np.median(rv)
mad = np.median(np.abs(rv - median))
robust_sigma = 1.4826 * mad

print("\n===== RV DISTRIBUTION =====")
print("Observations:", len(rv))
print("Minimum RV:", np.min(rv))
print("Maximum RV:", np.max(rv))
print("Median RV:", median)
print("Mean RV:", np.mean(rv))
print("Standard deviation:", np.std(rv))
print("MAD:", mad)
print("Robust sigma:", robust_sigma)

print("\n===== RV PERCENTILES =====")

for p in [0, 1, 5, 25, 50, 75, 95, 99, 100]:
    print(f"P{p}: {np.percentile(rv, p):.5f}")

print("\n===== RV UNCERTAINTY =====")
print("Minimum:", np.min(err))
print("Median:", np.median(err))
print("Maximum:", np.max(err))
print("Mean:", np.mean(err))

print("\n===== EXTREME RV OBSERVATIONS =====")

df["abs_deviation"] = np.abs(
    df["rv_relative_ms"] - median
)

extreme = df.nlargest(15, "abs_deviation")

columns = [
    "date_obs",
    "bjd",
    "rv_relative_ms",
    "rv_error_ms",
    "drs_snr",
    "drs_bis_rv",
    "drs_ccf_fwhm"
]

columns = [c for c in columns if c in df.columns]

print(extreme[columns].to_string(index=False))

print("\n===== EXTREME VALUE COUNTS =====")

for threshold in [10, 25, 50, 100, 250, 500]:
    count = np.sum(np.abs(rv - median) > threshold)
    print(f"|RV - median| > {threshold} m/s: {count}")

print("\n===== CORRELATIONS =====")

for col in ["drs_snr", "drs_bis_rv", "drs_ccf_fwhm",
            "drs_ccf_contrast"]:
    if col in df.columns:
        values = pd.to_numeric(df[col], errors="coerce")
        corr = pd.Series(rv).corr(values.reset_index(drop=True))
        print(f"RV vs {col}: {corr:.5f}")

print("\n===== DIAGNOSTIC COMPLETE =====")
