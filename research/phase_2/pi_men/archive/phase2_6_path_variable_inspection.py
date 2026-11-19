import ast
from pathlib import Path

folder = Path("research/phase_2/pi_men/scripts")

for file in sorted(folder.glob("phase2_6_pi_men_*.py")):
    source = file.read_text(encoding="utf-8-sig")
    lines = source.splitlines()
    tree = ast.parse(source)

    found = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            targets = []

            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            else:
                targets = [node.target]

            names = [
                ast.unparse(target)
                for target in targets
            ]

            if any(
                name.upper() in {
                    "INPUT", "SOURCE", "FILE", "PATH",
                    "OUTPUT", "OUTPUT_CSV", "OUTPUT_REPORT",
                    "REPORT", "REPORT_FILE", "RESIDUAL_FILE",
                    "PERIOD_FILE", "PEAK_FILE", "WINDOW_FILE",
                    "INDICATOR_FILE", "EPOCH_OUTPUT"
                }
                for name in names
            ):
                start = max(0, node.lineno - 2)
                end = min(len(lines), node.end_lineno + 1)
                found.extend(lines[start:end])

    if found:
        print(f"\n===== {file.name} =====")
        for line in dict.fromkeys(found):
            print(line)
