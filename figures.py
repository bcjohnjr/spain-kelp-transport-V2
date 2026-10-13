"""Figures 4-8: deep-ocean farm zones, nutrient supply, nuclear biorefinery, scenario costs, build list."""
import json
import pickle
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import shapely

from deep_farm import ZONES, FarmCost, nutrient_options, farm_cost
from nuclear_refinery import Feed, routes as nroutes
from spatial import DOMAINS

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
S = json.load(open(OUT / "scenarios.json"))
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False})

# ------------------------------------------------------------------ Fig 4 deep-ocean farm zones
L = pickle.load(open(OUT / "_layers.pkl", "rb"))
STEP = 0.025
cols = {0: "#ffffff00", 1: "#e5e5e5", 2: "#c7e9c0", 3: "#74c476", 4: "#238b45", 5: "#fdd0a2", 6: "#bdd7e7"}


def raster(d, bbox):
    x0, y0, x1, y1 = bbox
    nx, ny = int(round((x1 - x0) / STEP)), int(round((y1 - y0) / STEP))
    ix = np.floor((d["lon"] - x0) / STEP).astype(int); iy = np.floor((d["lat"] - y0) / STEP).astype(int)
    g = np.zeros((ny, nx))
    deep = (d["depth"] == ">1000") & (~d["ship"])
    nor = d["reg"] == "Noratlantica"
    g[iy, ix] = 1
    g[iy[deep & nor & (d["dist"] > 200)], ix[deep & nor & (d["dist"] > 200)]] = 2
    g[iy[deep & nor & (d["dist"] > 100) & (d["dist"] <= 200)], ix[deep & nor & (d["dist"] > 100) & (d["dist"] <= 200)]] = 3
    g[iy[deep & nor & (d["dist"] <= 100)], ix[deep & nor & (d["dist"] <= 100)]] = 4
    shelf = nor & (d["depth"] != ">1000") & (~d["ship"])
    g[iy[shelf], ix[shelf]] = 5
    warm = deep & (~nor)
    g[iy[warm], ix[warm]] = 6
    return g


fig = plt.figure(figsize=(11, 7.2))
axa = fig.add_axes([0.04, 0.08, 0.60, 0.88])
d = L["peninsula"]; bb = DOMAINS["peninsula"]["bbox"]
g = raster(d, bb)
cm = ListedColormap([cols[i] for i in range(7)])
axa.imshow(np.ma.masked_equal(g, 0), origin="lower", extent=(bb[0], bb[2], bb[1], bb[3]), cmap=cm, vmin=0, vmax=6,
           interpolation="nearest")
for gg in shapely.get_parts(d["land"]):
    if gg.geom_type == "Polygon":
        x, y = gg.exterior.xy; axa.fill(x, y, color="#e9e4d8", ec="#8c8273", lw=0.4)
axa.set_xlim(-14.0, 6.0); axa.set_ylim(34.6, 46.2); axa.set_aspect(1 / np.cos(np.radians(40)))
axa.set_title("a  Where the deep-ocean kelp farms go (kelp-led design)", loc="left", fontsize=9.5)
kl = S["kelp_led"]["kelp_km2"]
used = {b: sum(v for k, v in kl.items() if k.startswith(f"nor_deep|{b}|")) for b in ("0-100", "100-200", "200-370")}
tot = {b: ZONES["nor_deep"].area_km2[b] for b in used}
leg = [Patch(fc=cols[4], label=f"Deep >1,000 m, ≤100 km: {used['0-100']:,.0f} of {tot['0-100']:,.0f} km² used"),
       Patch(fc=cols[3], label=f"Deep, 100–200 km: {used['100-200']:,.0f} of {tot['100-200']:,.0f} km² used"),
       Patch(fc=cols[2], label=f"Deep, 200–370 km: {used['200-370']:,.0f} of {tot['200-370']:,.0f} km² used"),
       Patch(fc=cols[5], label="Noratlántica shelf + slope (10% used; fishing grounds)"),
       Patch(fc=cols[6], label="Warm deep water (Med, Strait, Canaries): too warm, nutrient-poor"),
       Patch(fc=cols[1], label="Other Spanish waters / shipping lanes")]
axa.legend(handles=leg, loc="lower left", fontsize=7.2, frameon=True, framealpha=0.9)
axb = fig.add_axes([0.68, 0.55, 0.30, 0.38])
d2 = L["canaries"]; bb2 = DOMAINS["canaries"]["bbox"]
g2 = raster(d2, bb2)
axb.imshow(np.ma.masked_equal(g2, 0), origin="lower", extent=(bb2[0], bb2[2], bb2[1], bb2[3]), cmap=cm, vmin=0, vmax=6,
           interpolation="nearest")
for gg in shapely.get_parts(d2["land"]):
    if gg.geom_type == "Polygon":
        x, y = gg.exterior.xy; axb.fill(x, y, color="#e9e4d8", ec="#8c8273", lw=0.4)
axb.set_xlim(-21.5, -11.5); axb.set_ylim(25.0, 31.5); axb.set_aspect(1 / np.cos(np.radians(28)))
axb.set_title("b  Canary deep water (388,000 km² free):\nnot selected — €960+/t dry", loc="left", fontsize=8.5)
axc = fig.add_axes([0.70, 0.08, 0.28, 0.36]); axc.axis("off")
k = S["kelp_led"]
lines = [f"Kelp-led design (all aviation, heavy-equipment",
         f"and half of truck fuel from kelp):",
         f"  farm area            {k['kelp_total_km2']:,.0f} km²",
         f"  harvest              {k['kelp_dry_mt']:.0f} Mt dry = {k['kelp_wet_mt']:.0f} Mt wet / yr",
         f"  biorefineries        {k['build']['Biorefineries (2 Mt dry/yr each)']:.0f} × 2 Mt dry/yr",
         f"  vessels              {k['build']['Harvest/transport vessels (1 Mt wet/yr each)']:.0f} × 1 Mt wet/yr",
         f"  drop-in diesel/jet   {k['kelp_hc_twh']:.0f} TWh/yr",
         f"  ethanol → jet (ATJ)  {k['kelp_ethanol_twh']:.0f} TWh/yr",
         f"  N / P / K            {k['fertiliser_mt']['N']:.2f} / {k['fertiliser_mt']['P']:.2f} / {k['fertiliser_mt']['K']:.1f} Mt/yr",
         f"  nutrients by         depth cycling (9–80 m daily)"]
axc.text(-0.05, 1, "\n".join(lines), va="top", family="monospace", fontsize=6.9)
fig.savefig(OUT / "fig4_deep_ocean_farm_zones.png", dpi=200)

# ------------------------------------------------------------------ Fig 5 nutrient supply
c = FarmCost()
fig, axs = plt.subplots(1, 2, figsize=(11, 4.3), gridspec_kw={"width_ratios": [1.5, 1]})
ax = axs[0]
meth = [("depth_cycling", "Depth cycling\n(kelp moved to\nnutrients nightly)"), ("solar_pipe", "Solar-PV pumped\n1.6 m pipe"),
        ("wave_pump", "Passive wave\npump 0.75 m\n(as tested)"), ("wave_pump_xl", "Passive wave\npump 1.5 m\n(scaled)"),
        ("salt_fountain", "Salt fountain\n(heat-driven,\nCanaries only)"), ("refinery_return", "Return refinery\nammonium (restricted\nas ocean fertilisation)")]
zs = [("nor_deep", "Noratlántica deep", "#238b45"), ("can_deep", "Canaria deep", "#fd8d3c"), ("med_deep", "Med deep", "#6baed6")]
x = np.arange(len(meth)); w = 0.26
for i, (zk, zl, cc) in enumerate(zs):
    nut, _, info = nutrient_options(ZONES[zk], c)
    vals = [nut[m] if np.isfinite(nut[m]) and nut[m] > 0 else np.nan for m, _ in meth]
    ax.bar(x + (i - 1) * w, vals, w, color=cc, label=zl)
ax.axhline(c.base_eur_t * c.deep_factor, color="black", ls="--", lw=0.8)
ax.text(5.55, c.base_eur_t * c.deep_factor * 1.15, "deep-farm cost without\nnutrients (€390/t)", fontsize=6.8, ha="right")
ax.set_yscale("log"); ax.set_ylim(5, 2e5)
ax.set_xticks(x); ax.set_xticklabels([m[1] for m in meth], fontsize=6.8)
ax.set_ylabel("€ per dry tonne of kelp for the nutrient supplement (log)")
ax.set_title("a  Cost of bringing deep nutrients to the farm", loc="left", fontsize=9)
ax.legend(fontsize=7, frameon=False, loc="upper left")
ax = axs[1]
vol = [nutrient_options(ZONES[zk], c)[2]["deep_water_m3_per_t_dw"] / 1000 for zk, _, _ in zs]
ax.bar([z[1] for z in zs], vol, color=[z[2] for z in zs])
for i, v in enumerate(vol):
    ax.text(i, v + 8, f"{v:,.0f}", ha="center", fontsize=7.5)
ax.set_ylabel("thousand m³ of deep water lifted per dry tonne")
ax.set_title("b  Water that must be pumped (25% capture)", loc="left", fontsize=9)
sl = S["kelp_led_solar_upwelling"]
ax.text(0.02, 0.97, f"Kelp-led design with pumped upwelling:\n{sl['upwelling_pipes']:,.0f} pipes, "
        f"{sl['deep_water_lifted_km3']:,.0f} km³/yr\n(≈{sl['deep_water_lifted_km3'] * 1e9 / 3.156e7 / 209000:.0f}× the Amazon's discharge);\n"
        f"cost +€{sl['total_cost_beur'] - S['kelp_led']['total_cost_beur']:.0f} bn/yr vs depth cycling",
        transform=ax.transAxes, va="top", fontsize=7.3)
fig.tight_layout()
fig.savefig(OUT / "fig5_nutrient_supply.png", dpi=200)

# ------------------------------------------------------------------ Fig 6 nuclear biorefinery per dry tonne
R = nroutes(Feed())
order = [("NUC_EH", "Ferment → ethanol,\nHTL of residue\n(proposed design)"), ("NUC_H", "Whole-kelp HTL\n→ diesel/jet"),
         ("NUC_A", "Anaerobic digestion\n→ biomethane")]
fig, axs = plt.subplots(1, 2, figsize=(10.5, 4.2), gridspec_kw={"width_ratios": [1.3, 1]})
ax = axs[0]
x = np.arange(len(order))
eth = [R[k]["ethanol_gj"] for k, _ in order]; hc = [R[k]["hc_gj"] for k, _ in order]; ch4 = [R[k]["ch4_gj"] for k, _ in order]
fe = [R[k]["fert_energy_gj"] for k, _ in order]
el = [-R[k]["el_mwh"] * 3.6 for k, _ in order]; st = [-R[k]["heat_mwh_th"] * 3.6 for k, _ in order]
ax.bar(x, eth, color="#fec44f", label="Ethanol (→ jet via ATJ, or ED95/E100)")
ax.bar(x, hc, bottom=eth, color="#08519c", label="HTL renewable diesel / jet")
ax.bar(x, ch4, bottom=np.add(eth, hc), color="#41ab5d", label="Biomethane (fleet + export)")
ax.bar(x, fe, bottom=np.add(np.add(eth, hc), ch4), color="#bcbddc", hatch="//", label="Fertiliser: synthesis energy avoided")
ax.bar(x, el, color="#fb6a4a", label="Electricity in (incl. SOEC hydrogen)")
ax.bar(x, st, bottom=el, color="#a50f15", label="Nuclear steam in")
ax.axhline(0, color="black", lw=0.6)
ax.set_xticks(x); ax.set_xticklabels([o[1] for o in order], fontsize=7.5)
ax.set_ylabel("GJ per dry tonne (kelp holds 13.5 GJ HHV)")
ax.set_title("a  Nuclear biorefinery balances, no thermal drying", loc="left", fontsize=9)
ax.legend(fontsize=6.8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
ax.set_ylim(-4.5, 10)
ax = axs[1]
fz = R["NUC_EH"]
items = [("N", fz["fert_n_kg"]), ("P", fz["fert_p_kg"]), ("K", fz["fert_k_kg"])]
ax.bar([i[0] for i in items], [i[1] for i in items], color=["#2171b5", "#6a51a3", "#cb181d"])
for i, (n, v) in enumerate(items):
    ax.text(i, v + 0.8, f"{v:.1f} kg", ha="center", fontsize=8)
kl = S["kelp_led"]
ax.set_ylabel("kg recovered per dry tonne of kelp")
ax.set_title("b  Fertiliser recovered", loc="left", fontsize=9)
ax.text(0.03, 0.97, f"Kelp-led design: N {kl['fertiliser_mt']['N']:.2f} Mt, P {kl['fertiliser_mt']['P']:.2f} Mt, "
        f"K {kl['fertiliser_mt']['K']:.1f} Mt/yr\nSpain uses ≈1.0 Mt N, 0.17 Mt P, 0.33 Mt K/yr\n"
        f"Synthesis energy avoided {kl['fertiliser_energy_avoided_pj']:.0f} PJ/yr "
        f"({kl['fertiliser_energy_avoided_pj'] / 3.6:.0f} TWh, mostly gas);\nCO₂ avoided {kl['fertiliser_co2_avoided_mt']:.1f} Mt/yr; "
        f"sales €{kl['fertiliser_value_beur']:.1f} bn/yr", transform=ax.transAxes, va="top", fontsize=7.2)
ax.set_ylim(0, 60)
fig.tight_layout()
fig.savefig(OUT / "fig6_nuclear_biorefinery.png", dpi=200)

# ------------------------------------------------------------------ Fig 7 scenario costs
names = [("open_least_cost", "Technology-open least cost"),
         ("liquid_required", "Liquid fuel required for aviation,\nheavy equipment and ½ of trucks"),
         ("liquid_required_no_kelp", "  … same, without kelp"),
         ("kelp_led", "Kelp supplies all those liquids\n(deep ocean, depth cycling)"),
         ("kelp_led_nuclear_refineries", "  … with all-nuclear biorefineries\n(steam + power)"),
         ("your_design", "  … proposed design: ethanol + HTL,\nall-nuclear refineries"),
         ("kelp_led_ethanol_route", "  … ethanol + HTL route only"),
         ("kelp_led_solar_upwelling", "  … nutrients by pumped upwelling"),
         ("kelp_led_optimistic", "  … optimistic kelp\n(€150/t base, full alginate use)"),
         ("liquid_required_domestic", "Domestic transport only,\nliquid required"),
         ("kelp_led_domestic", "Domestic only, kelp-led")]
fig, axs = plt.subplots(1, 2, figsize=(11.5, 5.9), gridspec_kw={"width_ratios": [1.35, 1]})
yy = np.arange(len(names))[::-1]
ax = axs[0]
tc = [S[k]["total_cost_beur"] for k, _ in names]
f26 = [S[k]["fossil_cost_beur"]["oct2026"] for k, _ in names]
f25 = [S[k]["fossil_cost_beur"]["avg2025"] for k, _ in names]
ax.barh(yy, tc, color=["#238b45" if (k.startswith("kelp_led") or k == "your_design") else "#6baed6" for k, _ in names])
ax.scatter(f26, yy, marker="|", s=260, color="black", zorder=5, label="fossil, Oct 2026 prices")
ax.scatter(f25, yy, marker="|", s=260, color="#969696", zorder=5, label="fossil, 2025 prices")
for y, v, a1, a2 in zip(yy, tc, f26, f25):
    ax.text(max(v, a1, a2) + 2, y, f"€{v:.0f} bn", va="center", fontsize=7.3)
ax.set_yticks(yy); ax.set_yticklabels([n for _, n in names], fontsize=7.2)
ax.set_xlabel("€ bn/yr, pre-tax energy supply (vehicle capital excluded)")
ax.set_title("a  Annual cost", loc="left", fontsize=9)
ax.legend(fontsize=7, frameon=False, loc="lower right")
ax = axs[1]
ka = [S[k]["kelp_total_km2"] / 1000 for k, _ in names]
ax.barh(yy, ka, color="#74c476")
for y, (k, _) in zip(yy, names):
    s = S[k]
    ax.text(ka[list(yy).index(y)] + 1, y, f"{s['kelp_dry_mt']:.0f} Mt dry; {s['kelp_share_pct']:.0f}% of energy", va="center", fontsize=7.0)
ax.set_yticks(yy); ax.set_yticklabels([])
ax.set_xlim(0, 115)
ax.set_xlabel("Kelp farm area, thousand km²")
ax.set_title("b  Kelp farms", loc="left", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "fig7_scenarios.png", dpi=200)

# ------------------------------------------------------------------ Fig 8 build list (capital)
sel = [("open_least_cost", "Technology-open"), ("liquid_required", "Liquid required"),
       ("kelp_led", "Kelp-led"), ("your_design", "Proposed design")]
cats = ["PV", "Onshore wind", "Offshore wind", "CSP", "New nuclear", "Nuclear life extension", "Electrolysers",
        "E-fuel synthesis", "DAC", "Kelp farms", "Biorefineries", "Vessels", "ATJ plants", "Charging and grid"]
cc = ["#fdb863", "#4393c3", "#2166ac", "#d6604d", "#762a83", "#c2a5cf", "#b2abd2", "#8073ac", "#969696",
      "#238b45", "#74c476", "#00441b", "#fec44f", "#542788"]
fig, axs = plt.subplots(1, 2, figsize=(11.5, 4.8), gridspec_kw={"width_ratios": [1.1, 1]})
ax = axs[0]
x = np.arange(len(sel)); bottom = np.zeros(len(sel))
for cat, col in zip(cats, cc):
    v = np.array([S[k]["build"]["capex_beur"].get(cat, 0.0) for k, _ in sel])
    if v.max() < 0.5:
        continue
    ax.bar(x, v, bottom=bottom, color=col, label=cat, width=0.6)
    bottom += v
for i, (k, _) in enumerate(sel):
    b = S[k]["build"]
    ax.text(i, bottom[i] + 8, f"€{b['capex_total_beur']:.0f} bn\n(€{b['capex_per_year_2027_2050_beur']:.0f} bn/yr)", ha="center", fontsize=7.3)
ax.set_xticks(x); ax.set_xticklabels([s for _, s in sel], fontsize=7.8)
ax.set_ylabel("Capital investment, € bn (2027–2050)")
ax.set_ylim(0, bottom.max() * 1.18)
ax.set_title("a  Capital needed", loc="left", fontsize=9)
ax.legend(fontsize=6.6, frameon=False, ncol=2, loc="upper left")
ax = axs[1]; ax.axis("off")
rows = [("PV (GW)", "PV, GW"), ("Onshore wind (GW)", "Onshore wind, GW"), ("Nuclear life extension (GW)", "Nuclear kept open, GW"),
        ("New nuclear (1.1 GW units)", "New 1.1 GW reactors"), ("Electrolysers (GW)", "Electrolysers, GW"),
        ("Kelp farms (km2)", "Kelp farms, km²"), ("Kelp (Mt wet/yr)", "Kelp harvest, Mt wet/yr"),
        ("Biorefineries (2 Mt dry/yr each)", "Biorefineries (2 Mt dry/yr)"), ("Harvest/transport vessels (1 Mt wet/yr each)", "Vessels (1 Mt wet/yr)")]
tab = [[lab] + [f"{S[k]['build'][key]:,.0f}" for k, _ in sel] for key, lab in rows]
tab += [["Electricity, TWh/yr"] + [f"{S[k]['electricity_delivered_twh']:,.0f}" for k, _ in sel]]
t = ax.table(cellText=tab, colLabels=["", "Tech-open", "Liquid req.", "Kelp-led", "Proposed"], loc="center",
             cellLoc="right", colLoc="center", colWidths=[0.40, 0.15, 0.15, 0.15, 0.15])
t.auto_set_font_size(False); t.set_fontsize(7.2); t.scale(1, 1.35)
for (r, cidx), cell in t.get_celld().items():
    cell.set_linewidth(0.3)
    if cidx == 0:
        cell.set_text_props(ha="left")
ax.set_title("b  What has to be built", loc="left", fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "fig8_build_list.png", dpi=200)
print("figures ok")
