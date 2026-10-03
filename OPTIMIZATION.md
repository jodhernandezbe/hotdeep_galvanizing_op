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
| 8 | `pickling_renewal_fe_g_per_l` | [60, 150] | g/L |

Baseline design: `BASELINE_POLICY` (thesis-nominal midpoints: 50 °C, 17 %, 900 s, 50 °C, pH 4.5, 400 g/L, 450 °C,
renewal at 150 g/L). Variable 8 is the Fe²⁺ concentration that triggers a normal-pickling renewal: renewing late
exhausts the acid and carries residual rust into the flux (more flux renewals: salts + waste), renewing early spends
acid and spent-bath volume — both sides are priced in the objectives. The bath's Fe²⁺ plateaus near 130 g/L at the
thesis drag-out, so the thesis trigger (150) in practice never fires. The fluxing trigger (5 g/L) and the rinse
cadence (54/year) stay **fixed**: the model has no downstream coupling for them (dross is drawn randomly and the
rinses are sinks), so freeing them would fabricate improvement with no modeled penalty.

### Robust objectives (minimize) and chance constraints (g ≤ 0)

Per candidate, N = 100 common-random-number samples (`np.random.SeedSequence(seed).spawn(N)`; renewals use a
dedicated stream so lots/ambient stay paired across candidates). The optimizer minimizes the CVaR at the 10 % tail
of each objective — the mean of the worst 10 sampled years — instead of the plain mean:

F(x) = [ −CVaR₀.₁(U_P, worst = lowest), max over price scenarios of CVaR₀.₁(COM) (USD),
CVaR₀.₁(V_l-poll) (m³), CVaR₀.₁(V_WT) (m³) ].

The cost objective is the **worst case across the three price scenarios** (market2025, thesis_corrected, thesis):
prices enter COM only through the purchased raw-material masses, so each sample's COM under another scenario is
recomputed exactly as `COM + 1.23e-3 · Δprices · masses` with no extra simulation (`BatchSummary`).

g₁ = q₀.₉₅(annual defect fraction) − 0.02; g₂ = q₀.₉₅(peak pickling Fe²⁺) − 150 g/L (chance constraints: the 95th
percentile of the Monte Carlo years must comply, not only the mean). `tail_fraction=None`, `defect_quantile=None`
and `price_scenarios=None` recover the expectation-based formulation of the first runs.

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