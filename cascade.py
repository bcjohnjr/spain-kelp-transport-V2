"""Kelp biorefinery cascades: mass and energy balances per dry tonne, and co-location with floating wind.

Routes
  P_self  : pyrolysis-first, energy self-sufficient (biomethane runs harvesters, SkySails-assisted transport
            vessels and a CHP; drying heat from CHP waste heat + char + CSP heat or bio-oil if short)
  P_grid  : pyrolysis-first, external renewable electricity for heat-pump drying and electrolytic H2
  P_csp   : pyrolysis-first, pressed kelp shipped to southern Spain, dried with CSP heat
  A_self  : AD-first, no pyrolysis; biomethane runs vessels and CHP, remainder exported
  AP_grid : AD-first, then digestate pyrolysis + hydrotreating (biochar returned to digester),
            external renewable electricity for drying and H2
Energy in GJ (LHV) per dry tonne; electricity in MWh per dry tonne; money in EUR per dry tonne.
"""
from dataclasses import dataclass, field, asdict, replace
import json

LHV_CH4_NM3 = 35.8e-3   # GJ per Nm3
LHV_H2 = 0.120          # GJ per kg
LHV_FUEL = 0.043        # GJ per kg hydrocarbon fuel


@dataclass
class P:
    # biomass
    yield_t_ha: float = 15.0          # t dry / ha / yr
    dm_harvest: float = 0.13          # dry-matter fraction at harvest
    ash: float = 0.30
    hhv: float = 13.5                 # GJ/t dry
    c_frac: float = 0.27              # carbon, fraction of dry mass
    n_frac: float = 0.020             # nitrogen, fraction of dry mass
    # marine operations (energy at the engine shaft expressed as fuel energy, GJ/t dry)
    harvest_fuel: float = 0.35        # harvesting, seeding, maintenance vessels
    transport_km: float = 40.0        # farm to port, one way
    transport_mj_tkm: float = 0.25    # small coaster, laden; empty return adds 60%
    skysails_saving: float = 0.10     # fraction of transit fuel saved by kite (10-15% measured on Beluga)
    # dewatering and drying
    dm_pressed: float = 0.25
    pressate_vs_frac: float = 0.12    # share of VS that leaves with the pressate (mannitol, laminarin)
    dm_dried: float = 0.90
    dryer_gj_per_t_water: float = 2.9
    dryer_fan_mwh_per_t_water: float = 0.03
    heat_pump_cop: float = 3.0
    # pyrolysis (per t dry feed)
    oil_org: float = 0.22             # organic bio-oil
    oil_hhv: float = 27.0             # GJ/t organic oil
    char: float = 0.35
    char_c: float = 0.25              # carbon fraction of kelp char (ash-rich)
    char_lhv: float = 9.0
    gas: float = 0.20
    gas_lhv: float = 6.0
    aq_cod: float = 0.05              # dissolved organics in aqueous phase (t COD / t dry)
    pyro_heat: float = 1.3            # GJ/t dry feed
    pyro_el: float = 0.08             # MWh/t dry feed
    # hydrotreating
    ht_yield: float = 0.42            # t hydrocarbon fuel / t organic oil
    h2_per_oil: float = 0.05          # t H2 / t organic oil
    ht_el: float = 0.03               # MWh/t dry feed (scaled)
    electrolysis_mwh_per_kg: float = 0.055
    jet_share: float = 0.35           # energy share of hydrotreated product in the jet cut
    # anaerobic digestion
    ch4_nm3_kgvs: float = 0.24        # whole kelp, continuous digestion (BMP up to 0.34)
    pressate_ch4_nm3_kgvs: float = 0.30
    aq_ch4_nm3_kgcod: float = 0.25
    biochar_uplift: float = 0.10      # +16-17% reported in batch tests; half-credited centrally
    co2_to_ch4: float = 0.82          # Nm3 CO2 per Nm3 CH4 in kelp biogas (~45:55)
    ad_el: float = 0.05               # MWh/t dry (maceration, mixing, pumping)
    upgrade_kwh_nm3_biogas: float = 0.25
    digester_heat: float = 0.40       # GJ/t dry after heat recovery
    vs_destroyed_per_biogas_mass: float = 0.88
    digestate_ash_to_solids: float = 0.40
    digestate_oil: float = 0.18       # organic oil yield from digestate pyrolysis
    digestate_char: float = 0.40
    digestate_char_c: float = 0.35
    # CHP
    chp_el: float = 0.38
    chp_heat: float = 0.45
    smr_eff: float = 0.70             # H2 from biomethane (self-sufficient mode)
    # CSP drying in the south
    csp_ship_km: float = 1100.0       # Galicia -> Huelva/Cadiz by sea
    csp_ship_mj_tkm: float = 0.12
    # costs (EUR per t dry unless stated)
    biomass_cost: float = 300.0       # delivered to port
    press_cost: float = 15.0
    dryer_cost: float = 35.0
    pyro_ht_cost: float = 110.0       # pyrolysis + hydrotreating, annualised capex + O&M
    ad_cost: float = 70.0             # AD + upgrading, annualised capex + O&M
    dig_pyro_cost: float = 55.0       # digestate drying + pyrolysis + hydrotreating
    csp_heat_eur_mwh: float = 45.0
    csp_ship_eur_t_wet: float = 15.0
    nutrient_credit_ad: float = 20.0  # liquid digestate N/K value
    nutrient_credit_p: float = 8.0
    biochar_credit_eur_tco2: float = 0.0


def marine(p, electric=False):
    wet = 1 / p.dm_harvest
    transit = wet * p.transport_km * p.transport_mj_tkm * 1.6 / 1000 * (1 - p.skysails_saving)
    fuel = p.harvest_fuel + transit
    return {"wet_t": wet, "fuel_gj": fuel, "skysails_saved_gj": transit / (1 - p.skysails_saving) * p.skysails_saving,
            "el_mwh": fuel * 0.40 / 0.90 / 3.6 if electric else 0.0}


def drying(p, dry_mass=1.0):
    water = dry_mass * ((1 / p.dm_pressed - 1) - (1 / p.dm_dried - 1))
    return water, water * p.dryer_gj_per_t_water, water * p.dryer_fan_mwh_per_t_water


def pyrolysis_first(p, mode):
    """mode in {'self', 'grid', 'csp'}."""
    vs = 1 - p.ash
    m = marine(p)
    feed = 1.0  # pressate VS is lost from the solids but small; treat feed mass ~1 t dry
    water, dry_heat, dry_fan = drying(p, feed)
    oil = p.oil_org * feed
    fuel_t = oil * p.ht_yield
    liquids = fuel_t * 1000 * LHV_FUEL                         # GJ
    h2_kg = oil * p.h2_per_oil * 1000
    gas_heat = p.gas * p.gas_lhv
    pyro_deficit = max(0.0, p.pyro_heat - gas_heat)
    ch4_nm3 = (p.pressate_vs_frac * vs * 1000 * p.pressate_ch4_nm3_kgvs + p.aq_cod * 1000 * p.aq_ch4_nm3_kgcod) \
        * (1 + p.biochar_uplift)
    ch4 = ch4_nm3 * LHV_CH4_NM3
    biogas_nm3 = ch4_nm3 * (1 + p.co2_to_ch4)
    co2_t = ch4_nm3 * p.co2_to_ch4 * 1.977e-3
    el_base = 0.015 + dry_fan + p.pyro_el + p.ht_el + 0.3 * p.ad_el + biogas_nm3 * p.upgrade_kwh_nm3_biogas / 1000
    char_c_t = p.char * p.char_c
    out = dict(route=f"P_{mode}", liquids_gj=liquids, jet_gj=liquids * p.jet_share, ch4_gross_gj=ch4,
               co2_bio_t=co2_t, char_c_t=char_c_t, h2_kg=h2_kg, marine_fuel_gj=m["fuel_gj"],
               skysails_saved_gj=m["skysails_saved_gj"], drying_heat_gj=dry_heat, water_evap_t=water)
    if mode == "self":
        # biomethane covers vessels, pyrolysis deficit, SMR hydrogen and electricity via CHP;
        # drying heat from CHP waste heat, then burning char, then burning bio-oil
        need_ch4 = m["fuel_gj"] + pyro_deficit + h2_kg * LHV_H2 / p.smr_eff
        chp_ch4 = el_base * 3.6 / p.chp_el
        need_ch4 += chp_ch4
        chp_heat = chp_ch4 * p.chp_heat
        heat_gap = max(0.0, dry_heat + 0.3 * p.digester_heat - chp_heat)
        char_burn = min(heat_gap, p.char * p.char_lhv * 0.85)
        heat_gap -= char_burn
        ch4_gap = max(0.0, need_ch4 - ch4)
        oil_burn = heat_gap / 0.85 + ch4_gap        # GJ of bio-oil-derived energy diverted
        net_liq = liquids - oil_burn * (liquids / (oil * p.oil_hhv))  # convert raw-oil GJ to product GJ
        out.update(net_liquids_gj=max(net_liq, 0.0), net_ch4_gj=max(ch4 - need_ch4, 0.0), el_import_mwh=0.0,
                   csp_heat_mwh=0.0, char_c_t=0.0 if char_burn > 0 else char_c_t,
                   note="char burned for drying" if char_burn > 0 else "",
                   self_sufficient_deficit_gj=heat_gap + ch4_gap)
        cost = p.biomass_cost + p.press_cost + p.dryer_cost + p.pyro_ht_cost + 0.4 * p.ad_cost - p.nutrient_credit_p
    elif mode == "grid":
        el = el_base + dry_heat / 3.6 / p.heat_pump_cop + h2_kg * p.electrolysis_mwh_per_kg
        # biomethane: vessels first, pyrolysis deficit, digester heat; rest exported
        net_ch4 = ch4 - m["fuel_gj"] - pyro_deficit
        out.update(net_liquids_gj=liquids, net_ch4_gj=net_ch4, el_import_mwh=el, csp_heat_mwh=0.0)
        cost = p.biomass_cost + p.press_cost + p.dryer_cost + p.pyro_ht_cost + 0.4 * p.ad_cost - p.nutrient_credit_p
    elif mode == "csp":
        wet_pressed = 1 / p.dm_pressed
        ship_fuel = wet_pressed * p.csp_ship_km * p.csp_ship_mj_tkm * 1.3 / 1000 * (1 - p.skysails_saving)
        el = el_base + h2_kg * p.electrolysis_mwh_per_kg
        net_ch4 = ch4 - m["fuel_gj"] - pyro_deficit - ship_fuel
        out.update(net_liquids_gj=liquids, net_ch4_gj=net_ch4, el_import_mwh=el, csp_heat_mwh=dry_heat / 3.6,
                   csp_ship_fuel_gj=ship_fuel)
        cost = (p.biomass_cost + p.press_cost + 0.6 * p.dryer_cost + p.pyro_ht_cost + 0.4 * p.ad_cost
                - p.nutrient_credit_p + dry_heat / 3.6 * p.csp_heat_eur_mwh + wet_pressed * p.csp_ship_eur_t_wet)
    cost -= out["char_c_t"] * 44 / 12 * p.biochar_credit_eur_tco2
    out["cost_eur"] = cost
    return out


def ad_first(p, pyrolyse_digestate, self_sufficient):
    vs = 1 - p.ash
    m = marine(p)
    uplift = p.biochar_uplift if pyrolyse_digestate else 0.0
    ch4_nm3 = vs * 1000 * p.ch4_nm3_kgvs * (1 + uplift)
    co2_nm3 = ch4_nm3 * p.co2_to_ch4
    biogas_mass = (ch4_nm3 * 0.717 + co2_nm3 * 1.977) / 1000
    vs_left = max(vs - biogas_mass * p.vs_destroyed_per_biogas_mass, 0.05)
    dig_dry = vs_left + p.ash * p.digestate_ash_to_solids
    ch4 = ch4_nm3 * LHV_CH4_NM3
    el = p.ad_el + ch4_nm3 * (1 + p.co2_to_ch4) * p.upgrade_kwh_nm3_biogas / 1000
    heat = p.digester_heat
    liquids, h2_kg, char_c, dry_heat = 0.0, 0.0, 0.0, 0.0
    if pyrolyse_digestate:
        water, dry_heat, fan = drying(p, dig_dry)
        oil = dig_dry * p.digestate_oil
        liquids = oil * p.ht_yield * 1000 * LHV_FUEL
        h2_kg = oil * p.h2_per_oil * 1000
        char_c = dig_dry * p.digestate_char * p.digestate_char_c
        el += fan + dig_dry * (p.pyro_el + p.ht_el)
    out = dict(route="AP_grid" if pyrolyse_digestate else ("A_self" if self_sufficient else "A_grid"),
               liquids_gj=liquids, jet_gj=liquids * p.jet_share, ch4_gross_gj=ch4, co2_bio_t=co2_nm3 * 1.977e-3,
               char_c_t=char_c, h2_kg=h2_kg, marine_fuel_gj=m["fuel_gj"], skysails_saved_gj=m["skysails_saved_gj"],
               digestate_dry_t=dig_dry, drying_heat_gj=dry_heat)
    if self_sufficient:
        chp_ch4 = el * 3.6 / p.chp_el
        heat_gap = max(0.0, heat - chp_ch4 * p.chp_heat)
        need = m["fuel_gj"] + chp_ch4 + heat_gap / 0.9
        out.update(net_liquids_gj=liquids, net_ch4_gj=ch4 - need, el_import_mwh=0.0, csp_heat_mwh=0.0,
                   chp_ch4_gj=chp_ch4)
    else:
        el_total = el + dry_heat / 3.6 / p.heat_pump_cop + h2_kg * p.electrolysis_mwh_per_kg + heat / 3.6 / p.heat_pump_cop
        out.update(net_liquids_gj=liquids, net_ch4_gj=ch4 - m["fuel_gj"], el_import_mwh=el_total, csp_heat_mwh=0.0)
    cost = p.biomass_cost + p.ad_cost - p.nutrient_credit_ad + (p.dig_pyro_cost if pyrolyse_digestate else 0.0)
    cost -= char_c * 44 / 12 * p.biochar_credit_eur_tco2
    out["cost_eur"] = cost
    return out


def all_routes(p):
    return {r["route"]: r for r in (pyrolysis_first(p, "self"), pyrolysis_first(p, "grid"),
                                     pyrolysis_first(p, "csp"), ad_first(p, False, True),
                                     ad_first(p, False, False), ad_first(p, True, False))}


# ------------------------------------------------------------- co-location with floating wind
@dataclass
class Coloc:
    turbine_mw: float = 15.0
    rotor_m: float = 236.0
    spacing_d: float = 7.0
    depth_m: float = 400.0
    mooring_radius_per_depth: float = 1.75    # semi-taut synthetic moorings
    mooring_lines: int = 3
    line_clearance_m: float = 100.0            # each side of a mooring line
    platform_keepout_m: float = 150.0
    cable_corridor_m: float = 200.0            # inter-array dynamic cable corridor along each turbine row
    access_lane_m: float = 100.0               # O&M vessel lane per row
    wind_cf: float = 0.42
    kelp_mooring_cost_factor: float = 1.30     # deeper moorings for kelp grids (200-1,000 m)
    shared_om_factor: float = 0.90             # shared port, vessels, monitoring, lease
    usable_override: float | None = None


def colocation(c: Coloc):
    s = c.spacing_d * c.rotor_m / 1000                       # km
    cell = s * s
    r = c.depth_m * c.mooring_radius_per_depth / 1000
    excl = (c.mooring_lines * r * 2 * c.line_clearance_m / 1000
            + 3.1416 * (c.platform_keepout_m / 1000) ** 2
            + s * (c.cable_corridor_m + c.access_lane_m) / 1000)
    usable = c.usable_override if c.usable_override is not None else max(0.0, 1 - excl / cell)
    mw_km2 = c.turbine_mw / cell
    return dict(spacing_km=s, cell_km2=cell, mooring_radius_km=r, excluded_km2_per_turbine=excl,
                usable_frac=usable, mw_per_km2=mw_km2, gwh_per_km2=mw_km2 * c.wind_cf * 8.76,
                kelp_cost_factor=c.kelp_mooring_cost_factor * c.shared_om_factor)


if __name__ == "__main__":
    p = P()
    res = all_routes(p)
    col = colocation(Coloc())
    for k, v in res.items():
        print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
    print("coloc", {a: round(b, 3) for a, b in col.items()})
    json.dump({"params": asdict(p), "routes": res, "colocation": col},
              open("outputs/cascade_per_dry_tonne.json", "w"), indent=1)
