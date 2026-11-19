import pyvo

URL = "https://archive.eso.org/tap_cat"

print("===== ESO TAP CATALOGUE DISCOVERY =====")
print("PyVO version:", pyvo.__version__)
print("Endpoint:", URL)

try:
    service = pyvo.dal.TAPService(URL)

    query = """
        SELECT table_name, description
        FROM TAP_SCHEMA.tables
    """

    result = service.search(query).to_table()

    print("\nTotal catalogue tables:", len(result))
    print("\n===== MATCHING CATALOGUES =====")

    matches = []

    for row in result:
        name = str(row["table_name"])
        description = str(row["description"])

        if any(word in (name + " " + description).lower()
               for word in ["harps", "radial velocity", "radial velocities"]):
            matches.append((name, description))

    if matches:
        for name, description in matches:
            print("\nTABLE:", name)
            print("DESCRIPTION:", description)
    else:
        print("No direct HARPS name match.")
        print("\nAvailable table names containing RV-related terms:")
        for row in result:
            name = str(row["table_name"])
            if any(word in name.lower() for word in ["rv", "radial"]):
                print(name)

except Exception as exc:
    print("\nERROR:", type(exc).__name__, str(exc))
