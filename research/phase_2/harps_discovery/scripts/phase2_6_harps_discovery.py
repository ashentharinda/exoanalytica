from astroquery.eso import Eso

eso = Eso()

print("\n===== ESO TAP CATALOGUE DISCOVERY =====")

try:
    tables = eso.query_tap(
        "SELECT table_name FROM TAP_SCHEMA.tables",
        tap_endpoint="tap_cat"
    )

    names = [
        str(row["table_name"])
        for row in tables
        if "harps" in str(row["table_name"]).lower()
    ]

    print("\nHARPS TABLES:")
    for name in names:
        print(name)

    if not names:
        print("No HARPS table name returned.")
    else:
        for name in names:
            print(f"\n===== COLUMNS: {name} =====")
            query = (
                "SELECT column_name, datatype, unit "
                "FROM TAP_SCHEMA.columns "
                f"WHERE table_name = '{name}'"
            )
            columns = eso.query_tap(
                query,
                tap_endpoint="tap_cat"
            )

            for row in columns:
                print(
                    row["column_name"],
                    "|", row["datatype"],
                    "|", row["unit"]
                )

except Exception as exc:
    print("\nERROR:", type(exc).__name__, str(exc))
