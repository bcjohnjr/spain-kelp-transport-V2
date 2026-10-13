"""Shared style for the main-text figures (Nature double-column width, 180 mm)."""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
FIG = HERE / "paper_figures"
FIG.mkdir(exist_ok=True)

# reference categorical palette, fixed order
C = {"blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100", "magenta": "#e87ba4",
     "green": "#008300", "violet": "#6250d6", "red": "#e34948"}
INK, INK2, MUTED, GRID = "#0b0b0b", "#52514e", "#8a8984", "#e6e5e1"
MM = 1 / 25.4

plt.rcParams.update({"font.size": 7, "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.titlesize": 7.5, "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
                     "axes.grid": False, "savefig.dpi": 300, "pdf.fonttype": 42})


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=300)
    fig.savefig(FIG / f"{name}.pdf")
    plt.close(fig)


def hgrid(ax):
    ax.grid(axis="x", color=GRID, lw=0.5); ax.set_axisbelow(True)


def vgrid(ax):
    ax.grid(axis="y", color=GRID, lw=0.5); ax.set_axisbelow(True)


# ---------------------------------------------------------------- source data (exact values plotted)
SOURCE = {}


def record(fig_name, panel, columns, rows, note=""):
    """Store the values plotted in one panel; written by dump_source() and turned into Excel by source_data.py."""
    SOURCE.setdefault(fig_name, {})[panel] = {"columns": list(columns), "rows": [list(r) for r in rows], "note": note}


def dump_source(fig_name):
    import json
    d = OUT / "source_data"; d.mkdir(exist_ok=True)
    json.dump(SOURCE[fig_name], open(d / f"{fig_name}.json", "w"), indent=1,
              default=lambda v: float(v) if hasattr(v, "__float__") else str(v))
