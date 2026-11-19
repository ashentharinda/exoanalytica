import ast
import shutil
from pathlib import Path

SCRIPT_DIR = Path("research/phase_2/pi_men/scripts")
BACKUP_DIR = Path(r"D:\exoanalytica_phase2_6_scripts_backup_before_path_refactor")

DATA_FILES = {
    "phase2_6_pi_men_harps_timeseries.csv",
    "phase2_6_pi_men_instrument_audit.csv",
    "phase2_6_pi_men_corrected_dataset.csv",
}

VARIABLE_NAMES = {
    "INPUT", "SOURCE", "FILE", "PATH", "path",
    "OUTPUT", "OUTPUT_CSV", "OUTPUT_REPORT",
    "REPORT", "REPORT_FILE", "RESIDUAL_FILE",
    "PERIOD_FILE", "PEAK_FILE", "WINDOW_FILE",
    "INDICATOR_FILE", "EPOCH_OUTPUT",
    "output", "report", "report_file",
    "residual_file", "period_file", "peak_file",
    "window_file", "indicator_file", "epoch_output",
}

def target_dir(filename):
    if filename.endswith(".txt"):
        return "REPORTS_DIR"
    if filename in DATA_FILES:
        return "DATA_DIR"
    if filename.endswith(".csv"):
        return "RESULTS_DIR"
    return None

def path_expression(filename):
    folder = target_dir(filename)
    if folder:
        return f'{folder} / "{filename}"'
    return None

files = sorted(SCRIPT_DIR.glob("phase2_6_pi_men_*.py"))

if len(files) != 30:
    raise SystemExit(
        f"STOP: Expected 30 scripts, found {len(files)}"
    )

if not (SCRIPT_DIR / "paths.py").exists():
    raise SystemExit("STOP: paths.py is missing")

if BACKUP_DIR.exists():
    raise SystemExit(
        f"STOP: Backup folder already exists: {BACKUP_DIR}"
    )

# Create a fresh backup before changing anything.
BACKUP_DIR.mkdir(parents=True)

for file in files:
    shutil.copy2(file, BACKUP_DIR / file.name)

if len(list(BACKUP_DIR.glob("*.py"))) != 30:
    raise SystemExit("STOP: Backup verification failed")

print("Backup verified:", len(list(BACKUP_DIR.glob("*.py"))))

changed_files = 0
total_replacements = 0

for file in files:
    source = file.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(file))
    replacements = {}

    def add_replacement(node, expression):
        start = (
            sum(len(line) for line in source.splitlines(keepends=True)[:node.lineno-1])
            + node.col_offset
        )
        end = (
            sum(len(line) for line in source.splitlines(keepends=True)[:node.end_lineno-1])
            + node.end_col_offset
        )
        replacements[(start, end)] = expression

    for node in ast.walk(tree):

        # Path("filename") -> DATA_DIR / "filename"
        if isinstance(node, ast.Call):
            if (
                isinstance(node.func, ast.Name)
                and node.func.id == "Path"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                value = node.args[0].value

                if value == "." and file.name == (
                    "phase2_6_pi_men_corrected_alias_analysis.py"
                ):
                    add_replacement(node, "RESULTS_DIR")
                    continue

                expression = path_expression(value)
                if expression:
                    add_replacement(node, expression)
                    continue

            # Direct read_csv("file") / to_csv("file") paths
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in {"read_csv", "to_csv"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                expression = path_expression(node.args[0].value)
                if expression:
                    add_replacement(node.args[0], expression)

        # String path assignments such as INPUT = "file.csv"
        if isinstance(node, ast.Assign):
            names = set()
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)

            if (
                names.intersection(VARIABLE_NAMES)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                expression = path_expression(node.value.value)
                if expression:
                    add_replacement(node.value, expression)

    if not replacements:
        continue

    # Apply source edits from bottom to top, preserving other code.
    updated = source
    for (start, end), expression in sorted(
        replacements.items(), reverse=True
    ):
        updated = updated[:start] + expression + updated[end:]

    # Add the shared path import after module docstring/future imports.
    updated_tree = ast.parse(updated, filename=str(file))

    has_paths_import = any(
        isinstance(node, ast.ImportFrom) and node.module == "paths"
        for node in updated_tree.body
    )

    if not has_paths_import:
        header_end = 0

        for node in updated_tree.body:
            is_docstring = (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
                and header_end == 0
            )
            is_future = (
                isinstance(node, ast.ImportFrom)
                and node.module == "__future__"
            )

            if is_docstring or is_future:
                header_end = node.end_lineno
            else:
                break

        lines = updated.splitlines(keepends=True)

        if header_end:
            insert_at = sum(len(x) for x in lines[:header_end])
        elif updated_tree.body:
            first_line = updated_tree.body[0].lineno - 1
            insert_at = sum(len(x) for x in lines[:first_line])
        else:
            insert_at = 0

        import_line = (
            "from paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR\n"
        )
        updated = updated[:insert_at] + import_line + updated[insert_at:]

    # Syntax check before saving.
    compile(updated, str(file), "exec")

    file.write_text(updated, encoding="utf-8")
    changed_files += 1
    total_replacements += len(replacements)

    print(f"UPDATED: {file.name} ({len(replacements)} path changes)")

print("\n===== REFACTOR SUMMARY =====")
print("Scripts scanned:", len(files))
print("Scripts updated:", changed_files)
print("Path replacements:", total_replacements)
print("Pre-refactor backup:", BACKUP_DIR)
print("Scientific algorithms intentionally untouched.")
