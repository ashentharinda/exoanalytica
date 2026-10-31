"""Planet characterisation from transit depth + stellar parameters (SI units internally)."""
import math

G = 6.674e-11
RSUN, MSUN, AU = 6.957e8, 1.989e30, 1.496e11
REARTH, MEARTH, RJUP = 6.371e6, 5.972e24, 7.1492e7
G_EARTH = 9.80665


def mass_from_radius(r_earth: float) -> tuple[float, str]:
    """Chen & Kipping (2017) probabilistic mass-radius relation, median values."""
    if r_earth < 1.23:
        return (r_earth / 1.008) ** (1 / 0.279), "rocky (Terran) relation"
    if r_earth < 14.3:
        return (r_earth / 0.808) ** (1 / 0.589), "Neptunian relation"
    return 318.0, "Jovian regime: radius does not constrain mass; ~1 Jupiter mass assumed"


def characterize(depth, period_d, rs, ms, teff, albedo=0.3):
    rp_e = math.sqrt(depth) * rs * RSUN / REARTH
    mass_e, mass_note = mass_from_radius(rp_e)
    r_m, m_kg = rp_e * REARTH, mass_e * MEARTH
    gravity = G * m_kg / r_m**2
    density = m_kg / (4 / 3 * math.pi * r_m**3)
    a_m = (G * ms * MSUN * (period_d * 86400) ** 2 / (4 * math.pi**2)) ** (1 / 3)
    teq = teff * math.sqrt(rs * RSUN / (2 * a_m)) * (1 - albedo) ** 0.25
    lum = rs**2 * (teff / 5772) ** 4  # solar units
    # Kopparapu-style flux limits (solar-type approximation)
    hz = {"inner_cons": math.sqrt(lum / 1.107), "outer_cons": math.sqrt(lum / 0.356),
          "inner_opt": math.sqrt(lum / 1.776), "outer_opt": math.sqrt(lum / 0.32)}
    a_au = a_m / AU
    if hz["inner_cons"] <= a_au <= hz["outer_cons"]:
        status = "Inside the conservative habitable zone"
    elif hz["inner_opt"] <= a_au <= hz["outer_opt"]:
        status = "Inside the optimistic habitable zone"
    else:
        status = "Too hot (inside the habitable zone)" if a_au < hz["inner_opt"] else "Too cold (beyond the habitable zone)"
    return {
        "radius_earth": rp_e, "radius_jupiter": rp_e * REARTH / RJUP,
        "mass_earth": mass_e, "mass_note": mass_note,
        "density_gcc": density / 1000, "gravity_ms2": gravity, "gravity_g": gravity / G_EARTH,
        "semi_major_au": a_au, "teq_k": teq,
        "hz": {k: round(v, 4) for k, v in hz.items()} | {"status": status},
        "gaseous_likely": rp_e > 1.6,
    }
