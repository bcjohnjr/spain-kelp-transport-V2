"""Screening well-to-wheel lifecycle greenhouse-gas accounting.

The energy-system optimisation is economic; this module adds a transparent
screening LCA layer to the solved system without changing the optimiser.
It is intended to test whether the economic solution delivers a large GHG
reduction, not to substitute for an ISO 14040/44 process LCA.

Functional unit: one year of transport energy service represented by the model.
Fossil comparators are lifecycle intensities for the same modelled demand.
Vehicle manufacture is excluded from the central estimate and discussed as a
separate limitation.  Electricity-generation factors are cradle-to-grave.
Biofuel/e-fuel/kelp factors are fuel-cycle intensities, so electricity used to
make those fuels is not counted a second time.

Central literature factors:
- road gasoline/diesel: IPCC AR6 WGIII Ch. 10, Table 10.8, 92 gCO2e/MJ
- e-FT with low-carbon electricity: IPCC, 12 gCO2e/MJ
- low-carbon renewable ammonia: IPCC, 3.2 gCO2e/MJ
- generic advanced biofuels: IPCC IAM median, 25 gCO2e/MJ
- jet fossil baseline: ICAO CORSIA baseline, 89 gCO2e/MJ
- marine fossil baseline: IMO current average GFI, 93.3 gCO2e/MJ
- offshore macroalgal fuel: Greene et al. (2020), central 22 gCO2e/MJ;
  reported net range 14--29 gCO2e/MJ
- PV/wind/nuclear/CSP electricity: harmonised NREL/IPCC lifecycle values.
"""

FOSSIL_G_PER_MJ = {
    "ldv_gasoline": 92.0,
    "ldv_diesel": 92.0,
    "hdv": 92.0,
    "offroad": 92.0,
    "aviation": 89.0,
    "shipping": 93.3,
}

# Central cradle-to-grave generation intensities, gCO2e/kWh.
ELECTRICITY_G_PER_KWH = {
    "PV": 40.0,
    "Onshore wind": 9.3,
    "Offshore wind": 11.0,
    "CSP": 23.0,
    "Nuclear (life extension)": 12.0,
    "Nuclear (new)": 12.0,
}

# Fuel-cycle intensities, gCO2e/MJ of delivered carrier.
FUEL_G_PER_MJ = {
    "eFT_liquids": 12.0,
    "e_methanol": 12.0,  # low-carbon e-fuel proxy; tested broadly in sensitivity
    "e_ammonia": 3.2,
    "e_methane": 12.0,   # low-carbon e-fuel proxy; tested broadly in sensitivity
    "ATJ_jet_from_ethanol": 25.0,
    "bio_methanol_from_CH4": 25.0,
    "waste_biomethane": 25.0,
    "HEFA_waste_lipids": 25.0,
    "residue_FT": 25.0,
    "FAME_biodiesel_existing": 25.0,
    "crop_ethanol_existing": 25.0,
    "kelp HTL diesel/jet": 22.0,
    "kelp ethanol": 22.0,
    "kelp biomethane (net of fleet)": 22.0,
}

LOW_FACTORS = {
    "electricity": {"PV": 20.0, "Onshore wind": 7.0, "Offshore wind": 8.0, "CSP": 15.0,
                    "Nuclear (life extension)": 6.0, "Nuclear (new)": 6.0},
    "biofuel": 18.0, "kelp": 14.0, "efuel": 8.0, "ammonia": 2.0,
}
HIGH_FACTORS = {
    "electricity": {"PV": 60.0, "Onshore wind": 15.0, "Offshore wind": 20.0, "CSP": 40.0,
                    "Nuclear (life extension)": 20.0, "Nuclear (new)": 20.0},
    "biofuel": 36.0, "kelp": 29.0, "efuel": 25.0, "ammonia": 19.0,
}


def _electricity_intensity(s, factors):
    gen = s["generation_twh"]
    tot = sum(gen.values())
    if tot <= 0:
        return 0.0
    return sum(gen[k] * factors[k] for k in gen) / tot


def _fuel_factors_from_brackets(bracket):
    f = dict(FUEL_G_PER_MJ)
    for k in ("ATJ_jet_from_ethanol", "bio_methanol_from_CH4", "waste_biomethane",
              "HEFA_waste_lipids", "residue_FT", "FAME_biodiesel_existing",
              "crop_ethanol_existing"):
        f[k] = bracket["biofuel"]
    for k in ("kelp HTL diesel/jet", "kelp ethanol", "kelp biomethane (net of fleet)"):
        f[k] = bracket["kelp"]
    for k in ("eFT_liquids", "e_methanol", "e_methane"):
        f[k] = bracket["efuel"]
    f["e_ammonia"] = bracket["ammonia"]
    return f


def fossil_lifecycle_mt(s, fossil_factors=None):
    """Lifecycle GHG of the fossil comparator for the same demand, MtCO2e/yr."""
    factors = fossil_factors or FOSSIL_G_PER_MJ
    # 1 TWh = 3.6e9 MJ; 1 Mt = 1e12 g -> multiplier 0.0036.
    return sum(s["demand_twh"].get(k, 0.0) * v * 0.0036 for k, v in factors.items())


def lowcarbon_lifecycle_mt(s, electricity_factors=None, fuel_factors=None):
    """Screening lifecycle GHG for the low-carbon energy carriers, MtCO2e/yr."""
    ef = electricity_factors or ELECTRICITY_G_PER_KWH
    ff = fuel_factors or FUEL_G_PER_MJ
    e_ci = _electricity_intensity(s, ef)
    # Count lifecycle electricity only for direct electric end uses. Fuel-cycle
    # factors already include production energy, preventing double counting.
    direct_el = s["electricity_vehicles_rail_twh"] * e_ci * 0.001
    fuels = sum(max(v, 0.0) * ff[k] * 0.0036 for k, v in s["fuels_twh"].items())
    return direct_el + fuels


def screening_lifecycle(s):
    fossil = fossil_lifecycle_mt(s)
    low = lowcarbon_lifecycle_mt(s)
    low_lo = lowcarbon_lifecycle_mt(s, LOW_FACTORS["electricity"], _fuel_factors_from_brackets(LOW_FACTORS))
    low_hi = lowcarbon_lifecycle_mt(s, HIGH_FACTORS["electricity"], _fuel_factors_from_brackets(HIGH_FACTORS))
    avoided = fossil - low
    return {
        "fossil_wtw_mtco2e": fossil,
        "lowcarbon_wtw_mtco2e": low,
        "lowcarbon_factor_sensitivity_mtco2e": [low_lo, low_hi],
        "avoided_wtw_mtco2e": avoided,
        "reduction_pct": 100.0 * avoided / fossil if fossil else 0.0,
        "reduction_factor_sensitivity_pct": [
            100.0 * (fossil - low_hi) / fossil if fossil else 0.0,
            100.0 * (fossil - low_lo) / fossil if fossil else 0.0,
        ],
        "electricity_ci_gco2e_kwh": _electricity_intensity(s, ELECTRICITY_G_PER_KWH),
        "scope_note": "Screening well-to-wheel/carrier LCA; vehicle manufacture excluded; international bunkers included in all-scope case.",
    }


def sampled_lifecycle(s, rng):
    """One uncertainty draw for the screening LCA factors."""
    tri = rng.triangular
    el = {
        "PV": tri(20, 40, 60),
        "Onshore wind": tri(7, 9.3, 15),
        "Offshore wind": tri(8, 11, 20),
        "CSP": tri(15, 23, 40),
        "Nuclear (life extension)": tri(6, 12, 20),
        "Nuclear (new)": tri(6, 12, 20),
    }
    b = {"biofuel": tri(18, 25, 36), "kelp": tri(14, 22, 29),
         "efuel": tri(8, 12, 25), "ammonia": tri(2, 3.2, 19)}
    low = lowcarbon_lifecycle_mt(s, el, _fuel_factors_from_brackets(b))
    fossil = fossil_lifecycle_mt(s)
    return low, fossil, 100.0 * (fossil - low) / fossil
