import sys
import inspect
import importlib.metadata as metadata

print("===== PYTHON ENVIRONMENT =====")
print("Python:", sys.version)
print("Executable:", sys.executable)

print("\n===== PACKAGE VERSIONS =====")

for package in ["astroquery", "astropy", "pyvo"]:
    try:
        print(f"{package}: {metadata.version(package)}")
    except metadata.PackageNotFoundError:
        print(f"{package}: NOT INSTALLED")

print("\n===== ESO API INSPECTION =====")

try:
    from astroquery.eso import Eso

    eso = Eso()

    print("Eso class:", type(eso))
    print("query_tap available:", hasattr(eso, "query_tap"))
    print("tap available:", hasattr(eso, "tap"))
    print("list_catalogs available:", hasattr(eso, "list_catalogs"))

    print("\nAvailable TAP-related methods:")
    for name in dir(eso):
        if "tap" in name.lower() or "catalog" in name.lower():
            print(name)

except Exception as exc:
    print("IMPORT ERROR:", repr(exc))
