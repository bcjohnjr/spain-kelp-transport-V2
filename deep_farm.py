"""Deep-ocean seaweed farms: zones, yields, nutrient supply (artificial upwelling vs depth cycling) and biomass cost.

Nutrient demand is met partly by natural supply (winter mixing, upwelling) and partly by one of:
  wave_pump      passive wave-driven pipe pump (Isaacs/Atmocean type). Field test off Hawaii: 0.75 m x 300 m
                 tube delivered 16-45 m3/h, about 10% of model predictions, with structural failure
                 (White et al. 2010, J. Atmos. Oceanic Technol. 27:385).
  wave_pump_xl   the same principle scaled to 1.5 m diameter (4x area), assuming design life is fixed.
  solar_pipe     floating-PV-driven low-head axial pump in a 1.6 m x 400 m pipe, 1 m/s while the sun shines.
  salt_fountain  heat-driven 'perpetual salt fountain' (Stommel 1956): no energy input, needs surface water
                 saltier than deep water (true in the Canary region, not off northern Spain); flow of a few mm/s.
  depth_cycling  the kelp grid is lowered to the nitracline at night and raised to ~9 m by day
                 (Navarrete et al. 2021: 9-80 m daily for 90 days, ~4x biomass, deep nitrate >15 uM).
  refinery_return  ammonium recovered at the biorefinery returned to the farm (cheap, but legally
                 'ocean fertilisation' under the London Protocol; shown for comparison only).
Pumping head for deep water lifted inside a pipe: density excess of the cold column (~0.5 m) plus friction.
"""
from dataclasses import dataclass, asdict
import json

SECONDS_YR = 3.156e7
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)


@dataclass
class Zone:
    name: str
    yield_t_ha: float           # t dry / ha / yr with adequate nutrients
    n_frac: float               # tissue N, fraction of dry mass
    natural_n_share: float      # share of N demand met by natural supply
    nitrate_300m: float         # uM at ~300 m
    nitrate_400m: float
    nitrate_700m: float
    salt_fountain_ok: bool
    depth_cycle_effect: float   # share of the supplemental N need that depth cycling can meet
    carb_factor: float          # fermentable-sugar content relative to North Atlantic Saccharina
    species: str
    area_km2: dict              # free area (outside lanes, beyond 6 nm) by distance band
    mid_km: dict


ZONES = {
    "nor_shelf": Zone("Noratlántica shelf 0-200 m", 15, 0.020, 1.00, 10, 12, 18, False, 1.0, 1.0,
                      "Saccharina latissima / Alaria esculenta (native)", {"0-100": 13605}, {"0-100": 40}),
    "nor_slope": Zone("Noratlántica slope 200-1,000 m", 15, 0.020, 0.80, 10, 12, 18, False, 1.0, 1.0,
                      "Saccharina latissima / Alaria esculenta (native)", {"0-100": 18291}, {"0-100": 60}),
    "nor_deep": Zone("Noratlántica deep >1,000 m", 15, 0.020, 0.60, 10, 12, 18, False, 1.0, 1.0,
                     "Saccharina latissima / Laminaria ochroleuca, winter-spring crop (native)",
                     {"0-100": 38409, "100-200": 81064, "200-370": 133078}, {"0-100": 70, "100-200": 150, "200-370": 285}),
    "can_deep": Zone("Canaria deep >1,000 m", 10, 0.015, 0.10, 8, 12, 25, True, 0.6, 0.75,
                     "warm-temperate natives (Sargassum, Lobophora, L. ochroleuca in cooled water)",
                     {"0-100": 128830, "100-200": 109219, "200-370": 149814}, {"0-100": 60, "100-200": 150, "200-370": 285}),
    "med_deep": Zone("Levantino-Balear deep >1,000 m", 8, 0.015, 0.15, 5, 6, 8, False, 0.5, 0.75,
                     "warm-temperate natives (Sargassum, Cystoseira); winter crop",
                     {"0-100": 98757, "100-200": 56216, "200-370": 6026}, {"0-100": 60, "100-200": 150, "200-370": 230}),
}


@dataclass
class FarmCost:
    base_eur_t: float = 300.0          # shelf longline farm incl. harvest and 40 km transport (Greene et al. 2020 range)
    deep_factor: float = 1.30          # deep moorings or station keeping beyond 1,000 m
    slope_factor: float = 1.20
    transport_eur_t_wet_km: float = 0.02
    capture_eff: float = 0.25          # share of upwelled nitrate taken up by the kelp
    wave_unit_m3s: float = 0.0083      # 30 m3/h measured midpoint
    wave_unit_capex: float = 60e3
    wave_unit_life: float = 5
    wave_xl_m3s: float = 0.033
    wave_xl_capex: float = 250e3
    solar_pipe_m3s_avg: float = 0.67   # 2.0 m3/s for ~1/3 of the hours
    solar_pipe_capex: float = 500e3    # 400 m of 1.6 m HDPE (~EUR 800/m), pump, float, mooring, 30 kWp PV
    solar_pipe_life: float = 15
    salt_m3s: float = 0.006            # 3 mm/s in a 1.6 m pipe
    salt_capex: float = 700e3          # 700 m conductive pipe to Antarctic Intermediate Water
    salt_life: float = 15
    depth_cycle_capex_km2: float = 1.0e6
    depth_cycle_opex_km2: float = 50e3
    depth_cycle_life: float = 15
    return_eur_kgN: float = 1.30       # fertiliser value forgone
    return_handling_eur_kgN: float = 0.4
    return_uptake: float = 0.5
    om_frac: float = 0.03
    rate: float = 0.07
    dm_harvest: float = 0.13


def nitrate_gN_m3(uM):
    return uM * 1e-3 * 14.0


def nutrient_options(z: Zone, c: FarmCost):
    """EUR per dry tonne of kelp for each nutrient method (inf if not applicable)."""
    t_km2 = z.yield_t_ha * 100
    n_need = t_km2 * z.n_frac * 1000 * (1 - z.natural_n_share)    # kg N / km2 / yr from supplement
    out, units = {}, {}
    def pipe(q, capex, life, uM):
        kgN_unit = q * SECONDS_YR * nitrate_gN_m3(uM) * c.capture_eff / 1000
        n_units = n_need / kgN_unit if kgN_unit > 0 else float("inf")
        ann = n_units * capex * (CRF(c.rate, life) + c.om_frac)
        return ann / t_km2, n_units
    out["wave_pump"], units["wave_pump"] = pipe(c.wave_unit_m3s, c.wave_unit_capex, c.wave_unit_life, z.nitrate_300m)
    out["wave_pump_xl"], units["wave_pump_xl"] = pipe(c.wave_xl_m3s, c.wave_xl_capex, c.wave_unit_life, z.nitrate_300m)
    out["solar_pipe"], units["solar_pipe"] = pipe(c.solar_pipe_m3s_avg, c.solar_pipe_capex, c.solar_pipe_life, z.nitrate_400m)
    if z.salt_fountain_ok:
        out["salt_fountain"], units["salt_fountain"] = pipe(c.salt_m3s, c.salt_capex, c.salt_life, z.nitrate_700m)
    else:
        out["salt_fountain"], units["salt_fountain"] = float("inf"), 0
    dc = (c.depth_cycle_capex_km2 * CRF(c.rate, c.depth_cycle_life) + c.depth_cycle_opex_km2) / t_km2
    out["depth_cycling"] = dc
    units["depth_cycling"] = 1.0
    out["refinery_return"] = n_need / c.return_uptake * (c.return_eur_kgN + c.return_handling_eur_kgN) / t_km2
    units["refinery_return"] = 0
    m3_per_t = n_need / t_km2 * 1000 / (nitrate_gN_m3(z.nitrate_400m) * c.capture_eff)
    return out, units, {"n_supplement_kgN_per_t": n_need / t_km2, "deep_water_m3_per_t_dw": m3_per_t}


def farm_cost(zone_key, band, c: FarmCost, method="depth_cycling"):
    z = ZONES[zone_key]
    factor = 1.0 if zone_key == "nor_shelf" else (c.slope_factor if zone_key == "nor_slope" else c.deep_factor)
    yield_adj = 15.0 / z.yield_t_ha            # fixed per-area costs spread over fewer tonnes
    base = c.base_eur_t * factor * (0.4 + 0.6 * yield_adj)
    wet = 1 / c.dm_harvest
    transport = wet * max(z.mid_km[band] - 40, 0) * c.transport_eur_t_wet_km
    nut, units, info = nutrient_options(z, c)
    eff_yield = z.yield_t_ha
    if z.natural_n_share >= 1.0:
        method, nut_cost = "natural", 0.0
    elif method == "depth_cycling" and z.depth_cycle_effect < 1.0:
        # depth cycling meets only part of the supplement; yield falls in proportion to unmet N
        unmet = (1 - z.natural_n_share) * (1 - z.depth_cycle_effect)
        eff_yield = z.yield_t_ha * (1 - unmet)
        base = c.base_eur_t * factor * (0.4 + 0.6 * 15.0 / eff_yield)
        nut_cost = nut["depth_cycling"] * z.yield_t_ha / eff_yield
    elif method != "natural":
        nut_cost = nut[method]
    return dict(zone=zone_key, band=band, method=method, yield_t_ha=eff_yield, base_eur_t=base,
                transport_eur_t=transport, nutrient_eur_t=nut_cost, total_eur_t=base + transport + nut_cost,
                transport_km=z.mid_km[band], units_per_km2=units.get(method, 0), **info)


if __name__ == "__main__":
    c = FarmCost()
    tab = {}
    for k, z in ZONES.items():
        nut, units, info = nutrient_options(z, c)
        tab[k] = {"nutrient_eur_per_t": nut, "units_per_km2": units, **info}
        print(k, {m: round(v) if v != float('inf') else 'n/a' for m, v in nut.items()},
              {m: round(v, 1) for m, v in units.items()}, {a: round(b) for a, b in info.items()})
    for k in ZONES:
        for b in ZONES[k].area_km2:
            print(farm_cost(k, b, c))
    json.dump(tab, open("outputs/nutrient_supply_options.json", "w"), indent=1, default=str)
