import pyvo

URL = "https://archive.eso.org/tap_cat"
TABLE = "safcat.HARPS_RVCAT_V1"

service = pyvo.dal.TAPService(URL)

query = f"""
SELECT TOP 50
    tel_object,
    main_id_simbad,
    COUNT(*) AS obs_count,
    MIN(drs_bjd) AS first_bjd,
    MAX(drs_bjd) AS last_bjd,
    AVG(drs_dvrms) AS mean_rv_error_ms,
    AVG(drs_snr) AS mean_snr
FROM {TABLE}
WHERE
    drs_bjd IS NOT NULL
    AND drs_ccf_rvc IS NOT NULL
    AND drs_dvrms IS NOT NULL
GROUP BY tel_object, main_id_simbad
HAVING COUNT(*) >= 10
ORDER BY obs_count DESC
"""

print("===== HARPS TARGET-LEVEL FEASIBILITY =====")

try:
    result = service.search(query).to_table()

    print("Targets returned:", len(result))
    print()

    for row in result:
        baseline = float(row["last_bjd"]) - float(row["first_bjd"])

        print("-" * 65)
        print("Target:", row["tel_object"])
        print("SIMBAD:", row["main_id_simbad"])
        print("Observations:", row["obs_count"])
        print("Baseline (days):", round(baseline, 3))
        print("Mean RV error (m/s):", row["mean_rv_error_ms"])
        print("Mean SNR:", row["mean_snr"])

except Exception as exc:
    print("ERROR:", type(exc).__name__, str(exc))
