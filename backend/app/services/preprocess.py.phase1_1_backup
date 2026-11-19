"""Light-curve loading, cleaning, transit search (BLS) and phase folding."""
import numpy as np
import pandas as pd
from scipy.ndimage import median_filter


class DataError(ValueError):
    """Problem with the user's data; the message is safe to show them."""


def load_csv(path):
    df = pd.read_csv(path, nrows=500_000, comment="#")
    low = {str(c).strip().lower(): c for c in df.columns}
    tc = next((low[k] for k in ("time", "t", "btjd", "bkjd", "bjd") if k in low), None)
    fc = next((low[k] for k in ("pdcsap_flux", "flux", "sap_flux") if k in low), None)
    if tc is None or fc is None:
        num = list(df.select_dtypes("number").columns)
        if len(num) < 2:
            raise DataError("CSV needs a time column and a flux column.")
        tc, fc = num[0], num[1]
    return df[tc].to_numpy(float), df[fc].to_numpy(float), {}


def load_fits(path):
    from astropy.io import fits

    with fits.open(path, memmap=False) as h:
        if len(h) < 2 or getattr(h[1], "columns", None) is None:
            raise DataError("FITS file has no light-curve table in extension 1.")
        names = {n.upper(): n for n in h[1].columns.names}
        fcol = next((names[k] for k in ("PDCSAP_FLUX", "SAP_FLUX", "FLUX") if k in names), None)
        if "TIME" not in names or fcol is None:
            raise DataError("FITS table needs TIME and PDCSAP_FLUX (or SAP_FLUX) columns.")
        t = np.array(h[1].data[names["TIME"]], dtype=float)
        f = np.array(h[1].data[fcol], dtype=float)
        hdr = h[0].header
        meta = {"radius_rsun": hdr.get("RADIUS"), "teff_k": hdr.get("TEFF")}
    return t, f, meta


def prepare(t, f):
    """Drop bad points, sort, normalise by the median. No detrending yet."""
    m = np.isfinite(t) & np.isfinite(f)
    t, f = t[m], f[m]
    if len(t) < 500:
        raise DataError("Need at least 500 valid data points.")
    o = np.argsort(t)
    t, f = t[o], f[o]
    if t[-1] - t[0] < 3:
        raise DataError("Need at least 3 days of observations.")
    med = np.median(f)
    if med <= 0:
        raise DataError("Flux values must be positive.")
    if float(np.median(np.diff(t))) <= 0:
        raise DataError("Timestamps contain duplicates.")
    return t, f / med


def detrend(t, f, window_days=1.0, gap_days=0.5):
    """Median-filter detrend, done separately on each continuous stretch of data.
    Filtering across a gap leaks the trend from one side to the other and creates fake transit-like steps,
    so each stretch is filtered alone and its first and last half-window (where the trend is unreliable) is trimmed."""
    cad = float(np.median(np.diff(t)))
    breaks = np.where(np.diff(t) > max(gap_days, 10 * cad))[0] + 1
    flat = np.ones_like(f)
    ok = np.zeros(len(f), bool)
    for idx in np.split(np.arange(len(f)), breaks):
        if len(idx) < 30:
            continue  # too short to detrend
        win = min(max(11, int(window_days / cad) | 1), (len(idx) // 3) | 1)
        flat[idx] = f[idx] / median_filter(f[idx], size=win, mode="nearest")
        ts = t[idx]
        trim = 0.5 * window_days if (ts[-1] - ts[0]) > 3 * window_days else 0.0
        ok[idx] = (ts >= ts[0] + trim) & (ts <= ts[-1] - trim)
    if ok.sum() < 200:
        raise DataError("Too little continuous data to detrend.")
    t, flat = t[ok], flat[ok]
    sig = 1.4826 * float(np.median(np.abs(flat - 1)))
    if sig <= 0:
        raise DataError("Flux is constant; nothing to analyse.")
    keep = flat < 1 + 5 * sig  # clip upward outliers only, so transits survive
    return t[keep], flat[keep]


def clean(t, f, window_days=1.0):
    return detrend(*prepare(t, f), window_days)


def bls_search(t, f):
    from astropy.timeseries import BoxLeastSquares

    k = max(1, int(np.ceil(len(t) / 20000)))
    n = len(t) // k * k
    tb, fb = t[:n].reshape(-1, k).mean(1), f[:n].reshape(-1, k).mean(1)
    sigma = 1.4826 * float(np.median(np.abs(f - np.median(f)))) / np.sqrt(k)
    dy = np.full(len(tb), max(sigma, 1e-9))  # without dy, astropy's depth_snr is not a real SNR
    pmax = min((t[-1] - t[0]) / 2, 40.0)
    if pmax <= 0.6:
        raise DataError("Observation window too short to search for periodic transits.")
    periods = np.exp(np.linspace(np.log(0.5), np.log(pmax), 6000))
    res = BoxLeastSquares(tb, fb, dy=dy).power(periods, np.array([0.04, 0.08, 0.12, 0.2, 0.3]), objective="snr")
    i = int(np.argmax(res.power))
    return dict(period=float(res.period[i]), t0=float(res.transit_time[i]), depth=float(res.depth[i]),
                duration=float(res.duration[i]), snr=float(res.depth_snr[i]))


def phase(t, period, t0):
    return ((t - t0 + 0.5 * period) % period) - 0.5 * period


def binned(x, y, edges):
    idx = np.digitize(x, edges) - 1
    ok = (idx >= 0) & (idx < len(edges) - 1)
    s = pd.Series(y[ok]).groupby(idx[ok]).median()
    out = np.full(len(edges) - 1, np.nan)
    out[s.index.to_numpy()] = s.to_numpy()
    return out


def norm_view(v):
    """Median 0, deepest point -1 (AstroNet-style), gaps filled with 0."""
    if np.all(~np.isfinite(v)):
        return np.zeros_like(v)
    v = np.where(np.isfinite(v), v, np.nanmedian(v))
    v = v - np.median(v)
    return v / max(-v.min(), 1e-9)


def make_views(ph, f, period, duration):
    g = norm_view(binned(ph, f, np.linspace(-0.5 * period, 0.5 * period, 202)))
    w = 3 * duration
    l = norm_view(binned(ph, f, np.linspace(-w, w, 62)))
    return g.astype("float32"), l.astype("float32")


def refine(t, f, sig):
    """Polish the BLS result: search a fine grid of period, epoch and duration for the best box fit.
    Small errors in period/epoch otherwise drift across many transits and bias every per-transit measurement."""
    P0, d0 = sig["period"], sig["duration"]
    noise = 1.4826 * float(np.median(np.abs(f - np.median(f))))
    base = float(np.median(f))
    tm = 0.5 * (t[0] + t[-1])
    t0m = sig["t0"] + np.round((tm - sig["t0"]) / P0) * P0  # epoch near the middle of the data

    def fit(P, t0, d):
        inn = np.abs(((t - t0 + P / 2) % P) - P / 2) < d / 2
        n = int(inn.sum())
        if n < 3:
            return -1.0, 0.0
        depth = base - float(np.mean(f[inn]))
        return depth / (noise / np.sqrt(n)), depth

    best = (-1.0, P0, t0m, 0.0)
    for P in P0 * (1 + np.linspace(-0.004, 0.004, 41)):
        for off in np.linspace(-0.5 * d0, 0.5 * d0, 21):
            snr, depth = fit(P, t0m + off, d0)
            if snr > best[0]:
                best = (snr, P, t0m + off, depth)
    snr, P, t0, depth = best
    d_best = d0
    for d in d0 * np.array([0.5, 0.65, 0.8, 1.25, 1.5, 2.0]):
        s, dp = fit(P, t0, d)
        if s > snr and d < 0.6:
            snr, depth, d_best = s, dp, d
    if depth <= 0:  # refinement found nothing better than the original: keep it
        return sig
    return dict(period=float(P), t0=float(t0), depth=float(depth), duration=float(d_best), snr=float(max(snr, 0.0)))


def red_noise_snr(t, f, sig):
    """SNR that accounts for correlated (red) noise. The depth is compared with the scatter of the flux
    averaged over one transit duration, so slow stellar variability cannot fake a high SNR."""
    P, t0, dur = sig["period"], sig["t0"], sig["duration"]
    cad = float(np.median(np.diff(t)))
    off = np.abs(((t - t0 + P / 2) % P) - P / 2)
    to, fo = t[off >= 1.5 * dur], f[off >= 1.5 * dur]
    if len(to) < 100:
        return None
    idx = np.digitize(to, np.arange(to[0], to[-1] + dur, dur))
    counts, sums = np.bincount(idx), np.bincount(idx, weights=fo)
    good = counts >= max(3, 0.6 * dur / cad)
    if good.sum() < 10:
        return None
    means = sums[good] / counts[good]
    sigma = 1.4826 * float(np.median(np.abs(means - np.median(means))))
    core = off < dur / 2
    n_tr = len(np.unique(np.round((t[core] - t0) / P))) if core.sum() >= 3 else 0
    if sigma <= 0 or n_tr == 0:
        return None
    return float(sig["depth"] / sigma * np.sqrt(n_tr))