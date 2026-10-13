"""Map of Spanish waters: fishing-pressure proxy, shipping lanes/TSS/ports and kelp/wind candidate zones."""
import pickle
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import shapely

from spatial import PORTS, DOMAINS

HERE = Path(__file__).resolve().parent
L = pickle.load(open(HERE / "outputs/_layers.pkl", "rb"))
STEP = 0.025

COL = {1: "#d6e6f2", 2: "#f7cf94", 3: "#e07b39"}  # deep-low, trawl/seine/longline, artisanal


def raster(d, extent):
    x0, y0, x1, y1 = extent
    nx, ny = int(round((x1 - x0) / STEP)), int(round((y1 - y0) / STEP))
    ix = np.floor((d["lon"] - x0) / STEP).astype(int)
    iy = np.floor((d["lat"] - y0) / STEP).astype(int)
    base = np.zeros((ny, nx))
    code = np.where(d["fish"] == "artisanal_0-6nm", 3, np.where(d["fish"] == "deep_low", 1, 2))
    base[iy, ix] = code
    kelp = np.zeros((ny, nx)); wind = np.zeros((ny, nx))
    sel = (d["reg"] == "Noratlantica") & (~d["ship"]) & (d["fish"] != "artisanal_0-6nm") & (d["dist"] <= 100)
    shp = np.zeros((ny, nx)); shp[iy[d["ship"]], ix[d["ship"]]] = 1
    kelp[iy[sel & (d["depth"] == "0-200")], ix[sel & (d["depth"] == "0-200")]] = 1
    wind[iy[sel & (d["depth"] == "200-1000")], ix[sel & (d["depth"] == "200-1000")]] = 1
    return base, kelp, wind, shp


def draw(ax, dom, extent, title):
    d = L[dom]
    base, kelp, wind, shp = raster(d, DOMAINS[dom]["bbox"])
    bx = DOMAINS[dom]["bbox"]
    cmap = ListedColormap(["#ffffff00", COL[1], COL[2], COL[3]])
    ax.imshow(np.ma.masked_equal(base, 0), origin="lower", extent=(bx[0], bx[2], bx[1], bx[3]),
              cmap=cmap, vmin=0, vmax=3, interpolation="nearest")
    xs = np.arange(bx[0] + STEP / 2, bx[2], STEP); ys = np.arange(bx[1] + STEP / 2, bx[3], STEP)
    ax.contourf(xs, ys, kelp, levels=[0.5, 1.5], colors="none", hatches=["////"])
    ax.contour(xs, ys, kelp, levels=[0.5], colors="#1b7837", linewidths=0.9)
    ax.contourf(xs, ys, wind, levels=[0.5, 1.5], colors="none", hatches=["\\\\\\\\"])
    ax.contour(xs, ys, wind, levels=[0.5], colors="#00441b", linewidths=0.9, linestyles="--")
    # shipping
    ax.imshow(np.ma.masked_equal(shp, 0), origin="lower", extent=(bx[0], bx[2], bx[1], bx[3]),
              cmap=ListedColormap(["#c0392b"]), alpha=0.6, interpolation="nearest")
    for t in d["tss_ll"]:
        x, y = t.exterior.xy
        ax.plot(x, y, color="#7b0d0d", lw=1.4)
    # land
    for g in shapely.get_parts(d["land"]):
        if g.geom_type == "Polygon":
            x, y = g.exterior.xy
            ax.fill(x, y, color="#e9e4d8", ec="#8c8273", lw=0.4)
    for n, (la, lo, r) in PORTS.items():
        if extent[0] <= lo <= extent[1] and extent[2] <= la <= extent[3]:
            ax.plot(lo, la, "o", ms=2.6, color="black")
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3])
    ax.set_aspect(1 / np.cos(np.radians(np.mean(extent[2:]))))
    ax.set_title(title, fontsize=10, loc="left")
    ax.tick_params(labelsize=7)


fig = plt.figure(figsize=(11, 8.6))
ax1 = fig.add_axes([0.05, 0.34, 0.90, 0.63])
draw(ax1, "peninsula", (-14.0, 6.0, 34.6, 46.2), "a  Peninsula and Balearic Islands")
for name, (x, y) in {"NORATLÁNTICA": (-11.2, 44.9), "SUDATLÁNTICA": (-8.2, 36.1),
                     "ESTRECHO-ALBORÁN": (-5.6, 35.3), "LEVANTINO-BALEAR": (3.0, 38.2)}.items():
    ax1.text(x, y, name, fontsize=8, color="#333", weight="bold")
ax2 = fig.add_axes([0.05, 0.05, 0.40, 0.24])
draw(ax2, "canaries", (-19.5, -12.0, 26.0, 30.6), "b  Canary Islands")
leg = [Patch(fc=COL[3], label="Artisanal fishing, shellfish beds, mussel rafts (0–6 nm)"),
       Patch(fc=COL[2], label="Trawl, purse-seine and longline grounds (6 nm to 1,000 m depth)"),
       Patch(fc=COL[1], label="Deep water >1,000 m (pelagic longline; low conflict)"),
       Patch(fc="#c0392b", alpha=0.45, label="Shipping lanes, port approaches"),
       Patch(fc="none", ec="#7b0d0d", lw=1.4, label="Traffic separation schemes (approx. position)"),
       Patch(fc="none", ec="#1b7837", hatch="////", label="Kelp-suitable shelf: Noratlántica 0–200 m, outside lanes, >6 nm"),
       Patch(fc="none", ec="#00441b", hatch="\\\\\\\\", ls="--", label="Floating wind + kelp co-location: Noratlántica 200–1,000 m"),
       plt.Line2D([], [], marker="o", ls="", color="black", ms=3, label="Main commercial ports")]
fig.legend(handles=leg, loc="lower left", bbox_to_anchor=(0.50, 0.06), fontsize=7.6, frameon=False)
fig.text(0.51, 0.012, "Fishing classes are a depth/distance proxy, not observed effort. Lanes: Benden (2022) after CIA (2012),\n"
         "buffered 10/6/3 km, shown inside Spanish waters only; ferry and coastal routes are under-represented.\n"
         "EEZ by equidistance approximation. Candidate zones \u2264100 km from the coast.",
         fontsize=6.5, color="#555")
fig.savefig(HERE / "outputs/fig1_marine_space_map.png", dpi=220)
print("ok")
