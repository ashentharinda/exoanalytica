from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import pandas as pd
import numpy as np
from pathlib import Path

path = DATA_DIR / "phase2_6_pi_men_harps_timeseries.csv"
df = pd.read_csv(path)

print("\n===== AVAILABLE COLUMNS =====")
print(df.columns.tolist())

print("\n===== SNR ZERO OBSERVATIONS =====")
print(df[df["drs_snr"] == 0].to_string(index=False))

print("\n===== YEARLY DATA QUALITY =====")
df["date_obs"] = pd.to_datetime(df["date_obs"], errors="coerce")
df["year"] = df["date_obs"].dt.year

for year, g in df.groupby("year"):
    print(f"\nYEAR: {year}")
    print("Observations:", len(g))
    print("Median RV:", g["rv_relative_ms"].median())
    print("RV std:", g["rv_relative_ms"].std())
    print("Median SNR:", g["drs_snr"].median())
    print("Median FWHM:", g["drs_ccf_fwhm"].median())
    print("Median contrast:", g["drs_ccf_contrast"].median())
    print("RV-FWHM correlation:",
          g["rv_relative_ms"].corr(g["drs_ccf_fwhm"]))

print("\n===== RV AND CCF PROFILE SUMMARY =====")
cols = [
    "rv_relative_ms",
    "rv_error_ms",
    "drs_snr",
    "drs_bis_rv",
    "drs_ccf_fwhm",
    "drs_ccf_contrast"
]
print(df[cols].describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]).to_string())

print("\n===== AUDIT COMPLETE =====")
