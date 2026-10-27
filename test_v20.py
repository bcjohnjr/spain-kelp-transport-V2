#!/usr/bin/env python3
"""Minimal replay / conservation assertions for the V20 addendum."""
import json, csv, math, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).parent
subprocess.run([sys.executable, str(ROOT/'model_v20.py')],check=True,capture_output=True,text=True)
s=json.loads((ROOT/'outputs/V20_SUMMARY.json').read_text())
rows=list(csv.DictReader((ROOT/'outputs/V20_CARGO_FLEET_100_YEAR_SENSITIVITY.csv').open()))
sel=lambda kit,speed,life: next(r for r in rows if r['kit']==kit and float(r['speed_kn'])==speed and float(r['hull_lifetime_y'])==life)
# Correction: pv+kite must carry nonzero kite/pv/storage module cost.
r=sel('pv_kite',7,100)
assert float(r['module_cost_meur_y'])>10, r
assert abs(float(r['net_saving_meur_y']) - 29.85813227631416)<1e-7
assert abs(s['best_financial_cargo_fleet']['net_saving_meur_y']-36.309926941377)<1e-7
assert s['best_financial_cargo_fleet']['hull_lifetime_y']==100
assert s['controls']['100yr_hull_is_sensitivity_not_guarantee']
assert s['illustrative_autonomous_support']['fuel_energy_saved_twh']<s['baseline_v18']['harvest_support_twh_fuel_eq']
assert s['illustrative_autonomous_support']['remaining_support_fuel_energy_twh']>2.9
assert abs(s['controls']['harvester_pv_plus_vawt_delivered_gwh_y']-51.8361312)<1e-6
assert all(float(q['marine_transport_twh_fuel_eq'])>=0 for q in rows)
assert len(rows)==60
print('V20: PASS — 9 preservation-independent functional & financial assertions')
