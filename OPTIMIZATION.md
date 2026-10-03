A robust optimization under uncertainty framework using the kinetic, mass, and energy balance models developed in the thesis, the system variables can be categorized into three distinct control tiers.

## Decision Variables (Controllable Inputs)

* **Pickling conditions:** The concentration of HCl (typically 17% for normal pickling or 3-5% for dezincification) and the piece immersion time.


* **Fluxing parameters:** The ZnCl2/NH4Cl ratio (modeled at 60/40), total salt concentration, and the operating pH (controlled around 4.5).


* **Thermal management:** The operating temperatures of the degreasing (40-60°C), fluxing (50°C), and galvanizing baths (445-455°C).



## Uncertain Parameters (Stochastic Variables)

* **Material properties:** The mass, gauge thickness, and chemical composition of the incoming steel. The silicon content is particularly critical as it directly alters the zinc coating thickness kinetics.


* **Initial contamination:** The random distribution of rust (300-590 g/m2) and grease/oil levels on the incoming steel surfaces.


* **Environmental factors:** The ambient temperature variations that continuously impact the heat loss and energy balances across all open process tanks.



## Objective Functions & Constraints

* **Process Sustainability:** Maximizing the global process utility ($U_P$), which integrates the fuzzy-weighted environmental, economic, energy, and efficiency metrics.


* **Critical Stage Metrics:** Minimizing specific poorly performing indicators isolated within the pickling and fluxing stages, such as polluted liquid waste ($V_{l-poll}$), water consumption ($V_{WT}$), and manufacturing costs (COM).


* **Normative Quality:** Ensuring the final zinc coating thickness ($\delta$) rigorously satisfies the minimums established by the UNE-EN ISO 1461 standard without resulting in excessive zinc consumption.

---

## Implemented formulation (change `add-nsga2-robust-optimization`)

Simulation mode: corrected (`preserve_thesis_quirks=False`). Thesis mode stays frozen for chapter-4 validation.

### Decision vector (`src/process/operating_policy.py`)

| # | Variable | Bounds | Units |
|---|---|---|---|
| 1 | `degreasing_temperature_c` | [40, 60] | °C |
| 2 | `pickling_hcl_pct` | [12, 18] | % wt |
| 3 | `pickling_dip_time_s` | [600, 1200] | s |
| 4 | `fluxing_temperature_c` | [40, 60] | °C |
| 5 | `fluxing_ph_target` | [4, 5] | — |
| 6 | `fluxing_salt_g_per_l` (ZnCl₂/NH₄Cl fixed 60/40) | [300, 500] | g/L |
| 7 | `galvanizing_temperature_c` | [445, 455] | °C |

Baseline design: `BASELINE_POLICY` (thesis-nominal midpoints: 50 °C, 17 %, 900 s, 50 °C, pH 4.5, 400 g/L, 450 °C).

### Objectives (minimize) and constraints (g ≤ 0)

F(x) = [ −E[U_P], E[COM] (USD), E[V_l-poll] (m³), E[V_WT] (m³) ], Monte Carlo means over N = 100 common-random-number
samples per evaluation (`np.random.SeedSequence(seed).spawn(N)`; renewals use a dedicated stream so lots/ambient stay
paired across candidates).

g₁ = P(δ < δ_ISO) − 0.02; g₂ = E[peak pickling Fe²⁺] − 150 g/L.

The fluxing-bath Fe²⁺ limit (5 g/L) is the simulation's renewal trigger, not a constraint: the peak is ≥ 5 g/L at every
renewal by construction (a first run with it as g₃ had no feasible solution in 20 generations), and the literature gives
no annual renewal cap (`docs/LITERATURE.md`). Renewals are priced into E[COM] and E[V_l-poll].

### Algorithm and budgets

NSGA-II (`pymoo` 0.6): pop = offspring = 100, LHS sampling, SBX(p=0.9, η=15), PM(p=0.1/var, η=20); termination at
150 generations or hypervolume stagnation (best hypervolume of the last 15 generations improves < 1e-4 relative, not before generation 100). Evaluation budget: items = 10⁶ per sample
(benchmark: 0.088 s/year; full 41.4M-item year = 3.6 s). Deep characterization (as-is stochastic operation,
nominal baseline and compromise): N = 1000 at the full-year budget. MCDM: fuzzy linear memberships on the
utopia–nadir range, FAHP category weights mapped as
U_P ← efficiency+energy+quality, COM ← economy, V_l-poll/V_WT ← environment/2 (`objective_weights_from_fahp`).
P(sustainable) follows the thesis construct — U_P ~ N(mean, (U_max − mean)/3), band [0.8 U_max, U_max]
(`docs/MATLAB_PORT_NOTES.md`); the empirical exceedance fraction is reported separately because it is degenerate.

### Reproducing the pipeline

```bash
python -m src.optimization.run_nsga2 --seed 42 --workers 8 --cost-scenario market2025           # → results/checkpoints/nsga2_market2025_seed42/
# if interrupted: add `--resume latest` to the command above to continue from the last checkpoint
python -m src.optimization.mcdm --run-dir results/checkpoints/nsga2_market2025_seed42 --workers 8  # full-year front re-evaluation, selection, N=1000 → results/mc/
python -m src.optimization.price_sensitivity                                                   # from results/mc/front.npz (full year, exact COM shift, no re-simulation) → results/sensitivity/
python -m src.optimization.weight_sensitivity                                                  # → results/sensitivity/
python -m src.analysis.manuscript_outputs                                                      # → results/figures|tables/
```