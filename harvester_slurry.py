"""Grid Harvester energy versus slurry concentration (wet kelp mass fraction in the hose).

Starting point: the optimized Grid Harvester (6-m head, 100-m span, 51.6-m hose, 3 kn, 416.7 t wet/h) at
conventional-vessel C_DA = 30 m2 with an 85% hose fairing: pump 17.78 MJ, hose form drag 3.82 MJ, hose skin
friction 0.97 MJ, head + vessel 11.35 MJ per 1.44-ha cycle (grid 33.92 MJ); conventional vessel 90.9 MJ.
Pump model as in the harvester code: static head 0.50 m, minor-loss K = 4.0, efficiency 0.72.
Higher wet-kelp fraction c means less water pumped: Q = m_wet / (c * rho).
Cases: hose kept at 1.20 m; hose resized to keep 1.0 m/s (form and skin drag scale with diameter);
water-like rheology vs a pessimistic Bingham-plastic macerated-kelp slurry; optional size-reduction energy.
"""
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent / "outputs"
RHO, G = 1025.0, 9.81
M_WET = 416.7e3 / 3600            # kg/s wet kelp
L_HOSE = 51.6
STATIC, K, ETA = 0.50, 4.0, 0.72
MU_W = 0.0012
DM = 0.13                         # dry matter of wet kelp
BASE = dict(pump=17.78, form=3.82, skin=0.97, other=11.35, d=1.20, c=0.10)
CONV = 90.9
WET_PER_CYCLE_T = 180.0           # 12.5 kg/m2 x 1.44 ha


def friction_factor(re, d, eps=5e-5):
    if re < 2300:
        return 64 / max(re, 1)
    return 0.25 / (np.log10(eps / (3.7 * d) + 5.74 / re ** 0.9)) ** 2


def pump_head(c, d, rheology="water"):
    q = M_WET / (c * RHO)
    v = q / (np.pi * d ** 2 / 4)
    ds = c * DM * 100                                     # dry solids, % of slurry
    if rheology == "water":
        mu, tau_y = MU_W, 0.0
    else:                                                 # pessimistic macerated-kelp slurry (pulp-like)
        mu, tau_y = MU_W * (1 + 3 * ds), 2.0 * ds ** 2
    f = friction_factor(RHO * v * d / mu, d)
    h = STATIC + (K + f * L_HOSE / d) * v ** 2 / (2 * G) + 4 * tau_y * L_HOSE / (d * RHO * G)
    return q, v, h


_, _, h0 = pump_head(BASE["c"], BASE["d"])
q0 = M_WET / (BASE["c"] * RHO)
T_CYCLE = BASE["pump"] * 1e6 / (RHO * G * q0 * h0 / ETA)      # s, calibrated to the published 17.78 MJ


def grid_energy(c, resize=False, rheology="water", macerate_kwh_t=0.0, v_target=1.0, d_min=0.30):
    q = M_WET / (c * RHO)
    d = max(d_min, min(BASE["d"], np.sqrt(4 * q / (np.pi * v_target)))) if resize else BASE["d"]
    q, v, h = pump_head(c, d, rheology)
    pump = RHO * G * q * h / ETA * T_CYCLE / 1e6
    form = BASE["form"] * d / BASE["d"]
    skin = BASE["skin"] * d / BASE["d"]
    mac = macerate_kwh_t * WET_PER_CYCLE_T * 3.6
    total = pump + form + skin + BASE["other"] + mac
    return dict(c=c, d=d, v=v, head_m=h, pump=pump, form=form, skin=skin, other=BASE["other"], macerate=mac,
                total=total, ratio=CONV / total, water_t_per_wet_t=(1 - c) / c)


if __name__ == "__main__":
    cs = np.round(np.arange(0.05, 0.505, 0.01), 3)
    cases = {
        "1.20-m hose, water-like": dict(resize=False),
        "hose resized to 1 m/s, water-like": dict(resize=True),
        "hose resized, pessimistic slurry": dict(resize=True, rheology="bingham"),
        "resized + coarse chopping 0.2 kWh/t": dict(resize=True, macerate_kwh_t=0.2),
        "resized + fine maceration 1.0 kWh/t": dict(resize=True, macerate_kwh_t=1.0),
    }
    res = {k: [grid_energy(c, **kw) for c in cs] for k, kw in cases.items()}
    pick = {}
    for k in res:
        pick[k] = {f"{c:.2f}": res[k][list(cs).index(c)] for c in (0.10, 0.20, 0.30, 0.40)}
    json.dump({"T_cycle_s": T_CYCLE, "base_head_m": h0, "cases": pick}, open(OUT / "harvester_slurry.json", "w"), indent=1, default=float)
    print(f"cycle time {T_CYCLE:.0f} s, base head {h0:.3f} m")
    for k, v in pick.items():
        print(k)
        for c, r in v.items():
            print(f"  c={c}: D={r['d']:.2f} m v={r['v']:.2f} H={r['head_m']:.2f} m pump={r['pump']:.1f} form={r['form']:.1f} "
                  f"mac={r['macerate']:.0f} total={r['total']:.1f} MJ ratio={r['ratio']:.2f} water/wet={r['water_t_per_wet_t']:.1f}")
    # figure
    plt.rcParams.update({"font.size": 8, "axes.spines.top": False, "axes.spines.right": False})
    fig, axs = plt.subplots(1, 2, figsize=(10, 4.4))
    nice = {"1.20-m hose, water-like": "1.20-m hose, water-like slurry",
            "hose resized to 1 m/s, water-like": "Hose resized to 1 m/s, water-like slurry",
            "hose resized, pessimistic slurry": "Hose resized, pulp-like (Bingham) slurry",
            "resized + coarse chopping 0.2 kWh/t": "Resized + coarse chopping at sea (0.2 kWh/t)",
            "resized + fine maceration 1.0 kWh/t": "Resized + fine maceration at sea (1.0 kWh/t)"}
    cols = ["#2a78d6", "#1baf7a", "#eda100", "#eb6834", "#e34948"]
    for (k, rr), col in zip(res.items(), cols):
        axs[0].plot(cs * 100, [r["total"] for r in rr], color=col, lw=1.6, label=nice[k])
        axs[1].plot(cs * 100, [r["ratio"] for r in rr], color=col, lw=1.6)
    axs[0].axhline(CONV, color="#52514e", ls="--", lw=0.8); axs[0].text(49, CONV * 1.08, "conventional vessel 90.9 MJ", ha="right", fontsize=7)
    axs[0].set_yscale("log"); axs[0].set_ylim(10, 1000); axs[0].set_xlabel("Wet kelp in hose slurry (% by mass)"); axs[0].set_ylabel("Grid energy per 1.44-ha cycle (MJ)")
    axs[0].set_title("a  Harvester energy", loc="left", fontsize=9)
    axs[1].axhline(1, color="#52514e", lw=0.6); axs[1].axvline(10, color="#8a8984", ls=":", lw=0.8)
    axs[1].text(10.5, 0.3, "current design (10%)", fontsize=7, color="#52514e")
    axs[1].set_ylim(0, 6); axs[1].set_xlabel("Wet kelp in hose slurry (% by mass)"); axs[1].set_ylabel("Conventional / grid energy ratio")
    axs[1].set_title("b  Advantage over a conventional vessel", loc="left", fontsize=9)
    fig.legend(fontsize=7, frameon=False, loc="lower center", ncol=3)
    fig.tight_layout(rect=(0, 0.11, 1, 1))
    fig.savefig(OUT / "fig12_harvester_slurry.png", dpi=220)
    print("ok")
