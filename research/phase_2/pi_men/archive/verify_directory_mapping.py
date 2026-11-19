import ast
import sys
from pathlib import Path

script_dir = Path("research/phase_2/pi_men/scripts").resolve()
sys.path.insert(0, str(script_dir))

from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR

print("===== DIRECTORY CHECK =====")
for name, directory in [
    ("DATA_DIR", DATA_DIR),
    ("RESULTS_DIR", RESULTS_DIR),
    ("REPORTS_DIR", REPORTS_DIR),
]:
    print(name, "->", directory, "| Exists:", directory.is_dir())

print("\n===== FILE OPERATION PATH AUDIT =====")

files = sorted(script_dir.glob("phase2_6_pi_men_*.py"))
issues = []

for file in files:
    tree = ast.parse(file.read_text(encoding="utf-8-sig"))
    assignments = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id] = ast.unparse(node.value)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = ast.unparse(node.func)

        if func.endswith("read_csv") or func.endswith("to_csv"):
            if not node.args:
                continue
            arg = node.args[0]
            expression = ast.unparse(arg)

        elif func.endswith("write_text"):
            expression = ast.unparse(node.func.value)

        elif func == "open":
            if not node.args:
                continue
            expression = ast.unparse(node.args[0])

        else:
            continue

        if isinstance(arg, ast.Name) if func.endswith(("read_csv", "to_csv")) else False:
            expression = assignments.get(arg.id, expression)

        if not any(folder in expression for folder in
                   ("DATA_DIR", "RESULTS_DIR", "REPORTS_DIR")):
            issues.append((file.name, node.lineno, func, expression))

print("Scripts inspected:", len(files))
print("Unmapped file operations:", len(issues))

for issue in issues:
    print("CHECK:", issue)

if not all(d.is_dir() for d in (DATA_DIR, RESULTS_DIR, REPORTS_DIR)):
    raise SystemExit("DIRECTORY CHECK FAILED")

if issues:
    raise SystemExit("PATH AUDIT NEEDS REVIEW")

print("\nSUCCESS: All audited file operations use mapped directories.")
