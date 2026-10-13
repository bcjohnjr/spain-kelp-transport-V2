"""Least-cost low-carbon supply for all Spanish transport, with nuclear biorefineries and deep-ocean kelp.

Annual linear programme (scipy/HiGHS). Units: TWh/yr, km2, Mt, EUR.
Demand: 2025 fossil transport energy by segment (CORES 2025; bunkers from CORES 2026 monthly data; Adif rail).
End uses: battery-electric, drop-in liquid (renewable diesel / jet), ethanol (E100, ED95), methane,
methanol, ammonia. A 'liquid-required' switch forces aviation and heavy off-road equipment onto drop-in
liquids and at least half of heavy trucks onto liquid fuel (drop-in or ED95).
Supply: PV, onshore wind, floating offshore wind, CSP, existing nuclear life extension, new nuclear
(electricity and process steam), kelp farms on the shelf, slope and deep ocean (nutrients from natural supply,
depth cycling or pumped upwelling), nuclear kelp biorefineries (ethanol + HTL diesel/jet + biomethane +
fertiliser), ethanol-to-jet, waste/residue fuels, e-fuels, DAC and biogenic CO2.
Costs are 2026 EUR, pre-tax, energy supply only; vehicle and engine capital are excluded.
"""
import copy
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

from deep_farm import ZONES, FarmCost, farm_cost
from nuclear_refinery import Feed, Proc, routes as refinery_routes
from preprocess import Pre, options as preprocess_options
from lifecycle import screening_lifecycle

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TWH_PER_PJ = 1 / 3.6
GJ2TWH = 1 / 3.6e6


def demand(scope="all"):
    d = {"ldv_gasoline": 7.029162 * 43.4 * TWH_PER_PJ,
         "ldv_diesel": 0.52 * 22.054903 * 43.0 * TWH_PER_PJ,
         "hdv": 0.48 * 22.054903 * 43.0 * TWH_PER_PJ,
         "offroad": 3.80 * 43.0 * TWH_PER_PJ,
         "aviation": 7.744288 * 43.2 * TWH_PER_PJ,
         "shipping": 9.40 * 41.0 * TWH_PER_PJ + 3.8,
         "rail_el": 2.4}
    if scope == "domestic":
        d["aviation"] *= 0.22
        d["shipping"] *= 0.10
    if scope == "inland":
        d["aviation"] = d["shipping"] = 0.0
    return d


CO2_T_PER_MWH = {"ldv_gasoline": 0.249, "ldv_diesel": 0.267, "hdv": 0.267, "offroad": 0.267,
                 "aviation": 0.257, "shipping": 0.275, "rail_el": 0.0}
FOSSIL = {"oct2026": {"ldv_gasoline": 141, "ldv_diesel": 141, "hdv": 141, "offroad": 131, "aviation": 89, "shipping": 56},
          "avg2025": {"ldv_gasoline": 88, "ldv_diesel": 82, "hdv": 82, "offroad": 75, "aviation": 52, "shipping": 40}}

# segment -> option: (carrier, MWh carrier per MWh fossil replaced, max share, extra EUR/MWh carrier, liquid fuel?)
OPTIONS = {
    "ldv_gasoline": {"bev": ("el_direct", 0.31, 1.0, 45, False), "liq": ("dropin", 1.0, 1.0, 15, True),
                     "e100": ("ethanol", 1.0, 1.0, 15, True)},
    "ldv_diesel": {"bev": ("el_direct", 0.375, 1.0, 45, False), "liq": ("dropin", 1.0, 1.0, 15, True)},
    "hdv": {"bet": ("el_direct", 0.53, 0.90, 35, False), "lng": ("methane", 1.15, 0.50, 13, False),
            "liq": ("dropin", 1.0, 1.0, 15, True), "ed95": ("ethanol", 1.05, 0.50, 20, True)},
    "offroad": {"el": ("el_direct", 0.45, 0.40, 30, False), "cng": ("methane", 1.10, 0.30, 10, False),
                "liq": ("dropin", 1.0, 1.0, 15, True)},
    "aviation": {"jet": ("jet", 1.0, 1.0, 5, True)},
    "shipping": {"meoh": ("methanol", 1.0, 1.0, 5, True), "nh3": ("ammonia", 1.05, 0.50, 8, True),
                 "lng": ("methane", 1.0, 0.40, 8, False), "liq": ("dropin", 1.0, 1.0, 5, True)},
    "rail_el": {"el": ("el_direct", 1.0, 1.0, 0, False)},
}

UNIT_CAPEX = {
    "PV (EUR/kW)": 450, "Onshore wind (EUR/kW)": 1150, "Offshore wind (EUR/kW)": 3000, "CSP (EUR/kW)": 4500,
    "Nuclear new (EUR/kW)": 8000, "Nuclear life extension (EUR/kW)": 1000, "Electrolysers (EUR/kW)": 1000,
    "E-fuel synthesis (EUR/kW fuel)": 900, "DAC (EUR per t/yr)": 1500, "Kelp farm shelf (EUR/km2)": 2.0e6,
    "Kelp farm deep (EUR/km2)": 3.6e6, "Biorefinery (EUR per t dw/yr)": 1650, "Vessel (EUR each)": 60e6,
    "ATJ plant (EUR/kW jet)": 900, "Charging and grid (EUR bn per TWh/yr of EV load)": 0.35,
}


def base_params():
    return dict(
        pv=dict(lcoe=33, cf=0.205, cap_gw=300, mw_km2=50),
        onshore=dict(lcoe=45, cf=0.27, cap_gw=60, mw_km2=4),
        offshore=dict(lcoe=100, cf=0.40, area_km2=4947, mw_km2=5.5),
        csp=dict(lcoe=105, cf=0.45, cap_gw=25, mw_km2=30),
        nuc_ext=dict(lcoe=60, cf=0.88, cap_gw=7.1),
        nuc_new=dict(lcoe=120, cf=0.90, cap_gw=100, heat_el_loss=0.30, unit_gw=1.1),
        adder=dict(pv_day=8, pv_shift=55, onshore=15, offshore=12, csp=0, nuclear=5, network_direct=20,
                   network_flex=8, pv_day_share=0.45, flex_pv=30, flex_onshore=18, flex_offshore=6,
                   flex_csp=5, flex_nuclear=0),
        heat=dict(hp_cop=2.5, hp_max_share=0.6, eboiler_eff=0.99),
        eft=dict(el=2.40, cost=110, co2=0.30),
        emeoh=dict(el=1.90, cost=60, co2=0.25),
        enh3=dict(el=1.75, cost=50),
        ech4=dict(el=1.80, cost=55, co2=0.20),
        atj=dict(eff=0.925, cost=45),
        biomeoh=dict(ch4_per_meoh=1.5, cost=25),
        dac=dict(el=1.5, cost=300),
        bio_co2_other=dict(cap=6.0, cost=90),
        kelp_co2_capture=20.0,
        waste_ch4=dict(cap=25, cost=80, co2=0.20),
        hefa=dict(cap=12.0, cost=164),     # HVO/HEFA from waste lipids: Repsol Cartagena + Moeve Huelva capacity (~1 Mt/yr)
        fame=dict(cap=10.3, cost=136, blend_max=0.30),  # existing FAME biodiesel (2024: ~84% wastes/residues)
        crop_etoh=dict(cap=1.5, cost=108),  # existing crop bioethanol (corn, cane), held at today's volume
        cement_co2=dict(cap=0.0, cost=60),  # cement process CO2 (concentrated stream); EU RFNBO-eligible only to 2040
        wind_heat=dict(reach=0.0, loss_frac=0.06, cost=35, booster_el=0.20, lowtemp_share=0.36),
        allow_efuels=True,
        residue_ft=dict(cap=30, cost=170),
        fert=dict(price={"n": 1.30, "p": 2.6, "k": 0.65}, cap_mt={"n": 1.0, "p": 0.17, "k": 0.33}, export_share=0.6),
        farm=asdict(FarmCost()),
        nutrient_methods=("depth_cycling", "solar_pipe", "wave_pump", "wave_pump_xl", "salt_fountain"),
        area_share={"nor_shelf": 0.10, "nor_slope": 0.10, "nor_deep": 0.25, "can_deep": 0.25, "med_deep": 0.25},
        refinery_routes=("NUC_EH", "NUC_H", "NUC_A"),
        proc=asdict(Proc()),
        fleet=dict(harvest_gj=0.35, mj_tkm_near=0.15, mj_tkm_far=0.12, skysails_near=0.10, skysails_far=0.15),
        liquid_required=False,
        kelp_supplies_liquids=False,
        refinery_nuclear_only=False,      # all biorefinery steam and electricity from new nuclear plants
        allow_kelp=True,
        allow_new_nuclear=True,
        scope="all",
        # Part of any aviation demand reduction is a shift of domestic flights to high-speed rail. The shifted
        # fuel is a fixed fraction of domestic jet fuel (mainland routes, assumed) and the replacement trains
        # draw traction electricity per MWh of jet fuel avoided (EEA 2020, Train or plane?; upper end used).
        rail_shift=dict(domestic_share=0.22, shifted_domestic_frac=1 / 3, el_per_fuel=0.20),
    )


class LP:
    def __init__(self):
        self.names, self.cost, self.bounds, self.ub, self.eq = [], [], [], [], []

    def var(self, name, cost=0.0, lb=0.0, ub=None):
        self.names.append(name); self.cost.append(cost); self.bounds.append((lb, ub))
        return len(self.names) - 1

    def le(self, co, rhs, tag=None):
        self.ub.append((co, rhs, tag))

    def eqc(self, co, rhs, tag=None):
        self.eq.append((co, rhs, tag))

    def solve(self):
        n = len(self.names)
        def mat(rows):
            A = np.zeros((len(rows), n)); b = np.zeros(len(rows))
            for i, (co, rhs, _) in enumerate(rows):
                for j, v in co.items():
                    A[i, j] += v
                b[i] = rhs
            return A, b
        Au, bu = mat(self.ub); Ae, be = mat(self.eq)
        res = linprog(np.array(self.cost), A_ub=Au, b_ub=bu, A_eq=Ae, b_eq=be, bounds=self.bounds, method="highs")
        if res.status != 0:
            raise RuntimeError(res.message)
        duals = {}
        for i, (_, _, tag) in enumerate(self.ub):
            if tag: duals[tag] = -res.ineqlin.marginals[i]
        for i, (_, _, tag) in enumerate(self.eq):
            if tag: duals[tag] = -res.eqlin.marginals[i]
        return dict(zip(self.names, res.x)), res.fun, duals


def add(d, k, v):
    d[k] = d.get(k, 0.0) + v


def kelp_systems(prm):
    """Enumerate (zone, distance band, refinery route) with the cheapest allowed nutrient method."""
    saved = {k: z.yield_t_ha for k, z in ZONES.items()}
    try:
        for k, y in prm.get("zone_yield", {}).items():
            ZONES[k].yield_t_ha = y
        return _kelp_systems(prm)
    finally:
        for k, y in saved.items():
            ZONES[k].yield_t_ha = y


def _kelp_systems(prm):
    fc = FarmCost(**prm["farm"])
    proc = Proc(**prm["proc"])
    fl = prm["fleet"]
    systems = []
    for zk, z in ZONES.items():
        feed = Feed() if zk.startswith("nor") else Feed(carb_factor=z.carb_factor, n=z.n_frac)
        rts = refinery_routes(feed, proc)
        for band in z.area_km2:
            best = None
            for m in prm["nutrient_methods"]:
                fcost = farm_cost(zk, band, fc, m)
                if fcost["total_eur_t"] == float("inf"):
                    continue
                if best is None or fcost["total_eur_t"] < best["total_eur_t"]:
                    best = fcost
            if best is None:
                continue
            t_km2 = best["yield_t_ha"] * 100
            km = z.mid_km[band]
            far = km > 100
            wet = 1 / fc.dm_harvest
            transit = wet * km * (fl["mj_tkm_far"] if far else fl["mj_tkm_near"]) * 1.6 / 1000
            sky = fl["skysails_far"] if far else fl["skysails_near"]
            pre_opts = preprocess_options(Pre(**prm.get("pre", {})))
            for pk in prm.get("preprocess", ("wet",)):
                po = pre_opts[pk]
                mass_ratio = po["mass_t"] / wet
                transport_new = po["mass_t"] * max(km - 40, 0) * fc.transport_eur_t_wet_km
                farm_eur = best["total_eur_t"] - best["transport_eur_t"] + transport_new + po["cost"]
                pproc = Proc(**{**prm["proc"], **({} if po["ensile"] else {"ensile_sugar_loss": 0.0})})
                pfeed = Feed(**{**asdict(feed), "mannitol": feed.mannitol * po["mannitol_keep"]})
                rts_p = refinery_routes(pfeed, pproc)
                for r in prm["refinery_routes"]:
                    rr = dict(rts_p[r])
                    if r != "NUC_EH":
                        for kk in ("hc_gj", "jet_gj", "ch4_gj", "co2_ferm_t"):
                            rr[kk] *= po["vs_keep"]
                    else:
                        for kk in ("hc_gj", "jet_gj", "ch4_gj"):
                            rr[kk] *= po["vs_keep"]
                    ref_cost = (rr["cost_eur"] - (0.0 if po["ensile"] else pproc.cost_ensile)) * prm.get("refinery_cost_mult", 1.0)
                    systems.append(dict(
                        key=f"{zk}|{band}|{r}|{pk}", zone=zk, band=band, route=r, pre=pk, method=best["method"],
                        area_cap=z.area_km2[band] * prm["area_share"][zk], t_km2=t_km2,
                        farm_eur_t=farm_eur, refinery_eur_t=ref_cost,
                        fleet_gj_t=fl["harvest_gj"] + transit * mass_ratio * (1 - sky), skysails_saved_gj_t=transit * mass_ratio * sky,
                        ethanol_gj=rr["ethanol_gj"], hc_gj=rr["hc_gj"], jet_gj=rr["jet_gj"], ch4_gj=rr["ch4_gj"],
                        el_mwh=rr["el_mwh"], heat_mwh=rr["heat_mwh_th"], co2_t=rr["co2_ferm_t"],
                        fert=(rr["fert_n_kg"], rr["fert_p_kg"], rr["fert_k_kg"]), fert_energy_gj=rr["fert_energy_gj"],
                        fert_co2_t=rr["fert_co2_t"], units_km2=best["units_per_km2"],
                        deep_water_m3_t=best["deep_water_m3_per_t_dw"], ww_heat_mwh_t=po["ww_heat_mwh"],
                        pre_el_mwh_t=po["el_mwh"], wet_mass_t=po["mass_t"]))
    return systems


def solve(prm):
    d = demand(prm["scope"])
    av0 = d["aviation"]
    for k, m in prm.get("demand_mult", {}).items():
        d[k] *= m
    # Electricity for flights replaced by high-speed rail (only when aviation demand is reduced).
    rs = prm.get("rail_shift", {})
    shifted = min(rs.get("shifted_domestic_frac", 0.0) * rs.get("domestic_share", 0.0) * demand("all")["aviation"],
                  max(av0 - d["aviation"], 0.0))
    d["rail_el"] += shifted * rs.get("el_per_fuel", 0.0)
    lp = LP()
    a = prm["adder"]
    G = {}
    for t, lc, add_dir, add_flex in (("pv", prm["pv"]["lcoe"], None, a["flex_pv"]),
                                     ("onshore", prm["onshore"]["lcoe"], a["onshore"], a["flex_onshore"]),
                                     ("offshore", prm["offshore"]["lcoe"], a["offshore"], a["flex_offshore"]),
                                     ("csp", prm["csp"]["lcoe"], a["csp"], a["flex_csp"]),
                                     ("nuc_ext", prm["nuc_ext"]["lcoe"], a["nuclear"], a["flex_nuclear"]),
                                     ("nuc_new", prm["nuc_new"]["lcoe"], a["nuclear"], a["flex_nuclear"])):
        if t == "pv":
            G["pv_day"] = lp.var("pv_direct_day", lc + a["pv_day"] + a["network_direct"])
            G["pv_shift"] = lp.var("pv_direct_shifted", lc + a["pv_shift"] + a["network_direct"])
        else:
            G[t + "_dir"] = lp.var(f"{t}_direct", lc + add_dir + a["network_direct"])
        G[t + "_flex"] = lp.var(f"{t}_flex", lc + add_flex + a["network_flex"])
    G["nuc_new_steamloss"] = lp.var("nuc_new_steam_el_forgone", prm["nuc_new"]["lcoe"])
    if not prm["allow_new_nuclear"]:
        for k in ("nuc_new_dir", "nuc_new_flex", "nuc_new_steamloss"):
            lp.bounds[G[k]] = (0, 0)
    heat_nuc = lp.var("heat_nuclear_steam")
    heat_hp = lp.var("heat_heat_pump")
    heat_eb = lp.var("heat_electric_boiler")

    systems = kelp_systems(prm)
    K = {s["key"]: lp.var("kelp_km2|" + s["key"], s["t_km2"] * (s["farm_eur_t"] + s["refinery_eur_t"]) / 1e6)
         for s in systems}
    zb = {}
    for s in systems:
        zb.setdefault((s["zone"], s["band"]), []).append(s)
    for ss in zb.values():
        lp.le({K[s["key"]]: 1.0 for s in ss}, ss[0]["area_cap"])

    F = {}
    F["eft"] = lp.var("eFT_liquids", prm["eft"]["cost"])
    F["emeoh"] = lp.var("e_methanol", prm["emeoh"]["cost"])
    F["enh3"] = lp.var("e_ammonia", prm["enh3"]["cost"])
    F["ech4"] = lp.var("e_methane", prm["ech4"]["cost"])
    F["atj"] = lp.var("ATJ_jet_from_ethanol", prm["atj"]["cost"])
    F["biomeoh"] = lp.var("bio_methanol_from_CH4", prm["biomeoh"]["cost"])
    F["waste_ch4"] = lp.var("waste_biomethane", prm["waste_ch4"]["cost"], 0, prm["waste_ch4"]["cap"])
    F["hefa"] = lp.var("HEFA_waste_lipids", prm["hefa"]["cost"], 0, prm["hefa"]["cap"])
    F["resft"] = lp.var("residue_FT", prm["residue_ft"]["cost"], 0, prm["residue_ft"]["cap"])
    F["fame"] = lp.var("FAME_biodiesel_existing", prm["fame"]["cost"], 0, prm["fame"]["cap"])
    F["cetoh"] = lp.var("crop_ethanol_existing", prm["crop_etoh"]["cost"], 0, prm["crop_etoh"]["cap"])
    F["cco2"] = lp.var("cement_CO2_Mt", prm["cement_co2"]["cost"], 0, prm["cement_co2"]["cap"])
    heat_ww = lp.var("heat_wind_turbine_waste", prm["wind_heat"]["cost"])
    F["dac"] = lp.var("DAC_CO2_Mt", prm["dac"]["cost"])
    F["bco2"] = lp.var("other_biogenic_CO2_Mt", prm["bio_co2_other"]["cost"], 0, prm["bio_co2_other"]["cap"])
    F["kco2"] = lp.var("kelp_CO2_used_Mt", prm["kelp_co2_capture"])
    F["wind_assist"] = lp.var("wind_assist_saving", 45.0, 0, prm.get("wind_assist_share", 0.08) * d["shipping"])
    fert = {}
    for nut in ("n", "p", "k"):
        pr = prm["fert"]["price"][nut] * 1000   # EUR/kg -> MEUR per Mt
        fert[nut + "_dom"] = lp.var(f"fert_{nut}_domestic_Mt", -pr, 0, prm["fert"]["cap_mt"][nut])
        fert[nut + "_exp"] = lp.var(f"fert_{nut}_export_Mt", -pr * prm["fert"]["export_share"])

    U = {}
    for sg, opts in OPTIONS.items():
        for o, (car, ratio, share, extra, liq) in opts.items():
            U[(sg, o)] = lp.var(f"use|{sg}|{o}", extra * ratio)
    for sg, opts in OPTIONS.items():
        co = {U[(sg, o)]: 1.0 for o in opts}
        if sg == "shipping":
            co[F["wind_assist"]] = 1.0
        lp.eqc(co, d[sg])
        for o, (car, ratio, share, extra, liq) in opts.items():
            cap = share
            if prm["liquid_required"]:
                if sg == "offroad" and not liq:
                    cap = 0.0
                if sg == "hdv" and o == "bet":
                    cap = 0.5
                if sg == "hdv" and o == "lng":
                    cap = 0.0
            if cap < 1.0:
                lp.le({U[(sg, o)]: 1.0}, cap * d[sg])
    if prm["liquid_required"]:
        lp.le({U[("hdv", "liq")]: -1.0, U[("hdv", "ed95")]: -1.0}, -0.5 * d["hdv"])

    def use(car):
        co = {}
        for (sg, o), i in U.items():
            if OPTIONS[sg][o][0] == car:
                add(co, i, OPTIONS[sg][o][1])
        return co

    co = use("dropin")
    for k, v in use("jet").items(): add(co, k, v)
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["hc_gj"] * GJ2TWH)
    for f in ("eft", "hefa", "resft", "atj", "fame"): add(co, F[f], -1.0)
    lp.le(co, 0.0, "dropin")
    co = {F["fame"]: 1.0}
    for sg in ("ldv_diesel", "hdv", "offroad", "shipping"):
        add(co, U[(sg, "liq")], -prm["fame"]["blend_max"])
    lp.le(co, 0.0)
    co = use("jet")
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["jet_gj"] * GJ2TWH)
    for f in ("eft", "hefa", "resft", "atj"): add(co, F[f], -1.0)
    lp.le(co, 0.0, "jet")
    co = use("ethanol"); add(co, F["atj"], 1 / prm["atj"]["eff"]); add(co, F["cetoh"], -1.0)
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["ethanol_gj"] * GJ2TWH)
    lp.le(co, 0.0, "ethanol")
    co = use("methane")
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * (s["ch4_gj"] - s["fleet_gj_t"]) * GJ2TWH)
    add(co, F["waste_ch4"], -1); add(co, F["ech4"], -1); add(co, F["biomeoh"], prm["biomeoh"]["ch4_per_meoh"])
    lp.le(co, 0.0, "methane")
    co = use("methanol"); add(co, F["emeoh"], -1); add(co, F["biomeoh"], -1); lp.le(co, 0.0, "methanol")
    co = use("ammonia"); add(co, F["enh3"], -1); lp.le(co, 0.0, "ammonia")
    lp.le({F["eft"]: prm["eft"]["co2"], F["emeoh"]: prm["emeoh"]["co2"], F["ech4"]: prm["ech4"]["co2"],
           F["dac"]: -1, F["bco2"]: -1, F["kco2"]: -1, F["cco2"]: -1, F["waste_ch4"]: -prm["waste_ch4"]["co2"]}, 0.0, "co2")
    co = {F["kco2"]: 1.0}
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["co2_t"] / 1e6)
    lp.le(co, 0.0)
    for j, nut in enumerate(("n", "p", "k")):
        co = {fert[nut + "_dom"]: 1.0, fert[nut + "_exp"]: 1.0}
        for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["fert"][j] / 1e9)
        lp.le(co, 0.0)
    co = {heat_nuc: -1.0, heat_hp: -1.0, heat_eb: -1.0, heat_ww: -1.0}
    for s in systems: add(co, K[s["key"]], s["t_km2"] * s["heat_mwh"] / 1e6)
    lp.le(co, 0.0, "heat")
    wh = prm["wind_heat"]
    co = {heat_ww: 1.0}
    for s in systems: add(co, K[s["key"]], -wh["lowtemp_share"] * s["t_km2"] * s["heat_mwh"] / 1e6)
    lp.le(co, 0.0)
    lp.le({heat_ww: 1.0, G["onshore_dir"]: -wh["loss_frac"] * wh["reach"], G["onshore_flex"]: -wh["loss_frac"] * wh["reach"]}, 0.0)
    co = {heat_hp: 1.0}
    for s in systems: add(co, K[s["key"]], -prm["heat"]["hp_max_share"] * s["t_km2"] * s["heat_mwh"] / 1e6)
    lp.le(co, 0.0)
    lp.eqc({G["nuc_new_steamloss"]: 1.0, heat_nuc: -prm["nuc_new"]["heat_el_loss"]}, 0.0)
    co = use("el_direct")
    for s in systems: add(co, K[s["key"]], s["t_km2"] * s["el_mwh"] / 1e6)
    add(co, heat_hp, 1 / prm["heat"]["hp_cop"]); add(co, heat_eb, 1 / prm["heat"]["eboiler_eff"])
    add(co, heat_ww, prm["wind_heat"]["booster_el"])
    for k in ("pv_day", "pv_shift", "onshore_dir", "offshore_dir", "csp_dir", "nuc_ext_dir", "nuc_new_dir"):
        add(co, G[k], -1.0)
    lp.eqc(co, 0.0, "el_direct")
    co = {F["eft"]: prm["eft"]["el"], F["emeoh"]: prm["emeoh"]["el"], F["enh3"]: prm["enh3"]["el"],
          F["ech4"]: prm["ech4"]["el"], F["dac"]: prm["dac"]["el"]}
    for k in ("pv_flex", "onshore_flex", "offshore_flex", "csp_flex", "nuc_ext_flex", "nuc_new_flex"):
        add(co, G[k], -1.0)
    lp.le(co, 0.0, "el_flex")
    co = {G["pv_day"]: 1.0}
    for k, v in use("el_direct").items(): add(co, k, -a["pv_day_share"] * v)
    lp.le(co, 0.0)

    def cap(keys, gw, cf):
        lp.le({G[k]: 1.0 for k in keys}, gw * cf * 8.76)
    cap(("pv_day", "pv_shift", "pv_flex"), prm["pv"]["cap_gw"], prm["pv"]["cf"])
    cap(("onshore_dir", "onshore_flex"), prm["onshore"]["cap_gw"], prm["onshore"]["cf"])
    cap(("offshore_dir", "offshore_flex"), prm["offshore"]["area_km2"] * prm["offshore"]["mw_km2"] / 1000, prm["offshore"]["cf"])
    cap(("csp_dir", "csp_flex"), prm["csp"]["cap_gw"], prm["csp"]["cf"])
    cap(("nuc_ext_dir", "nuc_ext_flex"), prm["nuc_ext"]["cap_gw"], prm["nuc_ext"]["cf"])
    cap(("nuc_new_dir", "nuc_new_flex", "nuc_new_steamloss"), prm["nuc_new"]["cap_gw"], prm["nuc_new"]["cf"])

    co = {G["offshore_dir"]: -prm["wind_heat"]["loss_frac"], G["offshore_flex"]: -prm["wind_heat"]["loss_frac"]}
    for s_ in systems: add(co, K[s_["key"]], s_["t_km2"] * s_.get("ww_heat_mwh_t", 0.0) / 1e6)
    lp.le(co, 0.0)
    if prm.get("ww_force"):
        # build all POEM offshore wind and use its waste heat for drying
        lp.le({G["offshore_dir"]: -1.0, G["offshore_flex"]: -1.0},
              -prm["offshore"]["area_km2"] * prm["offshore"]["mw_km2"] / 1000 * prm["offshore"]["cf"] * 8.76 * 0.999)
        co = {G["offshore_dir"]: prm["wind_heat"]["loss_frac"] * 0.999, G["offshore_flex"]: prm["wind_heat"]["loss_frac"] * 0.999}
        for s_ in systems: add(co, K[s_["key"]], -s_["t_km2"] * s_.get("ww_heat_mwh_t", 0.0) / 1e6)
        lp.le(co, 0.0)
    if prm["refinery_nuclear_only"]:
        lp.bounds[heat_hp] = (0, 0); lp.bounds[heat_eb] = (0, 0)
        co = {G["nuc_new_dir"]: -1.0}
        for s in systems: add(co, K[s["key"]], s["t_km2"] * s["el_mwh"] / 1e6)
        lp.le(co, 0.0)
    if not prm["allow_kelp"]:
        for k in K.values():
            lp.bounds[k] = (0, 0)
    if prm["kelp_supplies_liquids"]:
        co = {U[("aviation", "jet")]: 1.0, U[("offroad", "liq")]: 1.0, U[("hdv", "liq")]: 1.0,
              U[("hdv", "ed95")]: OPTIONS["hdv"]["ed95"][1]}
        for s in systems:
            add(co, K[s["key"]], -s["t_km2"] * (s["hc_gj"] + s["ethanol_gj"] * prm["atj"]["eff"]) * GJ2TWH)
        if prm.get("existing_biofuels_count", True):
            add(co, F["hefa"], -1.0); add(co, F["fame"], -1.0); add(co, F["cetoh"], -1.0)
        else:
            lp.bounds[F["hefa"]] = (0, 0)
        lp.le(co, 0.0)
        for f in ("eft", "resft"):
            lp.bounds[F[f]] = (0, 0)
    if not prm["allow_efuels"]:
        for f in ("eft", "emeoh", "enh3", "ech4"):
            lp.bounds[F[f]] = (0, 0)

    x, total, duals = lp.solve()
    s = summarise(x, total, duals, prm, d, systems)
    s["aviation_shifted_to_rail_twh"] = shifted
    return s


def summarise(x, total, duals, prm, d, systems):
    s = {"total_cost_beur": total / 1000}
    gen = {"PV": x["pv_direct_day"] + x["pv_direct_shifted"] + x["pv_flex"],
           "Onshore wind": x["onshore_direct"] + x["onshore_flex"],
           "Offshore wind": x["offshore_direct"] + x["offshore_flex"],
           "CSP": x["csp_direct"] + x["csp_flex"],
           "Nuclear (life extension)": x["nuc_ext_direct"] + x["nuc_ext_flex"],
           "Nuclear (new)": x["nuc_new_direct"] + x["nuc_new_flex"] + x["nuc_new_steam_el_forgone"]}
    cf = {"PV": prm["pv"]["cf"], "Onshore wind": prm["onshore"]["cf"], "Offshore wind": prm["offshore"]["cf"],
          "CSP": prm["csp"]["cf"], "Nuclear (life extension)": prm["nuc_ext"]["cf"], "Nuclear (new)": prm["nuc_new"]["cf"]}
    s["generation_twh"] = gen
    s["capacity_gw"] = {k: v / (cf[k] * 8.76) for k, v in gen.items()}
    s["electricity_delivered_twh"] = sum(gen.values()) - x["nuc_new_steam_el_forgone"]
    s["heat_twh_th"] = {"nuclear steam": x["heat_nuclear_steam"], "heat pumps": x["heat_heat_pump"],
                        "electric boilers": x["heat_electric_boiler"], "wind-turbine waste heat": x["heat_wind_turbine_waste"]}
    sysd = {sy["key"]: sy for sy in systems}
    kel = {k.split("|", 1)[1]: v for k, v in x.items() if k.startswith("kelp_km2|") and v > 1e-3}
    tot = lambda f: sum(v * sysd[k]["t_km2"] * f(sysd[k]) for k, v in kel.items())
    s["kelp_km2"] = kel
    s["kelp_total_km2"] = sum(kel.values())
    s["kelp_dry_mt"] = tot(lambda q: 1) / 1e6
    s["kelp_wet_mt"] = s["kelp_dry_mt"] / prm["farm"]["dm_harvest"]
    s["kelp_ethanol_twh"] = tot(lambda q: q["ethanol_gj"]) / 3.6e6
    s["kelp_ethanol_mt"] = tot(lambda q: q["ethanol_gj"]) / 26.8 / 1e6
    s["kelp_hc_twh"] = tot(lambda q: q["hc_gj"]) / 3.6e6
    s["kelp_ch4_gross_twh"] = tot(lambda q: q["ch4_gj"]) / 3.6e6
    s["kelp_fleet_fuel_twh"] = tot(lambda q: q["fleet_gj_t"]) / 3.6e6
    s["skysails_saved_twh"] = tot(lambda q: q["skysails_saved_gj_t"]) / 3.6e6
    s["kelp_refinery_el_twh"] = tot(lambda q: q["el_mwh"]) / 1e6
    s["kelp_refinery_heat_twh"] = tot(lambda q: q["heat_mwh"]) / 1e6
    s["kelp_co2_mt"] = tot(lambda q: q["co2_t"]) / 1e6
    s["fertiliser_mt"] = {n: tot(lambda q, j=j: q["fert"][j]) / 1e9 for j, n in enumerate(("N", "P", "K"))}
    s["fertiliser_domestic_mt"] = {n.upper(): x[f"fert_{n}_domestic_Mt"] for n in ("n", "p", "k")}
    s["fertiliser_value_beur"] = sum(x[f"fert_{n}_{w}_Mt"] * prm["fert"]["price"][n] * (1 if w == "domestic" else prm["fert"]["export_share"])
                                     for n in ("n", "p", "k") for w in ("domestic", "export"))
    s["fertiliser_energy_avoided_pj"] = tot(lambda q: q["fert_energy_gj"]) / 1e6
    s["fertiliser_co2_avoided_mt"] = tot(lambda q: q["fert_co2_t"]) / 1e6
    s["upwelling_pipes"] = tot(lambda q: q["units_km2"] / q["t_km2"] if q["method"] in ("solar_pipe", "wave_pump", "wave_pump_xl", "salt_fountain") else 0)
    s["deep_water_lifted_km3"] = tot(lambda q: q["deep_water_m3_t"] if q["method"] in ("solar_pipe", "wave_pump", "wave_pump_xl", "salt_fountain") else 0) / 1e9
    s["kelp_wet_shipped_mt"] = tot(lambda q: q.get("wet_mass_t", 1 / prm["farm"]["dm_harvest"])) / 1e6
    for key, field in (("kelp_by_zone_km2", "zone"), ("kelp_by_route_km2", "route"), ("kelp_by_nutrient_method_km2", "method"),
                       ("kelp_by_preprocess_km2", "pre")):
        s[key] = {}
        for k, v in kel.items():
            add(s[key], sysd[k].get(field, "wet"), v)
    fuels = {k: x[k] for k in ("eFT_liquids", "e_methanol", "e_ammonia", "e_methane", "ATJ_jet_from_ethanol",
                               "bio_methanol_from_CH4", "waste_biomethane", "HEFA_waste_lipids", "residue_FT",
                               "FAME_biodiesel_existing", "crop_ethanol_existing")}
    fuels["kelp HTL diesel/jet"] = s["kelp_hc_twh"]
    fuels["kelp ethanol"] = s["kelp_ethanol_twh"]
    fuels["kelp biomethane (net of fleet)"] = s["kelp_ch4_gross_twh"] - s["kelp_fleet_fuel_twh"]
    s["fuels_twh"] = fuels
    s["co2_mt"] = {"DAC": x["DAC_CO2_Mt"], "other biogenic": x["other_biogenic_CO2_Mt"], "kelp": x["kelp_CO2_used_Mt"],
                   "cement": x["cement_CO2_Mt"]}
    s["wind_assist_twh_saved"] = x["wind_assist_saving"]
    s["end_use_twh"] = {k[4:]: v for k, v in x.items() if k.startswith("use|") and v > 1e-6}
    el_fuels = (prm["eft"]["el"] * x["eFT_liquids"] + prm["emeoh"]["el"] * x["e_methanol"] + prm["enh3"]["el"] * x["e_ammonia"]
                + prm["ech4"]["el"] * x["e_methane"])
    s["electricity_for_efuels_twh"] = el_fuels
    s["electricity_for_dac_twh"] = prm["dac"]["el"] * x["DAC_CO2_Mt"]
    s["electrolyser_gw"] = el_fuels * 0.95 / (0.55 * 8.76)
    ev = sum(v * OPTIONS[k.split("|")[0]][k.split("|")[1]][1] for k, v in s["end_use_twh"].items()
             if OPTIONS[k.split("|")[0]][k.split("|")[1]][0] == "el_direct")
    s["electricity_vehicles_rail_twh"] = ev
    s["marginal_eur_mwh"] = {k: v for k, v in duals.items() if k != "co2"}
    s["co2_marginal_eur_t"] = duals.get("co2", 0.0)
    s["demand_twh"] = d
    s["fossil_cost_beur"] = {sc: sum(FOSSIL[sc][k] * d[k] for k in FOSSIL[sc]) / 1000 for sc in FOSSIL}
    s["fossil_co2_mt"] = sum(CO2_T_PER_MWH[k] * d[k] for k in d)
    dem = sum(v for k, v in d.items() if k != "rail_el")
    s["avg_cost_eur_mwh"] = total / dem
    s["lifecycle"] = screening_lifecycle(s)
    avoided = s["lifecycle"]["avoided_wtw_mtco2e"]
    s["abatement_eur_t"] = {sc: (total - v * 1000) / avoided for sc, v in s["fossil_cost_beur"].items()}
    s["kelp_share_pct"] = (s["kelp_hc_twh"] + s["kelp_ethanol_twh"] + max(fuels["kelp biomethane (net of fleet)"], 0)) / dem * 100
    s["build"] = build_list(s, prm, x, ev)
    return s


def build_list(s, prm, x, ev):
    c = s["capacity_gw"]; u = UNIT_CAPEX
    b = {"PV (GW)": c["PV"], "Onshore wind (GW)": c["Onshore wind"], "Offshore wind (GW)": c["Offshore wind"],
         "CSP (GW)": c["CSP"], "Nuclear life extension (GW)": c["Nuclear (life extension)"],
         "New nuclear (GW_e)": c["Nuclear (new)"], "New nuclear (1.1 GW units)": c["Nuclear (new)"] / prm["nuc_new"]["unit_gw"],
         "Electrolysers (GW)": s["electrolyser_gw"], "DAC (Mt CO2/yr)": s["co2_mt"]["DAC"],
         "Kelp farms (km2)": s["kelp_total_km2"], "Kelp (Mt dry/yr)": s["kelp_dry_mt"], "Kelp (Mt wet/yr)": s["kelp_wet_mt"],
         "Biorefineries (2 Mt dry/yr each)": s["kelp_dry_mt"] / 2.0,
         "Harvest/transport vessels (1 Mt wet/yr each)": s["kelp_wet_mt"] / 1.0,
         "Upwelling pipes": s["upwelling_pipes"]}
    shelf = sum(v for k, v in s["kelp_by_zone_km2"].items() if k in ("nor_shelf", "nor_slope"))
    deep = s["kelp_total_km2"] - shelf
    efuel_gw = (x["eFT_liquids"] + x["e_methanol"] + x["e_ammonia"] + x["e_methane"]) / (0.55 * 8.76)
    capex = {"PV": c["PV"] * u["PV (EUR/kW)"] / 1e3, "Onshore wind": c["Onshore wind"] * u["Onshore wind (EUR/kW)"] / 1e3,
             "Offshore wind": c["Offshore wind"] * u["Offshore wind (EUR/kW)"] / 1e3, "CSP": c["CSP"] * u["CSP (EUR/kW)"] / 1e3,
             "New nuclear": c["Nuclear (new)"] * u["Nuclear new (EUR/kW)"] / 1e3,
             "Nuclear life extension": c["Nuclear (life extension)"] * u["Nuclear life extension (EUR/kW)"] / 1e3,
             "Electrolysers": s["electrolyser_gw"] * u["Electrolysers (EUR/kW)"] / 1e3,
             "E-fuel synthesis": efuel_gw * u["E-fuel synthesis (EUR/kW fuel)"] / 1e3,
             "DAC": s["co2_mt"]["DAC"] * u["DAC (EUR per t/yr)"] / 1e3,
             "Kelp farms": (shelf * u["Kelp farm shelf (EUR/km2)"] + deep * u["Kelp farm deep (EUR/km2)"]) / 1e9,
             "Biorefineries": s["kelp_dry_mt"] * u["Biorefinery (EUR per t dw/yr)"] / 1e3,
             "Vessels": b["Harvest/transport vessels (1 Mt wet/yr each)"] * u["Vessel (EUR each)"] / 1e9,
             "ATJ plants": x["ATJ_jet_from_ethanol"] / (0.9 * 8.76) * u["ATJ plant (EUR/kW jet)"] / 1e3,
             "Charging and grid": ev * u["Charging and grid (EUR bn per TWh/yr of EV load)"],
             "Upwelling pipes": s["upwelling_pipes"] * prm["farm"]["solar_pipe_capex"] / 1e9}
    b["capex_beur"] = capex
    b["capex_total_beur"] = sum(capex.values())
    b["capex_per_year_2027_2050_beur"] = b["capex_total_beur"] / 24
    return b


DEEP_ALL = {"nor_shelf": 0.10, "nor_slope": 0.10, "nor_deep": 1.0, "can_deep": 1.0, "med_deep": 1.0}
SCENARIOS = {
    "open_least_cost": {},
    "liquid_required": {"liquid_required": True},
    "liquid_required_no_new_nuclear": {"liquid_required": True, "allow_new_nuclear": False},
    "kelp_led": {"liquid_required": True, "kelp_supplies_liquids": True, "area_share": DEEP_ALL},
    "kelp_led_optimistic": {"liquid_required": True, "kelp_supplies_liquids": True,
                            "area_share": {**DEEP_ALL, "nor_shelf": 0.25, "nor_slope": 0.25},
                            "farm": {"base_eur_t": 150.0, "deep_factor": 1.15, "depth_cycle_capex_km2": 0.5e6},
                            "proc": {"alginate_use": 1.0, "htl_biocrude_resid": 0.30, "htl_biocrude_whole": 0.25}},
    "kelp_led_solar_upwelling": {"liquid_required": True, "kelp_supplies_liquids": True, "area_share": DEEP_ALL,
                                 "nutrient_methods": ("solar_pipe",)},
    "your_design": {"liquid_required": True, "kelp_supplies_liquids": True, "area_share": DEEP_ALL,
                    "refinery_routes": ("NUC_EH",), "refinery_nuclear_only": True},
    "kelp_led_ethanol_route": {"liquid_required": True, "kelp_supplies_liquids": True, "area_share": DEEP_ALL,
                               "refinery_routes": ("NUC_EH",)},
    "liquid_required_no_kelp": {"liquid_required": True, "allow_kelp": False},
    "kelp_led_nuclear_refineries": {"liquid_required": True, "kelp_supplies_liquids": True, "area_share": DEEP_ALL,
                                    "refinery_nuclear_only": True},
    "liquid_required_cheap_nuclear": {"liquid_required": True, "nuc_new": {"lcoe": 85}},
    "liquid_required_expensive_nuclear": {"liquid_required": True, "nuc_new": {"lcoe": 170}},
    "liquid_required_domestic": {"liquid_required": True, "scope": "domestic"},
    "kelp_led_domestic": {"liquid_required": True, "kelp_supplies_liquids": True, "area_share": DEEP_ALL, "scope": "domestic"},
}


def merge(base, over):
    b = copy.deepcopy(base)
    for k, v in over.items():
        b[k] = {**b[k], **v} if isinstance(v, dict) and isinstance(b.get(k), dict) else v
    return b


if __name__ == "__main__":
    allres = {}
    for name, over in SCENARIOS.items():
        prm = merge(base_params(), over)
        s = solve(prm)
        allres[name] = s
        print(f"\n== {name}: {s['total_cost_beur']:.1f} bn/yr vs fossil {s['fossil_cost_beur']['oct2026']:.1f} (Oct26) / "
              f"{s['fossil_cost_beur']['avg2025']:.1f} (2025); abatement {s['abatement_eur_t']['oct2026']:.0f}/{s['abatement_eur_t']['avg2025']:.0f} EUR/t")
        print("  GW:", {k: round(v, 1) for k, v in s["capacity_gw"].items() if v > 0.05}, "| el TWh", round(s["electricity_delivered_twh"]))
        print("  kelp km2", round(s["kelp_total_km2"]), {k: round(v) for k, v in s["kelp_by_zone_km2"].items()},
              {k: round(v) for k, v in s["kelp_by_route_km2"].items()}, {k: round(v) for k, v in s["kelp_by_nutrient_method_km2"].items()})
        print("  kelp Mt dry", round(s["kelp_dry_mt"], 1), "share %", round(s["kelp_share_pct"], 1),
              "fert Mt", {k: round(v, 3) for k, v in s["fertiliser_mt"].items()}, "fert bn", round(s["fertiliser_value_beur"], 2))
        print("  fuels:", {k: round(v, 1) for k, v in s["fuels_twh"].items() if abs(v) > 0.05})
        print("  heat:", {k: round(v, 1) for k, v in s["heat_twh_th"].items()}, "CO2:", {k: round(v, 1) for k, v in s["co2_mt"].items()})
        print("  marg:", {k: round(v) for k, v in s["marginal_eur_mwh"].items()}, "capex bn", round(s["build"]["capex_total_beur"]))
    json.dump(allres, open(OUT / "scenarios.json", "w"), indent=1, default=float)
