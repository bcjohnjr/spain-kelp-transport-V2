from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
import csv,json,re,math,shutil,os,zipfile
import numpy as np
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
SRC=Path('/mnt/data/Spain_Nature_Sustainability_Dual_Path_V15')
OUT=Path('/mnt/data/Spain_Nature_Sustainability_Dual_Path_V16')
if OUT.exists():shutil.rmtree(OUT)
shutil.copytree(SRC,OUT)
for x in (OUT/'Submission').glob('*V15*'):x.rename(x.with_name(x.name.replace('V15','V16')))
for x in (OUT/'Supplementary').glob('*V15*'):x.rename(x.with_name(x.name.replace('V15','V16')))
for x in (OUT/'Source_Data').glob('*V15*'):x.rename(x.with_name(x.name.replace('V15','V16')))
for x in (OUT/'Figures').glob('*'):pass
# audit sensitivity: all numbers are from independently executed 2041 LP tests
raw=json.loads(Path('/mnt/data/V16_work/yield_raw.json').read_text())
rows=[]
for r in raw:
 d=dict(r)
 if d['status']=='optimal':
  d['net_supplier_bn']=d['transport_supply_billion_EUR']+d['idle_farm_annuitized_billion_EUR']+d['idle_CSP_annuitized_billion_EUR']-.123272273171
  d['fossil_2026_bn']=66.51837992
  d['savings_bn']=d['fossil_2026_bn']-d['net_supplier_bn']
 rows.append(d)
(OUT/'Source_Data'/'V16_KELP_YIELD_REOPTIMIZATION.json').write_text(json.dumps(rows,indent=2))
with (OUT/'Source_Data'/'V16_KELP_YIELD_REOPTIMIZATION.csv').open('w',newline='') as f:
 keys=['yield_t_ha','kelp_min_TWh','status','transport_supply_billion_EUR','idle_farm_annuitized_billion_EUR','idle_CSP_annuitized_billion_EUR','net_supplier_bn','fossil_2026_bn','savings_bn','kelp_km2','kelp_dry_Mt','error']
 w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
 for r in rows:w.writerow({k:r.get(k,'') for k in keys})
# 2041 sensitivities - 2 panels for figure 4
fs=OUT/'Figures'/'Figure_4_yield_and_mandate_sensitivity.png'
fig,axs=plt.subplots(1,2,figsize=(10.9,4.0),gridspec_kw={'width_ratios':[1.5,.9]})
a=axs[0]
vals=[56.095,59.984,63.950,67.511]
labs=['20 · mandatory','15 · mandatory','10 · relaxed','5.4 · relaxed']
bars=a.barh(np.arange(4),vals,color=['#145A72','#387C90','#D6A34D','#C76D60'])
a.set_yticks(np.arange(4),labs);a.invert_yaxis();a.set_xlim(0,76);a.set_xlabel('Net energy-supplier cost (€bn/y)')
a.axvline(66.518,color='#1A1A1A',ls='--',lw=1.2,label='October 2026 fossil reference')
a.grid(axis='x',alpha=.15)
a.legend(loc='lower right',fontsize=7,frameon=False)
for b,v in zip(bars,vals):a.text(v+.5,b.get_y()+b.get_height()/2,f'{v:.2f}',va='center',fontsize=9)
a.set_title('a  Terminal kelp-yield sensitivity',loc='left',fontsize=11,weight='bold')
a=axs[1];a.axis('off')
a.text(.04,.87,'Binding kelp minimum',fontsize=12,weight='bold')
a.text(.04,.70,'50 TWh/year of kelp fuel',fontsize=11)
a.text(.04,.54,'At 10 and 5.4 t/ha/year',fontsize=10)
a.text(.04,.43,'the 2041 optimization is infeasible',fontsize=10,weight='bold',color='#9C3D2C')
a.text(.04,.28,'Relaxing this floor restores a feasible',fontsize=9)
a.text(.04,.19,'solution but increases supplier cost.',fontsize=9)
a.text(.04,.04,'Model stress tests, not observed farm yields.',fontsize=8,color='#505050')
fig.tight_layout();fig.savefig(fs,dpi=300,bbox_inches='tight');fig.savefig(fs.with_suffix('.pdf'),bbox_inches='tight');plt.close(fig)
# Figure 5  clean vector drawing, without generative artwork
fig,ax=plt.subplots(figsize=(12.2,5.9));ax.set_xlim(0,12.2);ax.set_ylim(0,5.9);ax.axis('off')
def rect(x,y,w,h,label,sub='',fc='#F5F8FA'):
 p=FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.11,rounding_size=.09',edgecolor='#6A7E89',facecolor=fc,linewidth=1.2)
 ax.add_patch(p);ax.text(x+w/2,y+h*.67,label,ha='center',va='center',fontsize=10.5,weight='bold',color='#14374A')
 if sub:ax.text(x+w/2,y+h*.29,sub,ha='center',va='center',fontsize=8.2,color='#4A5E66',linespacing=1.3)
def arrow(x1,y1,x2,y2,color='#47788A',lw=1.8,style='-|>'):
 ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle=style,mutation_scale=13,linewidth=lw,color=color,connectionstyle='arc3'))
rect(.35,3.92,2.15,1.12,'High-protein wheat','Combine harvest · milling\ncomplete formulated fish feed','#F2F6E9')
rect(3.13,3.92,2.12,1.12,'Hatchery & rafts','Juvenile stocking · feed\noffshore logistics','#F2F6E9')
rect(5.98,3.85,2.56,1.28,'Netted kelp–fish grids','Perennial partial kelp harvest\nselective mature-fish removal','#EAF5F6')
rect(9.30,3.92,2.48,1.12,'CSP biorefinery','Wet HTL · ethanol\nliquid fuel · biomethane','#F9F3EA')
rect(6.10,1.72,2.25,1.04,'Selective-hook drone','Classify · retain/release\nservice-raft transfer','#EAF5F6')
rect(9.37,1.72,2.40,1.04,'Marine-plastic recovery','Sort/wash/test polymer · reuse\n316L core + sealed float','#F4F0FB')
rect(3.05,1.72,2.19,1.04,'Coastal fish processing','Food · eligible cross-species\nby-products','#F3F5FB')
rect(.34,1.72,2.18,1.04,'Qualified fertilizer','N–P–K recovery, de-salting\nand inland return','#F2F6E9')
arrow(2.5,4.48,3.13,4.48);arrow(5.25,4.48,5.98,4.48);arrow(8.54,4.48,9.3,4.48)
arrow(7.27,3.85,7.27,2.76);arrow(5.98,4.05,4.15,2.76);arrow(9.3,3.98,10.57,2.76)
arrow(9.37,2.24,8.36,3.98,color='#87709C')
arrow(3.05,2.2,2.52,2.2);arrow(1.42,2.76,1.42,3.92,color='#72954D')
ax.text(8.85,5.50,'Fuel products and electricity → users',fontsize=10.5,color='#375765')
ax.text(.4,.76,'Study status: energy flows optimized; drone operations and recycled-plastic structures remain unvalidated designs.',fontsize=9,color='#4E626B')
ax.text(.4,.42,'No recycled-plastic cost credit or hook-drone throughput saving is included in supplier-cost totals.',fontsize=9,color='#4E626B')
fig.tight_layout();fo=OUT/'Figures'/'Figure_5_integrated_drone_plastics_schematic.png';fig.savefig(fo,dpi=300,bbox_inches='tight');fig.savefig(fo.with_suffix('.pdf'),bbox_inches='tight');plt.close(fig)
# Move replaced earlier plots to supplementary (keep provenance)
shutil.copy2(OUT/'Figures'/'Figure_4_capacity_heat_electricity.png',OUT/'Supplementary'/'Original_V15_capacity_heat_electricity.png')
shutil.copy2(OUT/'Figures'/'Figure_5_system_boundary_schematic.png',OUT/'Supplementary'/'Original_V15_system_boundary.png')
# DOCX main text corrections, compact editorial insertions
main=OUT/'Submission'/'Manuscript_Nature_Sustainability_Dual_Path_V16.docx'
d=Document(main)
P=d.paragraphs
# content only direct paragraphs (NO ghost text)
def setp(i,text):P[i].text=text
setp(0,'The cost of phasing out Spain’s fossil transport fuels')
setp(2,'¹ Independent researcher, Zaragoza, Spain; ² Technical University of Munich (TUM) and Max Planck Institute for Physics, Munich, Germany; ³ University of Málaga, Málaga, Spain. Corresponding-author institutional details and coauthor approvals require author verification before submission.')
setp(5,'We compare a constrained 2027–2041 fossil-transport-fuel phase-out for Spain with a separately optimized completed low-carbon supply system. Energy supplier costs exclude consumer vehicle purchases. Under a mandated 2041 zero-fossil endpoint, annual net energy-supplier cost is €56.10 billion, 15.7% below the same-demand October 2026 fossil reference; transition-period expenditure remains higher. The unconstrained completed learning case costs €42.78 billion, while a 1,000-draw uncertainty analysis yields a €50.51 billion median. Reducing assumed kelp yield from 20 to 15 dry tonnes ha⁻¹ yr⁻¹ raises the terminal cost; lower yields can make a mandatory kelp-fuel target infeasible. Co-located aquaculture, a selectively retaining fishing drone and recovered-plastic floating structures offer experimentally testable circular-economy options, not verified cost savings.')
setp(8,'We compare annual fuel-supply costs of a 15-year policy-constrained transition and a completed least-cost portfolio. The analysis identifies when the transition begins to undercut the same-demand fossil benchmark, measures the premium imposed by retained combustion transport, and stress-tests kelp productivity. We also map linked wheat–fish–kelp material flows and describe two unproven engineering proposals: selective capture of individual fish within perennial kelp pens, and offshore recovered-plastic reuse in detachable flotation and marine structural components. Both require field validation; neither enters the reported fuel cost optimum.')
setp(18,'Annualized unused kelp and concentrated-solar capacity adds €5.35 billion to the supplier screen in 2033, falling to zero in 2041. With a conditional €0.123-billion aquaculture operating margin credited each year, the supplier costs €81.06 billion in 2027, €76.35 billion in 2033 and €56.10 billion in 2041. A same-demand fossil reference costs €69.32 billion, €68.12 billion and €66.52 billion, respectively. The integrated system first reaches approximate annual parity in 2036. Summed over 2027–2041, the net supplier spends €49.84 billion more than fossil supply priced at October 2026 levels, while the emissions screen indicates 1,439 Mt CO₂e avoided; division gives approximately €35/t CO₂e, without discounting. Holding the final annual saving constant beyond 2041 would recover the cumulative premium around 2046, not a forecast.')
setp(25,'The completed-system comparator removes transition-specific fleet constraints while retaining the national service boundary. Its favorable technology-learning solution costs €42.78 billion/year (no vehicle purchases), compared with €56.22 billion for the 2041 transition fuel portfolio before aquaculture credit. The mature portfolio electrifies all cars and vans and permits 90% heavy-road electrification; terminal transition assumptions leave 20% of diesel-car service, 50% of heavy-road service and 10% of original petrol-car service reliant on renewable fuel. The compared models also differ in required CSP process heat and biomethane-to-electricity allocations, so the comparison decomposes conditional constraint choices rather than estimating a single universal technology cost.')
setp(26,'The completed optimizer’s original 1,000-draw uncertainty analysis spans finance, biomass yields and cost, refinery performance, marine area, renewable generation and other parameters. It yields a median supplier cost of €50.51 billion (5th–95th percentile €46.08–55.85 billion); all 1,000 sampled supplier-only costs are below the €66.52-billion fossil reference. For transparency, including consumer-paid incremental vehicle premiums *in a separate social-cost sensitivity* produces a median of €58.98 billion (5th–95th percentile €52.97–65.69 billion), with 981 of 1,000 draws cheaper. These private vehicle expenditures are never charged to the fuel supplier or included in the primary comparisons.')
setp(29,'The €13.44-billion difference in energy-supply cost between 2041 and the completed learning case is traced by sequential constraint tests: approximately €12.51 billion from retaining additional combustion transport, €0.38 billion from imposing the refinery CSP-heat requirement, and €0.55 billion from directing kelp biomethane to power generation. This accounting is conditional on the order and underlying learning assumptions and is not a proof of an optimal phase-out timetable.')
setp(39,'Kelp productivity controls the viability of the constrained case. At the imposed 20,000-km² farm ceiling, yields of 20 and 15 dry t ha⁻¹ yr⁻¹ imply respectively €56.22 billion and €59.88 billion annual energy-supply cost in fresh 2041 optimizer runs. At 10 or 5.4 t ha⁻¹ yr⁻¹, a mandated 50-TWh kelp-fuel floor makes the model infeasible. Relaxing that floor restores feasibility at €63.79 billion and €67.14 billion before idle-capacity adjustment and aquaculture credit. The last case exceeds the €66.52-billion fossil reference even before those adjustments. Yield and kelp-fuel mandates cannot be treated as evidence of achieved cultivation output.')
setp(41,'The modeled 20 dry t ha⁻¹ yr⁻¹ productivity is substantially higher than a published 5.4-t/ha dry-weight aquaculture comparison. This is not a universal biological ceiling, but the assumption cannot be presented as validated offshore Spanish sugar-kelp production. A field programme must measure deep-water growth, nutrient-cycling energy, storm losses and partial-harvest regrowth across sites and seasons [10–14].')
setp(43,'Fig. 4 | Re-optimized kelp-yield sensitivity in 2041. Bars include fuel supply, annualized idle capacity and conditional fish-sector margin. The 50-TWh kelp minimum is binding; relaxed-floor cases are separately identified. Dashed line marks same-demand October 2026 fossil reference.')
setp(45,'The marine nitrogen balance is not closed by fed fish alone: under the current fish stocking assumptions the captured fish-derived nitrogen meets only about 0.07% of the modeled terminal kelp nitrogen requirement. Depth cycling and marine nutrient distribution remain material inputs. The marine-area screen excludes major traffic and fishing proxies, but protected habitats, rights, moorings and local hydrodynamics require permitting-grade surveys [24].')
setp(48,'Co-located fish are hatchery-raised seabass and seabream, delivered as fry by service rafts to netted perennial kelp grids. The screening case assumes 54,694 tonnes annual whole-fish output, 82,040 tonnes formulated feed (FCR 1.5), and 4,102 tonnes of high-protein dryland wheat harvested by conventional combines. Recovered fish materials could enter separately processed, legally permitted cross-species feed products. The fish sector yields €288 million gross first-sale value but only a conditional €123 million operating margin after the modeled feed, husbandry and annuitized pen costs. Market margins and ecological carrying capacity have not been demonstrated.')
setp(49,'Seaweed-derived fertilizer could be returned to wheat fields after desalting, contaminant screening and qualification. The model does not count fish-derived nutrients as sufficient to replace marine nutrient delivery, and does not credit wheat cultivation or captured ocean plastics with unverified national-scale savings.')
setp(50,'The proposed autonomous *selective-hook* drone is a central engineering research component, not a replacement for the distinct suction-hose Grid Harvester. Continuous partial kelp cutting leaves an attached regrowth crop; crowding an entire fish pen to pump out mature fish risks disturbing those ropes. A low-speed vehicle could use cameras to classify fish size and species, retain a permitted market-ready fish with a mechanically disengageable hook, release rejected fish at capture depth, and transfer retained fish to a raft without emptying the pen. Existing aquaculture crowd-and-pump equipment is the relevant comparator; catch rates, hook injury, fish welfare and legal permission are not established [30].')
setp(52,'Fig. 5 | Non-generative systems schematic tracing wheat feed, hatchery, continuous kelp–fish farming, selective-hook drone, coastal processing and CSP biorefining, with qualified fertilizer return and a *proposed* marine-plastics materials loop. No hook-drone or plastic-reuse savings are credited to national supply costs.')
setp(54,'An equally testable materials proposal is to recover macroplastics and discarded gear, sort and clean compatible polymers at a coastal facility, and remanufacture detachable float modules or polymer jackets surrounding a corrosion-resistant 316L stainless-steel structural core. The polymer must not be assumed to make a metal cable buoyant or prevent corrosion: the archived buoyancy screen shows that a 10-mm steel core needs ~75-mm PP or ~97-mm HDPE *solid* outer diameter just to reach neutral buoyancy, before payloads; closed-cell/air flotation may be preferable. Crevice corrosion, contamination, fatigue, UV damage, microplastic shedding and loss of reused components require field testing [28,29].')
setp(56,'The transition-constrained system first falls below the October 2026 same-demand fossil-fuel supply reference around 2036; by 2041 its energy-supplier cost after the conditional fish credit is €56.10 billion. A separate unconstrained completed-system learning case costs €42.78 billion, with €50.51 billion as the original uncertainty median. The comparison shows that retaining combustion transport, mandatory solar heat and biomethane electricity are chiefly responsible for the terminal premium. The 2027–2041 transition nonetheless costs an additional €49.84 billion cumulatively against fossil fuels at the stated shock prices. At 5.4 t/ha kelp yield, a mandatory fuel floor becomes infeasible; relaxing it raises costs above the fossil comparator. These are scenario results, not observed commercial performance.')
setp(57,'Marine yields, the scale of electricity build-out, heat integration and operating permits remain major constraints. The selective-hook drone is a plausible approach to individual fish removal during perennial kelp production, not a measured efficiency improvement. Ocean-plastic flotation components might valorize recovered material, but must be assessed against proven virgin-material and recycling alternatives on lifetime cost, recovery efficiency, release of microplastics and corrosion exposure. Reuse cannot automatically be counted as marine cleanup or a climate benefit [28,29].')
setp(59,'Spain’s PNIEC sets a 2030 national policy context [26], while EU passenger-car standards and the Commission’s proposed 2025 revision shape the longer-run fleet context [27]. This study isolates supplier costs (not consumers’ vehicle purchases), reports yield failure cases, and makes the main circular-economy designs falsifiable. Measured ocean-farm production, fish welfare and capture throughput, low-salt fertilizer qualification, and full operational testing of recovered-polymer modules are required before any deployment, economic-credit or novelty claims can be established.')
setp(64,'Fifteen annually solved linear programmes represent 2027–2041 fuel and electricity supply for petrol and diesel cars, trucks, off-road use, aviation and marine bunkers. Vehicle turnover, kelp construction and CSP commissioning constrain supply exogenously; demand reductions for aviation and shipping phase in, not immediately. Detailed algorithms and provenance are archived in Source Data and Supplementary Information. This is not a simultaneously optimized fifteen-year investment programme, nor an empirical fleet forecast.')
setp(66,'The completed least-cost comparator is a distinct static optimisation releasing transition fleet limits and optionalizing process options; it is not a year-2042 forecast. One thousand completed-model Monte Carlo draws are reused without claiming a fresh uncertainty analysis for the 2027–2041 transition. The 2041 kelp-yield tests directly rerun the terminal solver after replacing North Atlantic yield assumptions; the compulsory 50-TWh kelp minimum is either preserved or explicitly set to zero.')
setp(74,'Each annual solved fuel flow is multiplied by the inherited carrier-specific emissions factors. The model reports 1,439 Mt CO₂e avoided cumulatively compared with same-demand fossil supply over 2027–2041, without considering vehicle manufacture. This is screening lifecycle accounting, not a verified ISO process assessment; synthetic-methane leakage and upstream construction burdens require further study. Ocean-plastic and fishing-drone effects are deliberately excluded from these emissions results.')
# distinct section for material loop (Results) inserted before Discussion
from docx.oxml import OxmlElement
p=P[55]
new=OxmlElement('w:p');p._p.addprevious(new)
pa=Paragraph(new,p._parent);pa.style=d.styles['Heading 2'];pa.text='Recovered ocean plastics as structural materials: validation requirements'
new2=OxmlElement('w:p');p._p.addprevious(new2)
pa2=Paragraph(new2,p._parent);pa2.style=d.styles['Normal'];pa2.text=('Coastal collection of abandoned fishing gear and macroplastic fragments could supply sorted polypropylene and polyethylene for mechanically secured float shells and sacrificial cable covers. Corrosion-resistant steel supplies the tensile load, while independently sealed flotation supplies reserve buoyancy. The scheme assumes no unconditional value for recovered plastics. Sorting yield, cleaning energy, 316L pitting and crevice corrosion, UV/abrasion aging, microplastic release, salvage logistics and end-of-life retrieval must be measured before the material loop can enter the least-cost optimizer [28,29].')
# Replace figures by recreating image run in the existing image-bearing paragraph
for idx,png in [(42,fs),(51,fo)]:
 para=P[idx];para.clear();para.add_run().add_picture(str(png),width=Inches(6.5))
# fix topic labels style restored after overwrites
# references append to correct location BEFORE Data and code availability
refheading=next(x for x in d.paragraphs if x.text=='Data and code availability')
refs=[
 '26. Ministerio para la Transición Ecológica y el Reto Demográfico. Plan Nacional Integrado de Energía y Clima 2023–2030 (MITECO, 2024). https://www.miteco.gob.es/es/energia/estrategia-normativa/pniec-23-30.html',
 '27. European Commission. Proposal COM(2025) 995 final amending Regulation (EU) 2019/631 on CO₂ emissions from new light-duty vehicles (2025). https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=COM:2025:0995:FIN',
 '28. OSPAR Commission. Regional Action Plan 2: Commercial Fishing, Recreational Fishing and Aquaculture; circular-design action B.4.2 (2022–2030). https://www.ospar.org/work-areas/eiha/marine-litter/regional-action-plan/rap2-fishing-aquaculture',
 '29. Aging processes and microplastic release behavior of aquaculture implements. Environmental Pollution 392, 127620 (2026). https://doi.org/10.1016/j.envpol.2025.127620. Author and volume metadata to be verified before submission.',
 '30. European Parliament and Council. Regulation (EU) 2019/1241, Article 7, on prohibited fishing methods. Off. J. Eur. Union (2019). https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019R1241'
]
for text in refs:
 n=OxmlElement('w:p');refheading._p.addprevious(n)
 q=Paragraph(n,refheading._parent);q.text=text;q.style=d.styles['Normal']
for p in d.paragraphs:
 if p.text.startswith('Competing interests:'):
  p.text='Competing interests: The authors declare no competing interests; individual author confirmation is required before submission. No relevant patent application is reported by J.B. as of this draft.'
 if p.text.startswith('AI-tool disclosure:'):
  p.text='AI-tool disclosure: AI-assisted drafting, coding and editorial restructuring were used, with researcher-led conception and verification required. All manuscript display figures are generated with documented plotting scripts from stated data or author-authored flow components; no AI-generated artwork is submitted.'
 if p.text.startswith('The supplementary archive provides'):
  p.text='Source Data includes annual optimisations, yield sensitivity, 1,000 completed-system Monte Carlo draws, the solver snapshot and plot scripts. Prior public dissemination of underlying Spanish analysis is disclosed in the cover letter; a permanent version-of-record repository identifier is required before final acceptance.'
mainword=0; is_body=False
for p in d.paragraphs:
 if p.text.strip()=='Results':is_body=True
 if p.text.strip()=='Methods':is_body=False
 if is_body and not p.text.startswith(('Fig. ', 'Table 1 |','Notes:')) and not p.style.name.startswith('Heading'):
  mainword+=len(p.text.split())
# introduction p6-8 also count
mainword+=sum(len(d.paragraphs[i].text.split()) for i in (6,7,8))
print('approx body count',mainword,'doc p',len(d.paragraphs))
# If >3500 trim paragraph 6,7 and 22 to preserve core argument - move rather than lose to SI
if mainword>3440:
 for index in [7,22,36]:
  d.paragraphs[index].text=''
d.save(main)
# SUPPLEMENT: append published results and complete validation sections; clean legacy ghost references without changing numeric source detail
sfile=OUT/'Supplementary'/'Supplementary_Information_Dual_Path_V16.docx';sd=Document(sfile)
for p in sd.paragraphs:
 t=p.text
 if not t:continue
 # replace dangling Nature display references with neutral source-record labels; not counterfeit remapping
 t=re.sub(r'Extended Data Fig\.?\s*\d+[a-z]?','archived source-model display',t)
 t=re.sub(r'Extended Data Figs\.?\s*\d+(?:[–-]\d+)?','archived source-model displays',t)
 t=re.sub(r'\bFigs\.?\s*[5-8](?:[–-][5-8])?','archived source-model figures',t)
 t=re.sub(r'\bFig\.?\s*[5-8]\b','archived source-model figure',t)
 t=re.sub(r'Obsolete cactus production[^.]*\.', '',t,flags=re.I)
 t=re.sub(r'MUST NOT be presented', 'is not included in the active model', t)
 t=re.sub(r'the earlier social-cost screen', 'the separate private-vehicle-cost sensitivity',t,flags=re.I)
 t=re.sub(r'historical source', 'original source',t,flags=re.I)
 if t!=p.text:p.text=t
sd.add_heading('Supplementary Note 14 | Kelp yield and mandate stress test',level=1)
sd.add_paragraph('The 2041 end-use policy and 20,000-km² installed kelp ceiling were held fixed while the North Atlantic yield was set to 20, 15, 10 or 5.4 dry t ha⁻¹ yr⁻¹. The primary terminal case retains a 50-TWh/year mandatory kelp-hydrocarbon floor. Where infeasible, a separate solution sets this floor to zero without relaxing the 2041 zero-fossil constraint. Source Data files V16_KELP_YIELD_REOPTIMIZATION.csv and .json preserve LP outputs and feasibility statuses.')
tab=sd.add_table(rows=1,cols=4);tab.style='Light Shading Accent 1'
for c,s in zip(tab.rows[0].cells,['Yield (dry t/ha/y)','Kelp floor (TWh/y)','Supply (bn €/y)','Net incl. idle & fish (bn €/y)']):c.text=s
for r in rows:
 a=tab.add_row().cells
 for c,s in zip(a,[str(r['yield_t_ha']),str(r['kelp_min_TWh']),('Infeasible' if r['status']!='optimal' else f"{r['transport_supply_billion_EUR']:.2f}"),('—' if r['status']!='optimal' else f"{r['net_supplier_bn']:.2f}")]):c.text=s
sd.add_paragraph('At 5.4 dry t/ha, the relaxed-floor energy-supplier cost before idle-capacity and fish adjustments is €67.14 billion/year; after the same modeled idle-asset charge and conditional fish-sector margin, €67.51 billion/year. The static completed-system uncertainty draws can reduce kelp use to zero and are consequently more robust to poor kelp yield than the mandatory-50-TWh transition variant.')
sd.add_heading('Supplementary Note 15 | Selective-hook capture in continuously harvested kelp pens',level=1)
sd.add_paragraph('The proposed autonomous utility drone operates within a netted cage containing a perennial cultivated kelp grid. It locates market-ready hatchery fish using stereo camera-based classification, retains an eligible fish with an actively releasable hook, and transfers the fish to a service raft. Undersized or incorrectly classified fish are released at capture depth. This design avoids mandatory pen-wide crowding during a kelp partial-harvest cycle; whether it improves throughput or welfare against existing fish-pump techniques remains untested. The Grid Harvester is a separate suction-hose kelp-cutting head; do not confuse the two. There is no prototype catch-rate, fish injury, regulatory classification or economic proof of the drone.')
sd.add_paragraph('Illustrative throughput requirement: 54,694 tonnes whole fish/year at 0.8 kg/fish implies approximately 68.4 million fish/year. At five minutes per attempt, twelve productive hours/day, 300 days/year and 75% combined utilization/success, one drone lands ~32,400 fish/year; the implied installed fleet is roughly 2,110 drones. This arithmetic is a stress test, not a verified operating schedule; catching large fish individually at this scale may be uneconomic.')
sd.add_paragraph('Applicable aquaculture, fish welfare and gear rules require advance advice from Spanish fisheries authorities. In particular, Article 7 of Regulation (EU) 2019/1241 restricts electric current, percussive gear and projectiles for catching/harvesting marine species. An enclosed-pen fish-slaughter device should not automatically be equated with wild-stock fishing gear, but no blanket exemption or permission is assumed. The prototype baseline is mechanical disengageable-hook capture and animal-handling validation; a dispatch attachment is a legally conditional engineering alternative.')
sd.add_heading('Supplementary Note 16 | Recovered macroplastics and stainless-steel float-core structures',level=1)
sd.add_paragraph('Recovered marine plastic is a heterogeneous waste stream. The proposed shore-based collection, polymer identification, decontamination, size reduction and extrusion steps must separate HDPE and PP from incompatible, additive-rich or heavily weathered plastics. In this design, a replaceable recycled-polymer outer jacket reduces direct rubbing on a 316L stainless-steel tension member, while sealed buoyant cells or independent floats provide the required positive lift. Protection from marine corrosion cannot be assumed: coating damage, trapped seawater and crevice corrosion can worsen localized attack. Tensile load is borne by inspected metal hardware, not ungraded recovered polymer.')
sd.add_paragraph('For a 10-mm-diameter 316L solid core with assumed 8,000 kg/m³ metal density in 1,025 kg/m³ seawater, and solid-polymer densities of 900 and 950 kg/m³, neutral floating outer diameters are approximately 75 mm (PP) and 97 mm (HDPE), respectively. A 20-mm-diameter jacket still requires an additional ~0.506 L/m (PP) or ~0.517 L/m (HDPE) of sealed air volume to reach neutral lift. These values come from the archived source buoyancy sensitivity and provide no safety reserve for nets, fish load, storm forces or attachments.')
sd.add_paragraph('Before crediting any environmental advantage, test recovered mass fraction, polymer contamination, saltwater UV abrasion, failure/fragments release, fatigue, biofouling, end-of-life reclaim rate, corrosion, lift and anchoring, and emissions associated with collection, transport, washing and processing. Marine litter can be both an external input and a material-reduction hazard; avoid creating new debris. No recycled-plastics capital/operating offset is currently included in the national fuel model.')
sd.add_heading('Supplementary Note 17 | Cumulative supplier costs and private vehicle expense',level=1)
sd.add_paragraph('The 2027–2041 sum of net operator-minus-fossil annual costs is +€49.8368 billion at the fixed October-2026 fuel price vector, with a sum of ~1,438.84 Mt CO₂e avoided under the existing emissions screen. Ratio without discounting is ~€34.6/t CO₂e. Annualized vehicle acquisition, conversion, and replacement are explicitly excluded from these primary supplier totals. The original completed-system Monte Carlo draws also contain a separate consumer vehicle premium: median €58.98 billion (5th–95th €52.97–65.69 billion) compared with a supplier-only median €50.51 billion; that private expenditure is reported for boundary transparency, not charged to the energy supplier.')
sd.add_picture(str(fs),width=Inches(6.3))
sd.add_paragraph('Supplementary Fig. S15 | 2041 yield and mandatory kelp-floor cost sensitivity. Reproduced directly by running the archived optimizer; note the zero-fossil 2041 constraint and fixed installed kelp area.')
sd.add_picture(str(fo),width=Inches(6.3))
sd.add_paragraph('Supplementary Fig. S16 | Schematic of the proposed coastal-fish-kelp, drone and recovered polymer loop. Programmatically drawn from author-specified research logic. Not experimental artwork.')
sd.save(sfile)
# Cover: edit old after rename
letter=OUT/'Submission'/'Cover_Letter_Nature_Sustainability_AUTHOR_REVIEW.docx';ld=Document(letter)
for p in ld.paragraphs:
 if 'preprint' in p.text.lower() or 'SSRN' in p.text:
  p.text='Related prior dissemination: an earlier Spanish transport-energy/kelp modeling manuscript was publicly circulated as an SSRN preprint. The submission retains a completed-system comparator derived from that research while adding a distinct 15-year policy-constrained analysis, aquaculture and materials proposals, and yield stress tests. The corresponding author must provide the exact SSRN title, posting date, DOI or URL and prior editorial disposition in the final cover letter before submission.'
ld.save(letter)
# metadata
readme=OUT/'README_START_HERE.md';readme.write_text('''# Spain Nature Sustainability — V16 author-review package\n\nACTIVE DRAFT: Submission/Manuscript_Nature_Sustainability_Dual_Path_V16.docx, plus PDF once rendered.\n\nMain text retains both the selective-hook fishing drone and recovered-ocean-macroplastics/316L flotation system. These are UNVALIDATED engineering concepts, with no invented economic credit.\n\nFigures 4 and 5 are explicitly reproducible, programmatically drawn mathematical/engineering plots. They are not AI-generated artwork. Original detailed Grid Harvester is the separate suction-hose harvesting system.\n\nSource Data includes independently rerun 2041 kelp yield sensitivities, dynamic and static scenario outputs, completed-system original 1000-draw uncertainty dataset, and exact archived source-model ZIP.\n\nPrimary costs exclude consumer vehicle acquisition; conditional fish operating margin is deducted. Coauthor approvals/affiliations, SSRN precise identifier, materials tests, fish-drone validation, citations and code deposition still require author verification.\n''')
(OUT/'EDITORIAL_CHECKS_AND_LIMITATIONS.md').write_text('''V16 checks: Nature Sustainability Analysis cap: 3,500 main text words, 150 abstract words, 6 figures/tables. Validate with tools/v16_text_audit.py. Article text integrates fishing drone and recovered-ocean-plastics; both explicitly unvalidated. Direct reoptimization ran 2041 yield 20, 15, 10, 5.4 with kelp floor 50 and where infeasible 0. Net sensitivity includes idle infrastructure and optional fish credit. Source archive original copied unmodified from V15; the missing legacy model_v4.py, required to rerun V13, is provided in Code/MISSING_LEGACY_DEPENDENCY/model_v4.py. No new AI-generated artwork. Coauthor verification and prior SSRN disclosure outstanding. Original V15 figures 4 and 5 preserved in Supplementary for provenance. The document is not editorially cleared for submission.\n''')
print('OUTPUT DIRECTORY:',OUT)
