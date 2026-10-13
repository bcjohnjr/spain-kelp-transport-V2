"""Area missed or harvested twice in the turns of a conventional vessel and of the Grid Harvester.

Geometry (Fig. 3c-f):
- Conventional vessel of width W_cv harvesting a W x L field in a spiral with n 90-degree turns of radius R = W_cv:
  each turn leaves the corner (1 - pi/4) R^2 unharvested.
- Grid Harvester head of width W_hh = 2R sweeping laps across the farm while the primary vessel advances W_hh per lap;
  one 180-degree turn per lap end:
    turning while moving forward:  missed 2(4 - pi) R^2 per turn; with two lawn-mower moves (LMM) nothing is missed
                                   but (8 - 2(4 - pi)) R^2 is harvested twice;
    turning in place (stationary): missed (2 - pi/2) R^2 per turn; with LMMs nothing is missed but 2 R^2 is
                                   harvested twice.
Conventional configuration: 10-m vessel, 60 m x 240 m field (1.44 ha), 10 turns.
Grid Harvester: optimized geometry of the harvester model, 6-m head and 100-m cross-track span; the 1.44-ha cycle is
therefore 144 m long along the transport cable, i.e. 24 laps and 23 turns.
"""
import json
from math import pi
from pathlib import Path

OUT = Path(__file__).resolve().parent / "outputs"
CYCLE_M2 = 14_400.0


def conventional(w_cv=10.0, n_turns=10):
    r = w_cv
    missed = n_turns * (1 - pi / 4) * r ** 2
    return {"vessel_width_m": w_cv, "turns_90deg": n_turns, "missed_m2": missed, "missed_pct": missed / CYCLE_M2 * 100}


def grid(head_m=6.0, span_m=100.0):
    r = head_m / 2
    laps = round(CYCLE_M2 / span_m / head_m)
    turns = laps - 1
    out = {"head_width_m": head_m, "span_m": span_m, "laps": laps, "turns_180deg": turns}
    for mode, miss, twice in (("forward", 2 * (4 - pi), 8 - 2 * (4 - pi)), ("stationary", 2 - pi / 2, 2.0)):
        out[mode] = {"missed_per_turn_m2": miss * r ** 2, "missed_m2": turns * miss * r ** 2,
                     "missed_pct": turns * miss * r ** 2 / CYCLE_M2 * 100,
                     "lmm_twice_per_turn_m2": twice * r ** 2, "lmm_twice_m2": turns * twice * r ** 2,
                     "lmm_twice_pct": turns * twice * r ** 2 / CYCLE_M2 * 100}
    return out


def main():
    res = {"cycle_area_m2": CYCLE_M2, "conventional": conventional(), "grid": grid()}
    json.dump(res, open(OUT / "harvester_turns.json", "w"), indent=1)
    return res


if __name__ == "__main__":
    r = main()
    c, g = r["conventional"], r["grid"]
    print(f"conventional: missed {c['missed_m2']:.0f} m2 ({c['missed_pct']:.2f}%)")
    for m in ("forward", "stationary"):
        print(f"grid {m}: missed {g[m]['missed_m2']:.0f} m2 ({g[m]['missed_pct']:.2f}%), "
              f"with LMM harvested twice {g[m]['lmm_twice_m2']:.0f} m2 ({g[m]['lmm_twice_pct']:.2f}%)")
