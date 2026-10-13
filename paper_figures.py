"""Main-text Figs 1, 2, 4, 7 and 8 (180 mm wide, PNG + PDF). Fig. 3: grid_harvester_figure.py; Fig. 5: cost_figure.py; Fig. 6: lifecycle_figure.py."""
import csv
import json
import pickle
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import shapely

import optimise as o
from paper_analyses import build_case, fossil_same, vehicle_premium_beur
from deep_farm import ZONES, FarmCost, nutrient_options
from nuclear_refinery import Feed, routes as nroutes
from preprocess import Pre, options as pre_options
from spatial import DOMAINS

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
FIG = HERE / "paper_figures"
FIG.mkdir(exist_ok=True)
R = json.load(open(OUT / "paper_results.json"))
LEV = json.load(open(OUT / "levers.json"))

from figstyle import C, INK, INK2, MUTED, GRID, MM, save, hgrid, vgrid, record, dump_source  # noqa: E402


low = o.solve(build_case())
ind = o.solve(build_case(overrides={"hefa": {"cap": 5.0}, "fame": {"cap": 0.0}, "crop_etoh": {"cap": 0.0},
                                     "allow_new_nuclear": False, "nuc_ext": {"cap_gw": 0.0}}))

# ------------------------------------------------------------------ Figure 1: marine space and farm zones
L = pickle.load(open(OUT / "_layers.pkl", "rb"))
STEP = 0.025
d = L["peninsula"]; bb = DOMAINS["peninsula"]["bbox"]
x0, y0, x1, y1 = bb
nx, ny = int(round((x1 - x0) / STEP)), int(round((y1 - y0) / STEP))
ix = np.floor((d["lon"] - x0) / STEP).astype(int); iy = np.floor((d["lat"] - y0) / STEP).astype(int)
g = np.zeros((ny, nx))
deep = d["depth"] == ">1000"; nor = d["reg"] == "Noratlantica"
g[iy, ix] = 1                                                     # other Spanish waters
g[iy[~deep], ix[~deep]] = 2                                       # shelf + slope (fishing grounds)
g[iy[d["fish"] == "artisanal_0-6nm"], ix[d["fish"] == "artisanal_0-6nm"]] = 3
used = {b: sum(v for k, v in low["kelp_km2"].items() if k.startswith(f"nor_deep|{b}|")) for b in ("0-100", "100-200", "200-370")}
# fill used deep area band by band, nearest to shore first
for band, (lo_km, hi_km) in (("0-100", (0, 100)), ("100-200", (100, 200)), ("200-370", (200, 371))):
    m = deep & nor & (~d["ship"]) & (d["dist"] > lo_km) & (d["dist"] <= hi_km)
    g[iy[m], ix[m]] = 4                                           # candidate deep Atlantic
    if used[band] > 0:
        cell = (STEP * 111.32 * np.cos(np.radians(d["lat"][m]))) * (STEP * 110.57)
        order = np.argsort(d["dist"][m])
        csum = np.cumsum(cell[order])
        sel = order[csum <= used[band]]
        mi = np.where(m)[0][sel]
        g[iy[mi], ix[mi]] = 5                                     # used in least-cost system
shelf_used = nor & (~deep) & (~d["ship"]) & (d["fish"] != "artisanal_0-6nm")
g[iy[d["ship"]], ix[d["ship"]]] = 6
cols = ["#ffffff00", "#eef3f8", "#f6dcc0", "#eb6834", "#cfe8d9", "#008300", "#e34948"]
fig, ax = plt.subplots(figsize=(180 * MM, 112 * MM))
ax.imshow(np.ma.masked_equal(g, 0), origin="lower", extent=(x0, x1, y0, y1), cmap=ListedColormap(cols), vmin=0, vmax=6,
          interpolation="nearest")
for gg in shapely.get_parts(d["land"]):
    if gg.geom_type == "Polygon":
        xx, yy = gg.exterior.xy; ax.fill(xx, yy, color="#ecebe6", ec="#a8a7a2", lw=0.3)
ax.set_xlim(-14.0, 6.0); ax.set_ylim(34.6, 46.3); ax.set_aspect(1 / np.cos(np.radians(40)))
ax.set_xlabel("Longitude (°)"); ax.set_ylabel("Latitude (°)")
leg = [Patch(fc=cols[5], label=f"Kelp farms, least-cost system ({low['kelp_total_km2']:,.0f} km² incl. shelf/slope)"),
       Patch(fc=cols[4], label="Unused deep Atlantic water >1,000 m, outside lanes"),
       Patch(fc=cols[2], label="Shelf and slope <1,000 m: trawl, seine and longline grounds"),
       Patch(fc=cols[3], label="Artisanal fishing, shellfish and mussel rafts (0–6 nm)"),
       Patch(fc=cols[6], label="Shipping lanes, traffic separation schemes, port approaches"),
       Patch(fc=cols[1], label="Other Spanish waters (warm, nutrient-poor)")]
ax.legend(handles=leg, loc="lower left", fontsize=6.2, frameon=True, framealpha=0.92, edgecolor="none")
ax.text(-11.3, 45.55, "NORATLÁNTICA", fontsize=6.5, color=INK2, weight="bold")
fig.tight_layout()
MS = json.load(open(OUT / "marine_space_by_region.json"))
FA = json.load(open(OUT / "free_area_by_depth_distance.json"))
cols1 = list(next(iter(MS.values())).keys())
record("Fig1", "marine_area_by_region_km2", ["region"] + cols1, [[r] + [MS[r][c_] for c_ in cols1] for r in MS])
record("Fig1", "free_area_by_depth_distance_km2", ["region", "depth band | distance band", "free area (km2)"],
       [[r, k, v] for r in FA for k, v in FA[r].items()],
       note="Free area outside shipping lanes, TSS and port approaches and beyond the 0-6 nm artisanal zone.")
record("Fig1", "kelp_farms_least_cost_km2", ["zone | distance band (km) | refinery route | pre-processing", "area (km2)"],
       [[k, v] for k, v in low["kelp_km2"].items() if v > 0.5],
       note=f"Total {low['kelp_total_km2']:.0f} km2. Deep-water farms are drawn nearest-shore first within each distance band; shelf and slope farms are not drawn individually.")
dump_source("Fig1")
save(fig, "Fig1_marine_space")

# ------------------------------------------------------------------ Figure 2: kelp production chain
fig, axs = plt.subplots(2, 2, figsize=(180 * MM, 125 * MM))
ax = axs[0, 0]
HS = json.load(open(OUT / "harvester_slurry.json"))["cases"]
v30 = HS["hose resized to 1 m/s, water-like"]["0.30"]["total"]
labs = ["Conventional\nvessel", "Grid Harvester,\nbare hose,\n10% kelp", "Grid Harvester,\nfaired hose,\n10% kelp", "Grid Harvester,\nfaired hose,\n30% kelp"]
vals = [90.9, 55.59, 33.92, v30]
ax.bar(labs, vals, color=[MUTED, C["blue"], C["aqua"], C["green"]], width=0.55)
for i, v in enumerate(vals):
    ax.text(i, v + 2, f"{v:.1f} MJ" + ("" if i == 0 else f"\n{90.9 / v:.2f}× less"), ha="center", fontsize=6.0, color=INK)
ax.tick_params(axis="x", labelsize=5.8)
ax.set_ylabel("Energy per 1.44-ha harvest cycle (MJ)")
ax.set_ylim(0, 115); vgrid(ax)
ax.set_title("a  Harvesting energy (conventional C_DA = 30 m²)")
ax = axs[0, 1]
c = FarmCost()
nut, units, info = nutrient_options(ZONES["nor_deep"], c)
meth = [("depth_cycling", "Depth cycling\n(9–80 m daily)"), ("solar_pipe", "Solar-pumped\npipe, 1.6 m"),
        ("wave_pump", "Wave pump,\n0.75 m (tested)"), ("wave_pump_xl", "Wave pump,\n1.5 m (scaled)")]
v = [nut[m] for m, _ in meth]
ax.bar([m[1] for m in meth], v, color=[C["aqua"], C["yellow"], C["orange"], C["red"]], width=0.55)
for i, vv in enumerate(v):
    ax.text(i, vv * 1.15, f"€{vv:,.0f}", ha="center", fontsize=6.3)
ax.axhline(c.base_eur_t * c.deep_factor, color=INK2, ls="--", lw=0.7)
ax.text(3.45, c.base_eur_t * c.deep_factor * 1.12, "deep farm without nutrients", fontsize=5.8, ha="right", color=INK2)
ax.set_yscale("log"); ax.set_ylim(30, 1e5)
ax.set_ylabel("Nutrient supplement (€ per dry t, log)")
ax.tick_params(axis="x", labelsize=5.6)
ax.set_title("b  Deep-ocean nutrient supply, Noratlántica")
ax = axs[1, 0]
rr = nroutes(Feed())
order = [("NUC_H", "Whole-kelp HTL\n(least cost)"), ("NUC_EH", "Ethanol + HTL\nof residue"), ("NUC_A", "Anaerobic\ndigestion")]
x = np.arange(3)
parts = [("ethanol_gj", "Ethanol", C["yellow"]), ("hc_gj", "HTL diesel/jet", C["blue"]), ("ch4_gj", "Biomethane", C["aqua"]),
         ("fert_energy_gj", "Fertiliser energy avoided", C["violet"])]
bot = np.zeros(3)
for key, lab, col in parts:
    vv = np.array([rr[k][key] for k, _ in order])
    ax.bar(x, vv, bottom=bot, color=col, width=0.55, label=lab, edgecolor="white", lw=0.6)
    bot += vv
el = np.array([-rr[k]["el_mwh"] * 3.6 for k, _ in order]); st = np.array([-rr[k]["heat_mwh_th"] * 3.6 for k, _ in order])
ax.bar(x, el, color=C["red"], width=0.55, label="Electricity in", edgecolor="white", lw=0.6)
ax.bar(x, st, bottom=el, color=C["magenta"], width=0.55, label="Process heat in", edgecolor="white", lw=0.6)
ax.axhline(0, color=INK2, lw=0.6)
ax.set_xticks(x); ax.set_xticklabels([o_[1] for o_ in order])
ax.set_ylabel("GJ per dry tonne (13.5 GJ HHV in kelp)")
ax.set_ylim(-4.5, 13.5); vgrid(ax)
ax.legend(fontsize=5.4, ncol=3, loc="upper center")
ax.set_title("c  Biorefinery balances, no thermal drying")
ax = axs[1, 1]
po = pre_options(Pre())
km = np.linspace(0, 300, 61)
lines = [("wet", "Ship wet (13% DM)", INK2, "-"), ("press", "Press at sea (25% DM)", C["blue"], "-"),
         ("press_fan", "Press + fan-dry (40% DM)", C["yellow"], "--"), ("press_hpdry", "Press + heat-pump dry (90% DM)", C["orange"], "-."),
         ("press_wwdry", "Press + turbine-waste-heat dry", C["red"], ":")]
p = Pre()
for k, lab, col, ls in lines:
    yv = po[k]["cost"] + (po[k]["mass_t"] - po["wet"]["mass_t"]) * np.maximum(km - 40, 0) * p.transport_eur_t_wet_km
    ax.plot(km, yv, color=col, ls=ls, lw=1.4, label=lab)
ax.axhline(0, color=GRID, lw=0.5)
ax.set_xlabel("Farm-to-port distance (km)"); ax.set_ylabel("Cost relative to shipping wet (€ per dry t)")
ax.legend(fontsize=5.6, loc="center left", bbox_to_anchor=(0.02, 0.42)); vgrid(ax)
ax.set_title("d  Offshore dewatering and drying")
fig.tight_layout()
record("Fig2", "a_harvest_energy", ["case", "energy per 1.44-ha cycle (MJ)", "ratio to conventional vessel"],
       [[l.replace(chr(10), " "), v, 90.9 / v] for l, v in zip(labs, vals)])
record("Fig2", "b_nutrient_supply", ["method", "nutrient supplement (EUR per dry t)"],
       [[m[1].replace(chr(10), " "), nut[m[0]]] for m in meth] + [["deep farm without nutrients (reference line)", c.base_eur_t * c.deep_factor]])
record("Fig2", "c_biorefinery_balances", ["route"] + [lab for _, lab, _ in parts] + ["Electricity in", "Process heat in"],
       [[n_.replace(chr(10), " ")] + [rr[k][key] for key, _, _ in parts] + [-rr[k]["el_mwh"] * 3.6, -rr[k]["heat_mwh_th"] * 3.6] for k, n_ in order],
       note="GJ per dry tonne of kelp; inputs negative.")
record("Fig2", "d_offshore_dewatering", ["farm-to-port distance (km)"] + [lab for _, lab, _, _ in lines],
       [[kk] + [float(po[k]["cost"] + (po[k]["mass_t"] - po["wet"]["mass_t"]) * max(kk - 40, 0) * p.transport_eur_t_wet_km) for k, _, _, _ in lines] for kk in km],
       note="Cost relative to shipping wet kelp, EUR per dry tonne.")
dump_source("Fig2")
save(fig, "Fig2_kelp_chain")

# ------------------------------------------------------------------ Figure 3: least-cost system
fig, axs = plt.subplots(1, 3, figsize=(180 * MM, 78 * MM), gridspec_kw={"width_ratios": [1.0, 1.15, 1.15]})
ax = axs[0]
gen = low["generation_twh"]; cap = low["capacity_gw"]
sup = [("PV", gen["PV"], C["yellow"], cap["PV"]), ("Onshore wind", gen["Onshore wind"], C["blue"], cap["Onshore wind"]),
       ("Nuclear", gen["Nuclear (new)"] + gen["Nuclear (life extension)"], C["violet"], cap["Nuclear (new)"])]
b = 0
for n, v, col, gw in sup:
    if v < 0.5:
        continue
    ax.bar(0, v, bottom=b, color=col, width=0.6, edgecolor="white", lw=0.6)
    ax.text(0.36, b + v / 2 + (6 if n == "Nuclear" else 0), f"{n}\n{v:.0f} TWh, {gw:.1f} GW" if n == "Nuclear" else f"{n}\n{v:.0f} TWh\n{gw:.0f} GW", va="center", fontsize=5.8)
    b += v
use = [("Vehicles, rail", low["electricity_vehicles_rail_twh"], C["aqua"]), ("E-fuels", low["electricity_for_efuels_twh"], C["magenta"]),
       ("Biorefineries\n(incl. heat pumps)", low["electricity_delivered_twh"] - low["electricity_vehicles_rail_twh"] - low["electricity_for_efuels_twh"] - low["electricity_for_dac_twh"], C["green"])]
b = 0
for n, v, col in use:
    ax.bar(-1.2, v, bottom=b, color=col, width=0.6, edgecolor="white", lw=0.6)
    ax.text(-1.55, b + v / 2, f"{n}\n{v:.0f} TWh", va="center", ha="right", fontsize=5.8)
    b += v
ax.set_xlim(-2.9, 1.6); ax.set_xticks([-1.2, 0]); ax.set_xticklabels(["Use", "Supply"])
ax.set_ylabel("TWh per year"); vgrid(ax)
ax.set_title(f"a  Electricity, {low['electricity_delivered_twh']:.0f} TWh")
ax = axs[1]
fu = low["fuels_twh"]
items = [("Kelp HTL diesel/jet", fu["kelp HTL diesel/jet"], C["green"]), ("Residue FT", fu["residue_FT"], C["aqua"]),
         ("HVO, waste lipids", fu["HEFA_waste_lipids"], C["blue"]), ("FAME biodiesel", fu["FAME_biodiesel_existing"], C["blue"]),
         ("Crop ethanol", fu["crop_ethanol_existing"], C["yellow"]), ("E-ammonia", fu["e_ammonia"], C["magenta"]),
         ("E-methane", fu["e_methane"], C["magenta"]), ("Waste biomethane", fu["waste_biomethane"], C["orange"]),
         ("Kelp biomethane", fu["kelp biomethane (net of fleet)"], C["green"])]
yy = np.arange(len(items))[::-1]
ax.barh(yy, [i[1] for i in items], color=[i[2] for i in items], height=0.62)
for y_, (n, v, _) in zip(yy, items):
    ax.text(v + 1, y_, f"{v:.1f}", va="center", fontsize=5.8)
ax.set_yticks(yy); ax.set_yticklabels([i[0] for i in items])
ax.set_xlabel("TWh per year"); hgrid(ax)
ax.set_title("b  Fuels (kelp: green; e-fuels: magenta)")
ax = axs[2]
eu = low["end_use_twh"]
segs = [("Cars", ["ldv_gasoline", "ldv_diesel"]), ("Trucks, buses", ["hdv"]), ("Off-road", ["offroad"]),
        ("Aviation", ["aviation"]), ("Shipping", ["shipping"]), ("Rail", ["rail_el"])]
carriers = [("Battery-electric", ("bev", "bet", "el"), C["aqua"]), ("Drop-in liquids", ("liq", "jet"), C["green"]),
            ("Ethanol", ("e100", "ed95"), C["yellow"]), ("Methane", ("lng", "cng"), C["orange"]),
            ("Ammonia / methanol", ("nh3", "meoh"), C["magenta"])]
yy = np.arange(len(segs))[::-1]
left = np.zeros(len(segs))
for cname, opts, col in carriers:
    vv = np.array([sum(eu.get(f"{s_}|{op}", 0.0) for s_ in ss for op in opts) for _, ss in segs])
    ax.barh(yy, vv, left=left, color=col, height=0.62, label=cname, edgecolor="white", lw=0.6)
    left += vv
wa = low["wind_assist_twh_saved"]
ax.barh(yy[4], wa, left=left[4], color="none", edgecolor=INK2, hatch="////", height=0.62, lw=0.5, label="Wind assist (saved)")
ax.set_yticks(yy); ax.set_yticklabels([s_[0] for s_ in segs])
ax.set_xlabel("Fossil energy replaced (TWh/yr)"); hgrid(ax)
ax.legend(fontsize=5.4, loc="upper center", bbox_to_anchor=(0.35, -0.2), ncol=2)
ax.set_title("c  Supply by segment")
fig.tight_layout()
record("Fig4", "a_electricity_supply", ["source", "TWh/yr", "GW"], [[n_, v_, gw] for n_, v_, _, gw in sup])
record("Fig4", "a_electricity_use", ["use", "TWh/yr"], [[n_.replace(chr(10), " "), v_] for n_, v_, _ in use])
record("Fig4", "b_fuels", ["fuel", "TWh/yr"], [[n_, v_] for n_, v_, _ in items])
record("Fig4", "c_supply_by_segment", ["segment"] + [cn for cn, _, _ in carriers] + ["Wind assist (saved)"],
       [[sname] + [sum(eu.get(f"{s_}|{op}", 0.0) for s_ in ss for op in opts) for _, opts, _ in carriers] + [wa if sname == "Shipping" else 0.0]
        for sname, ss in segs], note="Fossil energy replaced, TWh/yr.")
dump_source("Fig4")
save(fig, "Fig4_least_cost_system")

# Figure 5 (cost vs fossil) is produced by cost_figure.py, which does not need the GIS layers.

# ------------------------------------------------------------------ Figure 5: price stability and independence
fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 68 * MM), gridspec_kw={"width_ratios": [1.2, 1]})
ax = axs[0]
ex = R["exposure"]
fs = R["lowcost"]["fossil_same"]
pts = [("Fossil fuels", fs["avg2025"], fs["oct2026"], INK),
       ("Least-cost low-carbon", R["lowcost"]["cost"], R["lowcost"]["cost"] + ex["lowcarbon_swing_beur"], C["green"]),
       ("No imported feedstocks", R["independent"]["cost"], R["independent"]["cost"], C["aqua"])]
for n, a, b_, col in pts:
    ax.plot([0, 1], [a, b_], "-o", color=col, lw=1.6, ms=4)
    ax.text(1.04, b_, f"{n}: {a:.1f} → {b_:.1f}", va="center", fontsize=6, color=INK)
ax.set_xticks([0, 1]); ax.set_xticklabels(["2025 average\nfuel prices", "October 2026\nfuel prices"])
ax.set_xlim(-0.15, 2.0); ax.set_ylim(30, 72); vgrid(ax)
ax.set_ylabel("€ bn per year")
ax.set_title(f"a  Price shock: fossil +€{ex['fossil_swing_beur']:.1f} bn (+{ex['fossil_swing_pct']:.0f}%), "
             f"low-carbon +€{ex['lowcarbon_swing_beur']:.1f} bn")
ax = axs[1]
bars = [("Fossil fuels\n(crude imported)", 100.0, INK), ("Least-cost\nlow-carbon", R["import_share_lowcost_pct"], C["green"]),
        ("No imported\nfeedstocks", 0.0, C["aqua"])]
ax.bar([b_[0] for b_ in bars], [b_[1] for b_ in bars], color=[b_[2] for b_ in bars], width=0.55)
for i, b_ in enumerate(bars):
    ax.text(i, b_[1] + 2, f"{b_[1]:.1f}%", ha="center", fontsize=6.3)
ax.set_ylabel("Transport energy from imported fuels\nor feedstocks (%)"); ax.set_ylim(0, 112); vgrid(ax)
ax.set_title("b  Import dependence of transport energy")
fig.tight_layout()
record("Fig7", "a_price_shock", ["system", "cost at 2025 average prices (EUR bn/yr)", "cost at October 2026 prices (EUR bn/yr)"],
       [[n_, a, b_] for n_, a, b_, _ in pts])
record("Fig7", "b_import_dependence", ["system", "transport energy from imported fuels or feedstocks (%)"],
       [[n_.replace(chr(10), " "), v_] for n_, v_, _ in bars])
dump_source("Fig7")
save(fig, "Fig7_stability_independence")

# ------------------------------------------------------------------ Figure 6: options that raise cost
base = R["lowcost"]["cost"]
tests = [
    ("Kelp must supply all liquid fuel", {"kelp_supplies_liquids": True}),
    ("Ethanol + HTL route at every refinery", {"refinery_routes": ("NUC_EH",)}),
    ("All refinery steam and power from new nuclear", {"refinery_nuclear_only": True, "refinery_routes": ("NUC_H", "NUC_EH")}),
    ("Press kelp at sea (all farms)", {"preprocess": ("press",)}),
    ("Fan-dry offshore to 40% DM (all farms)", {"preprocess": ("press_fan",)}),
    ("Heat-pump dry offshore to 90% DM (all farms)", {"preprocess": ("press_hpdry",)}),
    ("Dry with turbine waste heat (all POEM offshore wind built)", {"preprocess": ("wet", "press_wwdry"), "ww_force": True}),
    ("Nutrients by solar-pumped upwelling", {"nutrient_methods": ("solar_pipe",)}),
    ("No electricity-based fuels at all", {"allow_efuels": False}),
    ("Liquid fuel kept for heavy equipment, half of trucks", {"liquid_required": True}),
]
pen = []
for lab, ov in tests:
    s = o.solve(build_case(overrides=ov))
    pen.append((lab, s["total_cost_beur"] - base))
json.dump(pen, open(OUT / "option_penalties.json", "w"), indent=1)
fig, ax = plt.subplots(figsize=(180 * MM, 70 * MM))
pen_s = sorted(pen, key=lambda t: t[1])
yy = np.arange(len(pen_s))
ax.barh(yy, [p_[1] for p_ in pen_s], color=C["orange"], height=0.6)
for y_, (lab, v) in zip(yy, pen_s):
    ax.text(v + 0.3, y_, f"+€{v:.1f} bn", va="center", fontsize=6)
ax.set_yticks(yy); ax.set_yticklabels([p_[0] for p_ in pen_s])
ax.set_xlabel(f"Extra cost relative to the least-cost system (€ bn per year; base €{base:.1f} bn)"); hgrid(ax)
fig.tight_layout()
record("Fig8", "extra_cost", ["forced option", "extra cost vs least-cost system (EUR bn/yr)"], pen,
       note=f"Least-cost system: EUR {base:.2f} bn/yr.")
dump_source("Fig8")
save(fig, "Fig8_options")
print(json.dumps(pen, indent=0))
print("figures ok")
