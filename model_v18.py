#!/usr/bin/env python3
"""Spain V18 — transparent engineering screening overlay on original V17 LP.

Run with python model_v18.py ; requires scipy, numpy, matplotlib and the nested V17 source.
Units: shipping input is original model fuel-energy equivalent, never direct shaft energy.
Capital and solar resource assumptions are explicit scenario inputs, NOT bids/weather data.
"""
from __future__ import annotations
import sys, math, copy, csv, json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
SRC = ROOT/'legacy_source/SOURCE_MODEL_SNAPSHOT/Spain_Integrated_Circular_Marine_Energy_V13_Full_Restoration/National_Fuel_Model'
# `legacy_source` may not be shipped unpacked; standalone runner extracts only PY sources.
if not SRC.exists():
    import zipfile
    zpath=ROOT/'source_v17/Code/Original_Models_and_Source_Data.zip'
    with zipfile.ZipFile(zpath) as zz:
        for n in zz.namelist():
            if n.endswith('.py') or (n.endswith('nuclear_refinery_per_dry_tonne.json')):
                zz.extract(n,ROOT/'legacy_source')
sys.path.insert(0,str(SRC))
import optimise as o, lowcost
from nuclear_refinery import nuc_h, Feed, Proc

OUT=ROOT/'V18_outputs'; OUT.mkdir(exist_ok=True)
refp=lowcost.variant(True,kelp_supplies_liquids=False)
ref=o.solve(refp)
dry_t=ref['kelp_dry_mt']*1e6
wet_t=ref['kelp_wet_mt']*1e6
head_kwh_per_dry_t=0.9  # bounding study head energy, separate from fleet-wide 0.35 GJ/t
harvest_twh=dry_t*.35/3.6e6
transit_twh=ref['kelp_fleet_fuel_twh']-harvest_twh
kites_original=ref['skysails_saved_twh']
# Original reference uses kite already; factor restore pre-kite energy.
transit_before_kite=transit_twh+kites_original
jet_hc=nuc_h(Feed(),Proc())

A={
 'dry_kelp_t_year': dry_t, 'wet_kelp_t_year': wet_t,
 'shortsea_oneway_km':66, 'vessel_payload_wet_t':15000, 'port_turnaround_h':16, 'vessel_service_days_y':300,
 'reference_speed_kn':8, 'marine_transport_twh_y_after_legacy_kites':transit_twh,
 'reference_harvest_support_twh_y':harvest_twh,
 'baseline_kite_fraction': kites_original/transit_before_kite,
 'propulsive_share':.82,'auxiliary_share':.18,
 'pv_deck_m2':1200,'pv_kwp_m2':.20,'pv_specific_kwh_kwp_y':1100,
 'wind_generator_kw':35,'wind_generator_cf':.20,'wind_generator_net_factor':.75,
 'electric_storage_delivery_fraction':.87, 'replaced_engine_fuel_to_shaft_efficiency':.40,
 'marine_fuel_eur_per_mwh':80, 'vessel_hull_eur':25e6,
 'vessel_annual_capital_factor':.095,'vessel_annual_operating_eur':.38e6,
 'wind_assist_kite_eur':.85e6, 'pv_deck_eur':.56e6,'vawt_eur':.25e6,
 'battery_electrical_eur':.26e6, 'hybrid_annual_capital_factor':.12,
 'hybrid_annual_opex_pct':.035,
 'solar_harvester_m2':800,'harvester_units':280,'harvester_wind_kw':30,
 'harvester_wind_cf':.20,'harvester_marine_pv_kwh_kwp_y':1100,
 'harvester_wind_delivered_fraction':.70,
 'harvester_workdays_y':240,'harvester_hours_day':10,
 'solar_harvester_cost_eur':.32e6,'harvester_vawt_cost_eur':.21e6,'harvester_battery_cost_eur':.20e6,
 'evap_kg_m2_day_open_tray':3.0, 'open_tray_area_m2':1500,
 'h2_unit_electric_kwh_kg':38, 'h2_unit_steam_kwh_kg':8,
 'smr_module_mwth':140, 'smr_module_mwe':55,'smr_cf':.90,
 'cogen_electric_mwh_forgone_per_mwh_heat':.30,'smr_overnight_eur_per_kwe':7000,
 'smr_electric_cost_eur_mwh':105,'alternate_firm_power_eur_mwh':75,
 'seaborne_h2_hydrotreating_allocation':True,
}

def ships_needed(speed_kn, km=A['shortsea_oneway_km']):
    voyage_h=2*km/(speed_kn*1.852)+A['port_turnaround_h']
    trips=A['vessel_service_days_y']*24/voyage_h
    return math.ceil(wet_t/(A['vessel_payload_wet_t']*trips))

def marine_option(speed_kn, fitout, kite_strength=.1, code=''):
    n=ships_needed(speed_kn)
    r=speed_kn/A['reference_speed_kn']
    # For fixed journey distance, propulsion fuel ~= v^2; hotel/aux ~= 1/v.
    before=transit_before_kite*(A['propulsive_share']*r*r+A['auxiliary_share']/r)
    # Wind kite direct thrust, not electrical generation. Legacy already counts kite.
    kite= kite_strength if fitout in ('kite','pv_kite','full') else A['baseline_kite_fraction']
    after=before*(1-kite)
    raw_pv_mwh=n*A['pv_deck_m2']*A['pv_kwp_m2']*A['pv_specific_kwh_kwp_y']/1000
    raw_vawt_mwh=n*A['wind_generator_kw']*8760*A['wind_generator_cf']*A['wind_generator_net_factor']/1000
    pv_mwh=raw_pv_mwh*A['electric_storage_delivery_fraction'] if fitout in ('pv_kite','full') else 0.
    vawt_mwh=raw_vawt_mwh*A['electric_storage_delivery_fraction'] if fitout=='full' else 0.
    # Fuel-energy displaced (not shaft electrical). Cannot use more than motor fuel energy.
    displaced_twh=min(after*.8,(pv_mwh+vawt_mwh)/A['replaced_engine_fuel_to_shaft_efficiency']/1e6)
    net_twh=after-displaced_twh
    ref_hulls=ships_needed(A['reference_speed_kn'])
    cap_add=max(0,n-ref_hulls)*A['vessel_hull_eur']*A['vessel_annual_capital_factor']
    op_add=(n-ref_hulls)*A['vessel_annual_operating_eur']
    kit_cost=0
    if fitout in ('kite','pv_kite','full'): kit_cost+=A['wind_assist_kite_eur']
    if fitout in ('pv_kite','full'): kit_cost+=A['pv_deck_eur']+A['battery_electrical_eur']
    if fitout == 'full': kit_cost+=A['vawt_eur']
    # Relative to standard legacy-kite capital we charge only incremental price for a new unit.
    standard_kite_credit=0 # conservative, original cost does not disclose kite capex separately
    added_kit_cost=kit_cost*A['hybrid_annual_capital_factor']+kit_cost*A['hybrid_annual_opex_pct']
    cap_extra=n*added_kit_cost
    saved_twh=transit_twh-net_twh
    fuel_value_eur=saved_twh*1e6*A['marine_fuel_eur_per_mwh']
    net_saving_eur=fuel_value_eur-cap_add-op_add-cap_extra
    # Only surface exposed cargo, 1 day at sea; annual fraction is NOT arbitrary 5-10%.
    loaded_hours=A['shortsea_oneway_km']/(speed_kn*1.852)
    removed_tonnes_per_trip=A['evap_kg_m2_day_open_tray']*A['open_tray_area_m2']*loaded_hours/24/1000
    exposed_fraction=removed_tonnes_per_trip/A['vessel_payload_wet_t']
    return dict(case=code or f'{fitout}-{speed_kn:g}kt', speed_kn=speed_kn,fitout=fitout,hulls=n,
         marine_transport_twh=net_twh,marine_transport_saved_twh=saved_twh,
         marine_transport_saved_pct=100*saved_twh/transit_twh,
         kite_savings_fraction=kite,pv_delivered_gwh=pv_mwh/1000,vawt_delivered_gwh=vawt_mwh/1000,
         actual_evap_wet_cargo_pct=exposed_fraction*100,
         additional_fleet_capital_annual_meur=cap_add/1e6,
         incremental_operating_annual_meur=op_add/1e6,
         hybrid_equipment_annual_meur=cap_extra/1e6,
         avoided_fuel_cost_annual_meur=fuel_value_eur/1e6,
         net_annual_saving_meur=net_saving_eur/1e6)

variants=[]
for s in [8,7,6,5,4.5]:
    for equip in ['legacy','kite','pv_kite','full']:
        # reference at 8 knots with legacy kite, not added capex
        variants.append(marine_option(s,equip,kite_strength=.14))
base=next(v for v in variants if v['speed_kn']==8 and v['fitout']=='legacy')
# Anchor to exact original V17 energy. Make base cost exactly zero.
assert abs(base['marine_transport_twh']-transit_twh)<1e-9
max_energy=max(variants,key=lambda x:x['marine_transport_saved_twh'])
best_cash=max(variants,key=lambda x:x['net_annual_saving_meur'])
full6=next(v for v in variants if v['speed_kn']==6 and v['fitout']=='full')

# Harvester roof PV + VAWT are electricity; original model does not expose fraction of harvest support propulsion.
harv_pv_mwh=A['harvester_units']*A['solar_harvester_m2']*A['pv_kwp_m2']*A['harvester_marine_pv_kwh_kwp_y']/1000
harv_wind_mwh=(A['harvester_units']*A['harvester_wind_kw']*8760*A['harvester_wind_cf']*
                 A['harvester_wind_delivered_fraction']/1000)
harv_head_mwh=dry_t*head_kwh_per_dry_t/1000
harv_clean_mwh=(harv_pv_mwh+harv_wind_mwh)*A['electric_storage_delivery_fraction']
harv_energy_credit_twh=min(harvest_twh*.75,harv_clean_mwh/A['replaced_engine_fuel_to_shaft_efficiency']/1e6)
# don't take credit against site-wide miscellaneous loads in theoretical head-only test
harvest_equip_overnight_eur=A['harvester_units']*(A['solar_harvester_cost_eur']+A['harvester_vawt_cost_eur']+A['harvester_battery_cost_eur'])
harvest_equip_annual_meur=harvest_equip_overnight_eur*(A['hybrid_annual_capital_factor']+A['hybrid_annual_opex_pct'])/1e6
harvest_fuel_value_meur=harv_energy_credit_twh*A['marine_fuel_eur_per_mwh']
harvest_net_annual_saving_meur=harvest_fuel_value_meur-harvest_equip_annual_meur
harvester_modules_needed=math.ceil(A['harvester_units']*A['harvester_workdays_y']*A['harvester_hours_day']/2400)
harvester_peak_short_days_180=math.ceil(A['harvester_units']*2400/(180*A['harvester_hours_day']))
hectare_farm_area_km2=ref['kelp_total_km2']

# Hydrogen for original whole-kelp HTL from ORIGINAL Spain engine: no missing hydrotreatment.
h2kg_per_dry_t=jet_hc['h2_kg']
h2_kg=h2kg_per_dry_t*dry_t
h2_el_twh=h2_kg*A['h2_unit_electric_kwh_kg']/1e9
h2_heat_twh=h2_kg*A['h2_unit_steam_kwh_kg']/1e9
process_electric_twh=ref['kelp_refinery_el_twh']
process_heat_twh=ref['kelp_refinery_heat_twh']
module_electric_twh=A['smr_module_mwe']*A['smr_cf']*8760/1e6
module_thermal_twh=A['smr_module_mwth']*A['smr_cf']*8760/1e6
modules_just_h2=math.ceil(h2_el_twh/module_electric_twh)
modules_all_heat_and_power=math.ceil((process_electric_twh+A['cogen_electric_mwh_forgone_per_mwh_heat']*process_heat_twh)/module_electric_twh)
modules_heat_only=math.ceil(process_heat_twh/module_thermal_twh)
mod_capex_eur=A['smr_module_mwe']*1000*A['smr_overnight_eur_per_kwe']
# Alternative nuclear vs competitive electricity: roughly 0.3 MWh/MWh of process heat forgone.
process_el_equiv_twh=process_electric_twh+A['cogen_electric_mwh_forgone_per_mwh_heat']*process_heat_twh
nuc_power_cost_m_b=process_el_equiv_twh*A['smr_electric_cost_eur_mwh']/1e3
alt_power_cost_m_b=process_el_equiv_twh*A['alternate_firm_power_eur_mwh']/1e3

# Re-solve the original national LP with a V18 hybrid-fleet param change as a real separate outcome.
def rerun_with_transport(topt, harv_credit):
    p=lowcost.variant(True,kelp_supplies_liquids=False)
    # Effective fleet transfer is proportional to original formula (original kite already present).
    ratio=topt['marine_transport_twh']/transit_twh
    p['fleet']['mj_tkm_near']*=ratio
    p['fleet']['mj_tkm_far']*=ratio
    p['fleet']['harvest_gj']*=1-harv_credit/harvest_twh
    return o.solve(p)

rerun_energy=rerun_with_transport(max_energy,harv_energy_credit_twh)
rerun_cash=rerun_with_transport(best_cash,harv_energy_credit_twh)
rerun_full6=rerun_with_transport(full6,harv_energy_credit_twh)

# Output all scenario variants, and robust fuel-price/capital stresses.
for field,rows in [('V18_SHIP_SPEED_AND_ENERGY.csv',variants)]:
    with (OUT/field).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (OUT/'V18_GRID_HARVESTER_DAYLIGHT.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['days_in_season','hours_per_day','installed_heads_for_v17_wet_harvest','solar_head_energy_mwh','head_energy_demand_mwh'])
    w.writeheader()
    for days in [160,180,200,220,240,260]:
        for hrs in [8,10,12]:
            w.writerow({'days_in_season':days,'hours_per_day':hrs,'installed_heads_for_v17_wet_harvest':math.ceil(A['harvester_units']*2400/(days*hrs)),
             'solar_head_energy_mwh':round(harv_pv_mwh,2),'head_energy_demand_mwh':round(harv_head_mwh,2)})
with (OUT/'V18_MARINE_FUEL_OPPORTUNITY_SENSITIVITY.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['fuel_opportunity_eur_mwh','speed_kn','fitout','avoided_fuel_meur','added_capex_opex_meur','net_meur']);w.writeheader()
    for price in [40,60,80,100,140,200]:
        for rr in variants:
            added=rr['additional_fleet_capital_annual_meur']+rr['incremental_operating_annual_meur']+rr['hybrid_equipment_annual_meur']
            value=rr['marine_transport_saved_twh']*price
            w.writerow(dict(fuel_opportunity_eur_mwh=price,speed_kn=rr['speed_kn'],fitout=rr['fitout'],avoided_fuel_meur=round(value,3),added_capex_opex_meur=round(added,3),net_meur=round(value-added,3)))
summary={
 'archive': 'Spain Nature Sustainability V17 original, least-cost completed-system re-run (not V17 dynamic transition 2041)',
 'baseline':{'national_cost_b_eur_y':ref['total_cost_beur'],'dry_kelp_mt_y':ref['kelp_dry_mt'],
            'wet_kelp_mt_y':ref['kelp_wet_mt'],'farm_area_km2':hectare_farm_area_km2,
            'harvest_support_twh_fuel_eq':harvest_twh,'cargo_twh_fuel_eq_after_existing_kites':transit_twh,
            'total_marine_twh_fuel_eq':ref['kelp_fleet_fuel_twh'], 'original_kite_savings_twh':kites_original},
 'assumptions':A,
 'marine_options':{'max_fuel_saving':max_energy,'max_net_cash_saving':best_cash,'six_knots_full_hybrid':full6},
 'harvester':{'pv_gwh_electrical_annual':harv_pv_mwh/1000,'wind_gwh_electrical_annual_pre_storage':harv_wind_mwh/1000,
              'head_mwh_electrical_annual':harv_head_mwh,'renewables_delivered_gwh_electrical':harv_clean_mwh/1000,
              'displaced_fuel_equiv_twh_max':harv_energy_credit_twh,
              'heads_needed_at_180_days_10h':harvester_peak_short_days_180,
              'heads_needed_at_240_days_10h':harvester_modules_needed,
              'full_solar_wind_battery_annual_cost_meur':harvest_equip_annual_meur,
              'harvester_avoided_fuel_value_meur':harvest_fuel_value_meur,
              'harvester_net_cost_saving_meur':harvest_net_annual_saving_meur},
 'reactor':{'whole_kelps_htl_biocrude_fraction_dry':jet_hc['biocrude_t'],
           'finished_renewable_hydrocarbon_t_per_dry_t':jet_hc['hc_gj']/43.2,
           'h2_kg_per_dry_t':h2kg_per_dry_t,'h2_thousand_t_y':h2_kg/1e6,
           'soec_electric_twh_y':h2_el_twh,'soec_heat_twh_y':h2_heat_twh,
           'total_refinery_electric_twh_y':process_electric_twh,
           'total_refinery_heat_twh_y':process_heat_twh,
           'modules_for_sole_h2_electricity_only':modules_just_h2,
           'modules_for_all_refinery_el_and_heat_equivalent':modules_all_heat_and_power,
           'modules_if_heat_only':modules_heat_only,
           'module_55_mwe_energy_twh_annual':module_electric_twh,
           'module_140_mwth_heat_twh_annual':module_thermal_twh,
           'indicative_reactor_overnight_cost_b_eur':modules_all_heat_and_power*mod_capex_eur/1e9,
           'smr_full_equivalent_energy_cost_b_eur_y':nuc_power_cost_m_b,
           'alternative_electric_cost_b_eur_y_if_same_heat_exergy_opportunity':alt_power_cost_m_b},
 'national_lp_reruns':{
  'hybrid_max_fuel_saving':{'annual_cost_b_eur':rerun_energy['total_cost_beur'],'dry_kelp_mt_y':rerun_energy['kelp_dry_mt'],'fleet_twh_y':rerun_energy['kelp_fleet_fuel_twh']},
  'hybrid_max_cash_saving':{'annual_cost_b_eur':rerun_cash['total_cost_beur'],'dry_kelp_mt_y':rerun_cash['kelp_dry_mt'],'fleet_twh_y':rerun_cash['kelp_fleet_fuel_twh']},
  'hybrid_six_knots_full':{'annual_cost_b_eur':rerun_full6['total_cost_beur'],'dry_kelp_mt_y':rerun_full6['kelp_dry_mt'],'fleet_twh_y':rerun_full6['kelp_fleet_fuel_twh']}
 },
 'limitations':[
 'Representative fleet capacity, speed/fuel curve and marine irradiance are assumptions without vessel route trials or a shipyard bid.',
 'Refinery steam electricity penalty 0.30 MWh_el/MWhth is an archived modeling proxy; no licensed SEALER heat integration demonstration.',
 'All fuel-equivalent ship energy is drawn from the old biomass methane fleet pool; savings are energy-equivalent, not necessarily fossil diesel savings.',
 'Full LP reruns implement fuel-energy equivalent improvement inside fleet coefficients, but new hull/equipment capex charged separately in shipping cash ledger; NOT a fully integrated discrete nuclear-fleet jointly optimized MILP.',
 'Do not count solar and vertical-axis turbine as independent wind propulsion when the wind generator increases aerodynamic drag.',
 'No claim of more national kelp biomass or higher wet HTL yield from vessel evaporation.'
 ]
}
(OUT/'V18_SUMMARY.json').write_text(json.dumps(summary,indent=2,default=float))

plt.rcParams.update({'font.size':9})
fig,ax=plt.subplots(figsize=(9.5,5.3))
for typ,c in [('legacy','#5c6370'),('kite','#377ca3'),('pv_kite','#31a18d'),('full','#a679d2')]:
    rr=sorted([x for x in variants if x['fitout']==typ],key=lambda x:x['speed_kn'])
    ax.plot([r['speed_kn'] for r in rr],[r['marine_transport_saved_pct'] for r in rr],marker='o',lw=2,label=typ.replace('_',' + '),color=c)
ax.axhline(0,ls=':',color='black',lw=.8)
ax.set(xlabel='Cargo-vessel speed (knots)',ylabel='Reduction in cargo-transport fuel energy (%)',title='Spain V18 | Offshore kelp cargo transport: renewable-assist sensitivity')
ax.legend(title='Installed system',ncol=2);ax.grid(alpha=.15)
fig.text(.1,.02,'Relative to legacy V17 8-knot service with existing kite credit; modeled assumptions, not sea trials.',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(OUT/'Figure_V18_Marine_Transport_Energy.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(9.5,5.3))
for typ,c in [('legacy','#5c6370'),('kite','#377ca3'),('pv_kite','#31a18d'),('full','#a679d2')]:
    rr=sorted([x for x in variants if x['fitout']==typ],key=lambda x:x['speed_kn'])
    ax.plot([r['speed_kn'] for r in rr],[r['net_annual_saving_meur'] for r in rr],marker='o',lw=2,label=typ.replace('_',' + '),color=c)
ax.axhline(0,ls='--',color='black',lw=.8)
ax.set(xlabel='Cargo-vessel speed (knots)',ylabel='Annual net saving after additional hulls and equipment (€million)',title='Spain V18 | Energy optimum is not necessarily cost optimum')
ax.legend(ncol=2);ax.grid(alpha=.15)
fig.text(.1,.02,'Model €80/MWh fuel opportunity cost, vessel and kit CAPEX scenarios; original kite cost not re-credited.',fontsize=8)
fig.tight_layout(rect=(0,.05,1,1));fig.savefig(OUT/'Figure_V18_Marine_Transport_Cost.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(8.5,4.2))
labels=['Transport\n(original)','Harvest/support\n(original)','Transport\n(six-knot full)','Harvest/support\n(roof PV/wind upper bound)']
ys=[transit_twh,harvest_twh,full6['marine_transport_twh'],harvest_twh-harv_energy_credit_twh]
ax.bar(labels,ys,color=['#8794a6','#8794a6','#2d977c','#2d977c'])
for x,y in enumerate(ys): ax.text(x,y+.05,f'{y:.2f}',ha='center')
ax.set(ylabel='TWh fuel-equivalent / year',title='Spain V18 | Separate cargo propulsion from the broader harvesting fleet')
ax.set_ylim(0,max(ys)*1.20);fig.tight_layout();fig.savefig(OUT/'Figure_V18_Annual_Marine_Balance.png',dpi=180);plt.close(fig)

# Provenance-locked invariants, quick regression tests.
assert abs(harvest_twh+transit_twh-ref['kelp_fleet_fuel_twh'])<1e-10
assert jet_hc['h2_kg']>0 and jet_hc['hc_gj']>0
assert modules_all_heat_and_power>=modules_just_h2
assert abs(base['marine_transport_saved_twh'])<1e-9
assert best_cash['net_annual_saving_meur']>=0-1e-8
assert full6['actual_evap_wet_cargo_pct']<0.1
assert all(x['marine_transport_twh']>=0 for x in variants)
assert abs(ref['total_cost_beur']-42.7772369743691)<1e-7
print(json.dumps({
 'baseline':summary['baseline'],
 'speed_6_full_hybrid':full6,
 'most_fuel_saved':max_energy,
 'most_cash_saved':best_cash,
 'harvester':summary['harvester'],
 'smr':summary['reactor'],
 'national_reruns':summary['national_lp_reruns']
},indent=2,default=float))
