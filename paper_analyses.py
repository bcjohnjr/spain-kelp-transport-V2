"""Analyses reported in the manuscript.

1. Headline cases (electric vehicles where they work, existing biofuels counted, e-fuels allowed):
   - today's costs (no learning, 7% capital, current demand)
   - learning + low-cost finance, current demand
   - learning + low-cost finance + fuel-efficiency/modal shift (lowest cost)
2. Vehicle purchase-premium sensitivity (cars, vans, heavy trucks).
3. Monte Carlo over the low-cost case (1,000 draws).
4. Exposure to internationally traded fuel prices (fossil vs low-carbon) under the 2025 -> Oct 2026 price shock.
5. Transport-fuel independence: imported biofuel feedstocks removed.
6. Grid Harvester fleet and energy.
Writes outputs/paper_results.json and outputs/monte_carlo.csv.
"""
import copy
import csv
import json
from pathlib import Path

import numpy as np

import optimise as o
from lifecycle import sampled_lifecycle
from levers import LEVERS, cheaper_capital

OUT = Path(__file__).resolve().parent / "outputs"
RNG = np.random.default_rng(20261013)

# DGT 2024 average annual distance (km) by vehicle class
KM = {"car": 12295, "van": 14666, "truck": 27866}
# fossil energy per km (kWh fuel/km): petrol car 6.5 L/100 km, diesel car/van 5.5 L/100 km, truck 30 L/100 km
KWH_KM = {"petrol_car": 0.065 * 8.9, "diesel_ldv": 0.055 * 9.96, "truck": 0.30 * 9.96}
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)


def vehicle_premium_beur(s, car=1000, van=2000, truck=30000, r=0.04, life=15):
    """Annualised extra purchase cost of battery-electric vehicles, € bn/yr."""
    u = s["end_use_twh"]
    f = CRF(r, life)
    per_mwh = lambda prem, km_yr, kwh_km: prem * f / km_yr * (1000 / kwh_km)
    tot = 0.0
    tot += u.get("ldv_gasoline|bev", 0) * 1e6 * per_mwh(car, KM["car"], KWH_KM["petrol_car"])
    d = u.get("ldv_diesel|bev", 0) * 1e6
    tot += 0.75 * d * per_mwh(car, KM["car"], KWH_KM["diesel_ldv"]) + 0.25 * d * per_mwh(van, KM["van"], KWH_KM["diesel_ldv"])
    tot += (u.get("hdv|bet", 0) + u.get("offroad|el", 0)) * 1e6 * per_mwh(truck, KM["truck"], KWH_KM["truck"])
    return tot / 1e9


def build_case(learning=True, demand=True, r=0.04, overrides=None):
    p = o.merge(o.base_params(), o.SCENARIOS["your_design"])
    for key, _, fn in LEVERS:
        if key == "capital":
            continue
        if not learning and key in ("farm", "yield", "deep", "conversion", "refcapex"):
            continue
        if not demand and key == "demand":
            continue
        fn(p)
    if learning:
        cheaper_capital(p, r_new=r)
    p["kelp_supplies_liquids"] = False
    p["preprocess"] = ("wet", "press", "press_hpdry", "press_wwdry", "press_fan")
    for k, v in (overrides or {}).items():
        p[k] = {**p[k], **v} if isinstance(v, dict) and isinstance(p.get(k), dict) else v
    return p


def fossil_same(s):
    d = s["demand_twh"]
    return {sc: sum(o.FOSSIL[sc][k] * d[k] for k in o.FOSSIL[sc]) / 1000 for sc in o.FOSSIL}


def brief(s):
    return dict(cost=s["total_cost_beur"], fossil_same=fossil_same(s), fossil_base=s["fossil_cost_beur"],
                electricity_twh=s["electricity_delivered_twh"], capacity_gw=s["capacity_gw"], kelp_km2=s["kelp_total_km2"],
                kelp_dry_mt=s["kelp_dry_mt"], kelp_wet_mt=s["kelp_wet_mt"], kelp_share_pct=s["kelp_share_pct"],
                fuels=s["fuels_twh"], fert=s["fertiliser_mt"], fert_energy_pj=s["fertiliser_energy_avoided_pj"],
                fert_co2_mt=s["fertiliser_co2_avoided_mt"], co2=s["co2_mt"], build=s["build"], end_use=s["end_use_twh"],
                heat=s["heat_twh_th"], kelp_by_zone=s["kelp_by_zone_km2"], kelp_by_route=s["kelp_by_route_km2"],
                kelp_by_pre=s["kelp_by_preprocess_km2"], fossil_co2_mt=s["fossil_co2_mt"], demand=s["demand_twh"],
                fleet_fuel_twh=s["kelp_fleet_fuel_twh"], skysails_twh=s["skysails_saved_twh"],
                electrolyser_gw=s["electrolyser_gw"], ev_twh=s["electricity_vehicles_rail_twh"],
                lifecycle=s["lifecycle"])


def main():
    R = {}
    today = o.solve(o.merge(o.base_params(), o.SCENARIOS["open_least_cost"]))
    R["today"] = brief(today)
    learn = o.solve(build_case(learning=True, demand=False))
    R["learning"] = brief(learn)
    low = o.solve(build_case(learning=True, demand=True))
    R["lowcost"] = brief(low)
    for k, s in (("today", today), ("learning", learn), ("lowcost", low)):
        R[k]["vehicle_premium_beur"] = {"low": 0.0, "central": vehicle_premium_beur(s),
                                        "high": vehicle_premium_beur(s, car=3000, van=5000, truck=60000)}
    # price exposure: 2025 average -> Oct 2026 shock applied to anything priced off world fuel markets
    shock = {k: o.FOSSIL["oct2026"][k] / o.FOSSIL["avg2025"][k] - 1 for k in o.FOSSIL["oct2026"]}
    road_shock = shock["hdv"]
    f = low["fuels_twh"]
    p = build_case()
    traded = (f["HEFA_waste_lipids"] * p["hefa"]["cost"] + f["FAME_biodiesel_existing"] * p["fame"]["cost"]
              + f["crop_ethanol_existing"] * p["crop_etoh"]["cost"]) / 1000
    R["exposure"] = dict(fossil_swing_beur=fossil_same(low)["oct2026"] - fossil_same(low)["avg2025"],
                         fossil_swing_pct=(fossil_same(low)["oct2026"] / fossil_same(low)["avg2025"] - 1) * 100,
                         lowcarbon_traded_beur=traded, lowcarbon_swing_beur=traded * road_shock,
                         lowcarbon_swing_pct=traded * road_shock / low["total_cost_beur"] * 100, shock=shock)
    # transport-fuel independence: only domestic waste lipids (UCO + animal fats ~0.4 Mt -> ~5 TWh HVO), no imported FAME/crop ethanol
    ind = o.solve(build_case(overrides={"hefa": {"cap": 5.0}, "fame": {"cap": 0.0}, "crop_etoh": {"cap": 0.0}, "allow_new_nuclear": False, "nuc_ext": {"cap_gw": 0.0}}))
    R["independent"] = brief(ind)
    R["independent"]["vehicle_premium_beur"] = {"central": vehicle_premium_beur(ind)}
    imp = f["HEFA_waste_lipids"] + f["FAME_biodiesel_existing"] + f["crop_ethanol_existing"]
    R["import_share_lowcost_pct"] = imp / sum(v for kk, v in low["demand_twh"].items() if kk != "rail_el") * 100
    # liquid rule kept (sensitivity)
    lq = o.solve(build_case(overrides={"liquid_required": True}))
    R["liquid_rule"] = brief(lq)
    # Grid Harvester (companion harvester model, optimized geometry): 416.7 t wet/h, 2.68x lower energy than a
    # conventional vessel at C_DA 30 m2 with an 85% hose fairing (2.58-2.79 for 80-90%), 57.0 MJ saved per 1.44-ha cycle
    harvest_hours = 2400
    R["harvester"] = dict(throughput_t_wet_h=416.7, hours_per_season=harvest_hours,
                          units_lowcost=low["kelp_wet_mt"] * 1e6 / (416.7 * harvest_hours),
                          units_independent=ind["kelp_wet_mt"] * 1e6 / (416.7 * harvest_hours),
                          energy_ratio_central=2.68, energy_ratio_range=(2.58, 2.79), ratio_at_cda10=(0.97, 1.05),
                          ratio_proportion_opt_no_form_drag=3.06, saving_kwh_per_dry_t=0.59)
    json.dump(R, open(OUT / "paper_results.json", "w"), indent=1, default=float)
    return R


def tri(a, m, b):
    return RNG.triangular(a, m, b)


def monte_carlo(n=1000):
    rows = []
    for i in range(n):
        r = tri(0.03, 0.04, 0.07)
        farm = tri(150, 220, 600)
        yld = tri(5, 15, 22)
        over = {
            "farm": {"base_eur_t": farm, "deep_factor": tri(1.05, 1.15, 1.60), "depth_cycle_capex_km2": tri(0.3e6, 0.7e6, 3.0e6)},
            "zone_yield": {"nor_shelf": yld, "nor_slope": yld, "nor_deep": yld},
            "proc": {"htl_biocrude_whole": tri(0.15, 0.193, 0.25), "htl_biocrude_resid": tri(0.20, 0.30, 0.33),
                     "alginate_use": tri(0.5, 1.0, 1.0), "ad_ch4_nm3_kgvs": tri(0.18, 0.24, 0.30)},
            "pv": {"lcoe": tri(26, 33, 40)}, "onshore": {"lcoe": tri(38, 45, 55)},
            "hefa": {"cost": tri(140, 164, 200)}, "fame": {"cost": tri(120, 136, 160)},
            "demand_mult": {"aviation": tri(0.70, 0.75, 0.90), "shipping": tri(0.80, 0.85, 0.95)},
            "wind_assist_share": tri(0.10, 0.20, 0.25),
            "area_share": {"nor_shelf": tri(0.025, 0.10, 0.10), "nor_slope": tri(0.025, 0.10, 0.10),
                           "nor_deep": tri(0.0625, 0.25, 0.25), "can_deep": tri(0.0625, 0.25, 0.25),
                           "med_deep": tri(0.0625, 0.25, 0.25)},
        }
        efm = tri(0.8, 1.0, 1.4); refm = tri(0.8, 1.0, 1.4); fertm = tri(0.7, 1.0, 1.3)
        p = o.merge(o.base_params(), o.SCENARIOS["your_design"])
        for key, _, fn in LEVERS:
            if key in ("capital", "farm", "yield", "deep", "conversion", "demand"):
                continue
            fn(p)
        for k, v in over.items():
            p[k] = {**p[k], **v} if isinstance(v, dict) and isinstance(p.get(k), dict) else v
        for k in ("eft", "emeoh", "enh3", "ech4"):
            p[k]["cost"] *= efm
        p["refinery_cost_mult"] = p.get("refinery_cost_mult", 1.0) * refm
        p["fert"] = {**p["fert"], "price": {kk: vv * fertm for kk, vv in p["fert"]["price"].items()}}
        cheaper_capital(p, r_new=r)
        p["kelp_supplies_liquids"] = False
        p["preprocess"] = ("wet", "press")
        # In 10% of draws, represent structural failure/non-deployment of deep-ocean kelp.
        if RNG.random() < 0.10:
            p["allow_kelp"] = False
        s = o.solve(p)
        fs = fossil_same(s)
        lc_mt, fossil_lc_mt, lc_red = sampled_lifecycle(s, RNG)
        vp = vehicle_premium_beur(s, car=tri(0, 1000, 3000), van=tri(0, 2000, 5000), truck=tri(0, 30000, 60000))
        rows.append(dict(draw=i, wacc=r, farm_eur_t=farm, yield_t_ha=yld, cost_beur=s["total_cost_beur"], vehicle_premium_beur=vp,
                         cost_incl_vehicles_beur=s["total_cost_beur"] + vp, fossil_oct2026_beur=fs["oct2026"],
                         fossil_2025_beur=fs["avg2025"], kelp_km2=s["kelp_total_km2"], kelp_share_pct=s["kelp_share_pct"],
                         lowcarbon_lifecycle_mtco2e=lc_mt, fossil_lifecycle_mtco2e=fossil_lc_mt,
                         lifecycle_reduction_pct=lc_red,
                         abatement_2025_incl_vehicles_eur_t=(s["total_cost_beur"] + vp - fs["avg2025"]) * 1000 / (fossil_lc_mt - lc_mt)))
    with open(OUT / "monte_carlo.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    c = np.array([r_["cost_beur"] for r_ in rows]); cv = np.array([r_["cost_incl_vehicles_beur"] for r_ in rows])
    f26 = np.array([r_["fossil_oct2026_beur"] for r_ in rows]); f25 = np.array([r_["fossil_2025_beur"] for r_ in rows])
    k = np.array([r_["kelp_km2"] for r_ in rows])
    ghg = np.array([r_["lifecycle_reduction_pct"] for r_ in rows])
    abat = np.array([r_["abatement_2025_incl_vehicles_eur_t"] for r_ in rows])
    summ = dict(n=n, cost_p5_p50_p95=np.percentile(c, [5, 50, 95]).tolist(),
                cost_incl_vehicles_p5_p50_p95=np.percentile(cv, [5, 50, 95]).tolist(),
                p_below_oct2026=float(np.mean(c < f26)), p_below_2025=float(np.mean(c < f25)),
                p_incl_vehicles_below_oct2026=float(np.mean(cv < f26)), p_incl_vehicles_below_2025=float(np.mean(cv < f25)),
                kelp_km2_p5_p50_p95=np.percentile(k, [5, 50, 95]).tolist(),
                lifecycle_reduction_pct_p5_p50_p95=np.percentile(ghg, [5, 50, 95]).tolist(),
                abatement_2025_incl_vehicles_eur_t_p5_p50_p95=np.percentile(abat, [5, 50, 95]).tolist())
    json.dump(summ, open(OUT / "monte_carlo_summary.json", "w"), indent=1)
    return summ


if __name__ == "__main__":
    R = main()
    for k in ("today", "learning", "lowcost", "independent", "liquid_rule"):
        v = R[k]
        print(k, round(v["cost"], 1), "fossil same", {a: round(b, 1) for a, b in v["fossil_same"].items()},
              "kelp", round(v["kelp_km2"]), round(v["kelp_dry_mt"], 1), "share", round(v["kelp_share_pct"], 1),
              "veh", {a: round(b, 1) for a, b in v.get("vehicle_premium_beur", {}).items()},
              "GW", {a: round(b, 1) for a, b in v["capacity_gw"].items() if b > 0.05}, "capex", round(v["build"]["capex_total_beur"]))
    print("exposure", {a: (round(b, 2) if isinstance(b, float) else b) for a, b in R["exposure"].items() if a != "shock"})
    print("import share %", round(R["import_share_lowcost_pct"], 2), "harvester", {a: (round(b, 1) if isinstance(b, float) else b) for a, b in R["harvester"].items()})
    print("MC", monte_carlo(1000))
