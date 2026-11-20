from pathlib import Path
import sys
import traceback

from pyvo.dal import TAPService

ROOT = Path("research/phase_2/rv_ai_model")
REPORT = ROOT / "reports" / "harps_tap_inspection.txt"
REPORT.parent.mkdir(parents=True, exist_ok=True)

lines = []

def log(message=""):
    print(message)
    lines.append(str(message))

def save():
    REPORT.write_text("\n".join(lines), encoding="utf-8")

def main():
    log("===== ESO HARPS TAP INSPECTION =====")
    log("Client: PyVO")
    log("Mode: Metadata only")
    log("Science data download: DISABLED")
    log()

    service = TAPService("https://archive.eso.org/tap_cat")

    log("TAP connection initialized.")
    log()

    # Retrieve catalogue table metadata without SQL functions.
    query = """
    SELECT table_name
    FROM TAP_SCHEMA.tables
    """

    log("===== RETRIEVING TABLE NAMES =====")

    result = service.search(query, maxrec=2000)

    names = sorted({
        str(row["table_name"])
        for row in result
    })

    log(f"Metadata table names retrieved: {len(names)}")

    # Filter locally in Python.
    matches = [
        name for name in names
        if "harps" in name.lower()
        or "radial" in name.lower()
        or "rv" in name.lower()
    ]

    log()
    log("===== HARPS / RADIAL VELOCITY MATCHES =====")

    if not matches:
        log("No matching names found in returned metadata.")
        log("Catalogue discovery needs another approach.")
        return

    for name in matches:
        log(name)

    # Inspect metadata columns for each candidate.
    for table_name in matches:
        safe_name = table_name.replace("'", "''")

        column_query = f"""
        SELECT column_name, datatype, unit, ucd
        FROM TAP_SCHEMA.columns
        WHERE table_name = '{safe_name}'
        """

        log()
        log("===== COLUMN INSPECTION =====")
        log(f"Table: {table_name}")

        try:
            columns = service.search(column_query, maxrec=300)

            log(f"Columns returned: {len(columns)}")

            for row in columns:
                log(
                    f"{row['column_name']} | "
                    f"{row['datatype']} | "
                    f"{row['unit']} | "
                    f"{row['ucd']}"
                )

        except Exception as exc:
            log("COLUMN QUERY ERROR")
            log(repr(exc))

    log()
    log("===== INSPECTION COMPLETED =====")

if __name__ == "__main__":
    try:
        main()
    except Exception:
        log("===== INSPECTION ERROR =====")
        log(traceback.format_exc())
        save()
        sys.exit(1)

    save()
    print()
    print(f"Report saved: {REPORT.resolve()}")
