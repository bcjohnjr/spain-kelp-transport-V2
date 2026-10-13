"""Fig. 5: cost of low-carbon transport relative to fossil fuels (no GIS inputs required)."""
import csv
import json

import numpy as np
import matplotlib.pyplot as plt

from figstyle import C, INK, INK2, MUTED, MM, OUT, save, vgrid, record, dump_source

R = json.load(open(OUT / "paper_results.json"))
LEV = json.load(open(OUT / "levers.json"))

fig = plt.figure(figsize=(180 * MM, 135 * MM))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], width_ratios=[1.15, 1])

# a: headline cases
ax = fig.add_subplot(gs[0, 0])
cases = [("today", "Today's costs"), ("learning", "Learning + 4%\nfinance"),
         ("lowcost", "+ efficiency,\nmodal shift"), ("independent", "+ no imported\nfeedstocks")]
x = np.arange(len(cases))
en = [R[k]["cost"] for k, _ in cases]
vp = [R[k]["vehicle_premium_beur"]["central"] for k, _ in cases]
ax.bar(x, en, color=C["green"], width=0.55, label="Energy supply")
ax.bar(x, vp, bottom=en, color=C["aqua"], width=0.55, label="EV purchase premium (central)")
for i, (k, _) in enumerate(cases):
    fs = R[k]["fossil_same"]
    ax.plot([i - 0.38, i + 0.38], [fs["oct2026"]] * 2, color=INK, lw=1.4)
    ax.plot([i - 0.38, i + 0.38], [fs["avg2025"]] * 2, color=MUTED, lw=1.4, ls="--")
    ax.text(i, en[i] / 2, f"{en[i]:.1f}", ha="center", color="white", fontsize=6.3, fontweight="bold")
ax.plot([], [], color=INK, lw=1.4, label="Fossil bill, Oct 2026 prices")
ax.plot([], [], color=MUTED, lw=1.4, ls="--", label="Fossil bill, 2025 prices")
ax.set_xticks(x); ax.set_xticklabels([c[1] for c in cases])
ax.set_ylabel("€ bn per year (pre-tax)"); ax.set_ylim(0, 92); vgrid(ax)
ax.legend(fontsize=5.6, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
ax.set_title("a  Low-carbon system versus fossil fuel bill")

# b: Monte Carlo
ax = fig.add_subplot(gs[0, 1])
mc = list(csv.DictReader(open(OUT / "monte_carlo.csv")))
ce = np.array([float(r["cost_beur"]) for r in mc])
cv = np.array([float(r["cost_incl_vehicles_beur"]) for r in mc])
f26 = float(np.median([float(r["fossil_oct2026_beur"]) for r in mc]))
f25 = float(np.median([float(r["fossil_2025_beur"]) for r in mc]))
bins = np.arange(36, 76, 1)
ax.hist(ce, bins=bins, color=C["green"], alpha=0.85, label="Energy supply")
ax.hist(cv, bins=bins, color=C["aqua"], alpha=0.65, label="+ EV purchase premia")
top = 150
ax.set_ylim(0, top); ax.set_xlim(26, 76)
ax.axvline(f26, color=INK, lw=1.2); ax.axvline(f25, color=MUTED, lw=1.2, ls="--")
ax.axvline(R["lowcost"]["cost"], color=C["violet"], lw=0.9, ls=":")
ax.text(f26 - 0.6, top * 0.97, "fossil,\nOct 2026", ha="right", va="top", fontsize=5.8, color=INK)
ax.text(f25 - 0.6, top * 0.97, "fossil,\n2025", ha="right", va="top", fontsize=5.8, color=MUTED)
ax.text(R["lowcost"]["cost"] - 0.4, top * 0.62, "learning\ncase", ha="right", va="top", fontsize=5.6, color=C["violet"])
for arr, col in ((ce, C["green"]), (cv, C["aqua"])):
    ax.plot([np.median(arr)] * 2, [0, -4], color=col, lw=2.2, clip_on=False)
ax.set_xlabel("€ bn per year (1,000 draws)"); ax.set_ylabel("Draws")
ax.legend(fontsize=5.6, loc="center left", bbox_to_anchor=(0.0, 0.3))
ax.set_title("b  Monte Carlo uncertainty")

# c: levers
ax = fig.add_subplot(gs[1, :])
cum = LEV["cumulative"]
names = {"farm": "Biomass\n€300→\n200/t", "yield": "Yield\n15→20\nt/ha", "deep": "Cheaper\ndeep\nstructures",
         "conversion": "Full\nalginate,\nHTL yield", "refcapex": "Refinery\ncost\n−30%", "route": "Route\nchoice",
         "heat": "Heat\npumps,\ngrid power", "capital": "4% cost\nof\ncapital", "demand": "Efficiency,\nmodal\nshift",
         "relax": "Electric\nheavy\nequipment"}
vals = [LEV["base"]["cost"]] + [c["cost"] for c in cum]
xs = np.arange(len(vals))
for i in range(len(vals)):
    if i == 0:
        ax.bar(i, vals[0], color=C["red"], width=0.6)
    else:
        ax.bar(i, vals[i - 1] - vals[i], bottom=vals[i], color=C["blue"], width=0.6)
        ax.text(i, vals[i - 1] + 1.5, f"−{vals[i - 1] - vals[i]:.1f}", ha="center", fontsize=5.8)
ax.bar(len(vals), vals[-1] - R["lowcost"]["cost"], bottom=R["lowcost"]["cost"], color=C["blue"], width=0.6)
ax.text(len(vals), vals[-1] + 1.5, f"−{vals[-1] - R['lowcost']['cost']:.1f}", ha="center", fontsize=5.8)
ax.bar(len(vals) + 1, R["lowcost"]["cost"], color=C["green"], width=0.6)
ax.text(0, vals[0] + 1.5, f"{vals[0]:.1f}", ha="center", fontsize=6)
ax.text(len(vals) + 1, R["lowcost"]["cost"] + 1.5, f"{R['lowcost']['cost']:.1f}", ha="center", fontsize=6)
ax.set_xticks(list(xs) + [len(vals), len(vals) + 1])
ax.set_xticklabels(["Kelp-led\ndesign"] + [names[c["key"]] for c in cum] + ["Kelp share\nset by\noptimizer", "Least-cost\nsystem"],
                   fontsize=5.4, color=INK2)
ax.axhline(R["lowcost"]["fossil_same"]["oct2026"], color=INK, lw=1)
ax.axhline(R["lowcost"]["fossil_same"]["avg2025"], color=MUTED, lw=1, ls="--")
ax.set_ylabel("€ bn per year"); ax.set_ylim(0, 125); vgrid(ax)
ax.set_title("c  From the kelp-led design to the least-cost system")

record("Fig5", "a_headline_cases", ["case", "energy supply (EUR bn/yr)", "central EV purchase premium (EUR bn/yr)",
                                    "fossil bill Oct 2026 prices, same demand", "fossil bill 2025 prices, same demand"],
       [[lab.replace(chr(10), " "), en[i], vp[i], R[k]["fossil_same"]["oct2026"], R[k]["fossil_same"]["avg2025"]] for i, (k, lab) in enumerate(cases)])
record("Fig5", "b_monte_carlo_draws", ["draw", "energy supply (EUR bn/yr)", "incl. EV purchase premia (EUR bn/yr)",
                                       "fossil bill Oct 2026 prices", "fossil bill 2025 prices"],
       [[int(r["draw"]), float(r["cost_beur"]), float(r["cost_incl_vehicles_beur"]), float(r["fossil_oct2026_beur"]), float(r["fossil_2025_beur"])] for r in mc],
       note=f"Vertical lines: median fossil bills {f26:.2f} (Oct 2026) and {f25:.2f} (2025); learning case {R['lowcost']['cost']:.2f}.")
record("Fig5", "c_cost_levers", ["step", "cumulative cost (EUR bn/yr)"],
       [["Kelp-led design", vals[0]]] + [[c["key"], c["cost"]] for c in cum] + [["Kelp share set by optimizer (least-cost system)", R["lowcost"]["cost"]]],
       note=f"Fossil bills for the reduced demand: {R['lowcost']['fossil_same']['oct2026']:.2f} (Oct 2026), {R['lowcost']['fossil_same']['avg2025']:.2f} (2025).")
dump_source("Fig5")
fig.tight_layout()
save(fig, "Fig5_cost")
print("Fig5_cost written")
