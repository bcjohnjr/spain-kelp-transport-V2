#!/usr/bin/env python3
"""Re-run the 2041 kelp-yield stress tests using the V15 archived source model.
Requires numpy and scipy. Outputs Source_Data/V16_KELP_YIELD_REOPTIMIZATION_REBUILT.csv
Do not confuse this with a full rerun of the 1000-draw static Monte Carlo.
"""
import csv,json,sys,tempfile,zipfile,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix='v16_yield_') as temp:
 with zipfile.ZipFile(BASE/'Code'/'Original_Models_and_Source_Data.zip') as z: z.extractall(temp)
 root=Path(temp)/'SOURCE_MODEL_SNAPSHOT'/'Spain_Integrated_Circular_Marine_Energy_V13_Full_Restoration'
 legacy=root/'Integrated_Cactus_Feed_Legacy_V4';legacy.mkdir(parents=True,exist_ok=True)
 shutil.copy2(BASE/'Code'/'MISSING_LEGACY_DEPENDENCY'/'model_v4.py',legacy/'model_v4.py')
 sys.path.insert(0,str(root/'V13_Restored_Model'))
 import run_transition_v13 as r
 raw_build=r.build_case
 records=[]
 for yield_t,kelp_min in [(20,50),(15,50),(10,50),(10,0),(5.4,50),(5.4,0)]:
  def custom_build(*args,**kwargs):
   over=dict(kwargs.get('overrides',{}))
   over['zone_yield']={zone:float(yield_t) for zone in ('nor_shelf','nor_slope','nor_deep')}
   kwargs['overrides']=over
   return raw_build(*args,**kwargs)
  r.build_case=custom_build
  original_solve=r.opt.solve
  def custom_solve(params):
   params['kelp_HTL_min_TWh_y']=float(kelp_min)
   return original_solve(params)
  r.opt.solve=custom_solve
  row={'yield_t_ha':yield_t,'kelp_min_TWh':kelp_min,'status':'optimal'}
  try:
   a=r.run_one(2041)
   for k in ('transport_supply_billion_EUR','idle_farm_annuitized_billion_EUR','idle_CSP_annuitized_billion_EUR','kelp_km2'):
    row[k]=a[k]
   row['net_supplier_bn']=sum(a[k] for k in ('transport_supply_billion_EUR','idle_farm_annuitized_billion_EUR','idle_CSP_annuitized_billion_EUR'))-a['fish_sector_cash_margin_million_EUR']/1000
   row['fossil_2026_bn']=a['fossil_bill_same_demand_oct2026_billion_EUR']
  except Exception as e:row.update(status='infeasible',detail=str(e)[:140])
  records.append(row);r.opt.solve=original_solve
 fields=['yield_t_ha','kelp_min_TWh','status','transport_supply_billion_EUR','idle_farm_annuitized_billion_EUR','idle_CSP_annuitized_billion_EUR','net_supplier_bn','fossil_2026_bn','kelp_km2','detail']
 output=BASE/'Source_Data'/'V16_KELP_YIELD_REOPTIMIZATION_REBUILT.csv'
 with open(output,'w',newline='') as fh:
  writer=csv.DictWriter(fh,fieldnames=fields);writer.writeheader()
  for row in records:writer.writerow(row)
 print(output)
 for row in records:print(row)
