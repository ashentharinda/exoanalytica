"""Isolated analysis process. Reads spec.json from its working dir, writes result.json."""
import json
import math
import sys
import traceback
from pathlib import Path

import numpy as np

from .services import injection, physics, preprocess as pp, vetting
from .services.model import classify, classify_locals

MAX_SIGNALS = 5        # most signals reported per star
MIN_SNR_EXTRA = 8.0    # signals after the first must reach this SNR
# period ratios that suggest an alias (harmonic) or a resonance with an earlier signal
RATIOS = ((2, 1, "warn"), (1, 2, "warn"), (3, 1, "warn"), (1, 3, "warn"), (3, 2, "info"), (2, 3, "info"))


def _lst(a, nd=6):
    return [None if not math.isfinite(x) else round(float(x), nd) for x in a]


def _plain(a):
    """astropy Masked array -> plain float ndarray (masked points become NaN)."""
    if hasattr(a, "filled"):
        a = a.filled(np.nan)
    return np.asarray(a, dtype=float)


def _acquire(job_dir: Path, spec):
    if spec["source"] == "upload":
        p = job_dir / f"input.{spec['kind']}"
        return pp.load_fits(p) if spec["kind"] == "fits" else pp.load_csv(p)
    import lightkurve as lk

    author = "SPOC" if spec["mission"] == "TESS" else "Kepler"
    sr = lk.search_lightcurve(spec["target"], mission=spec["mission"], author=author)
    if len(sr) == 0:
        raise pp.DataError(f"No {spec['mission']} light curves found for {spec['target']}.")
    lc = sr[:3].download_all(download_dir=str(job_dir)).stitch().remove_nans()
    meta = {"radius_rsun": lc.meta.get("RADIUS"), "teff_k": lc.meta.get("TEFF")}
    t, f = _plain(lc.time.value), _plain(lc.flux.value)
    ok = np.isfinite(t) & np.isfinite(f)
    return t[ok], f[ok], meta


def _stellar(spec, meta):
    user = spec["stellar"]
    stellar, src = {}, {}
    for key, default in (("radius_rsun", 1.0), ("mass_msun", 1.0), ("teff_k", 5772.0)):
        if user.get(key):
            stellar[key], src[key] = user[key], "user"
        elif meta.get(key) and math.isfinite(float(meta[key])) and float(meta[key]) > 0:
            stellar[key], src[key] = float(meta[key]), "file header"
        else:
            stellar[key], src[key] = default, "solar default"
    if src["radius_rsun"] != "user" and src["mass_msun"] == "solar default":
        stellar["mass_msun"] = max(0.1, stellar["radius_rsun"])  # crude M~R for main-sequence stars
    return stellar, src


def _relation(period, earlier):
    """Compare a new period with the signals already accepted. Returns (n, label, level) or None."""
    for n, p0 in enumerate(earlier, 1):
        r = period / p0
        if abs(r - 1) < 0.02:
            return n, "same", None
        for a, b, level in RATIOS:
            if abs(r - a / b) / (a / b) < 0.015:
                return n, f"{a}:{b}", level
    return None


def _analyze(t, f, sig, stellar, known):
    """Everything we report about one signal: score, planet properties, per-transit table, vetting."""
    ph = pp.phase(t, sig["period"], sig["t0"])
    g, l = pp.make_views(ph, f, sig["period"], sig["duration"])
    score, method, trained_on = classify(g, l, sig["snr"])
    candidate = score >= 0.5
    planet = physics.characterize(max(sig["depth"], 1e-8), sig["period"], stellar["radius_rsun"],
                                  stellar["mass_msun"], stellar["teff_k"]) if candidate else None
    rows, noise = vetting.per_transit(t, f, sig, g, classify_locals)
    oe, sec = vetting.odd_even(rows, noise), vetting.secondary(t, f, sig, noise)
    ex = vetting.extra_checks(t, f, sig, rows, noise, stellar, known)
    fl = vetting.flags(sig, rows, oe, sec, planet, ex)
    snr_red = pp.red_noise_snr(t, f, sig)
    if snr_red is not None:
        if snr_red < 7:
            fl.append({"level": "warn", "text": f"Once correlated noise is accounted for, the signal-to-noise drops to {snr_red:.1f} (below 7). "
                                                "Slow stellar variability or instrumental trends can produce a signal like this.",
                       "tag": "correlated noise", "hard": False})
        else:
            fl.append({"level": "ok", "text": f"The signal stays strong after accounting for correlated noise (SNR {snr_red:.0f}).",
                       "tag": None, "hard": False})
    edges = np.linspace(-0.5 * sig["period"], 0.5 * sig["period"], 361)
    return {
        "detection": {"score": round(score, 4), "is_candidate": candidate, "method": method, "trained_on": trained_on},
        "signal": {"period_d": sig["period"], "epoch": sig["t0"], "depth_ppm": sig["depth"] * 1e6,
                   "duration_h": sig["duration"] * 24, "snr": sig["snr"],
                   "snr_red": None if snr_red is None else round(snr_red, 1)},
        "planet": planet,
        "transits": [{"time": round(r["time"], 4), "depth_ppm": round(r["depth_ppm"], 1), "snr": round(r["snr"], 1),
                      "coverage": round(r["coverage"], 2), "confidence": round(r.get("confidence", 0.0), 3)}
                     for r in rows][:40],
        "n_transits": len(rows),
        "classification": vetting.classify(fl, score, snr_red),
        "vetting": {"passed": not any(x["level"] == "warn" for x in fl), "flags": fl, "odd_even": oe, "secondary": sec, "checks": ex},
        "plots": {"phase_d": _lst((edges[:-1] + edges[1:]) / 2, 4), "folded": _lst(pp.binned(ph, f, edges))},
    }


def _mask(t, f, sigs, skip=None):
    """Remove the in-transit points of every signal in `sigs` (except index `skip`)."""
    keep = np.ones(len(t), bool)
    for i, s in enumerate(sigs):
        if i != skip:
            keep &= np.abs(pp.phase(t, s["period"], s["t0"])) > max(0.75 * s["duration"], 0.06)
    return t[keep], f[keep]


def _coincides(new, old, t):
    """True if (almost) every transit of `new` falls on a transit of `old`: a harmonic, not a new planet."""
    n0, n1 = int(np.floor((t[0] - new["t0"]) / new["period"])), int(np.ceil((t[-1] - new["t0"]) / new["period"]))
    tc = new["t0"] + np.arange(n0, n1 + 1) * new["period"]
    off = np.abs(((tc - old["t0"] + old["period"] / 2) % old["period"]) - old["period"] / 2)
    return bool(np.mean(off < max(old["duration"], new["duration"])) >= 0.8)


def find_signals(t, f, stellar, known):
    """Iterative search: find the strongest signal, mask its transits, search again.
    Then analyse each signal with the OTHER signals' transits masked, so they cannot contaminate it."""
    found, rels = [], []
    t_k, f_k = t, f
    for _ in range(MAX_SIGNALS + 3):  # a few spare rounds for duplicates that only get masked
        if len(found) >= MAX_SIGNALS or len(t_k) < 500:
            break
        try:
            sig = pp.bls_search(t_k, f_k)
        except pp.DataError:
            if not found:
                raise
            break
        sig = pp.refine(t_k, f_k, sig)
        if found and sig["snr"] < MIN_SNR_EXTRA:
            break
        rel = _relation(sig["period"], [x["period"] for x in found]) if found else None
        duplicate = (rel and rel[1] == "same") or any(_coincides(sig, old, t) for old in found)
        if not duplicate:  # a signal found again is masked but not reported twice
            found.append(sig)
            rels.append(rel)
        t_k, f_k = _mask(t_k, f_k, [sig])

    # Pass A: decide which extra signals are real. Each is judged on the data as it was when it was found.
    accepted = [0]
    for i in range(1, len(found)):
        ti, fi = _mask(t, f, found[:i])
        res = _analyze(ti, fi, found[i], stellar, known)
        cov = float(np.mean([x["coverage"] for x in res["transits"]])) if res["transits"] else 0.0
        red = res["signal"]["snr_red"]
        # extra signals must be repeated, fully observed transits that survive correlated noise
        if res["n_transits"] >= 2 and cov >= 0.7 and red is not None and red >= 7:
            accepted.append(i)
    # Pass B: analyse every accepted signal with only the OTHER accepted signals' transits hidden.
    number = {i: k for k, i in enumerate(accepted, 1)}  # display number of each kept signal
    out = []
    for i in accepted:
        ti, fi = _mask(t, f, [found[j] for j in accepted if j != i])
        res = _analyze(ti, fi, found[i], stellar, known)
        if rels[i] and rels[i][0] - 1 in number:
            n, label, level = rels[i]
            text = (f"Period is in a {label} ratio with signal {number[n - 1]} ({found[n - 1]['period']:.3f} d). It may be a harmonic of that planet rather than a separate one."
                    if level == "warn" else
                    f"Period is close to a {label} ratio with signal {number[n - 1]}. This is common for real planets in resonance, but check it is not an alias.")
            res["vetting"]["flags"].append({"level": level, "text": text, "tag": "possible alias" if level == "warn" else None, "hard": False})
            res["vetting"]["passed"] = not any(x["level"] == "warn" for x in res["vetting"]["flags"])
            res["classification"] = vetting.classify(res["vetting"]["flags"], res["detection"]["score"], res["signal"]["snr_red"])
        out.append(res)
    if out[0]["classification"]["label"] == "Likely false positive" or any(
            x.get("tag") == "out-of-eclipse variation" for x in out[0]["vetting"]["flags"]):
        out = out[:1]  # leftovers of an eclipsing binary are not extra planets
    return out


def main(job_dir: Path):
    spec = json.loads((job_dir / "spec.json").read_text())
    t, f, meta = _acquire(job_dir, spec)
    t_raw, f_raw = pp.prepare(t, f)
    t, f = pp.detrend(t_raw, f_raw)
    stellar, src = _stellar(spec, meta)
    signals = find_signals(t, f, stellar, src["radius_rsun"] != "solar default")
    first = signals[0]

    tb = np.linspace(t[0], t[-1], min(3000, len(t)) + 1)
    result = {k: first[k] for k in ("detection", "signal", "planet", "transits", "n_transits", "vetting", "classification")}
    result["stellar"] = {"values": stellar, "source": src}
    result["plots"] = {"time": _lst((tb[:-1] + tb[1:]) / 2, 4), "flux": _lst(pp.binned(t, f, tb)), **first["plots"]}
    result["n_signals"] = len(signals)
    result["planets"] = [{k: s[k] for k in ("detection", "signal", "planet", "vetting", "plots", "n_transits", "classification")}
                         for s in signals[1:]]

    if spec.get("injection"):
        try:  # an injection failure must never lose the main result
            keep = np.ones(len(t_raw), bool)
            for s in signals:
                if s["detection"]["is_candidate"]:  # remove real signals so they cannot interfere with the test
                    sg = s["signal"]
                    keep &= np.abs(pp.phase(t_raw, sg["period_d"], sg["epoch"])) > 1.5 * sg["duration_h"] / 24
            base_t, base_f = (t_raw[keep], f_raw[keep]) if keep.sum() >= 2000 else (t_raw, f_raw)
            result["injection"] = injection.run(base_t, base_f, np.random.default_rng(12345))
        except Exception:
            traceback.print_exc(file=sys.stderr)
            result["injection"] = {"error": "The injection test could not run on this light curve."}
    (job_dir / "result.json").write_text(json.dumps(result, allow_nan=False, default=float))


if __name__ == "__main__":
    d = Path(sys.argv[1])
    try:
        main(d)
    except pp.DataError as e:
        (d / "result.json").write_text(json.dumps({"error": str(e)}))
    except Exception:  # details stay in the container log, not in the API response
        traceback.print_exc(file=sys.stderr)
        (d / "result.json").write_text(json.dumps({"error": "Analysis failed. Check that the file is a valid light curve."}))