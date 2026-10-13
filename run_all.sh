#!/usr/bin/env bash
# Reproduce all numerical results and every figure that does not require external GIS data.
# If Natural Earth 10m files are installed (python3 fetch_natural_earth.py), the marine GIS,
# maps and all main-text figures are rebuilt as well.
set -euo pipefail
cd "$(dirname "$0")"
python3 cascade.py
python3 deep_farm.py
python3 nuclear_refinery.py
python3 optimise.py
python3 levers.py
python3 lowcost.py
python3 paper_analyses.py
python3 robustness.py
python3 harvester_slurry.py
python3 harvester_turns.py
python3 figures_cascades.py

NE="${NATURAL_EARTH_DIR:-data/naturalearth}"
have_bathy() { [[ -f "$NE/10m_physical/ne_10m_bathymetry_$1.shp" || -f "$NE/10m_physical/ne_10m_bathymetry_all/ne_10m_bathymetry_$1.shp" ]]; }
if [[ -f "$NE/10m_physical/ne_10m_land.shp" && -f "$NE/10m_cultural/ne_10m_admin_0_countries.shp" ]] && have_bathy K_200 && have_bathy J_1000; then
  python3 spatial.py
  python3 map_figure.py
  python3 figures.py
  python3 paper_figures.py      # Figs 1, 2, 4, 7, 8 and option_penalties.json
else
  echo "Natural Earth files not present: numerical results reproduced; committed spatial outputs and Figs 1, 2, 4, 7, 8 retained."
  echo "Run 'python3 fetch_natural_earth.py' once to enable full map regeneration."
fi
python3 grid_harvester_figure.py  # Fig 3
python3 cost_figure.py          # Fig 5
python3 lifecycle_figure.py     # Fig 6
python3 source_data.py          # one Source Data workbook per main-text figure
