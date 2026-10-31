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


def detrend(t, f, window_days=1.0):
    """Median-filter detrend plus upward-outlier clipping (so transits survive)."""
    cad = float(np.median(np.diff(t)))
    win = min(max(11, int(window_days / cad) | 1), (len(f) // 3) | 1)
    flat = f / median_filter(f, size=win, mode="nearest")
    sig = 1.4826 * float(np.median(np.abs(flat - 1)))
    if sig <= 0:
        raise DataError("Flux is constant; nothing to analyse.")
    keep = flat < 1 + 5 * sig
    return t[keep], flat[keep]


def clean(t, f, window_days=1.0):
    return detrend(*prepare(t, f), window_days)


def bls_search(t, f):
    from astropy.timeseries import BoxLeastSquares

    k = max(1, int(np.ceil(len(t) / 20000)))
    n = len(t) // k * k
    tb, fb = t[:n].reshape(-1, k).mean(1), f[:n].reshape(-1, k).mean(1)
    pmax = min((t[-1] - t[0]) / 2, 40.0)
    if pmax <= 0.6:
        raise DataError("Observation window too short to search for periodic transits.")
    periods = np.exp(np.linspace(np.log(0.5), np.log(pmax), 6000))
    res = BoxLeastSquares(tb, fb).power(periods, np.array([0.04, 0.08, 0.12, 0.2, 0.3]), objective="snr")
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
