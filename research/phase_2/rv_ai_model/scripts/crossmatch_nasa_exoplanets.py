from pathlib import Path
import re
import sys
import traceback

import pandas as pd
from pyvo.dal import TAPService

ROOT = Path("research/phase_2/rv_ai_model")
REPORTS = ROOT / "reports"
RAW = ROOT / "data" / "raw"

INPUT = REPORTS / "harps_pilot_target_candidates.csv"
NASA_CACHE = RAW / "nasa_pscomppars_snapshot.csv"

MATCHED = REPORTS / "harps_nasa_planet_matches.csv"
UNMATCHED = REPORTS / "harps_unmatched_targets.csv"
SUMMARY = REPORTS / "harps_nasa_crossmatch_report.txt"

REPORTS.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)

def normalize(value):
    if pd.isna(value):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())

def identifier(value):
    value = str(value).strip().upper()
    match = re.match(r"^(HD|HIP)[\s\-_]*0*(\d+)$", value)
    if match:
        return match.group(1), str(int(match.group(2)))
    return None

def nasa_identifier(value, prefix):
    if pd.isna(value):
        return None
    match = re.search(
        rf"\b{prefix}\s*0*(\d+)\b",
        str(value).upper()
    )
    if match:
        return prefix, str(int(match.group(1)))
    return None

def main():
    lines = []

    def log(message=""):
        print(message)
        lines.append(str(message))

    log("===== HARPS / NASA EXOPLANET CROSSMATCH =====")
    log("HARPS input: " + str(INPUT))
    log("NASA table: pscomppars")
    log("Matching: Exact HD/HIP identifier; exact name fallback")
    log("RV spectra download: DISABLED")
    log()

    if not INPUT.exists():
        raise FileNotFoundError(
            f"HARPS candidate CSV not found: {INPUT}"
        )

    harps = pd.read_csv(INPUT)

    if "tel_object" not in harps.columns:
        raise ValueError("Input CSV has no tel_object column.")

    log(f"HARPS targets loaded: {len(harps)}")
    log("Connecting to NASA Exoplanet Archive TAP...")

    service = TAPService(
        "https://exoplanetarchive.ipac.caltech.edu/TAP"
    )

    query = """
        SELECT
            pl_name,
            hostname,
            hd_name,
            hip_name,
            discoverymethod,
            disc_year,
            rv_flag,
            pl_orbper,
            pl_bmasse,
            pl_bmassj,
            pl_msinie,
            pl_msinij,
            pl_rvamp,
            pl_controv_flag,
            sy_pnum
        FROM pscomppars
        WHERE pl_name IS NOT NULL
    """

    result = service.search(query, maxrec=20000)
    nasa = result.to_table().to_pandas()

    log(f"NASA planet records retrieved: {len(nasa)}")

    if len(nasa) == 0:
        raise RuntimeError("NASA returned an empty catalogue.")

    nasa.to_csv(NASA_CACHE, index=False)
    log(f"NASA snapshot saved: {NASA_CACHE}")
    log()

    # Build identifier index.
    hd_index = {}
    hip_index = {}
    name_index = {}

    for _, planet in nasa.iterrows():
        hd = nasa_identifier(planet.get("hd_name"), "HD")
        hip = nasa_identifier(planet.get("hip_name"), "HIP")
        host = normalize(planet.get("hostname"))

        if hd:
            hd_index.setdefault(hd, []).append(planet)

        if hip:
            hip_index.setdefault(hip, []).append(planet)

        if host:
            name_index.setdefault(host, []).append(planet)

    matched_rows = []
    unmatched_rows = []

    for _, target in harps.iterrows():
        target_name = str(target["tel_object"]).strip()
        target_id = identifier(target_name)

        planets = []
        match_basis = ""

        if target_id and target_id[0] == "HD":
            planets = hd_index.get(target_id, [])
            if planets:
                match_basis = "HD_IDENTIFIER"

        elif target_id and target_id[0] == "HIP":
            planets = hip_index.get(target_id, [])
            if planets:
                match_basis = "HIP_IDENTIFIER"

        else:
            key = normalize(target_name)
            planets = name_index.get(key, [])
            if planets:
                match_basis = "EXACT_HOSTNAME"

        if planets:
            for planet in planets:
                row = target.to_dict()
                row.update(planet.to_dict())
                row["crossmatch_status"] = "MATCHED"
                row["match_basis"] = match_basis
                matched_rows.append(row)
        else:
            row = target.to_dict()
            row["crossmatch_status"] = "NO_EXACT_MATCH"
            row["match_basis"] = "NONE"
            unmatched_rows.append(row)

    matched_df = pd.DataFrame(matched_rows)
    unmatched_df = pd.DataFrame(unmatched_rows)

    matched_df.to_csv(MATCHED, index=False)
    unmatched_df.to_csv(UNMATCHED, index=False)

    matched_targets = (
        matched_df["tel_object"].nunique()
        if not matched_df.empty else 0
    )

    matched_planets = len(matched_df)
    unmatched_targets = len(unmatched_df)

    log("===== CROSSMATCH RESULTS =====")
    log(f"Total HARPS targets: {len(harps)}")
    log(f"Targets with exact NASA matches: {matched_targets}")
    log(f"Matched planet records: {matched_planets}")
    log(f"Targets without exact matches: {unmatched_targets}")
    log()

    if not matched_df.empty:
        log("===== MATCHED SYSTEMS =====")
        for _, row in matched_df.iterrows():
            log(
                f"{row['tel_object']} -> "
                f"{row.get('pl_name', '')} | "
                f"Host={row.get('hostname', '')} | "
                f"Method={row.get('discoverymethod', '')} | "
                f"Period={row.get('pl_orbper', '')} days | "
                f"RV amplitude={row.get('pl_rvamp', '')} m/s | "
                f"Basis={row['match_basis']}"
            )

    log()
    log("===== IMPORTANT INTERPRETATION =====")
    log("NO_EXACT_MATCH does NOT mean a star has no planets.")
    log("It means no exact identifier/name match was found.")
    log("Aliases require a separate SIMBAD identity-resolution step.")
    log("A NASA catalogue match is a reference label, not a new detection.")
    log()
    log(f"Matched CSV: {MATCHED.resolve()}")
    log(f"Unmatched CSV: {UNMATCHED.resolve()}")
    log(f"NASA snapshot: {NASA_CACHE.resolve()}")
    log("===== CROSSMATCH COMPLETED =====")

    SUMMARY.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        error = traceback.format_exc()
        print("\n===== CROSSMATCH ERROR =====")
        print(error)
        SUMMARY.write_text(error, encoding="utf-8")
        sys.exit(1)
