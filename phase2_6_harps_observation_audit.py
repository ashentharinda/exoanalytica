import pyvo
import pandas as pd
import numpy as np

URL = "https://archive.eso.org/tap_cat"
TABLE = "safcat.HARPS_RVCAT_V1"

TARGETS = [
    "HD39091",
    "HD-160691",
    "HD128621",
    "HD172555"
]

service = pyvo.dal.TAPService(URL)

target_list = ", ".join(f"'{x}'" for x in TARGETS)

query = f"""
SELECT
    tel_object,
    main_id_simbad,
    date_obs,
    mjd_obs,
    drs_bjd,
    ins_mode,
    drs_ccf_rvc,
    drs_dvrms,
    drs_snr,
    drs_bis_rv,
    drs_ccf_fwhm,
    drs_ccf_contrast
FROM {TABLE}
WHERE
    tel_object IN ({target_list})
    AND drs_bjd IS NOT NULL
    AND drs_ccf_rvc IS NOT NULL
    AND drs_dvrms IS NOT NULL
ORDER BY tel_object, drs_bjd
"""

print("===== HARPS OBSERVATION-LEVEL AUDIT =====")

try:
    table = service.search(query).to_table()
    df = table.to_pandas()

    print("Total records:", len(df))
    print()

    for target, group in df.groupby("tel_object"):

        group = group.sort_values("drs_bjd")

        bjd = pd.to_numeric(
            group["drs_bjd"], errors="coerce"
        ).dropna()

        gaps = np.diff(bjd.to_numpy())

        print("=" * 65)
        print("TARGET:", target)
        print("SIMBAD:", group["main_id_simbad"].iloc[0])
        print("Observations:", len(group))
        print("Unique observing dates:",
              group["date_obs"].nunique())
        print("First BJD:", round(bjd.min(), 5))
        print("Last BJD:", round(bjd.max(), 5))
        print("Baseline (days):",
              round(bjd.max() - bjd.min(), 3))

        if len(gaps):
            print("Median observation gap (days):",
                  round(float(np.median(gaps)), 4))
            print("Maximum observation gap (days):",
                  round(float(np.max(gaps)), 3))

        print("Mean RV uncertainty (m/s):",
              round(float(group["drs_dvrms"].mean()), 4))

        print("Median SNR:",
              round(float(group["drs_snr"].median()), 2))

        print("Instrument modes:")
        print(group["ins_mode"].value_counts().to_string())

        print("Missing BIS values:",
              group["drs_bis_rv"].isna().sum())

        print("Missing CCF FWHM values:",
              group["drs_ccf_fwhm"].isna().sum())

except Exception as exc:
    print("ERROR:", type(exc).__name__, str(exc))
