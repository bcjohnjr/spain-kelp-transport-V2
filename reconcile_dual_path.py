#!/usr/bin/env python3
"""Recompute dual-path supply costs and screen comparisons from archived model output.
This reconciles scenario datasets; it does NOT claim to optimize a new model.
"""
from pathlib import Path
import csv,json
base=Path(__file__).resolve().parents[1]
annual=list(csv.DictReader(open(base/'Source_Data/transition_annual_2027_2041.csv')))
meta=json.load(open(base/'Source_Data/dual_model_summary.json'))
for r in annual:
 sup=sum(float(r[x]) for x in ['transport_supply_billion_EUR','idle_farm_annuitized_billion_EUR','idle_CSP_annuitized_billion_EUR'])
 net=sup-float(r['fish_sector_cash_margin_million_EUR'])/1000
 assert abs(net-float(r['supplier_net_bn']))<5e-8,(r['year'],net,r['supplier_net_bn'])
 assert float(r['fossil_oct_bn'])>0
end=annual[-1];fossil=float(end['fossil_oct_bn'])
assert end['year']=='2041' and float(end['all_transport_fossil_TWh'])==0
assert abs(float(end['transport_supply_billion_EUR'])-56.218411661)<1e-5
assert abs(meta['static_median']-50.51084634792244)<1e-8
assert meta['static_p5']<meta['static_median']<meta['static_p95']
print('Transition supplier net, 2041: %.3f EUR bn/y'%float(end['supplier_net_bn']))
print('Completed learning: %.3f EUR bn/y'%meta['static_learning'])
print('Completed Monte Carlo p5/median/p95: %.3f / %.3f / %.3f EUR bn/y'%(meta['static_p5'],meta['static_median'],meta['static_p95']))
print('Same-demand fossil, Oct-2026 pricing: %.3f EUR bn/y'%fossil)
print('Terminal supplier saving: %.1f%%'%((fossil-float(end['supplier_net_bn']))/fossil*100))
print('Supplier-to-static learning cost difference: %.3f EUR bn/y'%(float(end['transport_supply_billion_EUR'])-meta['static_learning']))
print('Checks passed')
