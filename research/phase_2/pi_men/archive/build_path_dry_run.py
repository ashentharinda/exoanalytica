from pathlib import Path
import ast
import json

SCRIPT_DIR = Path("research/phase_2/pi_men/scripts")
DATA_DIR = Path("research/phase_2/pi_men/datasets")
RESULTS_DIR = Path("research/phase_2/pi_men/results")
REPORTS_DIR = Path("research/phase_2/pi_men/reports")

def classify(filename):
    if filename.endswith(".txt"):
        return "REPORTS_DIR"
    if filename.endswith(".csv"):
        if (DATA_DIR / filename).exists():
            return "DATA_DIR"
        return "RESULTS_DIR"
    return None

plan = []

for script in sorted(SCRIPT_DIR.glob("phase2_6_pi_men_*.py")):
    if script.name == "phase2_6_pi_men_extract.py":
        continue

    tree = ast.parse(script.read_text(encoding="utf-8-sig"))

    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if value.startswith("phase2_6_pi_men_") and value.endswith((".csv", ".txt")):
                category = classify(value)
                if category:
                    names.add((value, category))

    for filename, category in sorted(names):
        plan.append({
            "script": script.name,
            "filename": filename,
            "target": category
        })

output = Path("research/phase_2/pi_men/archive/phase2_6_path_refactor_dry_run.json")
output.write_text(json.dumps(plan, indent=2), encoding="utf-8")

print("Scripts scanned:", len(list(SCRIPT_DIR.glob("phase2_6_pi_men_*.py"))))
print("Path changes proposed:", len(plan))
print("Dry-run saved:", output)
print("\nFirst 25 proposed changes:")
for item in plan[:25]:
    print(f'{item["script"]}: {item["filename"]} -> {item["target"]}')
