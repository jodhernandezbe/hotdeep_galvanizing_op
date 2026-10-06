# MATLAB port notes

Everything here concerns the port of thesis annex D (`docs/matlab_reference/*.m`) to `src/`.
Fidelity policy (see `ARCHITECTURE.md`): numerically faithful; fix only (1) what cannot run, (2) provably result-neutral
defects; **preserve** result-changing defects behind a `preserve_thesis_quirks` flag (default `True`).

## Validation against the thesis (chapter 4)

Run (6 min, seed 7): 100 simulated years of 41 379 264 pieces, thesis weights (Table 4-1), `preserve_thesis_quirks=True`.

| Quantity | Thesis | Port |
|---|---|---|
| Mean standard thickness → U_P,max | U_P,admissible = 16 866 µm (80 %) → U_P,max ≈ 21 082 | 21 082.6 (exact) |
| Mean process utility, 95 % CI | [16 406 ; 16 987] µm | **[16 408 ; 16 988]** |
| P(process sustainable) | 0.4526 | **0.4529** |
| Independent effect, fluxing | 67.92 % | **67.5 %** |
| Independent effect, pickling | 13.80 % | **22.5 %** (still the second critical unit; Pareto picks fluxing + pickling as in the thesis) |
| Indicators below 80 % on average | GPW, V_l-poll, m_S-S, V_l-spec, ω_S,recy, AAE, W_RM, V_WT, COM | same set (RSEI ≥ 80 as implied) |

**P(sustainable) and the CI are the thesis' assumed-normal constructs, not empirical statistics** (`main_program.m`
lines 250-259): the thesis takes `Std_U_P = (U_P_max - U_P_average)/3` — a normal whose 3-sigma spans the gap to the
maximum — and reports `normcdf(U_P_max) - normcdf(0.8 U_P_max)` under it; the CI uses the same assumed sigma. The
empirical year-to-year spread of U_P/U_max is two orders of magnitude narrower (±0.06 percentage points at full-year
scale, because U_P and U_max share the year's standard-thickness mix), so the empirical exceedance fraction is a step
function of the mean (0 below 80 %, 1 above) and cannot reproduce 0.4526. `mcdm.sustainability_probability` follows
the thesis construct (`analysis.critical_points.assess_sustainability`);
`mcdm.empirical_sustainability_probability` keeps the empirical fraction for the discussion.

The thesis results only reproduce with the literal listing behaviour (quirks 1 and 11 below), so it is the default.
With `preserve_thesis_quirks=False` every balance is mass-conserving (see "Corrected mode" below) and the numbers shift
accordingly but stay close (20 samples, seed 7): mean U_P 16 700 vs 16 694 in thesis mode, P(sustainable) 0.4534 vs
0.4519, and the same critical units (fluxing, then pickling).

## Quirks preserved by default (`preserve_thesis_quirks=True`)

1. **Fluxing state (HDG ↔ `fluxing2`).** `fluxing2` returns `[Q6, m_sln, C, Tsln, m_sln_remove, mHCl_added, mNH4OH_added, Vol, pH]`
   but `HDG` unpacks 8 outputs, so the *volume* lands in the variable `pH`, `Vol_6` is never updated and the next call
   receives `pHo = Vol`. Also `initial_conditions(4)` is called with 5 outputs on start-up and 4 on renewal (the listing
   shows 4 outputs, so `pH` is also missing from the printed function). Port: `simulation._apply_flux_result`, `Bath.renew(keep_ph=...)`.
2. **Atmospheric acidification potential (GREENSCOPE).** `G_I(:,5)` is assigned twice, so AAP (SO₂) overwrites POCP and
   column 6 stays 0, while best/worst use the right columns (column-6 score is always 100). Port: `compute_greenscope`.
3. **Fuzzy AHP.** The reciprocal triangular number keeps the modal value un-inverted (`[TFN(15)^-1 TFN(14) TFN(13)^-1]`)
   and the synthetic extent multiplies by `B` instead of its inverse (`BB` is computed and never used). Port: `fuzzy_ahp_weights`.
4. **Zinc lost on reprocessing.** In the reprocessing branch `m_zn_lost` is overwritten inside the loop over pieces, so only
   the last reprocessed piece's coating counts (the coating total `m_zn_coating_T` does accumulate every piece, including
   the first coating of the same pieces: double counted). Port: `simulation._deposit_coating`.
5. **NaOH molar mass.** Degreasing uses 38.9971, everything else 39.9971 (`NAOH_MW_DEGREASING`).
6. **Drying.** The latent-heat term applies `22 570 600` J/kg (10× the usual 2 257 060) to `C_6(4)`, which is NH₄⁺, not water
   (column 5). Port: `drying.drying_heat_j`.
7. **Fluxing volume balance.** For `pH > pHo` the extent terms `(2·eta1 + eta2 + 2·eta3)` are not multiplied by 18.0152
   in one volume expression (both sub-branches). Port: `fluxing._basified_volume`; conserved under the flag, fixed when `False`.
8. **Pickling fallbacks.** If the target surface is never reached, MATLAB ignores the reaction and only removes the dragged-out solution.
9. **Rinse replacement schedule.** `Sum_items >= (N+1)·round(Items/54)` renews every lot until the counter catches up with the items processed (visible only when lots are few).
10. **Reprocessing.** `m_zn_coating_T` and pickling/fluxing/galvanizing passes of reprocessed pieces re-use the abnormal bath and skip the random scale on the first constant term of the coating polynomial.
11. **Fluxing ammonium creation.** In the `pH > pHo`, `pH >= 4` branch the listing sets `molNH4OH = k2*molNH4*CH2O/CH`
    (its equilibrium value) with `mNH4OH_added = 0`, and takes `molNH4 = molNH4_o - eta2` with an `eta2` balance that
    assumes an NH4OH addition which never happens: NH4⁺/NH4OH/H2O mass is created from nothing on every such call.
    In the listing the drift stays bounded only because quirk 1 keeps the stored bath volume stale, so the Fe≥5 g/L
    renewal fires often and resets the bath. Port: `fluxing._basified_equilibrium_reset` (thesis) vs
    `fluxing._basified_conserving` (corrected).

## Fixed (result-neutral or non-runnable)

- `CRM(7) = RMC(5)*Input*1-3` → `1e-3`. The COM score is a constant 64.39 for every unit process (best/worst are fixed multiples of `G_I(:,17)`), so the typo has no effect on scores.
- `fuzzy_inference` / `Fuzzyinference` name mismatch; `xlsread`/`xlswrite` I/O dropped (pure function; `sheet_block_to_comparisons` reads the sheet layout).
- `G_score` with best == worst (NaN/Inf in MATLAB) → 100 with a logged warning; fuzzy-AHP 0/0 expert uncertainty → equal expert weights with a warning.
- Rinse tanks 2 and 5 now fall back to the current batch if no batch was ever retired (MATLAB divides by zero when `N2 = 0`, only reachable with very few items).

## Numerical changes

- **ODE solver.** `ode113` → `scipy.integrate.solve_ivp(method="LSODA", rtol=1e-3, atol=1e-6)`.
  The thesis only uses the pickling trajectory up to the point where the surface target is met, so integration stops at a
  terminal event there: normal bath at 11.75 % of the initial FeO (exact crossing instead of linear interpolation between
  steps), abnormal bath at `round(Zn, 1) == 0` or when the rate switch turns off. Beyond that point the rate law has an
  unrelated discontinuity at which the solver chatters for millions of steps (full year: minutes → 6 s).
- **Hierarchical partitioning.** Subset enumeration (Chevan & Sutherland) instead of the index bookkeeping with `combinator`/`combntns`; tested against brute-force permutation averaging.
- **Randomness.** `numpy.random.Generator` passed explicitly; sequences cannot match MATLAB's `rand('state', ...)`.

## Not ported

Plots (`figure`, `boxplot`, `radarplot`, `pareto`), the Excel survey (`categorias.xlsx`, expert answers in annex B are an image: Table 4-1 weights are provided in `src/sustainability/thesis_weights.py`), and the Mac Nally hypothesis test of annex D.5 figures (critical value `critical_r2` is computed).

## Corrected mode (`preserve_thesis_quirks=False`)

Quirks 1, 2, 3, 7 and 11 are disabled: the fluxing step stores its returned volume and pH as intended, the ammonium and
volume balances conserve mass, GREENSCOPE fills POCP/AAP in their own columns, and the fuzzy AHP uses the textbook
reciprocal and synthetic extent. The previously observed unbounded growth of the fluxing bath was caused by quirk 11
compounding (one mid-run call showed NH4⁺ at 49 wt % of a 790 t bath); with conservation restored the bath stays bounded
and the Fe ≥ 5 g/L renewal fires naturally (3 renewals/year). Refactor equivalence of the thesis path was verified
bit-for-bit over 4 000 randomized bath states across all pH branches.

Corrected mode additionally enforces the physical tank capacity with an **overflow bleed**: whatever exceeds the
commissioned fill volume is withdrawn with the bath's composition and accounted in the spent-fluxing / hydroxide-sludge
output streams (`Bath.bleed_to`, `simulation._bleed_fluxing_overflow`, `YearResult.fluxing_bleed_kg`). This mirrors
industrial practice, where the flux bath is maintained by continuous side-stream withdrawal (and regeneration) rather
than dumping — see the sources below; disposal of whole baths is described as prohibitively expensive. Full-scale year:
≈ 7.8 t/year bled (≈ 5 t of it water), bath held at its 12.6–14 m³ fill. Without the bleed the computed volume peaked
at 25 m³, which is only arithmetic — the thesis model has no capacity constraint, and in the listing the issue is
invisible because quirk 1 freezes `Vol_6` forever. 20-sample Monte Carlo (seed 7), corrected mode with bleed:
mean U_P 16 710, P(sustainable) 0.456, critical units fluxing then pickling — same conclusions as thesis mode.

## Sources for the fluxing overflow-bleed decision

- [US 11091828 — Systems for removing impurities from galvanizing flux solution](https://patents.google.com/patent/US11091828):
  contaminated flux circulated through a concentration loop where ozone oxidizes Fe2+, which then precipitates
  (verified 2026-10-06; the earlier 'H2O2' description was wrong).
- [US 10316400 — Systems and methods for removing impurities from galvanizing flux solution](https://patents.google.com/patent/US10316400):
  same family; notes that disposal of contaminated flux as hazardous waste is usually prohibitively expensive and that
  neutralization creates large sludge volumes while wasting the ZnCl2/NH4Cl salts.
- EP 0722001 was listed here by mistake: it is an ion-exchange method for removing zinc from acid effluents, not a
  flux-regeneration patent (verified 2026-10-06).
- [US 6802912 — Deferrizing flux salt composition for flux baths](https://patents.google.com/patent/US6802912):
  iron carry-over into the flux bath cannot be fully avoided even with good rinsing; 1 g Fe forms ~25 g of hard zinc in
  the kettle (why the Fe limit matters).
- [finishing.com thread 485/26 — spent flux disposal practice](https://www.finishing.com/485/26.shtml):
  one US flux company accepts contaminated liquid flux for reprocessing and resale; some galvanizers evaporate to
  dryness; whole-bath disposal is the avoided case.

These support modelling the capacity excess as a withdrawn side stream (option 1) rather than early whole-bath renewal
(option 2); a treated-and-returned regeneration loop is the next-fidelity extension (see open points).

## Open points

- Decide whether the optimization work should run with the thesis behaviour (default) or the corrected, mass-conserving
  mode with the overflow bleed. For optimization under physical constraints the corrected mode is the sound choice; the
  thesis mode remains the reference for reproducing chapter 4.
- A regeneration loop (bleed treated with H2O2/NH4OH and returned instead of wasted) is the next-fidelity extension and
  also one of the thesis's own improvement suggestions for the fluxing stage.

## Economic parameters (2016-2018 prices) and units

- **Prices do not enter U_P.** The COM score is constant (64.39) for every unit process, so cost scenarios change only the
  raw COM [USD] (objective f₂ and reported costs). Scenarios live in `src/sustainability/costs.py`; sources and unit
  conversions are in `docs/LITERATURE.md`.
- **NH₄OH price unit defect, corrected in corrected mode only.** The thesis gives 257 000 COP for 2.1 L of 30 %
  solution (≈ 41 USD/L; the listing's 38.11 is a per-litre value), and the listing uses it as USD/**t** (understated
  ≈ 1000×). Thesis mode keeps the value as written (`THESIS_COSTS`); corrected mode (`preserve_thesis_quirks=False`) uses
  `THESIS_CORRECTED_COSTS`, where NH₄OH is an industrial bulk price (173 USD/t) rather than the laboratory-reagent price.
  Affects fluxing COM and therefore the pH decision variable. `default_costs(preserve_thesis_quirks)` selects the scenario.
- **Price bases.** The thesis prices are marketplace quotes; the `market2025` values are bulk or export indices, so the scenario
  mixes time and purchasing scale and is a sensitivity analysis, not an inflation update. NaOH is converted from the dry
  tonne Argus quotes to a 50 wt% solution (× 0.5); HCl, ZnCl₂ and NH₄Cl are used as published (the sources state region
  and period but not concentration or grade; the HCl value may understate the cost per tonne of 37 wt% acid by up to about
  15 %); zinc is the USGS-reported LME annual price.
- **Not updated for lack of a comparable source:** gas (0.45 USD/m³), electricity (0.17 USD/kWh), wastewater treatment,
  labor, fixed capital. Labor and fixed capital are identical for every policy (they shift the COM level, not the ranking).
- **Basis of the optimization vs. the manuscript.** The search runs on a reduced simulated year (10⁶ pieces) but the fixed
  annual costs (0.28·capital + 2.73·labor ≈ 0.64 M USD) do not scale with the pieces, so the objectives are not
  comparable with full-year (41.4 M pieces) figures. The front is therefore **re-evaluated at the full-year budget**
  (`mcdm.prepare_selection`) before the compromise is selected and Figure 1 is drawn.

## Data corrections in corrected mode (energy emission factors)

Thesis mode keeps the listing's factors verbatim. Corrected mode replaces them with sourced Colombian factors
(`greenscope.GRID_CO2_KG_PER_KWH_UPME_2024`, `greenscope.NATURAL_GAS_CO2_KG_PER_J`):

- **Electricity (dryer):** listing 4 kgCO2/kWh (thesis Table A-3 prints 43; the code uses 4) → 0.220 kgCO2e/kWh,
  the UPME 2024 SIN grid factor for GHG inventories (`upme2024fe`). The plant buys grid electricity, so the grid
  factor applies, not a hydropower life-cycle value.
- **Natural gas (heated baths):** listing `25e-6/1.99714` kgCO2 per J of duty ≈ 12.5 kgCO2/MJ → FECOC generic
  Colombian natural gas, 56.06 kgCO2/GJ of fuel over the 0.737 boiler efficiency (`upme2016fecoc`), ≈ 0.076 kgCO2/MJ
  of duty (0.274 kgCO2/kWh of duty). The listing is ~164x higher; its divisor 1.99714 is within 1 % of FECOC's per-m3 factor (1.9806 kgCO2/m3),
  suggesting a units mix-up in the original chain.

## Instrument findings (GREENSCOPE as an optimization objective)

Exposed by the NSGA-II stress test (2026-10-04); all faithful to the thesis and to Ruiz-Mercado's methodology:

1. **Self-referencing normalization.** The worst cases of V_l-poll, V_l-spec and V_WT are the process' own streams
   without recovery (thesis Anexo A, Table A-1 notes 4, 7, 8), so their scores measure the recovered fraction and are
   invariant to how much waste a policy creates. COM's best/worst are fixed multiples of COM itself (score 64.39).
   The drying GWP worst case equals its actual value (`G_I_worst(6,4)` = the same expression), so that score is 0 by
   construction. Only conversion (AAE), the energy scores and quality can move U_P.
2. **AAE is a limiting-reagent conversion.** Thesis eq. 2-41 specializes Ruiz-Mercado's actual atom economy to the
   limiting reagent (the incoming rust), so it cannot penalize acid overfeeding: unguarded optimization renews the
   pickling bath ~20x more, raises AAE from ~2 % to ~46 % and multiplies spent-acid volume by 7 with no U_P penalty.
   Mitigations: the no-backsliding veto on the MCDM selection (`mcdm.prepare_selection`), and the fed-basis option
   (`fed_atom_economy=True`): pickling AAE over rust share + HCl actually charged (FeCl2 as product). The fed basis is
   scoped to pickling; the fluxing unit keeps the thesis basis because its reacting iron arrives as an internal
   transfer (residual rust) and its chloride comes from the bath salts, so a fed denominator is not definable from
   the stored input streams.
