"""Isolated analysis process. Reads spec.json from its working dir, writes result.json."""
import json
import math
import sys
from pathlib import Path

import numpy as np

from .services import physics, preprocess as pp
from .services.model import classify


def _lst(a, nd=6):
    return [None if not math.isfinite(x) else round(float(x), nd) for x in a]


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
    return lc.time.value.astype(float), lc.flux.value.astype(float), meta


def main(job_dir: Path):
    spec = json.loads((job_dir / "spec.json").read_text())
    t, f, meta = _acquire(job_dir, spec)
    t, f = pp.clean(t, f)
    sig = pp.bls_search(t, f)
    ph = pp.phase(t, sig["period"], sig["t0"])
    g, l = pp.make_views(ph, f, sig["period"], sig["duration"])
    score, method, trained_on = classify(g, l, sig["snr"])

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

    candidate = score >= 0.5
    planet = physics.characterize(max(sig["depth"], 1e-8), sig["period"], stellar["radius_rsun"],
                                  stellar["mass_msun"], stellar["teff_k"]) if candidate else None

    tb = np.linspace(t[0], t[-1], min(3000, len(t)) + 1)
    flux_b = pp.binned(t, f, tb)
    fold_edges = np.linspace(-0.5 * sig["period"], 0.5 * sig["period"], 361)
    fold_b = pp.binned(ph, f, fold_edges)
    result = {
        "detection": {"score": round(score, 4), "is_candidate": candidate, "method": method, "trained_on": trained_on},
        "signal": {"period_d": sig["period"], "epoch": sig["t0"], "depth_ppm": sig["depth"] * 1e6,
                   "duration_h": sig["duration"] * 24, "snr": sig["snr"]},
        "planet": planet,
        "stellar": {"values": stellar, "source": src},
        "plots": {"time": _lst((tb[:-1] + tb[1:]) / 2, 4), "flux": _lst(flux_b),
                  "phase_d": _lst((fold_edges[:-1] + fold_edges[1:]) / 2, 4), "folded": _lst(fold_b)},
    }
    (job_dir / "result.json").write_text(json.dumps(result, allow_nan=False, default=float))


if __name__ == "__main__":
    d = Path(sys.argv[1])
    try:
        main(d)
    except pp.DataError as e:
        (d / "result.json").write_text(json.dumps({"error": str(e)}))
    except Exception as e:  # details stay in the container log, not in the API response
        print(repr(e), file=sys.stderr)
        (d / "result.json").write_text(json.dumps({"error": "Analysis failed. Check that the file is a valid light curve."}))
