from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR
import pandas as pd
from pathlib import Path

path = DATA_DIR / "phase2_6_pi_men_harps_timeseries.csv"
df = pd.read_csv(path)

df["date_obs"] = pd.to_datetime(df["date_obs"], errors="coerce")
df["year"] = df["date_obs"].dt.year

print("\n===== SNR ZERO RECORDS: ALL COLUMNS =====")
zero = df[df["drs_snr"] == 0]
print(zero.to_string(index=False))

print("\n===== 2019 CORRELATION CHECK =====")
g = df[df["year"] == 2019].copy()

pairs = [
    ("ALL 2019 RECORDS", g),
    ("EXCLUDING SNR=0 (DIAGNOSTIC ONLY)", g[g["drs_snr"] != 0]),
    ("EXCLUDING |RV| > 500 (DIAGNOSTIC ONLY)",
     g[g["rv_relative_ms"].abs() <= 500])
]

for label, x in pairs:
    print(f"\n{label}")
    print("Count:", len(x))
    print("Pearson RV-FWHM:",
          x["rv_relative_ms"].corr(x["drs_ccf_fwhm"]))
    print("Spearman RV-FWHM:",
          x["rv_relative_ms"].corr(x["drs_ccf_fwhm"], method="spearman"))
    print("Pearson RV-contrast:",
          x["rv_relative_ms"].corr(x["drs_ccf_contrast"]))

print("\n===== 2019 EXTREME RV RECORDS =====")
print(
    g.loc[g["rv_relative_ms"].abs().nlargest(10).index]
    .sort_values("rv_relative_ms")
    .to_string(index=False)
)

print("\n===== AVAILABLE ORIGINAL RV COLUMNS =====")
print([c for c in df.columns if "rv" in c.lower() or "ccf" in c.lower()])

print("\n===== VERIFICATION COMPLETE =====")
