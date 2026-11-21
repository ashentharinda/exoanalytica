from pathlib import Path
import traceback

import numpy as np
import pandas as pd
from pyvo.dal import TAPService

ROOT = Path("research/phase_2/rv_ai_model")
INPUT = ROOT / "data/interim/harps_rv_observations_18_targets.csv"
OUT = ROOT / "stage_6_independent_benchmarking/data"

ARCHIVE_CSV = OUT / "eso_harps_archive_metadata_18_targets.csv"
MATCHED_CSV = OUT / "harps_eso_provenance_crossmatch.csv"
REPORT = OUT / "eso_provenance_crossmatch_report.txt"

ARCHIVE_COLUMNS = [
    "tel_object", "date_obs", "ins_mode",
    "adp_dpid", "raw_dpid", "progid",
    "drs_bjd", "drs_ccf_rvc", "drs_dvrms"
]

COMPARE_COLUMNS = ["drs_bjd", "drs_ccf_rvc", "drs_dvrms"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lines = []

    def log(message=""):
        print(message)
        lines.append(str(message))

    log("===== ESO HARPS PROVENANCE EXPORT =====")
    log("Source: ESO safcat.HARPS_RVCAT_V1")
    log("Mode: Metadata only; no science data download")

    local = pd.read_csv(
        INPUT,
        dtype={"tel_object": str, "date_obs": str}
    )

    required = {
        "tel_object", "date_obs",
        "drs_bjd", "drs_ccf_rvc", "drs_dvrms"
    }

    missing = required - set(local.columns)
    if missing:
        raise ValueError(f"Missing local columns: {sorted(missing)}")

    local["tel_object"] = local["tel_object"].str.strip()
    local["date_obs"] = local["date_obs"].str.strip()

    if local.duplicated(["tel_object", "date_obs"]).any():
        raise ValueError("Duplicate local observation keys detected.")

    targets = sorted(local["tel_object"].dropna().unique())

    log(f"Local observations: {len(local)}")
    log(f"Unique targets: {len(targets)}")

    def sql_quote(value):
        return "'" + value.replace("'", "''") + "'"

    target_list = ", ".join(sql_quote(x) for x in targets)

    query = f"""
        SELECT
            tel_object,
            date_obs,
            ins_mode,
            adp_dpid,
            raw_dpid,
            progid,
            drs_bjd,
            drs_ccf_rvc,
            drs_dvrms
        FROM safcat.HARPS_RVCAT_V1
        WHERE tel_object IN ({target_list})
    """

    log("Connecting to ESO TAP...")
    service = TAPService("https://archive.eso.org/tap_cat")

    result = service.search(query, maxrec=100000)
    archive = result.to_table().to_pandas()

    if len(archive) == 0:
        raise RuntimeError("ESO returned zero observations.")

    archive = archive[ARCHIVE_COLUMNS].copy()
    archive["tel_object"] = archive["tel_object"].astype(str).str.strip()
    archive["date_obs"] = archive["date_obs"].astype(str).str.strip()

    log(f"ESO archive observations returned: {len(archive)}")

    if archive.duplicated(["tel_object", "date_obs"]).any():
        duplicates = archive[
            archive.duplicated(
                ["tel_object", "date_obs"], keep=False
            )
        ]
        raise ValueError(
            "Duplicate ESO observation keys detected:\n"
            + duplicates.head(10).to_string(index=False)
        )

    archive.to_csv(ARCHIVE_CSV, index=False)

    merged = local.merge(
        archive,
        on=["tel_object", "date_obs"],
        how="outer",
        suffixes=("_local", "_eso"),
        indicator=True,
        validate="one_to_one"
    )

    matched = merged[merged["_merge"] == "both"].copy()
    local_only = merged[merged["_merge"] == "left_only"]
    archive_only = merged[merged["_merge"] == "right_only"]

    log()
    log("===== OBSERVATION KEY CROSSMATCH =====")
    log(f"Local rows: {len(local)}")
    log(f"ESO rows: {len(archive)}")
    log(f"Matched rows: {len(matched)}")
    log(f"Local unmatched: {len(local_only)}")
    log(f"ESO archive-only: {len(archive_only)}")

    log()
    log("===== NUMERICAL CONSISTENCY =====")

    for column in COMPARE_COLUMNS:
        left = pd.to_numeric(
            matched[f"{column}_local"], errors="coerce"
        )
        right = pd.to_numeric(
            matched[f"{column}_eso"], errors="coerce"
        )

        valid = left.notna() & right.notna()
        differences = (left[valid] - right[valid]).abs()

        exact = np.isclose(
            left[valid],
            right[valid],
            rtol=0,
            atol=1e-12
        )

        maximum = (
            float(differences.max())
            if len(differences) else float("nan")
        )

        log(f"{column}:")
        log(f"  Comparable: {int(valid.sum())}")
        log(f"  Equal within 1e-12: {int(exact.sum())}")
        log(f"  Maximum absolute difference: {maximum:.15g}")

    matched.to_csv(MATCHED_CSV, index=False)

    log()
    log("===== METADATA COMPLETENESS =====")

    for column in [
        "ins_mode", "adp_dpid", "raw_dpid", "progid"
    ]:
        count = archive[column].notna().sum()
        log(
            f"{column}: {count}/{len(archive)} populated; "
            f"{archive[column].nunique()} unique"
        )

    log()
    log("===== OUTPUT FILES =====")
    log(str(ARCHIVE_CSV.resolve()))
    log(str(MATCHED_CSV.resolve()))
    log()
    log("===== EXPORT COMPLETED =====")

    REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n===== EXPORT FAILED =====")
        print(traceback.format_exc())
        raise
