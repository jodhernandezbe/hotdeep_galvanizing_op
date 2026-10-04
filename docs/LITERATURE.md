# Literature for the manuscript

Sources behind modeling decisions of the optimization (search date 2026-10-02). Entries note what each source was seen
to support in the search snippet; **read the full text and verify before citing** — none has been read in full.
Source quality: peer-reviewed > standards/trade association > patents > forum Q&A (forum is not citable in a paper;
use it only to find primary sources).

BibTeX entries for every source below (and for the methods: NSGA-II, pymoo, fuzzy AHP, GREENSCOPE, ISO 1461) are in
[`references.bib`](references.bib); each entry's `note` says whether it was seen in a search or written from memory.
Entries written from memory must have their DOI/pages checked before submission.

## Source framework (cite both)

| Work | What it provides | Status |
|---|---|---|
| Hernández Betancur, J. D. (2018). *Detección de los puntos críticos del proceso de galvanizado por inmersión en caliente…*, Tesis de Maestría, Universidad Nacional de Colombia ([repositorio](https://repositorio.unal.edu.co/handle/unal/63201)). Key `hernandez2018thesis` | MATLAB models, FAHP weights (Table 4-1), 2016–2018 prices, Monte Carlo of the line. Abstract: kinetic Monte Carlo; pickling and fluxing are the critical stages; probability of being sustainable 45.26 % | Repository record and abstract read |
| Hernández-Betancur, J. D., Hernández, H. F., Ocampo-Carmona, L. M. (2019). A holistic framework for assessing hot-dip galvanizing process sustainability. *J. Clean. Prod.* 206, 755–766. [doi:10.1016/j.jclepro.2018.09.177](https://doi.org/10.1016/j.jclepro.2018.09.177). Key `hernandez2019holistic` | Journal version of the assessment framework (GREENSCOPE + fuzzy AHP + additive utility + hierarchical partitioning) that this repository extends with optimization | Metadata verified via Crossref; **full text read** (PDF in `manuscript/references/`). Note: it states 410379.264 pieces per year, a typo for 41,379,264 (the MATLAB listing and the 180 t/month figure agree with 41.4 M) |

The optimization manuscript should present itself as an extension of these two works, and must say which results
reproduce theirs (thesis mode, chapter 4) and which are new (corrected mode, NSGA-II, price scenarios). Check the
paper's own numbers (weights, 45.26 % probability) against `thesis_weights.py` and the thesis-mode validation table
in `docs/MATLAB_PORT_NOTES.md` once the full text is available.

## Zinc use by sector (introduction)

Primary source: ILZSG, *The World Zinc Factbook 2024* (`ilzsg2024factbook`, p. 36, read): zinc usage by first use
application: galvanizing 60 %, zinc alloys 15 %, zinc compounds 11 %, brass and bronze 9 %, semi-manufactures 4 %,
miscellaneous 1 %; by end-use sector: construction 50 %, transport 20 %, infrastructure 15 %, industrial machinery 7 %,
household appliances 6 %. The Factbook (pp. 39 to 40) also states that batch (general) hot-dip galvanizing is "quite
fragmented with many small plants located close to their markets", unlike continuous galvanizing, which is capital
intensive and carried out by large integrated steel producers. The year of the shares is not printed on the page
(search results attribute them to 2023). The 60 % covers all galvanizing (continuous and batch); a split between the two
was not found in the primary source.

## Economic parameters: prices from 2016–2018 vs. 2025

The thesis prices (`docs/matlab_reference/greenscope.m`, lines 310–373) came from retail/marketplace sources (kemcore,
alibaba, wiegel.de, ebay) in USD per tonne of the stated commercial product; units and bases were checked against the
MATLAB comments. Three cost scenarios exist in `src/sustainability/costs.py`:

- `thesis`: the MATLAB values as written (used in thesis mode; keeps the NH₄OH unit defect below).
- `thesis_corrected`: thesis prices with the NH₄OH unit defect corrected; **the scenario the optimization uses**.
- `market2025`: sourced 2025 prices, converted to the thesis basis (conversions below).

**Key fact:** the COM *score* is constant (64.39) for every unit process, so prices do **not** enter U_P. They only
change the raw COM [USD] (objective f₂ and the reported cost figures).

| Item | `thesis` | `thesis_corrected` | `market2025` | Source and basis of the 2025 value (key in `references.bib`) |
|---|---|---|---|---|
| Zn, USD/t | 2590 | 2590 | 2866 | USGS Mineral Commodity Summaries 2026 (`usgs2026zinc`): LME cash price 130 cents/lb in 2025 (estimate) × 22.0462 lb/kg·1000 = 2866 USD/t. **Primary source, read** |
| ZnCl₂, USD/t | 990 | 990 | 1296 | IMARC (`imarc2025zncl2`), USA, Q3 2025. The page gives region and quarter only; grade not stated |
| NH₄Cl, USD/t | 150 | 150 | 260 | IMARC (`imarc2025nh4cl`), North America, 0.26 to 0.28 USD/kg (2025 to Sep 2026); regional spread 80 to 550 USD/t. Grade not stated |
| HCl, USD/t | 165.5 (37 wt%) | 165.5 | 244 | IMARC (`imarc2025hcl`), North America, 243.84 USD/t in Dec 2025. **Concentration not stated** (by-product acid, commercial grades are about 31 to 36 wt%); no rescaling is applied, so the value may understate the cost per tonne of 37 wt% acid by up to about 15 % |
| NaOH 50 wt%, USD/t of solution | 580 | 580 | 185 | Argus (`argus2025caustic`, 14 Nov 2025): US Gulf export 340 to 400 USD per **dry** metric tonne (mid-point 370) × 0.5 NaOH per tonne of 50 wt% solution. Basis explicitly stated by Argus; US domestic barge was 440 to 475 USD per dry short ton |
| NH₄OH 30 wt%, USD/t | 38.11 | 173 | 173 | Intratec (`intratec2025nh4oh`), USA: 173 USD/t (Sep 2025), 190 (Jan 2026, +11 % year on year, so about 171 in Jan 2025); concentration not stated. See the defect below |
| Gas 0.45 USD/m³, electricity 0.17 USD/kWh, wastewater, labor 4.5 USD/h, fixed capital | thesis | thesis | thesis | **Not updated**: no comparable source (`elcolombiano2025gas` is a purchase cost, not the industrial tariff; `cepci2017` = 567.5, 2024 value not retrieved; `dane2025smmlv`). Labor and capital are identical for every policy: they shift the COM level, not the ranking |

**Interpretation limit.** The thesis prices come from marketplace quotes (kemcore, alibaba, wiegel.de, ebay), i.e. small
lots, while the 2025 values are bulk or export market indices. The difference between the `thesis` and `market2025` columns
therefore mixes the passage of time with the purchasing scale (for example NaOH: 580 vs 185 USD/t of solution), and
`market2025` is a bulk-price sensitivity scenario, not a pure inflation update. Only the zinc price is a primary-source,
same-quantity update.

**NH₄OH unit defect (corrected in `thesis_corrected` and `market2025`).** The thesis (p. 86, Spanish text) gives the
price of the 30 % solution as "2,1 L es 257000 COP", i.e. 122 381 COP/L, which is about 41 USD/L at the thesis' own
exchange rate (≈ 2 980 COP/USD from its water price) and 38.11 USD/L at 3 211 COP/USD. The listing uses 38.11 as USD per
**tonne** (`RMC(7)*sum(Input_streams(10,:))*1e-3`, streams in kg), so NH₄OH cost is understated by about three orders of
magnitude. Converting the thesis' own source correctly would give ≈ 40 000 USD/t, a laboratory-reagent price that is not
representative of an industrial plant; the corrected scenarios therefore use an industrial bulk price (`intratec2025nh4oh`,
≈ 173 USD/t). NH₄OH is the pH regulator of the fluxing bath (decision variable `fluxing_ph_target`), so this matters for
the optimization. Confirm the intended price with the thesis author.

**Utilities are in COP in the thesis.** Water 2 308.30 COP/m³, natural gas 1 380.67 COP/m³ and electricity 521.48 COP/kWh
for industrial users of Empresas Públicas de Medellín (EPM) were converted to the listing's USD values (0.7755 USD/t,
0.45 USD/m³, 0.17 USD/kWh) at ≈ 2 980 to 3 070 COP/USD. Updating them requires 2025 EPM tariffs and the 2025 exchange rate
(average ≈ 4 049 COP/USD according to the search used for `references.bib`); they are not changed in `market2025`.

## Literature search: optimization of galvanizing under uncertainty (manuscript gap)

Search of the OpenAlex database on 2026-10-03 with 16 queries (relevance-ranked, 10 to 12 hits read per query, plus the
abstracts of the closest hits): hot-dip galvanizing combined with *multi-objective optimization*, *genetic algorithm*,
*NSGA-II*, *robust optimization*, *operating conditions optimization uncertainty*, *Monte Carlo simulation*, *stochastic or
fuzzy sustainability*, *process simulation (pickling, fluxing)*, *pickling bath optimization*, *batch process
optimization of coating thickness*, *zinc bath temperature and energy*, *life cycle assessment and environmental
optimization*, *sustainability and multi-criteria decision making*, and *circular economy*. Closest works found:

| Work | What it optimizes or assesses | Why it is not the gap |
|---|---|---|
| Wang (2018), *Ind. Eng. Manag.* 7(1), doi 10.4172/2169-0316.1000245 | Air-knife parameters (strip velocity, air pressure, distance) for zinc layer thickness by RSM, Taguchi and GA | Continuous strip line, one quality objective |
| Costa et al. (2019), *Metals* 9, 703; Reséndiz-Flores et al. (2021), *Metals* 11, 578 | Heat-treatment variables of continuous galvanizing of dual-phase steels; multi-objective (Pareto, genetic) on mechanical properties | Material properties, continuous line, no sustainability objectives or uncertainty |
| Crișan et al. (2023), *Materials* 16, 5567 (PickT) | Optimum pickling bath lifetime and inhibitor addition for steel in HCl | Single stage, laboratory data, no whole line |
| Arguillarena et al. (2022, 2023), Lorenz et al. (2023) | Recovery of zinc and iron from spent pickling acids in galvanizing, with life cycle assessment | Assessment of one waste treatment option, not operating-condition optimization |
| Hernandez-Betancur et al. (2019), *J. Clean. Prod.* 206, 755 | Process-level sustainability assessment under random uncertainty (the framework this work builds on) | Diagnostic, one fixed set of conditions |

No work was found that optimizes the operating conditions of the stages of a galvanizing line jointly against several
sustainability objectives under uncertainty. Limits: one database, relevance-ranked retrieval (not exhaustive), English
queries. A Scopus or Web of Science search with the same queries is advisable before submission.

## Fluxing bath (ZnCl₂/NH₄Cl preflux): iron limit and renewal practice

Decision (design D9): the 5 g/L Fe²⁺ limit is the bath-renewal trigger of the simulation, not an optimization
constraint; renewals are priced through COM and V_l-poll. Evidence:

| Claim | Source | Quality |
|---|---|---|
| Preflux contamination should be limited to about 0.5 % Fe (≈ 5 g/L) | [finishing.com Q&A, "Galvanizing Flux Bath Iron Contamination"](https://www.finishing.com/423/25.shtml) | Forum — find the primary source |
| Iron is routinely kept at 1–1.8 g/L; some guides allow up to 10 g/L | [Metchem, flux filter press & regeneration](https://metchem.com/flux-press-regeneration-system-hot-dip-galvanizing/) (vendor) | Vendor |
| Dumping the flux bath is prohibitively expensive as hazardous waste; neutralizing creates large sludge volumes; both waste the zinc ammonium chloride | [US 10316400](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10316400), [US 11091828](https://patents.google.com/patent/US11091828) | Patents |
| Regeneration (H₂O₂ oxidation of Fe²⁺, NH₄OH for pH, polymer-aided precipitation) instead of replacement | same two patents; [EP 0722001](https://data.epo.org/publication-server/rest/v1.2/publication-dates/19980617/patents/EP0722001NWB1/document.html) (see also `docs/MATLAB_PORT_NOTES.md`) | Patents |
| Iron entering the kettle forms hard zinc (≈ 1 g Fe → 25 g hard zinc), a zinc loss | [US 6802912](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6802912) | Patent |
| Iron in flux is tested weekly; low pH raises soluble iron and dross | [AGA knowledge base, flux quality](https://galvanizeit.org/knowledgebase/article/flux-quality-concentration-density-baume-flux-ratio-ph), [AGA, monitoring preflux pH](https://galvanizeit.org/knowledgebase/article/monitoring-ph-of-the-preflux-solution) | Trade association |

**Gap:** no source found giving the number of fluxing-bath renewals per year. The model yields ≈ 2–3 renewals/year
(3–4 batches counting the initial fill) in corrected mode. Candidate primary sources to chase for the manuscript:
[Composition, testing, and control of hot dip galvanizing flux (ResearchGate)](https://www.researchgate.net/publication/240387651_Composition_testing_and_control_of_hot_dip_galvanizing_flux)
and [Regel-Rosocka, Pol. J. Chem. Technol. 2 (2007)](https://yadda.icm.edu.pl/baztech/element/bwmeta1.element.baztech-article-BPS2-0045-0038/c/Polish_Journal_of_Chemical_Technology_2_2007_Regel-Rosocka.pdf)
(pickling-liquor regeneration; appeared in the search, relevance unverified).

## Pickling bath (HCl): exhaustion limit

Decision: constraint g₂ = E[peak pickling Fe²⁺] − 150 g/L. Evidence: regeneration/replacement is triggered at iron
≈ 100–160 g/L with free acid near 45–50 g/L ([US 4209489](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/4209489));
fresh baths start near 15 % HCl (150 g/L); iron reaching ≈ 9 % wt forces drain and recharge (same patent family).
Consistent with the 12–18 % wt HCl decision-variable range. Peer-reviewed support still to be added.

## Not yet researched (needed for the manuscript)

- Coating thickness vs. Si content/temperature regression ([Sandelin curve literature]; the model uses the thesis cubic).
- UNE-EN ISO 1461 thickness minima and the 2 % defect-probability criterion (the standard itself).
- GREENSCOPE methodology (Ruiz-Mercado et al.) and fuzzy-AHP (Chang 1996 extent analysis).
- NSGA-II (Deb et al. 2002) and pymoo (Blank & Deb 2020) for the methods section.
- Fuzzy compromise / max-min satisfaction MCDM on Pareto fronts.

## Energy emission factors (corrected mode)

The thesis energy emission factors are kept verbatim in thesis mode and replaced by sourced Colombian factors in
corrected mode (`src/sustainability/greenscope.py`):

| Factor | Thesis (code) | Corrected | Source |
|---|---|---|---|
| Electricity (dryer) | 4 kgCO₂/kWh (Table A-3 prints 43) | 0.220 kgCO₂e/kWh | UPME, FE del SIN 2024 for GHG inventories (`upme2024fe`); XM reported 164.38 g/kWh for recent generation |
| Natural gas (heated baths) | 25·10⁻⁶/1.99714 kgCO₂/J of duty ≈ 12.5 kgCO₂/MJ | 56.06 kgCO₂/GJ of fuel ÷ 0.737 boiler efficiency | FECOC/UPME 2016, generic Colombian natural gas (`upme2016fecoc`); the IPCC 2006 default (56.1 tCO₂/TJ) is equal to 3 figures |

The thesis gas chain is ~220× the FECOC value; its divisor 1.99714 is within 1 % of FECOC's per-m³ factor
(1.9806 kgCO₂/m³), which suggests a units mix-up in the original listing. The electric factor is the grid (SIN)
inventory factor, not a hydropower life-cycle value, because the plant buys grid electricity in Colombia.
