from pathlib import Path
import shutil
import py_compile

folder = Path("research/phase_2/pi_men/scripts")
backup = Path("research/phase_2/pi_men/archive/path_fix_backup")
backup.mkdir(parents=True, exist_ok=True)

fixes = {
    "phase2_6_pi_men_activity_indicator_validation.py":
        'REPORTS_DIR / "phase2_6_pi_men_activity_indicator_report.txt".write_text(',

    "phase2_6_pi_men_corrected_alias_analysis.py":
        'REPORTS_DIR / "phase2_6_pi_men_corrected_alias_analysis_report.txt".write_text(',

    "phase2_6_pi_men_detrended_activity_validation.py":
        'REPORTS_DIR / "phase2_6_pi_men_detrended_activity_report.txt".write_text(',

    "phase2_6_pi_men_epoch_alias_analysis.py":
        'REPORTS_DIR / "phase2_6_pi_men_epoch_specific_alias_report.txt".write_text(',

    "phase2_6_pi_men_published_period_validation.py":
        'REPORTS_DIR / "phase2_6_pi_men_published_period_validation_report.txt".write_text(',
}

for filename, old in fixes.items():
    path = folder / filename
    source = path.read_text(encoding="utf-8-sig")

    if source.count(old) != 1:
        raise RuntimeError(
            f"Expected exactly one occurrence in {filename}; "
            f"found {source.count(old)}. No changes made to this file."
        )

    shutil.copy2(path, backup / filename)

    new = "(" + old[:-len(".write_text(")] + ").write_text("
    updated = source.replace(old, new, 1)

    compile(updated, str(path), "exec")
    path.write_text(updated, encoding="utf-8")

    print("FIXED:", filename)

print("\n===== COMPILE VERIFICATION =====")

for filename in fixes:
    py_compile.compile(
        str(folder / filename),
        doraise=True
    )
    print("PASS:", filename)

print("\nSUCCESS: All 5 path expressions corrected and compiled.")
print("Backups:", backup.resolve())
