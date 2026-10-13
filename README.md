# Low-carbon transport for Spain: electrification and deep-ocean kelp

Code and source data for *Electrification and deep-ocean kelp could cut Spanish transport emissions by 90% for less than the 2026 fuel bill* (Bily, Pahl & Valdés Bacallao).

The model builds an annual least-cost low-carbon supply for the 599.7 TWh of transport energy sold in Spain in 2025 (597.3 TWh of fossil fuels including international aviation and marine bunkers, plus 2.4 TWh of rail electricity). When aviation demand is reduced, the flights shifted to high-speed rail are supplied with rail traction electricity. It combines electrification, existing biofuels, electrofuels, renewable and nuclear electricity and a deep-ocean kelp chain, and adds a screening well-to-wheel lifecycle greenhouse-gas layer, a 1,000-draw Monte Carlo analysis and structural stress tests.

## Reproduce

```bash
python -m pip install -r requirements-lock.txt   # tested environment (Python 3.13)
./run_all.sh
```

Without external downloads, `run_all.sh` reproduces the optimisation, Monte Carlo, lifecycle accounting, robustness tests, break-even multipliers, Grid Harvester turn losses, Figs 3, 5 and 6, the Extended Data figures that do not need maps, and the Source Data workbooks. The committed spatial outputs and Figs 1, 2, 4, 7 and 8 are kept.

To rebuild the marine GIS and every main-text figure from raw public vectors:

```bash
python fetch_natural_earth.py   # Natural Earth 1:10m land, countries, 200 m and 1,000 m bathymetry -> data/naturalearth/
./run_all.sh
```

Either Natural Earth layout is accepted (bathymetry directly in `10m_physical/` or in `10m_physical/ne_10m_bathymetry_all/`). The Global Shipping Lanes dataset is included under `data/shiplanes/` with its licence. A full run takes about 40 s.

## Files

| File | Content |
|---|---|
| `optimise.py` | Annual linear programme (HiGHS) and scenario set |
| `paper_analyses.py` | Headline cases, vehicle premia, Monte Carlo, price exposure and import independence |
| `levers.py`, `lowcost.py` | Cost levers and low-cost variants |
| `lifecycle.py` | Screening well-to-wheel lifecycle GHG accounting and factor sets |
| `robustness.py` | No-kelp, low-yield, marine-area, integration-cost, finance and domestic-scope stress tests; supply sensitivities; break-even price multipliers; vehicle-premium split |
| `deep_farm.py` | Farm zones, yields and nutrient supply |
| `nuclear_refinery.py`, `cascade.py`, `preprocess.py` | Wet biorefinery, cascade and offshore pre-processing balances |
| `harvester_slurry.py` | Grid Harvester hydraulics and slurry sensitivity |
| `harvester_turns.py` | Area missed or harvested twice in the turns of a conventional vessel and of the Grid Harvester head |
| `spatial.py`, `map_figure.py`, `figures.py` | Marine GIS and map figures (needs Natural Earth) |
| `paper_figures.py` | Main-text Figs 1, 2, 4, 7, 8 (needs Natural Earth) |
| `grid_harvester_figure.py`, `cost_figure.py`, `lifecycle_figure.py` | Main-text Figs 3, 5 and 6 |
| `illustrations/` | Grid Harvester illustrations and path and turn diagrams used in Fig. 3 |
| `figstyle.py` | Shared figure style and Source Data recording |
| `source_data.py` | One Source Data workbook per main-text figure |
| `outputs/` | Machine-readable results; `outputs/source_data/` holds the Source Data workbooks |
| `paper_figures/` | Main-text figures (PNG, PDF) |

## Headline results

- **Today's technology costs** (7% cost of capital, current demand): energy supply €69.6 bn yr⁻¹, against a fossil bill of €69.5 bn at October 2026 prices and €41.7 bn at 2025 prices. The incremental purchase price of electric vehicles at normal replacement adds a central €7.5 bn yr⁻¹ (€3.2 bn cars and vans, €4.3 bn heavy trucks and off-road machinery; range €0–17.8 bn).
- **Learning case** (learning, 4% finance, efficiency and modal shift): €42.8 bn yr⁻¹. Its kelp parameters sit at or near the favourable end of the uncertainty ranges, so every Monte Carlo draw costs more.
- **Monte Carlo** (1,000 draws): median €50.5 bn yr⁻¹ (5th–95th percentile €46.1–55.9 bn), or €59.0 bn (€53.0–65.7 bn) including vehicle premia. 981 of 1,000 draws including vehicle premia are below the October 2026 fossil bill; none are below the 2025 bill. These are conditional frequencies, not forecast probabilities.
- **Break-even**: the median draw breaks even at 1.26× 2025 average fossil prices (1.47× including vehicle premia); October 2026 prices were 1.67× the 2025 average. The learning case breaks even at 1.07× and 1.26×.
- **Lifecycle GHG**: 184.3 → 17.5 MtCO₂e yr⁻¹ (−90.5%; factor sensitivity 85.7–93.8%). Vehicle manufacture is excluded.
- **Stress tests** (learning case): no kelp €48.4 bn; kelp yield 5 t ha⁻¹ yr⁻¹ €47.6 bn; 5% of candidate marine area €43.7 bn; integration adders ×2 €48.0 bn; 7% finance €48.9 bn.

## Interpretation limits

The optimisation is annual, not hourly; integration, storage and network costs are represented by adders and stress-tested, but hourly resource adequacy is not claimed. Fishing pressure is a depth/distance proxy. The lifecycle calculation is a screening assessment based on published factors, not an ISO 14040/44 process LCA. Deep-ocean kelp yield, depth-cycling structures and continuous commercial-scale kelp HTL are scale-up uncertainties, and the stress tests include partial or complete failure of the kelp chain.

## Licence

Code: MIT. Outputs, figures and illustrations: CC BY 4.0. Shipping lanes: Benden (2022), CC BY 4.0. Natural Earth: public domain.
