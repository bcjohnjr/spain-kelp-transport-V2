"""Cost-reduction levers for the proposed design (deep-ocean kelp, ethanol + HTL, all-nuclear biorefineries).

Each lever is applied alone to the proposed design, then cumulatively. Outputs: outputs/levers.json and
outputs/fig9_cost_levers.png.
"""
import copy
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import optimise as o

OUT = Path(__file__).resolve().parent / "outputs"
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)


def cheaper_capital(prm, r_new=0.04, r_old=0.07, life=25):
    """Re-price capital-intensive items at a lower cost of capital (capital share of each cost line)."""
    f = CRF(r_new, life) / CRF(r_old, life)
    sc = lambda v, cs: v * (1 - cs + cs * f)
    for k, cs in (("pv", 0.85), ("onshore", 0.75), ("offshore", 0.75), ("csp", 0.75), ("nuc_new", 0.80), ("nuc_ext", 0.30)):
        prm[k]["lcoe"] = sc(prm[k]["lcoe"], cs)
    for k, cs in (("pv_shift", 0.8), ("network_direct", 0.7), ("network_flex", 0.7), ("flex_pv", 0.8),
                  ("flex_onshore", 0.8), ("flex_offshore", 0.8), ("flex_csp", 0.8)):
        prm["adder"][k] = sc(prm["adder"][k], cs)
    for k in ("eft", "emeoh", "enh3", "ech4", "atj"):
        prm[k]["cost"] = sc(prm[k]["cost"], 0.7)
    prm["dac"]["cost"] = sc(prm["dac"]["cost"], 0.6)
    for k in ("waste_ch4", "hefa", "residue_ft"):
        prm[k]["cost"] = sc(prm[k]["cost"], 0.5)
    prm["farm"]["base_eur_t"] = sc(prm["farm"]["base_eur_t"], 0.6)
    prm["farm"]["rate"] = r_new
    prm["refinery_cost_mult"] = sc(prm.get("refinery_cost_mult", 1.0), 0.7)
    return prm


NOR_YIELD = {"nor_shelf": 20.0, "nor_slope": 20.0, "nor_deep": 20.0}
LEVERS = [
    ("farm", "Cheaper farming: biomass €300 → €200/t dry\n(automated harvest, large arrays, shared anchors)",
     lambda p: p["farm"].update(base_eur_t=200.0)),
    ("yield", "Higher yield: 15 → 20 t dry/ha/yr\n(selected strains, two harvests per year)",
     lambda p: p.update(zone_yield=NOR_YIELD)),
    ("deep", "Cheaper deep-water structures: mooring factor 1.3 → 1.1,\ndepth-cycling €1.0M → €0.5M per km²",
     lambda p: p["farm"].update(deep_factor=1.1, slope_factor=1.05, depth_cycle_capex_km2=0.5e6)),
    ("conversion", "Better conversion: ferment all alginate,\nHTL residue yield 0.25 → 0.30",
     lambda p: p["proc"].update(alginate_use=1.0, htl_biocrude_resid=0.30)),
    ("refcapex", "Biorefinery cost −30%\n(nth-of-a-kind plants, standard modules)",
     lambda p: p.update(refinery_cost_mult=p.get("refinery_cost_mult", 1.0) * 0.7)),
    ("route", "Let each refinery choose ethanol + HTL\nor whole-kelp HTL",
     lambda p: p.update(refinery_routes=("NUC_EH", "NUC_H"))),
    ("heat", "Heat pumps and grid power where cheaper\nthan nuclear steam",
     lambda p: p.update(refinery_nuclear_only=False)),
    ("capital", "Cheaper capital: 4% instead of 7%\n(public / green-bond financing)",
     lambda p: cheaper_capital(p)),
    ("demand", "Use less fuel: aviation −25%, shipping −15%,\nwind-assisted ships up to 20%",
     lambda p: p.update(demand_mult={"aviation": 0.75, "shipping": 0.85}, wind_assist_share=0.20)),
    ("relax", "Electric heavy equipment and trucks where\nthey work (drop the 'liquid only' rule)",
     lambda p: p.update(liquid_required=False)),
]


def run(prm):
    return o.solve(prm)


def main():
    base_prm = o.merge(o.base_params(), o.SCENARIOS["your_design"])
    base = run(base_prm)
    fossil = base["fossil_cost_beur"]
    res = {"base": dict(cost=base["total_cost_beur"], kelp_km2=base["kelp_total_km2"], kelp_mt=base["kelp_dry_mt"],
                        new_nuclear_gw=base["capacity_gw"]["Nuclear (new)"], capex=base["build"]["capex_total_beur"]),
           "fossil": fossil, "single": {}, "cumulative": []}
    for key, label, fn in LEVERS:
        p = copy.deepcopy(base_prm); fn(p)
        s = run(p)
        res["single"][key] = dict(label=label, cost=s["total_cost_beur"], saving=base["total_cost_beur"] - s["total_cost_beur"],
                                  kelp_km2=s["kelp_total_km2"], kelp_mt=s["kelp_dry_mt"])
    p = copy.deepcopy(base_prm)
    prev = base["total_cost_beur"]
    for key, label, fn in LEVERS:
        fn(p)
        s = run(p)
        d = s["demand_twh"]
        fossil_same = {sc: sum(o.FOSSIL[sc][k] * d[k] for k in o.FOSSIL[sc]) / 1000 for sc in o.FOSSIL}
        res["cumulative"].append(dict(key=key, label=label, cost=s["total_cost_beur"], step_saving=prev - s["total_cost_beur"],
                                      kelp_km2=s["kelp_total_km2"], kelp_mt=s["kelp_dry_mt"], kelp_share=s["kelp_share_pct"],
                                      new_nuclear_gw=s["capacity_gw"]["Nuclear (new)"], capex=s["build"]["capex_total_beur"],
                                      fossil_same_demand=fossil_same, electricity_twh=s["electricity_delivered_twh"],
                                      fert_n=s["fertiliser_mt"]["N"]))
        prev = s["total_cost_beur"]
    # kelp share of liquids when the optimiser is free (after all levers, kelp not forced)
    p2 = copy.deepcopy(p); p2["kelp_supplies_liquids"] = False
    s2 = run(p2)
    res["all_levers_kelp_not_forced"] = dict(cost=s2["total_cost_beur"], kelp_km2=s2["kelp_total_km2"], kelp_mt=s2["kelp_dry_mt"],
                                             kelp_share=s2["kelp_share_pct"])
    json.dump(res, open(OUT / "levers.json", "w"), indent=1, default=float)
    return res


def figure(res):
    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False})
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 5.6), gridspec_kw={"width_ratios": [1, 1.05]})
    ax = axs[0]
    items = sorted(res["single"].items(), key=lambda kv: kv[1]["saving"])
    yy = np.arange(len(items))
    ax.barh(yy, [v["saving"] for _, v in items], color=["#238b45" if k not in ("demand", "relax") else "#6baed6" for k, _ in items])
    for y, (k, v) in zip(yy, items):
        ax.text(v["saving"] + 0.3, y, f"€{v['saving']:.1f} bn", va="center", fontsize=7.3)
    ax.set_yticks(yy); ax.set_yticklabels([v["label"] for _, v in items], fontsize=6.9)
    ax.set_xlabel("Saving on its own, € bn/yr (from €%.0f bn)" % res["base"]["cost"])
    ax.set_title("a  Each lever alone (green: kelp and refinery; blue: demand and end use)", loc="left", fontsize=9)
    ax = axs[1]
    cum = res["cumulative"]
    xs = np.arange(len(cum) + 1)
    vals = [res["base"]["cost"]] + [c["cost"] for c in cum]
    ax.plot(xs, vals, "-o", color="#238b45", ms=4)
    for i, v in enumerate(vals):
        ax.text(xs[i], v + 2.2, f"{v:.0f}", ha="center", fontsize=7.3)
    ax.axhline(res["fossil"]["oct2026"], color="black", ls="--", lw=0.9)
    ax.text(0.1, res["fossil"]["oct2026"] + 1.2, "fossil, Oct 2026", fontsize=7, ha="left")
    ax.axhline(res["fossil"]["avg2025"], color="#969696", ls=":", lw=0.9)
    ax.text(0.1, res["fossil"]["avg2025"] + 1.2, "fossil, 2025", fontsize=7, ha="left")
    ax.set_xticks(xs); ax.set_xticklabels(["Proposed\ndesign"] + [f"+ {c['key']}" for c in cum], fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("€ bn/yr, all Spanish transport (vehicle capital excluded)")
    ax.set_ylim(0, max(vals) * 1.12)
    ax.set_title("b  Levers stacked in order", loc="left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig9_cost_levers.png", dpi=200)


if __name__ == "__main__":
    r = main()
    print("base", {k: round(v, 1) for k, v in r["base"].items()}, "fossil", {k: round(v, 1) for k, v in r["fossil"].items()})
    for k, v in r["single"].items():
        print(f"single {k:10s} cost {v['cost']:6.1f} saving {v['saving']:5.1f} kelp {v['kelp_km2']:8.0f} km2 {v['kelp_mt']:6.1f} Mt")
    for c in r["cumulative"]:
        print(f"cum +{c['key']:10s} cost {c['cost']:6.1f} step {c['step_saving']:5.1f} kelp {c['kelp_km2']:8.0f} km2 {c['kelp_mt']:6.1f} Mt "
              f"share {c['kelp_share']:4.1f}% nucGW {c['new_nuclear_gw']:4.1f} capex {c['capex']:5.0f} fossil-same {c['fossil_same_demand']['oct2026']:.1f}/{c['fossil_same_demand']['avg2025']:.1f}")
    print("all levers, kelp not forced", {k: round(v, 1) for k, v in r["all_levers_kelp_not_forced"].items()})
    figure(r)
