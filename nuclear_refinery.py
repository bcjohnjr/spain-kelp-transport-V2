"""Nuclear-powered kelp biorefinery without thermal drying, per dry tonne of kelp.

Route NUC_EH (the proposed design):
  wet kelp (13% DM) -> ensiled for year-round supply -> screw press at the refinery (to ~25% DM; press juice
  with mannitol kept) -> enzymatic hydrolysis incl. alginate lyase -> fermentation -> distillation with nuclear
  steam -> fuel ethanol.  Stillage solids (protein, residual alginate, fucoidan) thickened mechanically to
  15% solids -> hydrothermal liquefaction (HTL, 340 C) -> biocrude -> hydrotreating with H2 from solid-oxide
  electrolysis on nuclear steam -> renewable diesel / jet.  HTL aqueous phase -> anaerobic digestion ->
  biomethane for the harvest and transport fleet.  N, P, K recovered as fertiliser.
Route NUC_H: whole kelp straight to HTL (no fermentation).
Route NUC_A: anaerobic digestion only (biomethane), digestate as fertiliser.
No route dries kelp thermally: fermentation, HTL and AD all run on wet feed.

Key literature anchors
  Ethanol: Wargacki et al. 2012 Science 335:308 - 0.281 g ethanol / g dry Saccharina japonica (~80% of
  theoretical, 0.41 g/g of alginate+mannitol+glucan), 4.7% v/v titre, engineered alginate pathway.
  HTL: Anastasakis & Ross 2011 Bioresour. Technol. 102:4876 - Laminaria saccharina, 19.3 wt% biocrude
  (dry basis) at 350 C, HHV 36.5 MJ/kg.
  Methane: Allen et al. (UCC) - S. latissima BMP ~342 L CH4/kg VS.
"""
from dataclasses import dataclass, asdict, field
import json

LHV_ETOH = 26.8e-3   # GJ/kg
LHV_HC = 43.2e-3     # GJ/kg hydrotreated hydrocarbons
LHV_CH4_NM3 = 35.8e-3


@dataclass
class Feed:
    ash: float = 0.28
    mannitol: float = 0.12
    laminarin: float = 0.10
    cellulose: float = 0.05
    alginate: float = 0.20
    fucoidan: float = 0.05
    protein: float = 0.10
    lipid: float = 0.015
    n: float = 0.020
    p: float = 0.003
    k: float = 0.045
    carb_factor: float = 1.0       # warm-water species: 0.75


@dataclass
class Proc:
    ensile_sugar_loss: float = 0.08
    cellulose_access: float = 0.8
    alginate_use: float = 0.5         # share of alginate fermented (engineered strains); 0 = conventional yeast
    etoh_per_sugar: float = 0.41      # g/g over alginate+mannitol+glucan (Wargacki 2012)
    distill_gj_per_t_etoh: float = 8.0
    htl_biocrude_resid: float = 0.25  # kg biocrude / kg residual organics after fermentation
    htl_biocrude_whole: float = 0.193 # kg / kg dry whole kelp (Anastasakis & Ross 2011)
    biocrude_hhv: float = 35.0
    ht_yield: float = 0.82
    ht_h2: float = 0.035              # kg H2 / kg biocrude
    jet_cut: float = 0.40             # energy share of HTL product cut as jet
    htl_solids: float = 0.15
    htl_dh_mj_kg: float = 1.35        # 25 -> 340 C, pressurised
    htl_heat_recovery: float = 0.80
    htl_topping_electric: float = 0.30
    aq_cod_resid: float = 0.25        # kg COD per kg residual organics in HTL aqueous phase
    aq_cod_whole: float = 0.25
    aq_ch4_nm3_kgcod: float = 0.25
    aq_inhibition: float = 0.70
    ad_ch4_nm3_kgvs: float = 0.24
    soec_kwh_e_kg: float = 38.0
    soec_kwh_th_kg: float = 8.0
    el_base_mwh: float = 0.135        # press, hydrolysis, fermentation, pumps, HT, AD, nutrient recovery
    ad_heat_gj: float = 0.2
    n_recovery: float = 0.60
    p_recovery: float = 0.80
    k_recovery: float = 0.80
    # costs, EUR per dry tonne (annualised capital + O&M), excluding energy
    cost_ensile: float = 20.0
    cost_press_hydrolysis_enzymes: float = 45.0
    cost_ferment_distill: float = 40.0
    cost_htl: float = 60.0
    cost_htl_whole: float = 95.0
    cost_ht: float = 25.0
    cost_ad: float = 15.0
    cost_ad_whole: float = 70.0
    cost_nutrients: float = 15.0
    # fertiliser energy and CO2 avoided per tonne of nutrient
    gj_per_t_n: float = 40.0
    gj_per_t_p: float = 15.0
    gj_per_t_k: float = 8.0
    co2_per_t_n: float = 2.7
    co2_per_t_p: float = 1.5
    co2_per_t_k: float = 0.6


def _fert(f, p):
    n, ph, k = f.n * p.n_recovery * 1000, f.p * p.p_recovery * 1000, f.k * p.k_recovery * 1000   # kg / t dw
    return dict(fert_n_kg=n, fert_p_kg=ph, fert_k_kg=k,
                fert_energy_gj=(n * p.gj_per_t_n + ph * p.gj_per_t_p + k * p.gj_per_t_k) / 1000,
                fert_co2_t=(n * p.co2_per_t_n + ph * p.co2_per_t_p + k * p.co2_per_t_k) / 1000)


def nuc_eh(f=Feed(), p=Proc()):
    cf = f.carb_factor
    sugars = cf * ((f.mannitol + f.laminarin) * (1 - p.ensile_sugar_loss) + f.cellulose * p.cellulose_access
                   + f.alginate * p.alginate_use)
    etoh = sugars * p.etoh_per_sugar                                      # t / t dw
    vs = 1 - f.ash
    resid_org = max(vs - sugars, 0.05)
    biocrude = resid_org * p.htl_biocrude_resid
    hc = biocrude * p.ht_yield
    h2_kg = biocrude * p.ht_h2 * 1000
    resid_dry = resid_org + f.ash * 0.4
    slurry = resid_dry / p.htl_solids
    htl_heat = slurry * p.htl_dh_mj_kg * (1 - p.htl_heat_recovery)           # GJ
    ch4 = resid_org * p.aq_cod_resid * 1000 * p.aq_ch4_nm3_kgcod * p.aq_inhibition * LHV_CH4_NM3
    el = p.el_base_mwh + htl_heat * p.htl_topping_electric / 3.6 + h2_kg * p.soec_kwh_e_kg / 1000
    heat = (etoh * 1000 * p.distill_gj_per_t_etoh / 1000 + htl_heat * (1 - p.htl_topping_electric)
            + h2_kg * p.soec_kwh_th_kg * 3.6e-3 + p.ad_heat_gj)
    out = dict(route="NUC_EH", ethanol_t=etoh, ethanol_gj=etoh * 1000 * LHV_ETOH, hc_gj=hc * 1000 * LHV_HC,
               jet_gj=hc * 1000 * LHV_HC * p.jet_cut, ch4_gj=ch4, el_mwh=el, heat_mwh_th=heat / 3.6,
               h2_kg=h2_kg, co2_ferm_t=etoh * 44 / 46, biocrude_t=biocrude,
               cost_eur=(p.cost_ensile + p.cost_press_hydrolysis_enzymes + p.cost_ferment_distill + p.cost_htl
                         + p.cost_ht + p.cost_ad + p.cost_nutrients))
    out.update(_fert(f, p))
    return out


def nuc_h(f=Feed(), p=Proc()):
    biocrude = p.htl_biocrude_whole
    hc = biocrude * p.ht_yield
    h2_kg = biocrude * p.ht_h2 * 1000
    slurry = 1 / p.htl_solids
    htl_heat = slurry * p.htl_dh_mj_kg * (1 - p.htl_heat_recovery)
    ch4 = (1 - f.ash) * p.aq_cod_whole * 1000 * p.aq_ch4_nm3_kgcod * p.aq_inhibition * LHV_CH4_NM3
    el = 0.09 + htl_heat * p.htl_topping_electric / 3.6 + h2_kg * p.soec_kwh_e_kg / 1000
    heat = htl_heat * (1 - p.htl_topping_electric) + h2_kg * p.soec_kwh_th_kg * 3.6e-3 + p.ad_heat_gj
    out = dict(route="NUC_H", ethanol_t=0.0, ethanol_gj=0.0, hc_gj=hc * 1000 * LHV_HC, jet_gj=hc * 1000 * LHV_HC * p.jet_cut,
               ch4_gj=ch4, el_mwh=el, heat_mwh_th=heat / 3.6, h2_kg=h2_kg, co2_ferm_t=0.0, biocrude_t=biocrude,
               cost_eur=p.cost_ensile + 15 + p.cost_htl_whole + p.cost_ht + p.cost_ad + p.cost_nutrients)
    out.update(_fert(f, p))
    return out


def nuc_a(f=Feed(), p=Proc()):
    vs = 1 - f.ash
    ch4_nm3 = vs * 1000 * p.ad_ch4_nm3_kgvs
    out = dict(route="NUC_A", ethanol_t=0.0, ethanol_gj=0.0, hc_gj=0.0, jet_gj=0.0, ch4_gj=ch4_nm3 * LHV_CH4_NM3,
               el_mwh=0.05 + ch4_nm3 * 1.82 * 0.25e-3, heat_mwh_th=0.4 / 3.6, h2_kg=0.0,
               co2_ferm_t=ch4_nm3 * 0.82 * 1.977e-3, biocrude_t=0.0,
               cost_eur=p.cost_ensile + p.cost_ad_whole + p.cost_nutrients)
    out.update(_fert(f, p))
    return out


def routes(f=Feed(), p=Proc()):
    return {r["route"]: r for r in (nuc_eh(f, p), nuc_h(f, p), nuc_a(f, p))}


if __name__ == "__main__":
    for name, f in (("north_atlantic", Feed()), ("warm_species", Feed(carb_factor=0.75, n=0.015))):
        for k, v in routes(f).items():
            print(name, k, {a: round(b, 3) if isinstance(b, float) else b for a, b in v.items()})
    json.dump({"feed": asdict(Feed()), "proc": asdict(Proc()), "routes": routes()},
              open("outputs/nuclear_refinery_per_dry_tonne.json", "w"), indent=1)
