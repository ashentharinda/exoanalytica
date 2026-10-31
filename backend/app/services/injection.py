"""Injection-recovery tests: does the preprocessing eat real signals, and does the whole pipeline find them?"""
import time

import numpy as np

from . import preprocess as pp

WINDOWS = (0.5, 1.0, 2.0)
DURATIONS = (0.05, 0.1, 0.2, 0.4, 0.8)  # days


def _box(t, P, t0, dur):
    return (np.abs(((t - t0 + P / 2) % P) - P / 2) < dur / 2).astype(float)


def _measured_depth(t, f, P, t0, dur):
    inn = _box(t, P, t0, dur) > 0
    if inn.sum() < 3 or (~inn).sum() < 3:
        return float("nan")
    return 1.0 - float(np.median(f[inn]) / np.median(f[~inn]))


def retention(t, f, rng, depth=0.003):
    """Preprocessing only: fraction of an injected transit's depth that survives detrending."""
    span = t[-1] - t[0]
    P = 5.0 if span > 15 else span / 3
    base = {w: pp.detrend(t, f, w) for w in WINDOWS}
    rows = []
    for dur in DURATIONS:
        if dur > P / 4:
            continue
        t0 = t[0] + rng.uniform(0, P)
        f_inj = f * (1 - depth * _box(t, P, t0, dur))
        kept = {}
        for w in WINDOWS:
            tc, fc = pp.detrend(t, f_inj, w)
            d_inj = _measured_depth(tc, fc, P, t0, dur)
            d_base = _measured_depth(*base[w], P, t0, dur)
            ok = np.isfinite(d_inj) and np.isfinite(d_base)
            kept[str(w)] = round(max(0.0, (d_inj - d_base) / depth), 3) if ok else None
        rows.append({"duration_h": round(dur * 24, 1), "kept": kept})
    return rows


def recovery(t, f, rng, budget_s=100, depths_ppm=(500, 1000, 2000, 4000), durs=(0.08, 0.25), reps=3):
    """End to end: inject transits, run detrend + BLS, count how many come back at the right period."""
    pmax = min(12.0, (t[-1] - t[0]) / 3)
    stats = {d: {"trials": 0, "found": 0, "ratios": []} for d in depths_ppm}
    start, truncated = time.time(), False
    for _ in range(reps):
        for depth in depths_ppm:
            for dur in durs:
                if time.time() - start > budget_s:
                    truncated = True
                    continue
                P = float(np.exp(rng.uniform(np.log(1.0), np.log(pmax))))
                t0 = float(t[0] + rng.uniform(0, P))
                f_inj = f * (1 - depth * 1e-6 * _box(t, P, t0, dur))
                try:
                    tc, fc = pp.detrend(t, f_inj)
                    s = pp.bls_search(tc, fc)
                except pp.DataError:
                    continue
                st = stats[depth]
                st["trials"] += 1
                dt = ((s["t0"] - t0 + P / 2) % P) - P / 2
                if abs(s["period"] - P) / P < 0.02 and abs(dt) < max(dur, 0.1):
                    st["found"] += 1
                    st["ratios"].append(s["depth"] / (depth * 1e-6))
    rows = [{"depth_ppm": d, "trials": v["trials"], "found": v["found"],
             "depth_kept": round(float(np.median(v["ratios"])), 2) if v["ratios"] else None}
            for d, v in stats.items()]
    return rows, truncated


def run(t, f, rng):
    ret = retention(t, f, rng)
    rec, truncated = recovery(t, f, rng)
    trials, found = sum(r["trials"] for r in rec), sum(r["found"] for r in rec)
    lines = [f"The full pipeline recovered {found} of {trials} injected transit signals"
             f" ({round(100 * found / max(trials, 1))}%)."]
    lost = [r["duration_h"] for r in ret if r["kept"].get("1.0") is not None and r["kept"]["1.0"] < 0.8]
    if lost:
        lines.append(f"With the default 1-day detrending window, transits of {min(lost)} hours or longer lose more than 20% of their depth. "
                     "Planets on long orbits around large stars may be under-measured.")
    else:
        lines.append("With the default 1-day detrending window, transits up to about 19 hours keep at least 80% of their depth.")
    if truncated:
        lines.append("The time budget ran out, so some trials were skipped.")
    return {"retention": ret, "recovery": rec, "summary": " ".join(lines), "windows": [str(w) for w in WINDOWS]}