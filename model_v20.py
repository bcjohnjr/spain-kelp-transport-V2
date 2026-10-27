#!/usr/bin/env python3
"""Spain V20: corrected renewable marine logistics, 100-year-hull sensitivities and utility-drone seeding.

Reconciles prior V18 energy ledgers without pretending the legacy 0.35 GJ/dry-tonne
harvesting/support allowance represents the small electric cutting head. All choices
are explicit scenario assumptions; historical V13/V17/V18 research files preserved.
Runs standalone from local V18_SUMMARY.json; built-in Python standard library only.
"""
import csv, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=json.loads((ROOT/'V18_BASELINE_PRESERVED.json').read_text())
B=DATA['baseline']; A=DATA['assumptions']; oldhead=DATA['harvester']
out=ROOT/'outputs';out.mkdir(exist_ok=True)
DRY=B['dry_kelp_mt_y']*1e6
V18_SUPP=B['harvest_support_twh_fuel_eq']; V18_CARGO=B['cargo_twh_fuel_eq_after_existing_kites']
C=oldhead['head_mwh_electrical_annual']/1e6
# Financially consistent capital recovery incl variable lifetime; hull renewal costs beyond horizon not assumed zero.
def crf(rate, years):return rate/(1-(1+rate)**(-years))
def carrying_cost(capex,life,discount,maint_pct):return capex*(crf(discount,life)+maint_pct)
# Recycled solar electric generation first serves cutting head; remaining energy may serve electrified helper craft.
pv_raw_twh=oldhead['pv_gwh_electrical_annual']/1000
wind_raw_twh=oldhead['wind_gwh_electrical_annual_pre_storage']/1000
renew_delivered_twh=oldhead['renewables_delivered_gwh_electrical']/1000
head_twh=oldhead['head_mwh_electrical_annual']/1e6
assert renew_delivered_twh>=head_twh
# Previous large, undifferentiated fleet allowance reclassified, NOT erased.
# old allowance includes harvesting, tending, planting etc; autonomous robot only spot-replants.
# Repair fractions describe physical fuel efficiency possibilities WITHOUT claiming source has audited breakdown.
# Limits of 0.35 GJ/t were a broad unvalidated fleet allowance; head power independently counted only as diagnostic.
# 'support_reducible' is the amount of 3.55 TWh potentially avoided via elimination of repeated vessel-only work,
# different from electrical substitution supplied by harvester-mounted generation.
BASE_LIFETIME=30; HULL_PRICE=A['vessel_hull_eur']; hull_ref=math.ceil(B['wet_kelp_mt_y']*1e6/(A['vessel_payload_wet_t']*(A['vessel_service_days_y']*24/(2*A['shortsea_oneway_km']/(8*1.852)+A['port_turnaround_h']))))
RATE=.04; PV_LIFE=23; EQUIP_LIFE=20
fuelprice=A['marine_fuel_eur_per_mwh']
# Vessel annualized costs: compare TOTAL hull capital, unlike older incremental-only hulls.
def ships_needed(v):
 cycle=2*A['shortsea_oneway_km']/(v*1.852)+A['port_turnaround_h']
 return math.ceil(B['wet_kelp_mt_y']*1e6/(A['vessel_payload_wet_t']*(A['vessel_service_days_y']*24/cycle)))
# Reference directly reproduces original V18 kite and 8-knot energy; kite credit is not sold twice.
PRE_KITE=V18_CARGO+B['original_kite_savings_twh'];BASE_KITE=A['baseline_kite_fraction']

def fleet_scenario(speed,years,kite=.14,kit='full',pv_life=PV_LIFE,discount=RATE,wind_cf=.20,night_hours=8, hull_maint=.035, hull_capex_multiplier=1.0):
 n=ships_needed(speed)
 # Propulsion fuel per mile~v², auxiliaries time~1/v.
 ratio=speed/A['reference_speed_kn']
 before=PRE_KITE*(A['propulsive_share']*ratio**2+A['auxiliary_share']/ratio)
 aft_kite=before*(1-kite if kit!='legacy' else 1-BASE_KITE)
 pv_raw_mwh=n*A['pv_deck_m2']*A['pv_kwp_m2']*A['pv_specific_kwh_kwp_y']/1000
 # night sailing available whenever wind or stored energy, no artificial solar after dusk.
 vawt_mwh=n*A['wind_generator_kw']*8760*wind_cf*A['wind_generator_net_factor']/1000
 pv_deliv=pv_raw_mwh*A['electric_storage_delivery_fraction'] if kit in ('full','pv_kite') else 0
 vawt_deliv=vawt_mwh*A['electric_storage_delivery_fraction'] if kit=='full' else 0
 elec_mwh=pv_deliv+vawt_deliv
 fuel_equiv_twh=min(aft_kite*A['propulsive_share'],elec_mwh/1e6/A['replaced_engine_fuel_to_shaft_efficiency'])
 net=aft_kite-fuel_equiv_twh
 # 100y lifetime ONLY a sensitivity, carries annual inspections/refits in maint_pct.
 hull_total_annual=n*carrying_cost(HULL_PRICE*hull_capex_multiplier,years,discount,hull_maint)
 # present value of module replacement: annuity over component lifetime (23/20 yrs), independent of hull life
 module_per_ship=0
 if kit in ('full','pv_kite'):
  module_per_ship += carrying_cost(A['pv_deck_eur'],pv_life,discount,.02)
  module_per_ship += carrying_cost(A['battery_electrical_eur'],12,discount,.035)
 if kit in ('full','pv_kite','kite'):
  module_per_ship += carrying_cost(A['wind_assist_kite_eur'],20,discount,.04)
 if kit=='full':module_per_ship+=carrying_cost(A['vawt_eur'],20,discount,.05)
 equip_total_annual=n*module_per_ship
 hull_reference_cost=hull_ref*carrying_cost(HULL_PRICE,BASE_LIFETIME,discount,hull_maint)
 operating_add=(n-hull_ref)*A['vessel_annual_operating_eur']
 annual_saving=(V18_CARGO-net)*1e6*fuelprice-(hull_total_annual-hull_reference_cost)-equip_total_annual-operating_add
 return dict(speed_kn=speed,hull_lifetime_y=years,discount_pct=100*discount,
         kit=kit,vessels=n,night_wind_allowed=bool(night_hours),hull_capex_multiplier=hull_capex_multiplier,
         marine_transport_twh_fuel_eq=net,marine_fuel_saved_twh=V18_CARGO-net,
         electrical_roof_pv_gwh=pv_deliv/1000,electrical_wind_gwh=vawt_deliv/1000,
         hull_capital_difference_meur_y=(hull_total_annual-hull_reference_cost)/1e6,
         module_cost_meur_y=equip_total_annual/1e6,
         operating_difference_meur_y=operating_add/1e6,
         value_of_fuel_saved_meur_y=(V18_CARGO-net)*fuelprice,
         net_saving_meur_y=annual_saving/1e6)

# Seeding at commissioning then drone spot repair: fractions are scenario sweeps, not proven shares.
# Avoid 100%-solar claims: PV/wind at 280 heads delivers only ~52 GWh/y, against 3,545 GWh fuel equivalent.
# Fuel displacement of 40% efficiency engine requires electricity before motor efficiency.
# Explicit offsite renewables may supplement, but those have price/capex and cannot be described as harvester-generated.
seed_maintenance_cases=[]
for work_removed in (0,.05,.15,.30,.50):
 for support_retrofit_pct in (0,.1,.25,.5,1.0):
  for offsite_wind_gwh in (0,250,1000):
   remaining=V18_SUPP*(1-work_removed)
   retro=remaining*support_retrofit_pct
   # electricity supply first covers the cutting head, then charging utility drones/support fleet.
   surplus_elec_twh=max(0,renew_delivered_twh-head_twh)+offsite_wind_gwh/1000
   # Shaft & grid losses -> electrical energy needed = engine fuel * thermal eff / inverter+motor eff.
   el_need_twh=retro*.40/.80
   elec_supplied=min(surplus_elec_twh,el_need_twh)
   fuel_displaced_twh=elec_supplied*.8/.40
   total_saved=V18_SUPP*work_removed+fuel_displaced_twh
   net_remaining=V18_SUPP-total_saved
   seed_maintenance_cases.append(dict(avoided_old_service_pct=work_removed*100,
     electrifiable_remaining_pct=support_retrofit_pct*100,offsite_renewable_gwh=offsite_wind_gwh,
     base_support_twh_fuel_eq=V18_SUPP,harvester_head_electricity_gwh=head_twh*1000,
     delivered_roof_pv_wind_gwh=renew_delivered_twh*1000,
     support_renewable_electricity_used_gwh=elec_supplied*1000,
     fuel_energy_saved_twh=total_saved,remaining_support_fuel_energy_twh=net_remaining,
     gross_fuel_equivalent_value_meur=total_saved*fuelprice,
     offsite_energy_procurement_meur=offsite_wind_gwh*0.075))
# Note: work removal implies no reduction in dry kelp biomass: model assumes autonomous seeding, inspection and lifecycle matched.
# But it is an unexplored counterfactual until time-motion data are obtained.

fleet=[]
for life in [30,50,75,100]:
 for speed in [8,7,6,5,4.5]:
  for kit in ['legacy','pv_kite','full']:
   fleet.append(fleet_scenario(speed,life,kit=kit,night_hours=8))
# Choose by cost, not solely by speed. Any 'legacy' entries retain existing kite credit.
best=max(fleet,key=lambda x:x['net_saving_meur_y'])
tech=max(fleet,key=lambda x:x['marine_fuel_saved_twh'])
# Illustrative: zero new offsite plant, prevent excess support fuel credit.
local=[x for x in seed_maintenance_cases if x['offsite_renewable_gwh']==0]
illustrative=next(x for x in local if x['avoided_old_service_pct']==15 and x['electrifiable_remaining_pct']==25)
# Global solar head electricity cannot displace 3.55TWh support burden; maintain separate buckets.
# Contrast life extension under two discount rates
life_sensitivity=[fleet_scenario(6,life,kit='full',discount=rate,night_hours=8,hull_maint=m,hull_capex_multiplier=premium)
                  for life in (30,50,75,100) for rate in (.04,.07) for m in (.025,.035,.06) for premium in (1.0,1.25,1.5,2.0)]

def writecsv(name, rows):
 with (out/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
writecsv('V20_CARGO_FLEET_100_YEAR_SENSITIVITY.csv',fleet)
writecsv('V20_AUTONOMOUS_SEEDING_AND_SUPPORT_RECLASSIFICATION.csv',seed_maintenance_cases)
writecsv('V20_HULL_LIFETIME_DISCOUNT_MAINTENANCE.csv',life_sensitivity)
# Product assumptions, not verified performance: solar roofs replaced every 23 yrs, battery every 12 yrs,
# hull refurbishments and certification unknown; 100y lifetime is not a proven engineering option.
S={'baseline_v18':B,'controls':{'fuel_eur_mwh':fuelprice,'dry_tonnes_y':DRY,
   'harvester_head_gwh_y':head_twh*1000,'prior_support_fuel_energy_twh':V18_SUPP,
   'harvester_pv_plus_vawt_delivered_gwh_y':renew_delivered_twh*1000,
   '100yr_hull_is_sensitivity_not_guarantee':True,'solar_roof_replacement_years':PV_LIFE,
   'battery_replacement_years':12,'100yr_vs_30yr_discount_rate_base':RATE,
   'hull_capex_premium_stressed_from_1_to_2x':True,
   'fish_and_drone_seeding_after_initial_establishment':'spot_replanting only; no annual reseeding of complete farms'},
   'best_financial_cargo_fleet':best,'maximum_cargo_energy_saving':tech,
   'illustrative_autonomous_support':illustrative,
   'available_support_savings_limits':{'max_onboard_support_electricity_gwh':max(0,(renew_delivered_twh-head_twh)*1000),
    'harvest_support_original_fuel_energy_gwh':V18_SUPP*1000,
    'comparison':'52 GWh renewable head power cannot replace 3,545 GWh fleet fuel input; electricity/fuel efficiencies differ'},
   'limitations':['Original 3.55 TWh is a broad historical support allowance with no audited subactivity breakdown: do not declare it all harvesting or drone seed use.',
    'Daylight harvester PV can supply small cutting-head electric load annually; night utility work depends on storage/wind and weather.',
    'Drone seeding only initial & repair is concept design, not field-observed time-motion cost.',
    'Vessel PV/kite/VAWT power outputs are engineered sensitivities; shaft energy, drag and actual wind kites require empirical trials.',
    '100-year hull service life is not verified; refits, downtime, steel renewal, class inspection and residual value uncertain.',
    'Perpetual selective kelp harvest requires multi-year independent ecological and nutrient validation.',
    'Do not subtract annualized 30-to-100yr capital savings if replacement is not really postponed.',
    'The files are a marine-energy sensitivity overlay; old Spain optimizer and manuscripts preserved verbatim, not retroactively recertified.']}
(out/'V20_SUMMARY.json').write_text(json.dumps(S,indent=2))
# QA conservation and cost checks
assert len(fleet)==60 and len(seed_maintenance_cases)==75
assert all(x['remaining_support_fuel_energy_twh']>=-1e-10 for x in seed_maintenance_cases)
assert all(x['marine_transport_twh_fuel_eq']>=0 for x in fleet)
assert all(x['fuel_energy_saved_twh']<=V18_SUPP+1e-9 for x in seed_maintenance_cases)
assert abs(head_twh-C)<1e-12
assert max(x['fuel_energy_saved_twh'] for x in local)<V18_SUPP
print(json.dumps({'best_financial':best,'highest_energy_saving':tech,'autonomous_example':illustrative},indent=2))
