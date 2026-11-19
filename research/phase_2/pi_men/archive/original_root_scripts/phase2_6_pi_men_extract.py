import pyvo
import pandas as pd
import numpy as np

URL = "https://archive.eso.org/tap_cat"
TABLE = "safcat.HARPS_RVCAT_V1"

service = pyvo.dal.TAPService(URL)

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
    drs_ccf_fwhm,
    drs_ccf_contrast
FROM {TABLE}
WHERE
    tel_object = 'HD39091'
    AND drs_bjd IS NOT NULL
    AND drs_ccf_rvc IS NOT NULL
    AND drs_dvrms IS NOT NULL
ORDER BY drs_bjd
"""

print("===== PI MEN HARPS DATA EXTRACTION =====")

try:
    result = service.search(query)
    df = result.to_table().to_pandas()

    if df.empty:
        print("No records returned for HD39091.")
        raise SystemExit(0)

    # Convert HARPS RV from km/s to m/s.
    df["rv_ms"] = pd.to_numeric(
        df["drs_ccf_rvc"], errors="coerce"
    ) * 1000.0

    df["rv_relative_ms"] = (
        df["rv_ms"] - df["rv_ms"].median()
    )

    df["rv_error_ms"] = pd.to_numeric(
        df["drs_dvrms"], errors="coerce"
    )

    df["bjd"] = pd.to_numeric(
        df["drs_bjd"], errors="coerce"
    )

    df = df.dropna(
        subset=["bjd", "rv_ms", "rv_error_ms"]
    ).sort_values("bjd")

    output = "phase2_6_pi_men_harps_timeseries.csv"
    df.to_csv(output, index=False)

    print("Target:", df["tel_object"].iloc[0])
    print("SIMBAD:", df["main_id_simbad"].iloc[0])
    print("Valid observations:", len(df))
    print("First BJD:", df["bjd"].min())
    print("Last BJD:", df["bjd"].max())
    print("Baseline (days):",
          round(df["bjd"].max() - df["bjd"].min(), 3))

    print("Mean RV uncertainty (m/s):",
          round(df["rv_error_ms"].mean(), 4))

    print("Median RV uncertainty (m/s):",
          round(df["rv_error_ms"].median(), 4))

    print("Instrument modes:")
    print(df["ins_mode"].value_counts().to_dict())

    print("CSV saved:", output)

except Exception as exc:
    print("ERROR:", type(exc).__name__, str(exc))
