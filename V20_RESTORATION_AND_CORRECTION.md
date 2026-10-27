# Spain renewable marine fleet — V20 complete-preservation and correction addendum

## Absolute preservation guarantee
This version adds files **without removing or rewriting** any content from the verified V19 restoration package. The following archive members remain unaltered in the delivery:

- `RESTORED_ORIGINAL_ARCHIVES/Spain_V13_FULL_Integrated_Research_Project.zip`: 201,380,200 bytes; 428 entries, including original concept artwork, long-form manuscripts, integrated models and figures.
- `RESTORED_ORIGINAL_ARCHIVES/Spain_Nature_Sustainability_V17_COMPLETE(1).zip`: 9,555,994 bytes; 46 entries.
- `RESTORED_ORIGINAL_ARCHIVES/Spain_Nature_Sustainability_Marine_Hybrid_SMR_V18_COMPLETE.zip`: 12,628,461 bytes; 68 entries.
- All 15 original `V19_Current/` entries, including its 100-year-vessel and utility-drone model and existing manuscripts and report, remain unchanged. The original V19 report remains a **historical** result; V20's corrected cost table supersedes only the V19 solar-plus-kite economic number.

**Integrity:** All 542 original internal archive entries were independently SHA-256 verified against the preservation manifest. All three nested ZIPs and the outer ZIP passed CRC checks. The original archive hash list and entry manifest remain intact. An additional verification list for V20 is included.

## Specific financial correction
The original V19 code omitted the kite capital/maintenance expense for the configuration named `pv_kite`, although it gave the option kite fuel savings. V20 charges that cost in the identical manner as the full-hybrid kite option. No historic files were overwritten to implement the correction.

| Scenario | Marine fuel saving, TWh/year (fuel equivalent) | Net modeled annual financial saving, EUR million/year |
|---|---:|---:|
| 7-knot, 100-year, solar + kite (V19 uncorrected) | 0.2677 | **36.42 — superseded** |
| 7-knot, 100-year, solar + kite (V20 corrected) | 0.2677 | **29.86** |
| 6-knot, 100-year, previously assumed kite configuration | 0.3356 | **36.31** |
| 4.5-knot, 30-year, full wind+solar+kite, maximum fuel saving | 0.5574 | **−21.72** |

The 100-year hull assumption is a **technology sensitivity, not an established vessel life**. Maintenance, renewals, docking, fatigue, inspections and financing can materially change the cost result. V20 includes 30-, 50-, 75- and 100-year scenarios at different capital premiums, maintenance and interest rates.

## Utility drone, perpetual harvesting and solar/wind energy
The V19 and V20 models assume seeding takes place at establishment, then solar-electric utility drones inspect and selectively replant bare patches; full annual reseeding is not assumed. They also allow night operation when stored electricity and available wind provide enough propulsion, subject to weather and storage limits. Both remain **proposed operating concepts** rather than measured fleet efficiencies.

Crucial distinction: 280 modeled solar/wind harvesters deliver approximately 51.84 GWh/year of electricity, sufficient on an **annual energy** basis for the 32.82 GWh/year small collection heads. The inherited 3.545 TWh/year for **all harvesting, seeding and vessel support** is much broader. It includes work that requires a separately audited breakdown, and the V20 screening case therefore does **not** claim solar roofs erase all 3.545 TWh.

In the illustrative 15% support-work avoidance + limited fleet electrification scenario, 0.570 TWh/year fuel energy is saved and 2.975 TWh/year remains. Those numbers represent user-driven scenario assumptions, not a validated operating fleet.

## How to reproduce the corrected current numbers

```
cd V20_Corrected_Marine_Model
python model_v20.py
python test_v20.py
```

The output files use the `V20_` prefix; a snapshot of V19 is retained unmodified. `V20_SUMMARY.json` is the updated screening output; it is **not** a new full national optimization, and none of the historic science documents should be read as independently revalidated by this overlay.
