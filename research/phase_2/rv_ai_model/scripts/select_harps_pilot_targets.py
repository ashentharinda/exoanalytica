from pathlib import Path
import traceback
import sys

from pyvo.dal import TAPService

ROOT = Path("research/phase_2/rv_ai_model")
REPORT = ROOT / "reports"

REPORT.mkdir(parents=True, exist_ok=True)

CSV_PATH = REPORT / "harps_pilot_target_candidates.csv"
TXT_PATH = REPORT / "harps_pilot_target_selection.txt"

lines = []

def log(message=""):
    print(message)
    lines.append(str(message))

def save_report():
    TXT_PATH.write_text("\n".join(lines), encoding="utf-8")

def main():

    log("===== HARPS PILOT TARGET SELECTION =====")
    log("Table: safcat.HARPS_RVCAT_V1")
    log("Mode: Target-level statistical summary")
    log("Raw spectra download: DISABLED")
    log()

    service = TAPService("https://archive.eso.org/tap_cat")

    query = """
        SELECT
            tel_object,
            COUNT(*) AS n_obs,
            MIN(drs_bjd) AS first_bjd,
            MAX(drs_bjd) AS last_bjd,
            AVG(drs_dvrms) AS mean_uncertainty_mps
        FROM safcat.HARPS_RVCAT_V1
        WHERE tel_object IS NOT NULL
          AND drs_bjd IS NOT NULL
          AND drs_ccf_rvc IS NOT NULL
          AND drs_dvrms IS NOT NULL
          AND drs_dvrms > 0
        GROUP BY tel_object
        HAVING COUNT(*) >= 20

    """

    log("Querying HARPS target summaries...")

    result = service.search(query, maxrec=20000)
    table = result.to_table()

    # Sort locally instead of using ORDER BY COUNT(*) in ADQL.
    table.sort("n_obs")
    table = table[::-1][:100]

    log(f"Candidate targets returned: {len(table)}")
    log()

    if len(table) == 0:
        log("No candidates returned.")
        save_report()
        return

    table["baseline_days"] = (
        table["last_bjd"] - table["first_bjd"]
    )

    table.write(
        str(CSV_PATH),
        format="ascii.csv",
        overwrite=True
    )

    log("===== TOP HARPS TARGET CANDIDATES =====")

    for row in table[:20]:
        log(
            f"{row['tel_object']} | "
            f"observations={row['n_obs']} | "
            f"baseline_days={row['baseline_days']:.2f} | "
            f"mean_uncertainty_mps="
            f"{row['mean_uncertainty_mps']:.3f}"
        )

    log()
    log(f"CSV saved: {CSV_PATH.resolve()}")
    log("===== TARGET SUMMARY COMPLETED =====")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("===== QUERY ERROR =====")
        log(traceback.format_exc())
        save_report()
        sys.exit(1)

    save_report()
    print()
    print(f"Report saved: {TXT_PATH.resolve()}")
