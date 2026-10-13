"""Figures 2-3: floating-wind/kelp co-location layout; pyrolysis-first vs AD-first cascades per dry tonne."""
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Patch
from matplotlib.lines import Line2D

from cascade import P, Coloc, all_routes, colocation

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
plt.rcParams.update({"font.size": 8.5, "axes.spines.top": False, "axes.spines.right": False})

# ------------------------------------------------------------------ Fig 2 co-location layout
c = Coloc(); col = colocation(c)
s = col["spacing_km"]; r = col["mooring_radius_km"]
fig, ax = plt.subplots(figsize=(7.2, 6.4))
nx, ny = 3, 3
clear = c.line_clearance_m / 1000
for i in range(nx):
    for j in range(ny):
        x0, y0 = i * s, j * s
        # cable corridor + access lane along each turbine row (east-west)
        ax.add_patch(Rectangle((-0.5 * s, y0 - (c.cable_corridor_m + c.access_lane_m) / 2000), nx * s,
                               (c.cable_corridor_m + c.access_lane_m) / 1000, color="#fde0dd", lw=0, zorder=1))
for i in range(nx):
    for j in range(ny):
        x0, y0 = i * s, j * s
        for k, ang in enumerate((90, 210, 330)):
            a = np.radians(ang)
            xe, ye = x0 + r * np.cos(a), y0 + r * np.sin(a)
            # clearance strip around mooring line
            nxv, nyv = -np.sin(a) * clear, np.cos(a) * clear
            ax.fill([x0 + nxv, xe + nxv, xe - nxv, x0 - nxv], [y0 + nyv, ye + nyv, ye - nyv, y0 - nyv],
                    color="#fdd0a2", lw=0, zorder=2)
            ax.plot([x0, xe], [y0, ye], color="#7f2704", lw=1.0, zorder=4)
            ax.plot(xe, ye, "s", color="#7f2704", ms=3, zorder=4)
        ax.add_patch(Circle((x0, y0), c.platform_keepout_m / 1000, color="#fdae6b", zorder=3))
        ax.plot(x0, y0, marker=(3, 0, 0), color="black", ms=11, zorder=5)
# kelp longline rows (north-south), skipping excluded strips
xs = np.arange(-0.5 * s + 0.05, (nx - 0.5) * s, 0.06)
excl_poly = []
for x in xs:
    for j in range(ny):
        y_lo = j * s + (c.cable_corridor_m + c.access_lane_m) / 2000
        y_hi = (j + 1) * s - (c.cable_corridor_m + c.access_lane_m) / 2000
        if j == ny - 1:
            y_hi = (ny - 0.5) * s
        yy = np.linspace(y_lo, y_hi, 120)
        ok = np.ones_like(yy, bool)
        for i in range(nx):
            for jj in range(ny):
                x0, y0 = i * s, jj * s
                if np.hypot(x - x0, 0) < 0 and False:
                    pass
                for ang in (90, 210, 330):
                    a = np.radians(ang)
                    # distance from point to mooring segment
                    px, py = x - x0, yy - y0
                    t = np.clip(px * np.cos(a) + py * np.sin(a), 0, r)
                    d = np.hypot(px - t * np.cos(a), py - t * np.sin(a))
                    ok &= d > clear
                ok &= np.hypot(x - x0, yy - y0) > c.platform_keepout_m / 1000
        yy = np.where(ok, yy, np.nan)
        ax.plot(np.full_like(yy, x), yy, color="#1b7837", lw=0.55, zorder=2.5)
    # southern half-row
    yy = np.linspace(-0.5 * s, -(c.cable_corridor_m + c.access_lane_m) / 2000, 60)
    ok = np.ones_like(yy, bool)
    for i in range(nx):
        x0, y0 = i * s, 0
        for ang in (90, 210, 330):
            a = np.radians(ang); px, py = x - x0, yy - y0
            t = np.clip(px * np.cos(a) + py * np.sin(a), 0, r)
            ok &= np.hypot(px - t * np.cos(a), py - t * np.sin(a)) > clear
    ax.plot(np.full_like(yy, x), np.where(ok, yy, np.nan), color="#1b7837", lw=0.55, zorder=2.5)
ax.set_xlim(-0.5 * s, (nx - 0.5) * s); ax.set_ylim(-0.5 * s, (ny - 0.5) * s)
ax.set_aspect("equal"); ax.set_xlabel("km"); ax.set_ylabel("km")
ax.set_title(f"Floating wind with kelp between turbine rows: {c.turbine_mw:.0f} MW turbines, "
             f"{c.spacing_d:.0f}D = {s:.2f} km spacing, {c.depth_m:.0f} m depth", fontsize=9, loc="left")
leg = [Line2D([], [], marker=(3, 0, 0), ls="", color="black", ms=9, label=f"Floating turbine ({col['mw_per_km2']:.1f} MW/km²)"),
       Line2D([], [], color="#7f2704", marker="s", ms=3, label=f"Semi-taut mooring line, {r*1000:.0f} m radius, + {c.line_clearance_m:.0f} m clearance"),
       Patch(color="#fde0dd", label=f"Dynamic-cable corridor + O&M lane ({c.cable_corridor_m + c.access_lane_m:.0f} m)"),
       Patch(color="#fdae6b", label=f"Platform keep-out ({c.platform_keepout_m:.0f} m)"),
       Line2D([], [], color="#1b7837", lw=1.2, label="Kelp longline rows (harvester runs N–S)")]
ax.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, -0.09), ncol=2, fontsize=7.3, frameon=False)
fig.text(0.02, 0.005, f"Geometric usable share {col['usable_frac']*100:.0f}% of farm area; model uses 50% (kelp-grid "
         f"anchors also need room).\nWind {col['gwh_per_km2']:.1f} GWh/km²/yr vs kelp biomethane "
         f"≈{0.5*1500*6.16/3600:.2f} GWh/km²/yr.", fontsize=7, color="#444")
fig.tight_layout(rect=(0, 0.04, 1, 1))
fig.savefig(OUT / "fig2_colocation_layout.png", dpi=220)

# ------------------------------------------------------------------ Fig 3 cascades per dry tonne
p = P(); R = all_routes(p)
el_price = 71  # EUR/MWh, flexible renewable electricity (marginal value in the least-cost system)
order = ["P_self", "P_grid", "P_csp", "A_self", "AP_grid"]
lab = {"P_self": "Pyrolysis-first,\nself-\nsufficient", "P_grid": "Pyrolysis-first,\n+ renewable\npower",
       "P_csp": "Pyrolysis-first,\nCSP drying\n(south)", "A_self": "AD-first,\nself-\nsufficient",
       "AP_grid": "AD-first,\n+ digestate\npyrolysis"}
fig, axs = plt.subplots(1, 2, figsize=(10, 4.0))
x = np.arange(len(order))
liq = [R[k]["net_liquids_gj"] for k in order]; ch4 = [max(R[k]["net_ch4_gj"], 0) for k in order]
el = [-R[k]["el_import_mwh"] * 3.6 for k in order]; csp = [-R[k].get("csp_heat_mwh", 0) * 3.6 for k in order]
deficit = [-R[k].get("self_sufficient_deficit_gj", 0) for k in order]
ax = axs[0]
ax.bar(x, liq, color="#08519c", label="Drop-in liquids (diesel/jet/naphtha)")
ax.bar(x, ch4, bottom=liq, color="#41ab5d", label="Net biomethane exported")
ax.bar(x, el, color="#fdae6b", label="Renewable electricity imported")
ax.bar(x, csp, bottom=el, color="#e6550d", label="CSP heat imported")
ax.bar(x, deficit, color="none", edgecolor="#a50f15", hatch="xxx", label="Unmet energy after burning char (not self-sufficient)")
ax.axhline(0, color="black", lw=0.6)
ax.set_xticks(x); ax.set_xticklabels([lab[k] for k in order], fontsize=7)
ax.set_ylabel("GJ per dry tonne of kelp (out +, in −)")
ax.set_title("a  Net energy per dry tonne (13.5 GJ/t HHV in the kelp)", loc="left", fontsize=9)
ax.legend(fontsize=6.8, frameon=False, loc="upper left")
ax = axs[1]
cost = []
for k in order:
    out_mwh = (R[k]["net_liquids_gj"] + max(R[k]["net_ch4_gj"], 0)) / 3.6
    tot = R[k]["cost_eur"] + R[k]["el_import_mwh"] * el_price
    cost.append(tot / out_mwh if out_mwh > 0.05 else np.nan)
cost_lo = []
for k in order:
    q = P(biomass_cost=100.0, yield_t_ha=20, ch4_nm3_kgvs=0.30, oil_org=0.27, biochar_uplift=0.16)
    rr = all_routes(q)[k]
    out_mwh = (rr["net_liquids_gj"] + max(rr["net_ch4_gj"], 0)) / 3.6
    cost_lo.append((rr["cost_eur"] + rr["el_import_mwh"] * el_price) / out_mwh if out_mwh > 0.05 else np.nan)
ax.bar(x - 0.18, cost, 0.36, color="#6a51a3", label="Central (biomass €300/t dry)")
ax.bar(x + 0.18, cost_lo, 0.36, color="#bcbddc", label="Optimistic (€100/t, higher yields)")
for i, v in enumerate(cost):
    if np.isnan(v):
        ax.text(i, 30, "no net\noutput", ha="center", fontsize=7, color="#a50f15")
refs = [(141, "Diesel/petrol pre-tax, Oct 2026", 5), (89, "Jet, Oct 2026", 5), (83, "Iberian gas, Oct 2026", -17)]
for v, t, dy in refs:
    ax.axhline(v, color="#555", lw=0.7, ls="--"); ax.text(0.55, v + dy, t, fontsize=6.5, ha="left", color="#333")
ax.set_xticks(x); ax.set_xticklabels([lab[k] for k in order], fontsize=7)
ax.set_ylabel("€ per MWh of fuel product (electricity at €%d/MWh)" % el_price)
ax.set_title("b  Production cost of the fuel products", loc="left", fontsize=9)
ax.legend(fontsize=7, frameon=False, loc="upper right")
fig.tight_layout()
fig.savefig(OUT / "fig3_kelp_cascades.png", dpi=220)
print("cascade figures ok")

