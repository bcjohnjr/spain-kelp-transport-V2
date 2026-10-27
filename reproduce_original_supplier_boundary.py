#!/usr/bin/env python3
"""Verify operator-only costs and conditional fish-margin credit using supplied annual LP output."""
from pathlib import Path
import pandas as pd
r=Path(__file__).resolve().parent
x=pd.read_csv(r/'Source_Data'/'SUPPLIER_BOUNDARY_2027_2041.csv')
assert len(x)==15 and x.year.iloc[0]==2027 and x.year.iloc[-1]==2041
assert (x.vehicle_charges_excluded_bn>=0).all()
assert ((x.supplier_gross_bn-(x.transport_supply_billion_EUR+x.idle_farm_annuitized_billion_EUR+x.idle_CSP_annuitized_billion_EUR)).abs()<1e-7).all()
assert ((x.supplier_net_bn-(x.supplier_gross_bn-x.fish_sector_cash_margin_million_EUR/1000)).abs()<1e-7).all()
assert abs(x.iloc[-1].supplier_net_bn-56.095139388)<0.01
assert abs(x.iloc[-1].all_transport_fossil_TWh)<1e-8
assert x.loc[x.supplier_net_bn<x.fossil_oct_bn,'year'].iloc[0]==2036
print('PASS: 15 annual records; supplier boundary excludes private fleet capital; terminal gross cost %.3f bn, fish margin %.3f bn, net %.3f bn, fossil comparator %.3f bn; crossover %d' % (x.iloc[-1].supplier_gross_bn,x.iloc[-1].fish_sector_cash_margin_million_EUR/1000,x.iloc[-1].supplier_net_bn,x.iloc[-1].fossil_oct_bn,2036))
