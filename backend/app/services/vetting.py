"""Per-transit scoring and false-positive checks (odd/even, secondary eclipse, SNR, size)."""
import numpy as np

from . import preprocess as pp


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
    return {"odd_ppm": out["odd"][0] * 1e6, "even_ppm": out["even"][0] * 1e6,
            "sigma": abs(out["odd"][0] - out["even"][0]) / err}


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


def flags(sig, rows, oe, sec, planet):
    out = []
    if len(rows) < 2:
        out.append(("warn", "Only one transit observed, so the period is unconstrained. Confirm with more data."))
    if sig["snr"] < 7:
        out.append(("warn", f"Overall signal-to-noise is {sig['snr']:.1f} (below 7). Stellar or instrumental noise can produce this."))
    if oe:
        if oe["sigma"] > 3:
            out.append(("warn", f"Odd and even transits differ by {oe['sigma']:.1f} sigma ({oe['odd_ppm']:.0f} vs {oe['even_ppm']:.0f} ppm). "
                                "This pattern is typical of an eclipsing binary at twice this period."))
        else:
            out.append(("ok", f"Odd and even transit depths agree ({oe['sigma']:.1f} sigma)."))
    if sec:
        if sec["snr"] >= 4:
            out.append(("warn", f"A secondary eclipse of {sec['depth_ppm']:.0f} ppm appears at phase 0.5 (SNR {sec['snr']:.1f}), which suggests an eclipsing binary."))
        else:
            out.append(("ok", "No secondary eclipse found at phase 0.5."))
    if rows and np.mean([r["snr"] < 3 for r in rows]) > 0.5:
        out.append(("info", "Most individual transits are below SNR 3, so the detection depends on stacking many. Correlated stellar noise can mimic this."))
    if planet and planet["radius_jupiter"] > 2.2:
        out.append(("warn", f"Implied radius is {planet['radius_jupiter']:.1f} Jupiter radii, larger than any known planet. Likely a stellar companion."))
    return [{"level": a, "text": b} for a, b in out]