import ast
from pathlib import Path

folder = Path("research/phase_2/pi_men/scripts")
files = sorted(folder.glob("phase2_6_pi_men_*.py"))

syntax_errors = []
missing_imports = []

for file in files:
    try:
        tree = ast.parse(file.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        syntax_errors.append((file.name, str(exc)))
        continue

    has_paths_import = any(
        isinstance(node, ast.ImportFrom) and node.module == "paths"
        for node in tree.body
    )

    if not has_paths_import:
        missing_imports.append(file.name)

print("Scripts found:", len(files))
print("Syntax errors:", len(syntax_errors))
print("Missing paths imports:", len(missing_imports))

for name, error in syntax_errors:
    print("SYNTAX ERROR:", name, error)

for name in missing_imports:
    print("MISSING IMPORT:", name)

if len(files) != 30 or syntax_errors or missing_imports:
    raise SystemExit("VERIFICATION FAILED")

print("SUCCESS: All 30 scripts passed syntax and import checks.")
