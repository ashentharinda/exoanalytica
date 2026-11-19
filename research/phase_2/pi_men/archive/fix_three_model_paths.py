from pathlib import Path

file = Path("research/phase_2/pi_men/scripts/phase2_6_pi_men_three_model_comparison.py")
source = file.read_text(encoding="utf-8-sig")

replacements = {
    'from scipy.optimize import differential_evolution\n':
        'from scipy.optimize import differential_evolution\nfrom paths import DATA_DIR, RESULTS_DIR, REPORTS_DIR\n',

    'INPUT = Path("phase2_6_pi_men_corrected_dataset.csv")':
        'INPUT = DATA_DIR / "phase2_6_pi_men_corrected_dataset.csv"',

    'OUTPUT_CSV = Path("phase2_6_pi_men_three_model_comparison.csv")':
        'OUTPUT_CSV = RESULTS_DIR / "phase2_6_pi_men_three_model_comparison.csv"',

    'OUTPUT_REPORT = Path("phase2_6_pi_men_three_model_comparison.txt")':
        'OUTPUT_REPORT = REPORTS_DIR / "phase2_6_pi_men_three_model_comparison.txt"',

    '"phase2_6_pi_men_three_model_residuals.csv",':
        'RESULTS_DIR / "phase2_6_pi_men_three_model_residuals.csv",',

    'Path(\'phase2_6_pi_men_three_model_residuals.csv\').resolve()':
        '(RESULTS_DIR / \'phase2_6_pi_men_three_model_residuals.csv\').resolve()',
}

for old, new in replacements.items():
    count = source.count(old)
    if count != 1:
        raise SystemExit(f"STOP: Expected one occurrence, found {count}: {old}")
    source = source.replace(old, new, 1)

compile(source, str(file), "exec")
file.write_text(source, encoding="utf-8")

print("Successfully fixed:", file.name)
print("Only file paths and shared path import changed.")
