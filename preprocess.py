"""Offshore pre-processing of harvested kelp before shipping to the biorefinery (per dry tonne).

Options
  wet          ship as harvested (13% dry matter, 7.7 t wet per dry t); ensiled at the refinery
  press        screw press on the harvester or a platform to 25% DM; press liquor (half the mannitol, salts)
               returned to the sea; electricity from the offshore wind farm
  press_hpdry  press, then belt-dry to 90% DM in electric heat-pump dryers on an offshore platform
               (offshore wind power); dry kelp stores without ensiling
  press_wwdry  press, then belt-dry to 90% DM with turbine waste heat (40-60 C glycol loops, about 6% of
               turbine output) piped to a drying platform inside the wind farm; capped by the heat the
               offshore turbines actually reject
  press_fan    press, then fan-assisted ambient-air drying to 40% DM on platform drying beds
HTL, fermentation and digestion all need a wet slurry (~15% solids), so any water removed by drying is
added back at the refinery; drying only saves shipping mass and ensiling.
"""
from dataclasses import dataclass, asdict

WATER_LATENT_GJ_T = 2.9      # belt dryer heat per tonne of water evaporated (convective)


@dataclass
class Pre:
    dm_harvest: float = 0.13
    dm_press: float = 0.25
    dm_dry: float = 0.90
    dm_fan: float = 0.40
    press_cost: float = 6.0              # EUR/t dw, press on harvester (capital + O&M)
    press_el_mwh: float = 0.02
    press_mannitol_loss: float = 0.5     # share of mannitol lost with the press liquor
    press_vs_loss_other: float = 0.03    # other organics lost (affects HTL/AD yields)
    hp_kwh_per_t_water: float = 220.0    # heat-pump dryer, electricity per tonne water evaporated
    dryer_platform_cost: float = 60.0    # EUR/t dw, offshore belt-dryer platform (capital + O&M)
    ww_heat_cost: float = 25.0           # EUR/MWh_th collected turbine waste heat delivered on the platform
    ww_fan_mwh: float = 0.05
    fan_mwh_per_t_water: float = 0.10
    fan_platform_cost: float = 70.0      # EUR/t dw, drying beds on offshore platforms
    offshore_el_cost: float = 100.0      # EUR/MWh, floating offshore wind at the farm (no grid)
    ensile_cost: float = 20.0            # avoided when the kelp is dried
    transport_eur_t_wet_km: float = 0.02


def options(p: Pre = Pre()):
    wet = 1 / p.dm_harvest
    pressed = 1 / p.dm_press
    dried = 1 / p.dm_dry
    fan = 1 / p.dm_fan
    w_dry = pressed - dried
    w_fan = pressed - fan
    o = {}
    o["wet"] = dict(mass_t=wet, cost=0.0, el_mwh=0.0, ww_heat_mwh=0.0, mannitol_keep=1.0, vs_keep=1.0, ensile=True)
    base_press = dict(cost=p.press_cost + p.press_el_mwh * p.offshore_el_cost, el_mwh=p.press_el_mwh,
                      mannitol_keep=1 - p.press_mannitol_loss, vs_keep=1 - p.press_vs_loss_other)
    o["press"] = dict(mass_t=pressed, ww_heat_mwh=0.0, ensile=True, **base_press)
    el_hp = w_dry * p.hp_kwh_per_t_water / 1000
    o["press_hpdry"] = dict(mass_t=dried, ww_heat_mwh=0.0, ensile=False,
                            **{**base_press, "cost": base_press["cost"] + p.dryer_platform_cost + el_hp * p.offshore_el_cost - p.ensile_cost,
                               "el_mwh": base_press["el_mwh"] + el_hp})
    heat = w_dry * WATER_LATENT_GJ_T / 3.6
    o["press_wwdry"] = dict(mass_t=dried, ww_heat_mwh=heat, ensile=False,
                            **{**base_press, "cost": base_press["cost"] + p.dryer_platform_cost + heat * p.ww_heat_cost
                               + p.ww_fan_mwh * p.offshore_el_cost - p.ensile_cost,
                               "el_mwh": base_press["el_mwh"] + p.ww_fan_mwh})
    el_fan = w_fan * p.fan_mwh_per_t_water
    o["press_fan"] = dict(mass_t=fan, ww_heat_mwh=0.0, ensile=True,
                          **{**base_press, "cost": base_press["cost"] + p.fan_platform_cost + el_fan * p.offshore_el_cost,
                             "el_mwh": base_press["el_mwh"] + el_fan})
    return o


if __name__ == "__main__":
    p = Pre()
    for k, v in options(p).items():
        print(k, {a: round(b, 3) if isinstance(b, float) else b for a, b in v.items()})
    for km in (60, 150, 285):
        print(km, {k: round(v["cost"] + v["mass_t"] * km * p.transport_eur_t_wet_km
                           - options(p)["wet"]["mass_t"] * km * p.transport_eur_t_wet_km, 1) for k, v in options(p).items()})
