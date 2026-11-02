"""Per-transit scoring and false-positive checks: odd/even, secondary eclipse, transit shape,
duration vs star density, depth stability, single-event dominance, gap edges, out-of-eclipse variation."""
import math

import numpy as np

from . import preprocess as pp

G, RSUN, MSUN = 6.674e-11, 6.957e8, 1.989e30


def _noise(f):
    return 1.4826 * float(np.median(np.abs(f - np.median(f))))


def per_transit(t, f, sig, g_view, scorer):
    """One row per observed transit: depth, SNR, coverage and a CNN confidence for that transit alone."""
    P, t0, dur = sig["period"], sig["t0"], sig["duration"]
    cad = float(np.median(np.diff(t)))
    noise = _noise(f)
    edges = np.linspace(-3 * dur, 3 * dur, 62)
    rows, views = [], []
    for n in range(int(np.floor((t[0] - t0) / P)), int(np.ceil((t[-1] - t0) / P)) + 1):
        tc = t0 + n * P
        d = t - tc
        inn = np.abs(d) < dur / 2
        n_in = int(inn.sum())
        if n_in < 3:
            continue
        near = np.abs(d) < 3 * dur
        out = near & ~inn
        base = float(np.median(f[out])) if out.sum() >= 3 else 1.0
        depth = base - float(np.mean(f[inn]))
        rows.append({"epoch": n, "time": tc, "depth_ppm": depth * 1e6,
                     "snr": depth / (noise / np.sqrt(n_in)),
                     "coverage": min(1.0, n_in / max(dur / cad, 1.0)),
                     "_n_in": n_in, "_depth": depth})
        views.append(pp.norm_view(pp.binned(d[near], f[near], edges)).astype("float32"))
    scores = scorer(g_view, views, [r["snr"] for r in rows]) if rows else []
    for r, s in zip(rows, scores):
        r["confidence"] = float(s)
    return rows, noise


def odd_even(rows, noise):
    out = {}
    for name, par in (("odd", 1), ("even", 0)):
        sel = [r for r in rows if r["epoch"] % 2 == par]
        if not sel:
            return None
        w = np.array([r["_n_in"] for r in sel], float)
        d = np.array([r["_depth"] for r in sel])
        out[name] = (float(np.average(d, weights=w)), noise / np.sqrt(w.sum()))
    err = float(np.hypot(out["odd"][1], out["even"][1]))
    mean = 0.5 * (out["odd"][0] + out["even"][0])
    return {"odd_ppm": out["odd"][0] * 1e6, "even_ppm": out["even"][0] * 1e6,
            "sigma": abs(out["odd"][0] - out["even"][0]) / err,
            "rel": abs(out["odd"][0] - out["even"][0]) / mean if mean > 0 else 0.0}


def secondary(t, f, sig, noise):
    P, t0, dur = sig["period"], sig["t0"], sig["duration"]
    if P / 2 < 1.5 * dur:
        return None
    ph = pp.phase(t, P, t0)
    sel = np.abs(ph) > P / 2 - dur / 2
    n = int(sel.sum())
    if n < 3:
        return None
    base = float(np.median(f[np.abs(ph) > dur]))
    depth = base - float(np.mean(f[sel]))
    return {"depth_ppm": depth * 1e6, "snr": depth / (noise / np.sqrt(n))}


def shape_check(t, f, sig, noise):
    """Planets have flat-bottomed transits; grazing eclipsing binaries are V-shaped."""
    P, t0, dur = sig["period"], sig["t0"], sig["duration"]
    x = pp.phase(t, P, t0)
    h = dur / 2
    far = np.abs(x) > 1.5 * dur
    base = float(np.median(f[far])) if far.sum() >= 10 else 1.0
    c = np.abs(x) < 0.15 * h
    m = (np.abs(x) >= 0.5 * h) & (np.abs(x) < 0.8 * h)
    if c.sum() < 5 or m.sum() < 5:
        return None
    dc, dm = base - float(f[c].mean()), base - float(f[m].mean())
    ec, em = noise / math.sqrt(c.sum()), noise / math.sqrt(m.sum())
    if dc <= 0 or dc / ec < 10:
        return None  # not enough signal to judge the shape
    ratio = dm / dc
    err = math.sqrt((em / dc) ** 2 + (dm * ec / dc ** 2) ** 2)
    return {"ratio": float(ratio), "err": float(err), "v_shaped": bool(ratio + 2 * err < 0.6)}


def duration_check(sig, stellar, known):
    """A planet cannot cross its star much more slowly than a central transit allows."""
    Rs, Ms, P = stellar["radius_rsun"] * RSUN, stellar["mass_msun"] * MSUN, sig["period"] * 86400
    a = (G * Ms * P ** 2 / (4 * math.pi ** 2)) ** (1 / 3)
    x = min(1.0, Rs * (1 + math.sqrt(max(sig["depth"], 0.0))) / a)
    T = P / math.pi * math.asin(x) / 86400  # days
    return {"expected_h": T * 24, "observed_h": sig["duration"] * 24, "ratio": float(sig["duration"] / T), "known": bool(known)}


def depth_variability(rows, noise):
    if len(rows) < 3:
        return None
    d = np.array([r["_depth"] for r in rows])
    sigma = noise / np.sqrt(np.array([r["_n_in"] for r in rows], float))
    w = 1 / sigma ** 2
    mean = float(np.sum(w * d) / np.sum(w))
    chi2 = float(np.sum(((d - mean) / sigma) ** 2) / (len(d) - 1))
    return {"chi2": chi2, "rel": float(np.std(d) / abs(mean)) if mean else 0.0}


def dominance(rows):
    if len(rows) < 3:
        return None
    s2 = np.array([max(r["snr"], 0.0) ** 2 for r in rows])
    if s2.sum() <= 0:
        return None
    i = int(np.argmax(s2))
    return {"share": float(s2[i] / s2.sum()), "time": float(rows[i]["time"])}


def near_gap(t, rows, gap_days=0.5, margin=0.5):
    if len(rows) < 3:
        return None
    br = np.where(np.diff(t) > max(gap_days, 10 * float(np.median(np.diff(t)))))[0]
    edges = np.concatenate([[t[0], t[-1]], t[br], t[br + 1]])
    near = sum(1 for r in rows if float(np.min(np.abs(edges - r["time"]))) < margin)
    return {"near": int(near), "n": len(rows)}


def out_of_eclipse(t, f, sig, noise):
    """Close eclipsing binaries bend each other's light all around the orbit (ellipsoidal / reflection effects)."""
    P, t0, dur = sig["period"], sig["t0"], sig["duration"]
    if P / 2 <= 3 * dur or sig["depth"] <= 0:
        return None
    ph = pp.phase(t, P, t0)
    sel = (np.abs(ph) > 1.5 * dur) & (np.abs(ph) < P / 2 - 1.5 * dur)
    if sel.sum() < 200:
        return None
    phi = 2 * np.pi * ph[sel] / P
    A = np.column_stack([np.cos(phi), np.sin(phi), np.cos(2 * phi), np.sin(2 * phi), np.ones(sel.sum())])
    coef = np.linalg.lstsq(A, f[sel], rcond=None)[0]
    amp = max(math.hypot(coef[0], coef[1]), math.hypot(coef[2], coef[3]))
    return {"amp_ppm": float(amp * 1e6), "snr": float(amp / (noise * math.sqrt(2 / sel.sum()))), "depth_ratio": float(amp / sig["depth"])}


def extra_checks(t, f, sig, rows, noise, stellar, known):
    return {"shape": shape_check(t, f, sig, noise), "duration": duration_check(sig, stellar, known),
            "variability": depth_variability(rows, noise), "dominance": dominance(rows),
            "near_gap": near_gap(t, rows), "out_of_eclipse": out_of_eclipse(t, f, sig, noise)}


def flags(sig, rows, oe, sec, planet, extra=None):
    out = []

    def add(level, text, tag=None, hard=False):
        out.append({"level": level, "text": text, "tag": tag, "hard": hard})

    if len(rows) < 2:
        add("warn", "Only one transit observed, so the period is unconstrained. Confirm with more data.", "single transit")
    if sig["snr"] < 7:
        add("warn", f"Overall signal-to-noise is {sig['snr']:.1f} (below 7). Stellar or instrumental noise can produce this.", "low SNR")
    if oe:
        if oe["sigma"] > 3 and oe["rel"] > 0.10:
            add("warn", f"Odd and even transits differ by {oe['sigma']:.1f} sigma ({oe['odd_ppm']:.0f} vs {oe['even_ppm']:.0f} ppm). "
                        "This pattern is typical of an eclipsing binary at twice this period.",
                "odd/even depth mismatch", hard=oe["sigma"] > 5 and oe["rel"] > 0.25)
        else:
            add("ok", f"Odd and even transit depths agree ({oe['sigma']:.1f} sigma).")
    if sec:
        if sec["snr"] >= 4:
            add("warn", f"A secondary eclipse of {sec['depth_ppm']:.0f} ppm appears at phase 0.5 (SNR {sec['snr']:.1f}), which suggests an eclipsing binary.",
                "secondary eclipse", hard=sec["depth_ppm"] >= 0.1 * sig["depth"] * 1e6)
        else:
            add("ok", "No secondary eclipse found at phase 0.5.")
    if rows and np.mean([r["snr"] < 3 for r in rows]) > 0.5:
        add("info", "Most individual transits are below SNR 3, so the detection depends on stacking many. Correlated stellar noise can mimic this.")
    if planet and planet["radius_jupiter"] > 2.2:
        add("warn", f"Implied radius is {planet['radius_jupiter']:.1f} Jupiter radii, larger than any known planet. Likely a stellar companion.",
            "too large for a planet", hard=True)

    ex = extra or {}
    sh = ex.get("shape")
    if sh:
        if sh["v_shaped"]:
            add("warn", f"The transit is V-shaped (depth {sh['ratio'] * 100:.0f}% of the maximum partway to the edge) rather than flat-bottomed. "
                        "Grazing eclipsing binaries look like this.", "V-shaped transit")
        else:
            add("ok", "The transit has a flat bottom, as expected for a planet.")
    du = ex.get("duration")
    if du and du["ratio"] > 1.5:
        base = (f"The transit lasts {du['observed_h']:.1f} h, but a planet crossing this star on this orbit could last at most about "
                f"{du['expected_h']:.1f} h ({du['ratio']:.1f} times longer). ")
        if du["known"]:
            add("warn", base + "The signal probably comes from a different, background star (a blended eclipsing binary).",
                "duration too long for this star", hard=du["ratio"] > 2.5)
        else:
            add("info", base + "The star was assumed to be Sun-like, so this is only a hint. Enter the real star size and mass to check.")
    elif du and du["known"]:
        add("ok", "The transit duration is consistent with the star's size and mass.")
    va = ex.get("variability")
    if va and va["chi2"] > 4 and va["rel"] > 0.15:
        add("warn", f"Individual transit depths vary by {va['rel'] * 100:.0f}%, more than noise allows. Instrumental effects or starspots can do this; planets repeat consistently.",
            "unstable transit depth")
    do = ex.get("dominance")
    if do and do["share"] > 0.6:
        add("warn", f"One transit (around day {do['time']:.1f}) supplies {do['share'] * 100:.0f}% of the total signal. "
                    "A single event can be a flare, a pointing jump or another instrumental glitch.", "one dominant event")
    ng = ex.get("near_gap")
    if ng and ng["near"] >= 2 and ng["near"] / ng["n"] >= 0.5:
        add("warn", f"{ng['near']} of {ng['n']} transits fall within half a day of a data gap or the edge of the data, where instruments are least stable.",
            "transits at data gaps")
    oo = ex.get("out_of_eclipse")
    if oo and oo["snr"] >= 5 and oo["depth_ratio"] >= 0.1:
        add("warn", f"The light curve varies at the orbital period outside the transits ({oo['amp_ppm']:.0f} ppm, {oo['depth_ratio'] * 100:.0f}% of the transit depth). "
                    "Close eclipsing binaries do this through ellipsoidal or reflection effects.", "out-of-eclipse variation")
    return out


def classify(flags, score, snr_red):
    """Combine the checks into one verdict: hard failures first, then the number of warnings."""
    warns = [x for x in flags if x["level"] == "warn"]
    hard = [x for x in warns if x.get("hard")]
    reasons = [x["tag"] for x in (hard or warns) if x.get("tag")]
    if score < 0.5 and (snr_red is None or snr_red < 7):
        label, tone = "Not a convincing detection", "no"
    elif hard:
        label, tone = "Likely false positive", "no"
    elif len(warns) >= 2:
        label, tone = "Possible false positive", "maybe"
    elif len(warns) == 1:
        label, tone = "Planet candidate (one check flagged)", "maybe"
    elif score < 0.5:
        label, tone = "Weak candidate", "maybe"
    else:
        label, tone = "Planet candidate", "yes"
    return {"label": label, "tone": tone, "reasons": reasons}