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

print("===== HARPS INDIVIDUAL TARGET AUDIT =====")

for target in TARGETS:

    query = f"""
    SELECT
        tel_object,
        main_id_simbad,
        date_obs,
        drs_bjd,
        ins_mode,
        drs_ccf_rvc,
        drs_dvrms,
        drs_snr,
        drs_bis_rv,
        drs_ccf_fwhm
    FROM {TABLE}
    WHERE
        tel_object = '{target}'
        AND drs_bjd IS NOT NULL
        AND drs_ccf_rvc IS NOT NULL
        AND drs_dvrms IS NOT NULL
    ORDER BY drs_bjd
    """

    print("\n" + "=" * 65)
    print("TARGET:", target)

    try:
        result = service.search(query)
        df = result.to_table().to_pandas()

        print("Returned records:", len(df))

        if df.empty:
            print("No matching records returned.")
            continue

        bjd = pd.to_numeric(
            df["drs_bjd"], errors="coerce"
        ).dropna()

        print("SIMBAD:", df["main_id_simbad"].iloc[0])
        print("Unique dates:", df["date_obs"].nunique())
        print("Baseline (days):",
              round(float(bjd.max() - bjd.min()), 3))

        print("Mean RV error (m/s):",
              round(float(df["drs_dvrms"].mean()), 4))

        print("Median SNR:",
              round(float(df["drs_snr"].median()), 2))

        print("Instrument modes:")
        print(df["ins_mode"].value_counts().to_dict())

        print("Missing BIS:",
              int(df["drs_bis_rv"].isna().sum()))

        print("Missing CCF FWHM:",
              int(df["drs_ccf_fwhm"].isna().sum()))

    except Exception as exc:
        print("ERROR:", type(exc).__name__, str(exc))

