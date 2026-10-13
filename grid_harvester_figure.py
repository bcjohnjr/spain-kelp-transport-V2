"""Fig. 3: the Grid Harvester, a conventional harvesting vessel, and the area lost in turns.

Panels a-b are the Grid Harvester illustrations; c-f are the path and turn diagrams. Loss figures are computed by
harvester_turns.py for the geometry stated there.
"""
import json

import matplotlib.pyplot as plt
from PIL import Image

from figstyle import INK, INK2, MM, OUT, HERE, save, record, dump_source

ILL = HERE / "illustrations"
T = json.load(open(OUT / "harvester_turns.json"))
c, g = T["conventional"], T["grid"]


def show(ax, name, label):
    ax.imshow(Image.open(ILL / name).convert("RGB"), interpolation="lanczos")
    ax.set_axis_off()
    ax.set_title(label, fontsize=7.5)


fig = plt.figure(figsize=(180 * MM, 150 * MM))
gs = fig.add_gridspec(2, 1, height_ratios=[1.0, 1.32], hspace=0.12)
top = gs[0].subgridspec(1, 2, wspace=0.04)
show(fig.add_subplot(top[0]), "grid_harvester_side.jpg", "a  Grid Harvester, side view")
show(fig.add_subplot(top[1]), "grid_harvester_top.jpg", "b  Grid Harvester, top view with the path of the head")

bot = gs[1].subgridspec(1, 2, width_ratios=[0.30, 1.0], wspace=0.10)
show(fig.add_subplot(bot[0]), "conventional_spiral.png", "c  Conventional vessel")
right = bot[1].subgridspec(3, 1, height_ratios=[0.85, 1.0, 1.0], hspace=0.55)


def loss_panel(spec, name, title, text):
    sub = spec.subgridspec(1, 2, width_ratios=[1.0, 0.95], wspace=0.05)
    show(fig.add_subplot(sub[0]), name, title)
    ax = fig.add_subplot(sub[1]); ax.set_axis_off()
    ax.text(0.0, 0.5, text, va="center", ha="left", fontsize=6.0, color=INK2, transform=ax.transAxes, linespacing=1.45)


loss_panel(right[0], "conventional_turn_loss.png", "d  Conventional vessel, 90° turn",
           f"Missed per 90° turn: (1 − π/4)$R^2$, $R = W_{{cv}}$\n"
           f"{c['turns_90deg']} turns, {c['vessel_width_m']:.0f}-m vessel, 1.44 ha\n"
           f"Missed: {c['missed_m2']:.0f} m² ({c['missed_pct']:.1f}%)")
fw, st = g["forward"], g["stationary"]
loss_panel(right[1], "grid_turn_forward.png", "e  Grid Harvester, head turning while moving forward",
           f"Missed per 180° turn: 2(4 − π)$R^2$\n"
           f"{g['turns_180deg']} turns, {g['head_width_m']:.0f}-m head, 1.44 ha\n"
           f"Missed: {fw['missed_m2']:.0f} m² ({fw['missed_pct']:.1f}%)\n"
           f"With LMMs: {fw['lmm_twice_pct']:.1f}% harvested twice")
loss_panel(right[2], "grid_turn_stationary.png", "f  Grid Harvester, head turning in place",
           f"Missed per 180° turn: (2 − π/2)$R^2$\n"
           f"{g['turns_180deg']} turns, {g['head_width_m']:.0f}-m head, 1.44 ha\n"
           f"Missed: {st['missed_m2']:.0f} m² ({st['missed_pct']:.1f}%)\n"
           f"With LMMs: {st['lmm_twice_pct']:.1f}% harvested twice")

record("Fig3", "d_f_turn_losses",
       ["configuration", "turns", "missed area (m2)", "missed (% of 1.44 ha)", "harvested twice with LMMs (m2)",
        "harvested twice with LMMs (%)"],
       [["Conventional vessel, 10 m, spiral, 90-degree turns", c["turns_90deg"], c["missed_m2"], c["missed_pct"], "", ""],
        ["Grid Harvester head 6 m, turning while moving forward", g["turns_180deg"], fw["missed_m2"], fw["missed_pct"],
         fw["lmm_twice_m2"], fw["lmm_twice_pct"]],
        ["Grid Harvester head 6 m, turning in place", g["turns_180deg"], st["missed_m2"], st["missed_pct"],
         st["lmm_twice_m2"], st["lmm_twice_pct"]]],
       note="Panels a-c are illustrations; values for d-f from harvester_turns.py (1.44-ha harvest cycle).")
dump_source("Fig3")
fig.subplots_adjust(left=0.01, right=0.99, top=0.97, bottom=0.01)
save(fig, "Fig3_grid_harvester")
print("Fig3_grid_harvester written")
