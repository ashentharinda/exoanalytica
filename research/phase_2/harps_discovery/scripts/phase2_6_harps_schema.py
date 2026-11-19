import pyvo

URL = "https://archive.eso.org/tap_cat"
TABLE = "safcat.HARPS_RVCAT_V1"

service = pyvo.dal.TAPService(URL)

print("===== HARPS_RVCAT_V1 SCHEMA =====")

query = f"""
SELECT column_name, datatype, unit, description
FROM TAP_SCHEMA.columns
WHERE table_name = '{TABLE}'
"""

try:
    result = service.search(query).to_table()

    print("Total columns:", len(result))

    for row in result:
        print(
            f"{row['column_name']} | "
            f"{row['datatype']} | "
            f"{row['unit']} | "
            f"{row['description']}"
        )

except Exception as exc:
    print("ERROR:", type(exc).__name__, str(exc))
