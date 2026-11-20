from pathlib import Path
import pandas as pd

ROOT = Path("research/phase_2/rv_ai_model")
REPORTS = ROOT / "reports"

MATCHED = REPORTS / "harps_nasa_planet_matches.csv"
CANDIDATES = REPORTS / "harps_pilot_target_candidates.csv"

VALIDATED = REPORTS / "harps_nasa_planet_validation.csv"
SYSTEMS = REPORTS / "harps_nasa_system_summary.csv"
ALIASES = REPORTS / "harps_duplicate_alias_targets.csv"
REPORT = REPORTS / "harps_nasa_validation_report.txt"

def truthy(value):
    if pd.isna(value):
        return False
    return str(value).strip().lower() in {
        "1", "true", "yes", "y"
    }

def main():
    matched = pd.read_csv(MATCHED)
    candidates = pd.read_csv(CANDIDATES)

    required = {
        "tel_object", "pl_name", "hostname",
        "discoverymethod", "rv_flag", "pl_controv_flag"
    }

    missing = required - set(matched.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    # Remove repeated planet records caused by aliases.
    planets = matched.drop_duplicates(
        subset=["hostname", "pl_name"]
    ).copy()

    planets["discovery_method_clean"] = (
        planets["discoverymethod"]
        .fillna("Unknown")
        .astype(str)
        .str.strip()
    )

    planets["is_rv_discovery"] = (
        planets["discovery_method_clean"]
        .str.contains("radial velocity", case=False, na=False)
    )

    planets["rv_flag_value"] = planets["rv_flag"].apply(truthy)
    planets["is_controversial"] = (
        planets["pl_controv_flag"].apply(truthy)
    )

    def classify(row):
        if row["is_rv_discovery"]:
            return "RV_DISCOVERY"
        if row["rv_flag_value"]:
            return "NON_RV_DISCOVERY_WITH_RV_FLAG"
        return "NON_RV_DISCOVERY"

    planets["rv_classification"] = planets.apply(
        classify, axis=1
    )

    planets.to_csv(VALIDATED, index=False)

    # Map HARPS target names to canonical NASA hostnames.
    target_map = (
        matched[["tel_object", "hostname"]]
        .dropna()
        .drop_duplicates()
    )

    alias_groups = (
        target_map.groupby("hostname")["tel_object"]
        .agg(lambda values: sorted(set(values)))
        .reset_index()
    )

    alias_groups["target_name_count"] = (
        alias_groups["tel_object"].apply(len)
    )

    duplicate_aliases = alias_groups[
        alias_groups["target_name_count"] > 1
    ].copy()

    duplicate_aliases["target_names"] = (
        duplicate_aliases["tel_object"].apply(
            lambda values: " | ".join(values)
        )
    )

    duplicate_aliases.drop(
        columns=["tel_object"]
    ).to_csv(ALIASES, index=False)

    # One summary row per canonical NASA host.
    summary_rows = []

    for host, group in planets.groupby("hostname"):
        target_names = sorted(
            set(group["tel_object"].dropna().astype(str))
        )

        summary_rows.append({
            "hostname": host,
            "harps_target_names": " | ".join(target_names),
            "n_unique_planets": group["pl_name"].nunique(),
            "n_rv_discoveries": int(group["is_rv_discovery"].sum()),
            "n_non_rv_discoveries": int((~group["is_rv_discovery"]).sum()),
            "n_rv_flagged": int(group["rv_flag_value"].sum()),
            "n_controversial": int(group["is_controversial"].sum()),
            "planet_names": " | ".join(
                sorted(set(group["pl_name"].dropna().astype(str)))
            )
        })

    systems = pd.DataFrame(summary_rows)
    systems.to_csv(SYSTEMS, index=False)

    matched_target_count = matched["tel_object"].nunique()
    unique_planets = planets["pl_name"].nunique()
    rv_count = int(planets["is_rv_discovery"].sum())
    non_rv_count = int((~planets["is_rv_discovery"]).sum())
    controversial_count = int(planets["is_controversial"].sum())

    lines = [
        "===== HARPS / NASA CROSSMATCH VALIDATION =====",
        f"HARPS input targets: {len(candidates)}",
        f"Matched HARPS target names: {matched_target_count}",
        f"Original matched rows: {len(matched)}",
        f"Unique planet records after deduplication: {unique_planets}",
        f"Unique canonical NASA host systems: {len(systems)}",
        f"Duplicate alias groups: {len(duplicate_aliases)}",
        "",
        "===== PLANET CLASSIFICATION =====",
        f"RV discovery planets: {rv_count}",
        f"Non-RV discovery planets: {non_rv_count}",
        f"RV-flagged planets: {int(planets['rv_flag_value'].sum())}",
        f"Controversial-flagged planets: {controversial_count}",
        "",
        "===== RV DISCOVERY SYSTEMS ====="
    ]

    rv_systems = systems[systems["n_rv_discoveries"] > 0]

    for _, row in rv_systems.sort_values(
        "n_rv_discoveries", ascending=False
    ).iterrows():
        lines.append(
            f"{row['hostname']} | "
            f"RV planets={row['n_rv_discoveries']} | "
            f"All planets={row['n_unique_planets']} | "
            f"HARPS names={row['harps_target_names']}"
        )

    lines.extend([
        "",
        "===== DUPLICATE ALIAS GROUPS ====="
    ])

    for _, row in duplicate_aliases.iterrows():
        lines.append(
            f"{row['hostname']} | {row['target_names']}"
        )

    lines.extend([
        "",
        "IMPORTANT:",
        "RV_DISCOVERY means discovery method is Radial Velocity.",
        "RV_FLAG is retained separately and is not a discovery label.",
        "Controversial records are flagged, not silently removed.",
        "Non-RV discovery does not mean the system has no RV data.",
        "NASA matches are reference labels, not new detections.",
        "",
        f"Validated planets CSV: {VALIDATED.resolve()}",
        f"System summary CSV: {SYSTEMS.resolve()}",
        f"Duplicate aliases CSV: {ALIASES.resolve()}",
        "===== VALIDATION COMPLETED ====="
    ])

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))

if __name__ == "__main__":
    main()
