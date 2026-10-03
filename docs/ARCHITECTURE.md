# MATLAB → Python port: architecture and contracts

Source: thesis annex D (`docs/matlab_reference/*.m`, extracted verbatim from the PDF with line numbers removed).
Target: modular Python under `src/`, mirrored by `tests/`.

## Conventions

- Randomness: every stochastic function takes `rng: np.random.Generator` explicitly (no global state).
  MATLAB `norminv(rand(), mu, s)` → `rng.normal(mu, s)`; `unifinv(rand(), a, b)` / `unifrnd(a, b)` → `rng.uniform(a, b)`.
- Units, indices and variable meanings follow the MATLAB code. Compound/stream/unit-process indices are 0-based and named
  in `src/sustainability/streams.py`.
- Results of unit operations are frozen dataclasses (replaces the 40-output MATLAB `HDG` signature).
- Shared constants live in `src/common/constants.py`; model-specific magic numbers are module-level `UPPER_CASE` constants.
- Plots (`figure`, `boxplot`, `radarplot`, `pareto`) are out of scope for this phase: compute only.

## Fidelity policy

Equations are ported **numerically faithfully**. Exceptions, all listed in `docs/MATLAB_PORT_NOTES.md`:

1. Where the listing cannot run (interface mismatches) the evident intent is implemented.
2. Defects that are provably result-neutral are fixed.
3. Defects that change numerical results are **preserved** and flagged, so thesis numbers can be reproduced.

## Package layout

```
src/common/constants.py            molar masses, physical constants          (done)
src/process/densities.py           NaOH / HCl solution densities             (done)
src/process/initial_conditions.py  fresh bath state for tanks 1,2,3,6        (D.3.1)
src/process/degreasing.py          mass + energy balance                      (D.3.3)
src/process/pickling.py            normal / abnormal pickling kinetics (ODE)  (D.3.4)
src/process/fluxing.py             fluxing equilibrium + energy balance       (D.3.5)
src/process/steel_lots.py          random lots: mass, geometry, composition   (D.3, items block)
src/process/galvanizing.py         coating thickness, dross/ash, bath energy  (D.3, step 7)
src/process/simulation.py          `simulate_year(items, rng)` = MATLAB HDG   (D.3)
src/sustainability/streams.py      Compound / stream / unit-process enums     (done)
src/sustainability/hazard.py       SH(): physical values for toxicity/hazard  (D.4)
src/sustainability/greenscope.py   17 indicators x 7 unit processes + scores  (D.4)
src/sustainability/fuzzy_ahp.py    fuzzy AHP weights + expert uncertainty     (D.2)
src/sustainability/utility.py      stream assembly + unit/global utility (D.1)
src/analysis/hierarchical_partitioning.py   independent/joint effects        (D.5)
src/analysis/critical_points.py    80 % Pareto selection, sustainability prob (D.1)
```

## Contracts (signatures are binding between modules)

### `src/process/initial_conditions.py`

```python
@dataclass(frozen=True)
class BathInitialCondition:
    volume_m3: float
    composition_wt: np.ndarray        # % wt, length 4 (degreasing) / 3 (normal pickling) / 4 (abnormal) / 9 (fluxing)
    mass_kg: float
    temperature_c: float | None       # only degreasing and fluxing
    ph: float | None                  # only fluxing

def degreasing_initial_condition(rng) -> BathInitialCondition      # MATLAB initial_conditions(1); mass = rho * volume
def normal_pickling_initial_condition(rng) -> BathInitialCondition # (2); mass = rho(ambient_c) * volume
def abnormal_pickling_initial_condition(rng) -> BathInitialCondition  # (3)
def fluxing_initial_condition(rng) -> BathInitialCondition         # (4), ph is returned (MATLAB listing omits it)
def rinsing_initial_volume(rng) -> float                           # (2 - 0.2*rand) * 7  (used by tanks 2 and 5)
```

Note: `mass_kg` for degreasing/pickling tanks is computed by the caller in MATLAB (`rho * Vol`, with `density(T, C(1), N)`);
the dataclass holds it so callers do not repeat it. Temperature of pickling tanks is ambient (caller supplies it), so
the pickling constructors take `ambient_c: float` for the density evaluation.

### `src/process/degreasing.py`

```python
@dataclass(frozen=True)
class DegreasingResult:
    saponified_kg: float
    remaining_grease_kg: float
    heat_j: float
    solution_mass_kg: float
    composition_wt: np.ndarray        # [NaOH, H2O, glycerol, sodium carboxylates]
    temperature_c: float
    removed_solution_kg: float

def degrease(grease_and_oil_kg, grease_mw, solution_mass_kg, composition_wt, temperature_c,
             greased_steel_kg, previous_heat_j, ambient_c) -> DegreasingResult
```

### `src/process/pickling.py`

```python
@dataclass(frozen=True)
class PicklingResult:
    solution_mass_kg: float
    composition_wt: np.ndarray
    surface_mass_kg: float            # remaining FeO (normal) or remaining Zn (abnormal) on the steel
    removed_solution_kg: float
    volume_m3: float

def pickle_normal(composition_wt, solution_mass_kg, temperature_c, volume_m3, rust_kg, steel_area_m2,
                  steel_mass_kg, rng) -> PicklingResult        # len(composition_wt) == 3
def pickle_abnormal(composition_wt, solution_mass_kg, temperature_c, volume_m3, zinc_coating_kg, steel_area_m2,
                    steel_mass_kg, rng) -> PicklingResult      # len(composition_wt) == 4
```

ODE integration: `scipy.integrate.solve_ivp` (MATLAB `ode113` ≈ non-stiff multistep → use `LSODA` or `RK45`,
rtol=1e-3, atol=1e-6 as MATLAB defaults). Dipping time `(10*rand + 10) * 60` s drawn from `rng`.

### `src/process/fluxing.py`

```python
@dataclass(frozen=True)
class FluxingResult:
    heat_j: float
    solution_mass_kg: float
    composition_wt: np.ndarray        # length 9
    temperature_c: float
    removed_solution_kg: float
    hcl_added_kg: float
    nh4oh_added_kg: float
    volume_m3: float
    ph: float

def flux(rust_kg, solution_mass_kg, composition_wt, temperature_c, steel_mass_kg, previous_heat_j, ambient_c,
         volume_m3, ph, rng, preserve_thesis_quirks=True) -> FluxingResult
# preserve_thesis_quirks=True reproduces the listing's ammonium bookkeeping and volume balance (see MATLAB_PORT_NOTES.md);
# False makes both balances mass-conserving.
```

### `src/sustainability/greenscope.py`

```python
@dataclass(frozen=True)
class GreenscopeResult:
    indicators: np.ndarray            # (7, 17) G_I
    best: np.ndarray                  # (7, 17)
    worst: np.ndarray                 # (7, 17)
    score: np.ndarray                 # (7, 17) G_score, in %

def compute_greenscope(input_streams: np.ndarray,       # (12, 17) kg
                       output_streams: np.ndarray,      # (10, 17) kg
                       energy_j: np.ndarray,            # (7,)  EC; index with UnitProcess
                       sodium_carboxylate_mw: float, grease_mw: float,
                       fe2_mass_pickling_kg: float, fe2_mass_fluxing_kg: float,
                       steel_surface_mass_kg: float) -> GreenscopeResult
```

### `src/sustainability/fuzzy_ahp.py`

```python
@dataclass(frozen=True)
class FuzzyAhpResult:
    weights: np.ndarray               # (n,) final weights, sum to 1
    expert_uncertainty: np.ndarray    # (n_experts,) theta, sum to 1

def fuzzy_ahp_weights(comparison_codes: np.ndarray) -> FuzzyAhpResult
# comparison_codes: (n_experts, n, n) integers in -4..4 (MATLAB sheet codes; only the upper triangle is read)
```

### `src/analysis/hierarchical_partitioning.py`

```python
@dataclass(frozen=True)
class HierarchicalPartitioningResult:
    independent_pct: np.ndarray       # (m,) I, normalised to 100
    joint_pct: np.ndarray             # (m,) J, normalised to 100
    zero_order_r2: np.ndarray         # (m,) R^2 of y ~ x_i
    critical_r2: float                # rr2 = T^2 / (n - 2 + T^2), T = t_{0.995, n-2}

def hierarchical_partitioning(y: np.ndarray, x: np.ndarray) -> HierarchicalPartitioningResult
```

### `src/process/simulation.py` and `src/sustainability/utility.py`

Owned by the integration step; consume the contracts above.

## Optimization layer (robust optimization under uncertainty)

The optimization work (see `OPTIMIZATION.md` and change `add-nsga2-robust-optimization`) runs the simulator in
corrected mode (`preserve_thesis_quirks=False`); thesis mode stays frozen for validation.

### `src/process/operating_policy.py`

```python
POLICY_BOUNDS: dict[str, tuple[float, float]]   # field name -> (lower, upper)

@dataclass(frozen=True)
class OperatingPolicy:
    degreasing_temperature_c: float    # [40, 60] degC, initial degreasing bath temperature
    pickling_hcl_pct: float            # [12, 18] % wt, fresh normal pickling bath (initial + renewals)
    pickling_dip_time_s: float         # [600, 1200] s, normal pickling integration horizon
    fluxing_temperature_c: float       # [40, 60] degC, fresh fluxing bath (initial + renewals)
    fluxing_ph_target: float           # [4, 5], fresh fluxing bath pH (initial + renewals)
    fluxing_salt_g_per_l: float        # [300, 500] g/L total ZnCl2/NH4Cl at fixed 60/40 ratio
    galvanizing_temperature_c: float   # [445, 455] degC, zinc bath set-point (replaces the N(450, 1.67) draw)

    def to_array(self) -> np.ndarray                 # (7,) in the field order above
    @classmethod
    def from_array(cls, x: np.ndarray) -> "OperatingPolicy"
# __post_init__ raises ValueError naming the variable and its bounds when out of range.
```

`simulate_year(items, rng, preserve_thesis_quirks=True, policy: OperatingPolicy | None = None)`; `policy=None`
preserves the pre-change draws exactly (thesis numerics untouched). The initial-condition constructors take the
matching optional overrides (`temperature_c`, `hcl_pct`, `ph`, `salt_kg_per_m3`); `pickle_normal` takes
`dip_time_s: float | None`; `draw_bath_temperature` / `initial_bath` take `setpoint_c: float | None`.
`LineTotals` gains additive accumulators: `n_defective_pieces`, `peak_pickling_fe2_g_per_l`,
`peak_fluxing_fe2_g_per_l` (no behavioural change in any mode).

### `src/optimization/evaluation.py`

```python
@dataclass(frozen=True)
class PolicyEvaluation:                 # one Monte Carlo batch of n samples for one policy
    process_utility: np.ndarray         # (n,) U_P
    quality_utility_pct: np.ndarray     # (n,)
    mean_standard_thickness_um: np.ndarray  # (n,)
    process_scores: np.ndarray          # (n, 18)
    unit_indicators: np.ndarray         # (n, 7, 17) raw G_I values (COM in USD, volumes in m3, ...)
    unit_scores: np.ndarray             # (n, 7, 17) scores in %
    defect_fraction: np.ndarray         # (n,) P(delta < delta_ISO) within the year
    peak_pickling_fe2_g_per_l: np.ndarray   # (n,)
    peak_fluxing_fe2_g_per_l: np.ndarray    # (n,)
    raw_material_masses_kg: np.ndarray  # (n, 7) purchases per RAW_MATERIAL_KEYS (exact COM recompute across scenarios)
    # Derived (properties): com_usd, polluted_liquid_m3, water_intake_m3 — unit sums of the matching Indicator column.
    # save(path) / PolicyEvaluation.load(path): .npz round trip.

def evaluate_policy(policy, base_seed, n_samples, items, weights=None, preserve_thesis_quirks=False,
                    n_jobs=1) -> PolicyEvaluation
# Common random numbers: sample i always uses np.random.SeedSequence(base_seed).spawn(n_samples)[i],
# so different policies face identical uncertainty realizations.
```

`src/sustainability/utility.py` gains `evaluate_year_detailed(year, weights, preserve_thesis_quirks)
-> tuple[YearEvaluation, GreenscopeResult]`; `evaluate_year` delegates to it (result-identical).

### `src/optimization/problem.py`, `run_nsga2.py`, `mcdm.py`

```python
class HdgRobustProblem(pymoo.core.problem.Problem)
# n_var=8 (OperatingPolicy order; the 8th is the pickling renewal Fe2+ trigger [60, 150] g/L), n_obj=4.
# Robust objectives (defaults): CVaR at TAIL_FRACTION=0.1 of [-U_P, COM, V_l-poll, V_WT] over the CRN samples;
# the cost is additionally the worst scenario of PRICE_ROBUST_SCENARIOS, shifted exactly through the
# per-sample raw-material masses (RAW_MATERIAL_COM_FACTOR). Chance constraints at DEFECT_QUANTILE=0.95:
# [q95(defect) - 0.02, q95(peak pickling Fe2+) - 150]. tail_fraction=None / defect_quantile=None /
# price_scenarios=None recover the plain expectation formulation. batch_summary(x) -> BatchSummary
# (robust_objectives, mean_objectives, constraints, raw_material_masses_kg).
# The fluxing Fe2+ 5 g/L limit and the rinse cadence stay fixed: the model has no downstream coupling
# for them (dross is random, rinses are sinks), so freeing them would fabricate improvement.
# _evaluate flattens (candidate, sample) pairs over joblib workers; CRN per sample.

# run_nsga2: NSGA2(pop=100, offspring=100, SBX(0.9, eta=15), PM(0.1, eta=20)), LHS sampling,
# custom hypervolume-stagnation termination + n_max_gen; checkpoints = .npz (X, F, G, hv) + config.json
# under results/checkpoints/<run_id>/ (no pickles). `load_checkpoint(path)` restores arrays + config.

@dataclass(frozen=True)
class CompromiseResult:
    index: int; x: np.ndarray; f: np.ndarray
    memberships: np.ndarray            # (4,) mu_k in [0, 1]
    overall: float                     # sum_k W_k mu_k
    utopia: np.ndarray; nadir: np.ndarray   # (4,)

def select_compromise(X, F, weights=None) -> CompromiseResult
# weights default: FAHP categories mapped to objectives — U_P: eff+energy+quality, COM: economy,
# V_l-poll and V_WT: environment/2 each; renormalized to sum 1 (documented constant, overridable).
```

### `src/analysis/plot_style.py` and `src/analysis/manuscript_outputs.py`

Figures/tables are built only from persisted `.npz`/JSON results (never re-simulate): Pareto projection,
18-indicator radar, critical-stage boxplots, U_P density with the 80 % threshold, LaTeX summary table, written to
`results/figures/` (PDF + PNG, 300 DPI, serif) and `results/tables/`.

### `src/sustainability/costs.py` and `src/optimization/price_sensitivity.py`

```python
@dataclass(frozen=True)
class CostParameters:                 # prices [USD/t] of the COM indicator + labor [USD/year]
    name: str; naoh_usd_per_t; hcl_usd_per_t; nh4cl_usd_per_t; zncl2_usd_per_t; zn_usd_per_t
    h2o_usd_per_t; nh4oh_usd_per_t; labor_usd_per_year
    raw_material_prices -> dict[str, float]          # keys naoh, hcl, nh4cl, zncl2, zn, h2o, nh4oh

THESIS_COSTS: CostParameters          # MATLAB values as written (thesis mode; keeps the NH4OH unit defect)
THESIS_CORRECTED_COSTS: CostParameters  # thesis prices, NH4OH as industrial USD/t (corrected mode; optimization)
MARKET_2025_COSTS: CostParameters     # sourced 2025 prices on the thesis basis; sources in docs/LITERATURE.md
default_costs(preserve_thesis_quirks) -> CostParameters   # THESIS_COSTS if True else THESIS_CORRECTED_COSTS
COST_SCENARIOS: dict[str, CostParameters]; get_cost_scenario(name) -> CostParameters   # ValueError if unknown

compute_greenscope(..., *, preserve_thesis_quirks=True, costs=None)      # None -> default_costs(flag)
evaluate_year_detailed(year, weights, preserve_thesis_quirks=True, costs=None)
evaluate_policy(..., costs=None); HdgRobustProblem(..., costs=None); RunConfig.cost_scenario="thesis_corrected"
RunConfig.min_generations=100   # hypervolume stagnation (best HV of the last window vs. best before) cannot fire earlier
RunConfig.resume_from=""        # checkpoint file name or "latest": continue an interrupted run
load_resume_state(path) -> ResumeState(population, generation, n_evaluations, hv_history)
#   The saved population is flagged as evaluated (no re-simulation). The ideal/nadir points of the hypervolume are
#   recovered by repeating generation 1 with the original seed, and the result is verified against the stored first
#   hypervolume (ValueError on mismatch). The resumed algorithm uses seed + generation as its seed; checkpoints keep the
#   total generation count; config.json records resumed_from_generation and the original is kept as config_before_resume.json.
PolicyEvaluation.objective_means -> (4,) [-E[U_P], E[COM], E[V_l-poll], E[V_WT]]

front_evaluation.reevaluate_front(x, scenario, base_seed, n_samples, items, n_jobs)
    -> (F (n+1, 4), G (n+1, 2), masses (n+1, 7))   # last row = baseline; masses per RAW_MATERIAL_KEYS [kg]
mcdm.prepare_selection(run_dir, out_dir, front_items=FULL_YEAR_ITEMS, n_jobs, weights=None) -> CompromiseResult
#   re-evaluates the front at the reporting budget, selects among FEASIBLE designs, writes front.npz + compromise.npz
#   front.npz carries raw_material_masses_kg / baseline_raw_material_masses_kg for the price sensitivity
mcdm.sustainability_probability(evaluation)  # thesis construct: U_P ~ N(mean, (U_max - mean)/3), band [0.8 U_max, U_max]
mcdm.empirical_sustainability_probability(evaluation)  # degenerate fraction (per-sample ratio sigma ~ 0.06 pp); discussion only
mcdm.characterize_designs(...)  # three designs: "asis" (policy=None, thesis draws), "baseline" (nominal), "optimal"
weight_sensitivity.analyze_weights(x, objectives, rng, n_draws) -> dict   # category_mapped / indicator_level / equal + simplex sweep
manuscript_outputs.generate_all(mc_dir, results_dir)   # reads front.npz, compromise.npz, baseline/optimal.npz, summary.json
price_sensitivity.shift_com(F, masses, reference, scenario) -> F'   # exact: COM' = COM + 1.23e-3 (p_s - p_ref) @ masses
#   ValueError if the scenarios differ in labor or water price (those sit outside the raw-material masses)
compare_scenarios(x, objectives_by_scenario, baselines_by_scenario) -> dict  # compromise per scenario, agreement, COM Spearman
run_sensitivity(front_path, out_dir, scenarios) -> dict    # from front.npz (full year), no re-simulation;
#   writes price_sensitivity.json + objectives.npz
```

Prices enter only the raw COM [USD]: the COM *score* is constant (64.39, see `MATLAB_PORT_NOTES.md`), so U_P,
V_l-poll and V_WT are identical across scenarios. The default scenario is the thesis one, so thesis numerics are untouched.
