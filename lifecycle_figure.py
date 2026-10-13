"""Fig. 6: screening lifecycle greenhouse-gas emissions, plus its source data."""
import csv
import json

import numpy as np
import matplotlib.pyplot as plt

import optimise as o
from paper_analyses import build_case
from lifecycle import ELECTRICITY_G_PER_KWH, FUEL_G_PER_MJ
from figstyle import C, INK, INK2, MUTED, MM, OUT, save, hgrid, vgrid, record, dump_source

EFUELS = ("eFT_liquids", "e_methanol", "e_ammonia", "e_methane")


def main():
    s = o.solve(build_case())
    lc = s["lifecycle"]
    gen = s["generation_twh"]
    eci = sum(gen[k] * ELECTRICITY_G_PER_KWH[k] for k in gen) / sum(gen.values())
    direct = s["electricity_vehicles_rail_twh"] * eci * 0.001
    f = s["fuels_twh"]
    kelp = sum(v * FUEL_G_PER_MJ[k] * 0.0036 for k, v in f.items() if k.startswith("kelp"))
    ef = sum(v * FUEL_G_PER_MJ[k] * 0.0036 for k, v in f.items() if k in EFUELS)
    bio = sum(v * FUEL_G_PER_MJ[k] * 0.0036 for k, v in f.items() if k not in EFUELS and not k.startswith("kelp"))
    comps = {"Direct electric transport": direct, "Kelp-derived fuels": kelp,
             "Existing/residue biofuels": bio, "Electrofuels": ef}
    with open(OUT / "lifecycle_source_data.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["metric", "value", "unit"])
        w.writerow(["fossil lifecycle", lc["fossil_wtw_mtco2e"], "MtCO2e/yr"])
        w.writerow(["low-carbon lifecycle", lc["lowcarbon_wtw_mtco2e"], "MtCO2e/yr"])
        w.writerow(["low-carbon factor sensitivity low", lc["lowcarbon_factor_sensitivity_mtco2e"][0], "MtCO2e/yr"])
        w.writerow(["low-carbon factor sensitivity high", lc["lowcarbon_factor_sensitivity_mtco2e"][1], "MtCO2e/yr"])
        for k, v in comps.items():
            w.writerow([k, v, "MtCO2e/yr"])
    json.dump({"lifecycle": lc, "components_mtco2e": comps}, open(OUT / "lifecycle_summary.json", "w"), indent=1, default=float)

    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 66 * MM), gridspec_kw={"width_ratios": [0.8, 1.2]})
    ax = axs[0]
    vals = [lc["fossil_wtw_mtco2e"], lc["lowcarbon_wtw_mtco2e"]]
    ax.bar([0, 1], vals, width=0.55, color=[MUTED, C["green"]])
    lo, hi = lc["lowcarbon_factor_sensitivity_mtco2e"]
    ax.errorbar([1.0], [vals[1]], yerr=[[vals[1] - lo], [hi - vals[1]]], fmt="none", ecolor=INK, elinewidth=0.9, capsize=3)
    ax.text(0, vals[0] + 4, f"{vals[0]:.1f}", ha="center", fontsize=6.3, color=INK)
    ax.text(1.33, vals[1] + 4, f"{vals[1]:.1f}\n({lo:.1f}–{hi:.1f})", ha="left", va="center", fontsize=6.0, color=INK)
    ax.text(1, hi + 14, f"−{lc['reduction_pct']:.1f}%", ha="center", fontsize=7, fontweight="bold", color=INK)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Fossil\ncomparator", "Low-carbon\nsystem"])
    ax.set_xlim(-0.5, 1.95); ax.set_ylim(0, 205)
    ax.set_ylabel("Lifecycle GHG emissions (MtCO$_2$e yr$^{-1}$)"); vgrid(ax)
    ax.set_title("a  Screening well-to-wheel emissions")

    ax = axs[1]
    names = list(comps); vv = list(comps.values())
    y = np.arange(len(names))
    ax.barh(y, vv, color=C["green"], height=0.55)
    ax.set_yticks(y); ax.set_yticklabels(names); ax.invert_yaxis()
    ax.set_xlabel("Contribution to low-carbon system (MtCO$_2$e yr$^{-1}$)"); hgrid(ax)
    ax.set_xlim(0, max(vv) * 1.18)
    for yi, v in zip(y, vv):
        ax.text(v + 0.1, yi, f"{v:.1f}", va="center", fontsize=6.3, color=INK2)
    ax.set_title("b  Low-carbon system by carrier")
    record("Fig6", "a_well_to_wheel", ["system", "MtCO2e/yr", "low factor set", "high factor set"],
           [["Fossil comparator", vals[0], "", ""], ["Low-carbon system", vals[1], lo, hi]],
           note=f"Reduction {lc['reduction_pct']:.2f}% (factor sensitivity {lc['reduction_factor_sensitivity_pct'][0]:.2f}-{lc['reduction_factor_sensitivity_pct'][1]:.2f}%).")
    record("Fig6", "b_contributions", ["carrier group", "MtCO2e/yr"], [[k, v] for k, v in comps.items()])
    record("Fig6", "factors", ["item", "gCO2e/MJ or gCO2e/kWh"],
           [[f"fuel-cycle factor: {k}", v] for k, v in FUEL_G_PER_MJ.items()] + [[f"electricity: {k}", v] for k, v in ELECTRICITY_G_PER_KWH.items()])
    dump_source("Fig6")
    fig.tight_layout()
    save(fig, "Fig6_lifecycle_ghg")
    print(lc, comps)


if __name__ == "__main__":
    main()
