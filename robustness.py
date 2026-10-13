"""Structural robustness checks not represented by the parameter-only base case.

These tests are deliberately adverse. They do not turn an annual optimisation
into an hourly dispatch model; instead they quantify how much the headline
annual cost moves when immature kelp assumptions, available marine area,
renewable-integration adders, finance or the price benchmark are stressed.
"""
import csv, json
from pathlib import Path
import numpy as np
import optimise as o
from paper_analyses import build_case, fossil_same, vehicle_premium_beur

OUT = Path(__file__).resolve().parent / "outputs"


def solve_label(label, prm):
    s = o.solve(prm)
    return {
        "case": label,
        "cost_beur": s["total_cost_beur"],
        "cost_incl_central_vehicle_premium_beur": s["total_cost_beur"] + vehicle_premium_beur(s),
        "kelp_km2": s["kelp_total_km2"],
        "kelp_share_pct": s["kelp_share_pct"],
        "lifecycle_mtco2e": s["lifecycle"]["lowcarbon_wtw_mtco2e"],
        "lifecycle_reduction_pct": s["lifecycle"]["reduction_pct"],
        "fossil_oct2026_beur": s["fossil_cost_beur"]["oct2026"],
        "fossil_2025_beur": s["fossil_cost_beur"]["avg2025"],
    }


def main():
    rows = []
    rows.append(solve_label("central", build_case()))
    rows.append(solve_label("no_kelp", build_case(overrides={"allow_kelp": False})))

    for y in (5, 10, 15, 20):
        rows.append(solve_label(f"north_atlantic_yield_{y}_t_ha", build_case(overrides={
            "zone_yield": {"nor_shelf": float(y), "nor_slope": float(y), "nor_deep": float(y)}})))

    # Fraction of mapped free area made available after additional ecological,
    # fishing, cable, military or planning exclusions. Shelf/slope remain capped
    # at 10% unless the remaining fraction is even lower.
    for frac in (0.50, 0.25, 0.10, 0.05):
        rows.append(solve_label(f"marine_candidate_area_{int(frac*100)}pct", build_case(overrides={
            "area_share": {"nor_shelf": min(0.10, frac), "nor_slope": min(0.10, frac),
                           "nor_deep": frac, "can_deep": frac, "med_deep": frac}})))

    # Annual model integration-cost stress. This does NOT claim hourly
    # feasibility; it tests whether omitted balancing/network costs overturn the
    # annual economic ranking.
    for mult in (1.5, 2.0):
        p = build_case()
        for k in ("pv_day", "pv_shift", "onshore", "offshore", "csp", "nuclear",
                  "network_direct", "network_flex", "flex_pv", "flex_onshore",
                  "flex_offshore", "flex_csp"):
            p["adder"][k] *= mult
        rows.append(solve_label(f"integration_adders_x{mult:.1f}", p))

    rows.append(solve_label("finance_7pct", build_case(r=0.07)))

    # Domestic territorial-like demand: domestic aviation and shipping shares
    # only. This is reported separately because the headline all-scope case
    # includes international bunkers sold in Spain.
    rows.append(solve_label("domestic_aviation_shipping_scope", build_case(overrides={"scope": "domestic"})))

    with open(OUT / "robustness.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

    central = rows[0]
    # If all fossil reference prices move proportionally, the multiplier at
    # which the low-carbon system breaks even is simply cost/fossil bill.
    break_even = {
        "energy_only_vs_2025_price_multiplier": central["cost_beur"] / central["fossil_2025_beur"],
        "incl_central_vehicle_premium_vs_2025_price_multiplier": central["cost_incl_central_vehicle_premium_beur"] / central["fossil_2025_beur"],
        "energy_only_vs_oct2026_price_multiplier": central["cost_beur"] / central["fossil_oct2026_beur"],
        "incl_central_vehicle_premium_vs_oct2026_price_multiplier": central["cost_incl_central_vehicle_premium_beur"] / central["fossil_oct2026_beur"],
    }
    # Today's-cost case (no learning, 7% finance, current demand).
    today = o.solve(o.merge(o.base_params(), o.SCENARIOS["open_least_cost"]))
    fs_today = fossil_same(today)
    vp_today = vehicle_premium_beur(today)
    break_even["today_energy_only_vs_2025_price_multiplier"] = today["total_cost_beur"] / fs_today["avg2025"]
    break_even["today_incl_central_vehicle_premium_vs_2025_price_multiplier"] = (today["total_cost_beur"] + vp_today) / fs_today["avg2025"]
    break_even["oct2026_vs_2025_fossil_bill_ratio"] = central["fossil_oct2026_beur"] / central["fossil_2025_beur"]
    # Monte Carlo: price multiplier on 2025 fossil prices at which each draw breaks even.
    mc = list(csv.DictReader(open(OUT / "monte_carlo.csv")))
    cost = np.array([float(r["cost_beur"]) for r in mc])
    costv = np.array([float(r["cost_incl_vehicles_beur"]) for r in mc])
    f25 = np.array([float(r["fossil_2025_beur"]) for r in mc])
    f26 = np.array([float(r["fossil_oct2026_beur"]) for r in mc])
    pct = lambda a: np.percentile(a, [5, 50, 95]).tolist()
    break_even["monte_carlo_energy_only_vs_2025_p5_p50_p95"] = pct(cost / f25)
    break_even["monte_carlo_incl_vehicles_vs_2025_p5_p50_p95"] = pct(costv / f25)
    mc_position = {
        "share_of_draws_costlier_than_learning_case": float(np.mean(cost > central["cost_beur"])),
        "median_saving_vs_oct2026_pct_energy_only": float(np.median((f26 - cost) / f26) * 100),
        "median_saving_vs_oct2026_pct_incl_vehicles": float(np.median((f26 - costv) / f26) * 100),
    }
    # Split of the central vehicle purchase premium (incremental cost at normal fleet replacement).
    s_c = o.solve(build_case())
    vehicle_split = {
        "learning_case": {"cars_and_vans": vehicle_premium_beur(s_c, truck=0),
                          "heavy_trucks_and_offroad": vehicle_premium_beur(s_c, car=0, van=0)},
        "today_case": {"cars_and_vans": vehicle_premium_beur(today, truck=0),
                       "heavy_trucks_and_offroad": vehicle_premium_beur(today, car=0, van=0)},
        "today_case_energy_cost_beur": today["total_cost_beur"],
        "today_case_fossil_same_demand_beur": fs_today,
    }
    # Supply-side sensitivities reported in Supplementary Table 5 (change relative to the learning case).
    def pv_integration_x15(p):
        for k in ("pv_day", "pv_shift", "flex_pv"):
            p["adder"][k] *= 1.5
        return p
    sens_cases = {
        "No residue FT": build_case(overrides={"residue_ft": {"cap": 0.0}}),
        "Waste biomethane 10 TWh": build_case(overrides={"waste_ch4": {"cap": 10.0}}),
        "No HVO/FAME/crop ethanol": build_case(overrides={"hefa": {"cap": 0.0}, "fame": {"cap": 0.0}, "crop_etoh": {"cap": 0.0}}),
        "Kelp area capped at 10% of deep Atlantic": build_case(overrides={"area_share": {"nor_deep": 0.10}}),
        "No kelp at all": build_case(overrides={"allow_kelp": False}),
        "PV +50% integration cost": pv_integration_x15(build_case()),
        "Offshore wind LCOE 70": build_case(overrides={"offshore": {"lcoe": 70.0}}),
        "New nuclear LCOE 70": build_case(overrides={"nuc_new": {"lcoe": 70.0}}),
    }
    sens = {}
    for lab, prm in sens_cases.items():
        s = o.solve(prm)
        sens[lab] = {"cost": s["total_cost_beur"], "delta": s["total_cost_beur"] - central["cost_beur"],
                     "kelp_km2": s["kelp_total_km2"], "kelp_share": s["kelp_share_pct"],
                     "gw": {k: round(v, 1) for k, v in s["capacity_gw"].items() if v > 0.05}}
    json.dump(sens, open(OUT / "supply_sensitivities.json", "w"), indent=1, default=float)

    out = {"cases": rows, "break_even": break_even, "monte_carlo_position": mc_position,
           "vehicle_premium_split_beur": vehicle_split,
           "note": "Integration-adder tests are annual cost stresses, not hourly dispatch validation."}
    json.dump(out, open(OUT / "robustness.json", "w"), indent=1)
    return out

if __name__ == "__main__":
    r = main()
    for x in r["cases"]:
        print(x["case"], round(x["cost_beur"],2), "bn; incl vehicles", round(x["cost_incl_central_vehicle_premium_beur"],2),
              "kelp", round(x["kelp_km2"]), "km2; GHG", round(x["lifecycle_reduction_pct"],1), "%")
    print("break-even", r["break_even"])
    print("monte carlo position", r["monte_carlo_position"])
    print("vehicle premium split", r["vehicle_premium_split_beur"])
