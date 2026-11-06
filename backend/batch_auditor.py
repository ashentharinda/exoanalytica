"""
batch_auditor.py - ExoAnalytica Benchmark Audit
================================================

Runs the ExoAnalytica vetting pipeline on 100-200 targets at once and writes a
Benchmark Audit Report (CSV + console summary).

What it does for every target:
  1. Download the light curve with lightkurve (first few quarters / sectors, stitched)
  2. Clean + detrend            (app.services.preprocess)
  3. Find the transit with BLS  (app.services.preprocess)
  4. Vet the signal             (app.services.vetting): transit SNR, red-noise SNR,
                                odd/even depth test, secondary eclipse, V-shape, ...
  5. Turn the verdict into "Planet" or "False Positive" and compare it with the
     expected label from your input file

Targets run in parallel (ThreadPoolExecutor by default, ProcessPoolExecutor optional).
A target that fails to download, has no data, or is all NaN is marked SKIPPED / ERROR
in the report and never stops the rest of the batch.

Usage (run from the backend folder):
    python batch_auditor.py                          # reads targets.csv
    python batch_auditor.py --limit 3                # quick test on the first 3 rows
    python batch_auditor.py --workers 4 --resume     # continue an interrupted run
    python batch_auditor.py --executor process       # use processes instead of threads

Input file (CSV or JSON) columns:
    target_id   KIC 11904151  /  EPIC 201367065  /  TIC 261136679   (or just the number)
    name        any label you like (optional)
    mission     Kepler | K2 | TESS (optional - guessed from the KIC/EPIC/TIC prefix)
    expected    Planet | False Positive   (Eclipsing binaries count as False Positive)
"""
import argparse
import json
import logging
import re
import sys
import time
import warnings
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import shutil
# These are the pipeline modules you already have. No torch / CNN needed here.
from app.services import physics, preprocess as pp, vetting
from astropy.io import fits

try:  # progress bar is optional
    # from tqdm import tqdm
    tqdm = None
except ImportError:  
    tqdm = None

# --------------------------------------------------------------------------------------
# Settings
# --------------------------------------------------------------------------------------
DEFAULT_INPUT = "targets.csv"
DEFAULT_OUTPUT = "exoanalytica_audit_report.csv"
DEFAULT_CACHE = "lk_cache"

# Column order of the CSV report
REPORT_COLUMNS = [
    "target_id", "name", "mission", "expected", "predicted", "correct", "status",
    "verdict", "reasons", "period_d", "depth_ppm", "duration_h", "snr_bls", "snr_red",
    "n_transits", "odd_even_sigma", "odd_ppm", "even_ppm", "secondary_snr",
    "n_points", "error", "runtime_s",
]

PLANET, FALSE_POS, UNKNOWN = "Planet", "False Positive", "Unknown"

# Words people use in the "expected" column -> our two labels
_PLANET_WORDS = {"planet", "confirmed", "confirmed planet", "cp", "kp"}
_FP_WORDS = {"false positive", "fp", "fa", "false alarm", "eb", "eclipsing binary", "not a planet"}

# If the light curve header has no stellar parameters we fall back to the Sun
_SOLAR = {"radius_rsun": 1.0, "mass_msun": 1.0, "teff_k": 5772.0}

# Column names that are accepted as aliases (e.g. straight from NASA Exoplanet Archive tables)
_ALIASES = {
    "kepid": "target_id", "tic": "target_id", "tic_id": "target_id", "tid": "target_id",
    "epic": "target_id", "id": "target_id",
    "koi_disposition": "expected", "tfopwg_disp": "expected", "disposition": "expected",
    "label": "expected",
}


# --------------------------------------------------------------------------------------
# 1. Target ingestion
# --------------------------------------------------------------------------------------
def _norm_expected(value) -> str:
    v = str(value).strip().lower() if value is not None and not pd.isna(value) else ""
    if v in _PLANET_WORDS:
        return PLANET
    if v in _FP_WORDS:
        return FALSE_POS
    return UNKNOWN  # blank or unrecognised: still processed, but not counted in accuracy


def _guess_mission(target_id: str, mission: str) -> str:
    m = (mission or "").strip().capitalize()
    if m in ("Kepler", "K2", "Tess", "TESS"):
        return "TESS" if m.upper() == "TESS" else m
    t = target_id.strip().upper()
    if t.startswith("KIC") or t.startswith("KOI"):
        return "Kepler"
    if t.startswith("EPIC"):
        return "K2"
    if t.startswith("TIC") or t.startswith("TOI"):
        return "TESS"
    return "Kepler"

def resolve_target(target_id: str, mission: str):
    """Return (search_string, mission, author, exposure_time_in_seconds)."""
    tid = target_id.strip()
    m = _guess_mission(tid, mission)
    
    if re.fullmatch(r"\d+", tid):
        prefix = {"Kepler": "KIC", "K2": "EPIC", "TESS": "TIC"}.get(m)
        if prefix:
            tid = f"{prefix} {tid}"

    author = {"Kepler": "Kepler", "K2": "K2", "TESS": "SPOC"}[m]
    exptime = 120 if m == "TESS" else 1800
    return tid, m, author, exptime


def load_targets(path: str) -> list:
    """Read the target list (CSV or JSON) and return a list of dicts."""
    p = Path(path)
    if not p.exists():
        sys.exit(f"Input file not found: {p.resolve()}")
    if p.suffix.lower() == ".json":
        df = pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))
    else:
        df = pd.read_csv(p, comment="#", dtype=str)
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.rename(columns={k: v for k, v in _ALIASES.items() if k in df.columns and v not in df.columns})
    if "target_id" not in df.columns:
        sys.exit("Input file needs a 'target_id' column (e.g. KIC 11904151 or TIC 261136679).")

    rows, seen = [], set()
    for _, r in df.iterrows():
        tid = str(r["target_id"]).strip()
        if not tid or tid.lower() == "nan" or tid in seen:  # skip blanks and duplicates
            continue
        seen.add(tid)
        name = r.get("name")
        mission = r.get("mission")
        rows.append({
            "target_id": tid,
            "name": tid if name is None or pd.isna(name) else str(name).strip(),
            "mission": _guess_mission(tid, "" if mission is None or pd.isna(mission) else str(mission)),
            "expected": _norm_expected(r.get("expected")),
        })
    if not rows:
        sys.exit("The input file has no usable rows.")
    return rows


# --------------------------------------------------------------------------------------
# 2. Light-curve download
# --------------------------------------------------------------------------------------
def _retry(fn, tries=3, delay=4.0):
    """MAST (NASA's server) sometimes drops a request. Try a few times before giving up."""
    for i in range(tries):
        try:
            return fn()
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(delay * (i + 1))


def resolve_target(target_id: str, mission: str):
    """Return (search_string, mission, author, exposure_time_in_seconds)."""
    tid = target_id.strip()
    if re.fullmatch(r"\d+", tid):  # bare number: add the right prefix for the mission
        prefix = {"Kepler": "KIC", "K2": "EPIC", "TESS": "TIC"}.get(mission)
        if not prefix:
            raise pp.DataError("Bare number given but 'mission' is missing (Kepler, K2 or TESS).")
        tid = f"{prefix} {tid}"
    if not mission:
        raise pp.DataError(f"Cannot tell the mission for '{target_id}'. Use a KIC / EPIC / TIC ID or fill 'mission'.")
    if re.match(r"(?i)^(koi|toi|kepler|k2)[-\s]", tid):
        raise pp.DataError("Use the star's KIC / EPIC / TIC number here, not the KOI / TOI / planet name.")
    author = {"Kepler": "Kepler", "K2": "K2", "TESS": "SPOC"}[mission]
    exptime = 120 if mission == "TESS" else 1800  # 2-minute TESS, long-cadence Kepler / K2
    return tid, mission, author, exptime


def _plain(a):
    """astropy Masked array -> plain float ndarray (masked points become NaN)."""
    if hasattr(a, "filled"):
        a = a.filled(np.nan)
    return np.asarray(a, dtype=float)


def _quarantine_invalid_fits(folder):
    """Download the first few quarters / sectors with lightkurve and stitch them together."""
    import lightkurve as lk  # imported here so every worker process loads it itself

    sr = _retry(lambda: lk.search_lightcurve(query, mission=mission, author=author, exptime=exptime))
    if len(sr) == 0:
        raise pp.DataError(f"No {mission} light curves found for {query}.")
    folder = Path(cache_dir) / re.sub(r"\W+", "_", query)  # one folder per target: threads never clash
    folder.mkdir(parents=True, exist_ok=True)
    coll = _retry(lambda: sr[:max_sectors].download_all(download_dir=str(folder)))
    if coll is None or len(coll) == 0:
        raise pp.DataError(f"Download returned no data for {query}.")
    lc = coll.stitch().remove_nans()
    t, f = _plain(lc.time.value), _plain(lc.flux.value)
    ok = np.isfinite(t) & np.isfinite(f)
    if ok.sum() == 0:
        raise pp.DataError("Light curve contains only NaN values.")
    meta = {"radius_rsun": lc.meta.get("RADIUS"), "teff_k": lc.meta.get("TEFF")}
    return t[ok], f[ok], meta


def _stellar(meta):
    """Use the star's radius / Teff from the file header when present, otherwise the Sun."""
    stellar, known = dict(_SOLAR), False
    try:
        r = float(meta.get("radius_rsun"))
        if np.isfinite(r) and r > 0:
            stellar["radius_rsun"], known = r, True
            stellar["mass_msun"] = max(0.1, r)  # crude M ~ R for main-sequence stars (same as the web app)
    except (TypeError, ValueError):
        pass
    try:
        te = float(meta.get("teff_k"))
        if np.isfinite(te) and te > 0:
            stellar["teff_k"] = te
    except (TypeError, ValueError):
        pass
    return stellar, known


# --------------------------------------------------------------------------------------
# 3. Analysis: detrend -> BLS -> SNR -> odd/even + other vetting checks
# --------------------------------------------------------------------------------------
def _no_cnn(_g_view, views, _snrs):
    """The audit does not use the CNN, so per-transit confidence scores are just zeros."""
    return [0.0] * len(views)


def analyze_light_curve(t, f, meta=None) -> dict:
    """Run the full vetting chain on one light curve and return a flat dict of results."""
    t_raw, f_raw = pp.prepare(t, f)           # drop NaNs, sort, normalise (raises DataError if unusable)
    t, f = pp.detrend(t_raw, f_raw)           # flatten stellar / instrument trends
    sig = pp.refine(t, f, pp.bls_search(t, f))  # transit search + fine polish
    if sig["depth"] <= 0:
        raise pp.DataError("No transit-like dip found.")

    stellar, known = _stellar(meta or {})
    rows, noise = vetting.per_transit(t, f, sig, None, _no_cnn)
    odd_even = vetting.odd_even(rows, noise)                  # odd vs even transit depth
    secondary = vetting.secondary(t, f, sig, noise)           # eclipse at phase 0.5
    snr_red = pp.red_noise_snr(t, f, sig)                     # SNR that respects correlated noise
    planet = physics.characterize(max(sig["depth"], 1e-8), sig["period"], stellar["radius_rsun"],
                                  stellar["mass_msun"], stellar["teff_k"])
    extra = vetting.extra_checks(t, f, sig, rows, noise, stellar, known)
    flags = vetting.flags(sig, rows, odd_even, secondary, planet, extra)
    if snr_red is not None and snr_red < 7:
        flags.append({"level": "warn", "text": "SNR below 7 once correlated noise is included.",
                      "tag": "correlated noise", "hard": False})

    # Without the CNN the detection score is simply "is the (red-noise) SNR at least 7?"
    best_snr = snr_red if snr_red is not None else sig["snr"]
    score = 1.0 if best_snr >= 7 else 0.0
    cls = vetting.classify(flags, score, snr_red)

    # Verdict -> label. Anything that is not a "Planet candidate ..." counts as False Positive.
    predicted = PLANET if cls["label"].startswith("Planet candidate") else FALSE_POS
    return {
        "predicted": predicted,
        "verdict": cls["label"],
        "reasons": "; ".join(cls["reasons"]),
        "period_d": round(sig["period"], 5),
        "depth_ppm": round(sig["depth"] * 1e6, 1),
        "duration_h": round(sig["duration"] * 24, 2),
        "snr_bls": round(sig["snr"], 1),
        "snr_red": None if snr_red is None else round(snr_red, 1),
        "n_transits": len(rows),
        "odd_even_sigma": None if odd_even is None else round(odd_even["sigma"], 2),
        "odd_ppm": None if odd_even is None else round(odd_even["odd_ppm"], 1),
        "even_ppm": None if odd_even is None else round(odd_even["even_ppm"], 1),
        "secondary_snr": None if secondary is None else round(secondary["snr"], 1),
        "n_points": int(len(t)),
    }


def audit_one(row: dict, cfg: dict) -> dict:
    """Process ONE target. Never raises: every failure becomes a row with status SKIPPED / ERROR."""
    t0 = time.perf_counter()
    out = {c: None for c in REPORT_COLUMNS}
    out.update(target_id=row["target_id"], name=row["name"], mission=row["mission"], expected=row["expected"])
    try:
        query, mission, author, exptime = resolve_target(row["target_id"], row["mission"])
        out["mission"] = mission
        t, f, meta = fetch_lightcurve(query, mission, author, exptime, cfg["max_sectors"], cfg["cache_dir"])
        out.update(analyze_light_curve(t, f, meta))
        out["status"] = "OK"
        if row["expected"] in (PLANET, FALSE_POS):
            out["correct"] = bool(out["predicted"] == row["expected"])
    except pp.DataError as e:  # expected problems: no data, NaNs, too short, ...
        out["status"], out["error"] = "SKIPPED", str(e)[:300]
    except Exception as e:  # anything else (network, bad file, bug): record it and carry on
        out["status"], out["error"] = "ERROR", f"{type(e).__name__}: {e}"[:300]
    out["runtime_s"] = round(time.perf_counter() - t0, 2)
    return out


# --------------------------------------------------------------------------------------
# 4. Report
# --------------------------------------------------------------------------------------
def save_report(results: list, path: str, order: dict):
    df = pd.DataFrame(results, columns=REPORT_COLUMNS)
    df = df.sort_values("target_id", key=lambda s: s.map(order)).reset_index(drop=True)
    df.to_csv(path, index=False, encoding="utf-8")
    return df


def compute_metrics(df: pd.DataFrame, wall_s: float) -> pd.DataFrame:
    ok = df[df["status"] == "OK"]
    scored = ok[ok["expected"].isin([PLANET, FALSE_POS])]
    tp = int(((scored["expected"] == PLANET) & (scored["predicted"] == PLANET)).sum())
    fn = int(((scored["expected"] == PLANET) & (scored["predicted"] == FALSE_POS)).sum())
    tn = int(((scored["expected"] == FALSE_POS) & (scored["predicted"] == FALSE_POS)).sum())
    fp = int(((scored["expected"] == FALSE_POS) & (scored["predicted"] == PLANET)).sum())
    n_planet, n_fp = tp + fn, tn + fp

    def pct(a, b):
        return "n/a" if b == 0 else f"{100.0 * a / b:.1f}%"

    avg_rt = ok["runtime_s"].mean() if len(ok) else float("nan")
    metrics = [
        ("Total targets in file", len(df)),
        ("Total processed (status OK)", len(ok)),
        ("Skipped / failed", len(df) - len(ok)),
        ("Scored (processed + expected label known)", len(scored)),
        ("True Positives (planets kept)", f"{tp} of {n_planet}"),
        ("False Positives Identified (rejected)", f"{tn} of {n_fp}"),
        ("Missed planets (wrongly rejected)", fn),
        ("False alarms (false positives kept)", fp),
        ("Overall Accuracy", pct(tp + tn, len(scored))),
        ("Planet recall", pct(tp, n_planet)),
        ("False-positive rejection rate", pct(tn, n_fp)),
        ("Average runtime per target", "n/a" if np.isnan(avg_rt) else f"{avg_rt:.1f} s"),
        ("Total wall-clock time", f"{wall_s / 60:.1f} min"),
    ]
    return pd.DataFrame(metrics, columns=["Metric", "Value"])


def print_summary(df: pd.DataFrame, wall_s: float, output: str):
    line = "=" * 74
    try:
        print(f"\n{line}\n  EXOANALYTICA BENCHMARK AUDIT REPORT\n{line}", flush=True)
        print(compute_metrics(df, wall_s).to_string(index=False), flush=True)

        ok = df[(df["status"] == "OK") & df["expected"].isin([PLANET, FALSE_POS])]
        if len(ok):
            print("\nConfusion matrix (rows = expected, columns = predicted):", flush=True)
            print(pd.crosstab(ok["expected"], ok["predicted"]).to_string(), flush=True)

        wrong = ok[ok["correct"] == False]
        if len(wrong):
            print("\nMisclassified targets:", flush=True)
            print(wrong[["name", "expected", "predicted", "verdict", "reasons"]].to_string(index=False, max_colwidth=40), flush=True)

        bad = df[df["status"] != "OK"]
        if len(bad):
            print("\nSkipped / failed targets:", flush=True)
            print(bad[["name", "status", "error"]].to_string(index=False, max_colwidth=60), flush=True)

        print(f"\nFull report saved to: {Path(output).resolve()}\n{line}", flush=True)
    except (ValueError, OSError):
        
        pass

# --------------------------------------------------------------------------------------
# Main: run everything in parallel
# --------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="ExoAnalytica batch auditor")
    ap.add_argument("--input", default=DEFAULT_INPUT, help="targets CSV or JSON (default: targets.csv)")
    ap.add_argument("--output", default=DEFAULT_OUTPUT, help="report CSV path")
    ap.add_argument("--workers", type=int, default=4, help="targets processed at the same time (default 4)")
    ap.add_argument("--executor", choices=["thread", "process"], default="thread",
                    help="thread = best for downloads (default); process = best for heavy CPU work")
    ap.add_argument("--max-sectors", type=int, default=4, help="quarters / sectors to download per target")
    ap.add_argument("--cache-dir", default=DEFAULT_CACHE, help="where downloaded FITS files are kept")
    ap.add_argument("--limit", type=int, default=0, help="only run the first N targets (for testing)")
    ap.add_argument("--resume", action="store_true", help="keep OK rows from an existing report, redo the rest")
    args = ap.parse_args()

    warnings.simplefilter("ignore")  # lightkurve / astropy warn a lot during batch runs
    logging.getLogger("lightkurve").setLevel(logging.ERROR)

    targets = load_targets(args.input)
    if args.limit > 0:
        targets = targets[: args.limit]
    order = {t["target_id"]: i for i, t in enumerate(targets)}

    results = []
    if args.resume and Path(args.output).exists():
        old = pd.read_csv(args.output, dtype={"target_id": str})
        old = old[(old["status"] == "OK") & old["target_id"].isin(order)]
        results = [{k: (None if pd.isna(v) else v) for k, v in r.items()} for r in old.to_dict("records")]
        print(f"Resuming: keeping {len(results)} finished targets from {args.output}")
    done = {r["target_id"] for r in results}
    todo = [t for t in targets if t["target_id"] not in done]

    cfg = {"max_sectors": args.max_sectors, "cache_dir": args.cache_dir}
    print(f"Auditing {len(todo)} targets with {args.workers} {args.executor} workers ...")
    t_start = time.perf_counter()

    Pool = ProcessPoolExecutor if args.executor == "process" else ThreadPoolExecutor
    pool = Pool(max_workers=args.workers)
    futures = {pool.submit(audit_one, row, cfg): row for row in todo}
    bar = tqdm(total=len(futures), unit="target") if tqdm else None
    try:
        for n, fut in enumerate(as_completed(futures), 1):
            row = futures[fut]
            try:
                res = fut.result()
            except Exception as e:  # a worker process crashed hard (very rare)
                res = {c: None for c in REPORT_COLUMNS}
                res.update(target_id=row["target_id"], name=row["name"], mission=row["mission"],
                           expected=row["expected"], status="ERROR", error=f"{type(e).__name__}: {e}"[:300])
            results.append(res)
            save_report(results, args.output, order)  # save after EVERY target: a crash loses nothing
            msg = f"{res['name']}: {res['status']}"
            if res["status"] == "OK":
                msg += f"  expected={res['expected']}  predicted={res['predicted']}  ({res['runtime_s']}s)"
            else:
                msg += f"  {str(res['error'])[:60]}"
            if bar:
                bar.update(1)
                bar.write(msg)
            else:
                try:
                    print(f"[{n}/{len(futures)}] {msg}", flush=True)
                except (ValueError, OSError):
                    pass
    except KeyboardInterrupt:
        print("\nStopped by user. Saving what is finished so far ...")
        pool.shutdown(wait=False, cancel_futures=True)
    else:
        pool.shutdown()
    finally:
        if bar:
            bar.close()

    df = save_report(results, args.output, order)
    print_summary(df, time.perf_counter() - t_start, args.output)


if __name__ == "__main__":  # this guard is required on Windows for --executor process
    main()