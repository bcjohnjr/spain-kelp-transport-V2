"""Low-cost model: the proposed design with every cost lever applied, plus Spain's existing terrestrial biofuels.

Variants answer three questions:
  1. Should electricity-based fuels (e-fuels) using concentrated CO2 streams be in the mix?
  2. Does wind-turbine waste heat help the biorefineries?
  3. What changes if heavy equipment and half of trucks must stay on liquid fuel?
Outputs: outputs/lowcost_scenarios.json, outputs/lowcost_summary.csv, fig10, fig11.
"""
import copy
import csv
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import optimise as o
from levers import LEVERS

OUT = Path(__file__).resolve().parent / "outputs"


def lowcost_base(relax=True):
    p = o.merge(o.base_params(), o.SCENARIOS["your_design"])
    for key, _, fn in LEVERS:
        if key == "relax" and not relax:
            continue
        fn(p)
    p["preprocess"] = ("wet", "press", "press_hpdry", "press_wwdry", "press_fan")
    return p


def variant(relax, **over):
    p = lowcost_base(relax)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(p.get(k), dict):
            p[k] = {**p[k], **v}
        else:
            p[k] = v
    return p


VARIANTS = {
    # electric where it works (lowest cost)
    "LC_kelp_biofuels": ("Kelp + existing biofuels supply all liquid fuel;\ne-fuels only for ships", variant(True)),
    "LC_no_efuels": ("… no electricity-based fuels at all", variant(True, allow_efuels=False)),
    "LC_efuels_free": ("… e-fuels may also supply liquids\n(optimiser chooses)", variant(True, kelp_supplies_liquids=False)),
    "LC_efuels_cement_co2": ("… plus cement CO2 stream (7 Mt/yr)", variant(True, kelp_supplies_liquids=False, cement_co2={"cap": 7.0})),
    "LC_wind_heat_30": ("Kelp + biofuels, with wind-turbine waste heat\n(30% of onshore turbines connected)",
                        variant(True, wind_heat={"reach": 0.30})),
    "LC_wind_heat_100": ("… every onshore turbine connected", variant(True, wind_heat={"reach": 1.0})),
    "LC_force_press": ("… every farm presses kelp at sea", variant(True, preprocess=("press",))),
    "LC_force_hpdry": ("… every farm dries kelp offshore with\nwind-powered heat-pump dryers", variant(True, preprocess=("press_hpdry",))),
    "LC_force_fan": ("… every farm fan-dries kelp offshore\nto 40% dry matter", variant(True, preprocess=("press_fan",))),
    "LC_wwdry_max": ("… turbine waste heat dries as much kelp as the\nPOEM offshore zones allow (wind built)",
                     variant(True, preprocess=("wet", "press", "press_wwdry"), ww_force=True)),
    # liquid fuel kept for aviation, heavy equipment, half of trucks
    "LCL_kelp_biofuels": ("Liquid rule kept: kelp + existing biofuels", variant(False)),
    "LCL_no_efuels": ("Liquid rule kept: no e-fuels at all", variant(False, allow_efuels=False)),
    "LCL_efuels_free": ("Liquid rule kept: e-fuels may supply liquids", variant(False, kelp_supplies_liquids=False)),
    "LCL_efuels_cement_co2": ("Liquid rule kept: e-fuels + cement CO2", variant(False, kelp_supplies_liquids=False, cement_co2={"cap": 7.0})),
}


def main():
    res = {}
    for k, (label, prm) in VARIANTS.items():
        s = o.solve(prm)
        d = s["demand_twh"]
        s["fossil_same_demand_beur"] = {sc: sum(o.FOSSIL[sc][kk] * d[kk] for kk in o.FOSSIL[sc]) / 1000 for sc in o.FOSSIL}
        s["label"] = label
        res[k] = s
        f = s["fuels_twh"]
        print(f"\n== {k}: €{s['total_cost_beur']:.1f} bn vs fossil (same demand) {s['fossil_same_demand_beur']['oct2026']:.1f}/"
              f"{s['fossil_same_demand_beur']['avg2025']:.1f}")
        print("  GW", {a: round(b, 1) for a, b in s["capacity_gw"].items() if b > 0.05}, "el", round(s["electricity_delivered_twh"]))
        print("  kelp", round(s["kelp_total_km2"]), "km2", round(s["kelp_dry_mt"], 1), "Mt dry", round(s["kelp_share_pct"], 1), "%",
              {a: round(b) for a, b in s["kelp_by_route_km2"].items()})
        print("  fuels", {a: round(b, 1) for a, b in f.items() if abs(b) > 0.05})
        print("  co2", {a: round(b, 1) for a, b in s["co2_mt"].items()}, "heat", {a: round(b, 1) for a, b in s["heat_twh_th"].items()})
        print("  pre", {a: round(b) for a, b in s["kelp_by_preprocess_km2"].items()}, "wet shipped Mt", round(s["kelp_wet_shipped_mt"]),
              "offshore GW", round(s["capacity_gw"]["Offshore wind"], 1))
        print("  capex", round(s["build"]["capex_total_beur"]), "marg", {a: round(b) for a, b in s["marginal_eur_mwh"].items()})
    json.dump(res, open(OUT / "lowcost_scenarios.json", "w"), indent=1, default=float)
    rows = []
    for k, s in res.items():
        b = s["build"]; f = s["fuels_twh"]
        rows.append(dict(scenario=k, cost_beur=round(s["total_cost_beur"], 1),
                         fossil_same_demand_oct2026=round(s["fossil_same_demand_beur"]["oct2026"], 1),
                         fossil_same_demand_2025=round(s["fossil_same_demand_beur"]["avg2025"], 1),
                         electricity_twh=round(s["electricity_delivered_twh"]), pv_gw=round(b["PV (GW)"], 1),
                         onshore_gw=round(b["Onshore wind (GW)"], 1), nuclear_kept_gw=round(b["Nuclear life extension (GW)"], 1),
                         new_nuclear_gw=round(b["New nuclear (GW_e)"], 1), electrolysers_gw=round(b["Electrolysers (GW)"], 1),
                         kelp_km2=round(s["kelp_total_km2"]), kelp_mt_dry=round(s["kelp_dry_mt"], 1), kelp_share_pct=round(s["kelp_share_pct"], 1),
                         hvo_twh=round(f["HEFA_waste_lipids"], 1), fame_twh=round(f["FAME_biodiesel_existing"], 1),
                         crop_ethanol_twh=round(f["crop_ethanol_existing"], 1), waste_biomethane_twh=round(f["waste_biomethane"], 1),
                         efuels_twh=round(f["eFT_liquids"] + f["e_methanol"] + f["e_ammonia"] + f["e_methane"], 1),
                         dac_mt=round(s["co2_mt"]["DAC"], 1), cement_co2_mt=round(s["co2_mt"]["cement"], 1),
                         wind_waste_heat_twh=round(s["heat_twh_th"]["wind-turbine waste heat"], 2),
                         capex_beur=round(b["capex_total_beur"]), fert_n_mt=round(s["fertiliser_mt"]["N"], 2)))
    with open(OUT / "lowcost_summary.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    return res


def figures(res):
    plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False})
    keys = list(VARIANTS)
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 5.6), gridspec_kw={"width_ratios": [1.15, 1]})
    yy = np.arange(len(keys))[::-1]
    ax = axs[0]
    tc = [res[k]["total_cost_beur"] for k in keys]
    f26 = [res[k]["fossil_same_demand_beur"]["oct2026"] for k in keys]
    f25 = [res[k]["fossil_same_demand_beur"]["avg2025"] for k in keys]
    ax.barh(yy, tc, color=["#238b45" if k.startswith("LC_") else "#74c476" for k in keys])
    ax.scatter(f26, yy, marker="|", s=240, color="black", zorder=5, label="fossil, Oct 2026 prices")
    ax.scatter(f25, yy, marker="|", s=240, color="#969696", zorder=5, label="fossil, 2025 prices")
    for y, v, a1 in zip(yy, tc, f26):
        ax.text(max(v, a1) + 1.5, y, f"€{v:.1f} bn", va="center", fontsize=7.3)
    ax.set_yticks(yy); ax.set_yticklabels([res[k]["label"] for k in keys], fontsize=7)
    ax.set_xlim(0, 90)
    ax.set_xlabel("€ bn/yr, all Spanish transport, pre-tax energy supply")
    ax.set_title("a  Low-cost model: annual cost", loc="left", fontsize=9)
    ax.legend(fontsize=7, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2)
    ax = axs[1]
    cats = [("kelp HTL diesel/jet", "Kelp diesel/jet", "#08519c"), ("kelp ethanol", "Kelp ethanol", "#fec44f"),
            ("HEFA_waste_lipids", "HVO (waste lipids)", "#6baed6"), ("FAME_biodiesel_existing", "FAME biodiesel", "#9ecae1"),
            ("crop_ethanol_existing", "Crop ethanol", "#fe9929"), ("residue_FT", "Residue FT", "#c6dbef"),
            ("eFT_liquids", "E-kerosene/diesel", "#807dba"), ("e_ammonia", "E-ammonia", "#bcbddc"),
            ("e_methanol", "E-methanol", "#dadaeb"), ("e_methane", "E-methane", "#fdae6b"),
            ("waste_biomethane", "Waste biomethane", "#fdd0a2"), ("kelp biomethane (net of fleet)", "Kelp biomethane", "#41ab5d"),
            ("bio_methanol_from_CH4", "Bio-methanol", "#a1d99b")]
    left = np.zeros(len(keys))
    for key, lab, col in cats:
        v = np.array([max(res[k]["fuels_twh"].get(key, 0.0), 0.0) for k in keys])
        if v.max() < 0.5:
            continue
        ax.barh(yy, v, left=left, color=col, label=lab)
        left += v
    ax.set_yticks(yy); ax.set_yticklabels([])
    ax.set_xlabel("Fuel supplied, TWh/yr (electricity for vehicles not shown)")
    ax.set_title("b  Where the fuel comes from", loc="left", fontsize=9)
    ax.legend(fontsize=6.6, frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.45, -0.09))
    fig.set_size_inches(12.5, 6.6)
    fig.tight_layout()
    fig.savefig(OUT / "fig10_lowcost_scenarios.png", dpi=200)

    # wind-turbine waste heat versus refinery heat demand
    fig, ax = plt.subplots(figsize=(10, 4.8))
    base = res["LC_kelp_biofuels"]
    need = sum(base["heat_twh_th"].values())
    onshore_twh = base["generation_twh"]["Onshore wind"]
    dry_need = base["kelp_dry_mt"] * 1e6 * 2.327 / 1e6
    poem = 4947 * 5.5 / 1000 * 0.40 * 8.76
    bars = [("Refinery heat\nneed", need, "#a50f15"),
            ("…of which\n≤90 °C", need * o.base_params()["wind_heat"]["lowtemp_share"], "#fb6a4a"),
            ("Heat to dry all\nkelp offshore\n(25→90% DM)", dry_need, "#67000d"),
            (f"Waste heat:\nnew onshore\nwind ({base['capacity_gw']['Onshore wind']:.0f} GW)", 0.06 * onshore_twh, "#4393c3"),
            ("Waste heat:\nall POEM\noffshore (27 GW)", 0.06 * poem, "#2166ac"),
            ("Waste heat:\nGalicia+Asturias\nonshore (4.6 GW)", 0.06 * 4.6 * 0.27 * 8.76, "#9ecae1"),
            ("Same new onshore\nwind power via\nheat pumps (COP 2.5)", 2.5 * onshore_twh, "#238b45")]
    x = np.arange(len(bars))
    ax.bar(x, [b[1] for b in bars], color=[b[2] for b in bars])
    for i, b in enumerate(bars):
        ax.text(i, b[1] * 1.08 + 0.3, f"{b[1]:.1f}", ha="center", fontsize=7.5)
    ax.set_yscale("log"); ax.set_ylim(0.5, max(b[1] for b in bars) * 3)
    ax.set_xticks(x); ax.set_xticklabels([b[0] for b in bars], fontsize=7.2)
    ax.set_ylabel("TWh of heat per year (log)")
    ax.set_title("Wind-turbine waste heat (≈6% of output, 40–90 °C) vs what the biorefineries need", loc="left", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "fig11_wind_waste_heat.png", dpi=200)


if __name__ == "__main__":
    r = main()
    figures(r)
