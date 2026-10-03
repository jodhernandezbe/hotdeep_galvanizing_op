# Design: add-nsga2-robust-optimization

## Context

Motivation: see `proposal.md` — Why. Current state that shapes the design:

- `simulate_year(items, rng, preserve_thesis_quirks)` draws **all** operating conditions internally:
  temperatures/concentrations come from `src/process/initial_conditions.py` draws and module constants
  (`src/process/simulation.py`, `src/process/galvanizing.py:draw_bath_temperature`). There is no decision-variable
  input anywhere.
- `run_monte_carlo` (`src/analysis/monte_carlo.py`) already stacks `YearEvaluation`s; `evaluate_year` already produces
  the 18 process scores, unit scores, and `process_utility` (U_P). FAHP weights live in
  `src/sustainability/thesis_weights.py` / `build_indicator_weights`.
- A full thesis year is 41,379,264 items (`DEFAULT_ANNUAL_ITEMS`). NSGA-II needs on the order of
  100 pop × 150 gen × N ≥ 100 MC samples ≈ 1.5 M year-simulations — the full-year budget is computationally
  impossible inside the optimizer. Evaluation cost is the dominant design constraint.
- Project rules: thesis-mode numerics are frozen; contracts change in `docs/ARCHITECTURE.md` first; explicit
  `rng: np.random.Generator` everywhere; ≤ 15-line methods; `bandit` runs in CI (relevant to pickle).

## Goals / Non-Goals

**Goals**

- Minimal, backward-compatible policy injection: default behaviour bit-identical, existing 142 tests untouched.
- One evaluation API reused by the optimizer, the MCDM deep runs, and the figures (no duplicated simulation glue).
- Deterministic, resumable, pickle-free persistence of everything the manuscript needs.

**Non-Goals**

- No surrogate models, no multi-fidelity scheduling, no distributed (multi-machine) execution.
- No change to the GREENSCOPE equations, FAHP math, or thesis-mode results.
- No GUI/interactive dashboards; static manuscript outputs only.

## Decisions

### D1 — `OperatingPolicy` frozen dataclass, threaded as an optional argument

A frozen dataclass `OperatingPolicy` (new `src/process/operating_policy.py`) with the seven unit-suffixed fields
(`degreasing_temperature_c`, `pickling_hcl_pct`, `pickling_dip_time_s`, `fluxing_temperature_c`, `fluxing_ph_target`,
`fluxing_salt_g_per_l`, `galvanizing_temperature_c`), bounds as module constants, `__post_init__` validation, and
`to_array()` / `from_array()` for pymoo. `simulate_year(..., policy: OperatingPolicy | None = None)` and the touched
unit-process constructors take `policy=None` defaults; `None` means "draw as today".

Injection points (each replaces a draw or constant with the policy value when a policy is given):

| Variable | Injection point |
|---|---|
| T_degreasing | `degreasing_initial_condition` temperature draw + bath renewals |
| C_HCl | `normal_pickling_initial_condition` HCl draw (initial and renewal compositions) |
| t_dipping | pickling ODE integration horizon in `pickle_normal` |
| T_fluxing | `fluxing_initial_condition` temperature + fluxing heat balance target |
| pH_fluxing | fluxing equilibrium/pH regulation setpoint |
| salt conc. | `fluxing_initial_condition` composition (60/40 ZnCl₂/NH₄Cl ratio kept fixed) |
| T_galvanizing | `draw_bath_temperature` → fixed setpoint (zinc-bath thermal target) |

*Alternative considered*: a parallel "parameterized simulator" copy — rejected (violates DRY, drifts from the
validated port). *Alternative*: global config object — rejected (project rule: explicit arguments, no hidden state).

### D2 — Optimize in corrected mode, on a scaled production budget

Optimization evaluations run with `preserve_thesis_quirks=False` (the mass-conserving model; thesis mode exists for
reproducing chapter 4, not for exploring new operating points) and a **reduced items-per-year budget**. All
candidates use the same budget, so Pareto ranking is unaffected; the final baseline/compromise deep runs use the
full budget. *Alternative*: full-budget evaluations inside the optimizer — infeasible at 100×150 generations.
*Alternative*: surrogate modeling — out of scope, larger validation burden than the manuscript needs.

**Benchmark outcome (task 1.3, corrected mode, M1-class CPU)**: 0.088 s at 10⁶ items, 3.60 s for the full
41,379,264-item year. Chosen budgets: optimization evaluations `items = 1_000_000` (≈ 42 lots, exercises the
pickling/fluxing renewal dynamics), `N = 100` samples per evaluation (≈ 110 s per generation on 8 workers, ≈ 4.5 h
for 150 generations); deep characterization runs (N = 1000) use the **full** 41,379,264-item year (≈ 8 min on 8
workers), so the manuscript numbers carry no budget-scaling bias.

### D3 — Common random numbers via `SeedSequence.spawn`

The evaluator derives per-sample generators from `np.random.SeedSequence(base_seed).spawn(n_samples)`; sample *i*
uses child seed *i* regardless of the policy. Different policies therefore face identical uncertainty realizations
(paired sampling), cutting Monte Carlo noise out of the Pareto comparisons, and the scheme is reproducible across
serial/parallel execution. *Alternative*: one shared generator — draws desynchronize between policies and across
worker counts, breaking the `parallel equals serial` and `paired sampling` spec scenarios.

### D4 — Vectorized pymoo `Problem` + joblib over Monte Carlo samples × population

`HdgRobustProblem` subclasses `pymoo.core.problem.Problem` (batch `_evaluate`), flattening (candidate, sample) pairs
into one `joblib.Parallel(n_jobs=w, backend="loky")` job list, then reducing to means/probabilities per candidate.
This keeps workers saturated even at generation boundaries and keeps CRN bookkeeping in one place.
*Alternative*: `ElementwiseProblem` + pymoo's `StarmapParallelization` — coarser load balancing, and the CRN seed
plumbing ends up inside pymoo's runner where we control it least.

### D5 — NSGA-II setup and termination

`NSGA2(pop_size=100, n_offsprings=100, sampling=LHS, crossover=SBX(prob=0.9, eta=15),
mutation=PM(prob=0.1, eta=20))`, seeded. Termination: `n_max_gen` in [100, 200] combined with a hypervolume-based
stagnation criterion (running HV against a fixed reference point from the first feasible generation; stop when
relative improvement < tol over a sliding window, defaults tol = 1e-4, window = 15). Implemented as a small custom
`Termination` so the tolerance semantics match the spec exactly. Defect-probability constraint enters as
`g1 = P(δ<δ_ISO) − 0.02` (pymoo's constrained dominance already penalizes by violation magnitude, satisfying the
"penalty scaling" intent).

### D6 — Pickle-free persistence

Checkpoints are `np.savez_compressed` (X, F, G, non-dominated mask, HV history) plus a JSON sidecar (seed, N, budget,
algorithm params, timing, termination reason) under `results/checkpoints/<run_id>/gen_XXXX.npz`. Deep MC datasets are
`.npz` per design (baseline/optimal). No pickles: `bandit` flags them, and raw arrays + config are all the
post-processing needs. *Alternative*: `dill`/pickle of the pymoo `Result` — opaque, version-fragile, flagged by B301.

### D7 — MCDM weight mapping

μ_k memberships are linear on [nadir, utopia] per objective (guard: utopia == nadir → μ ≡ 1 for that objective).
Weights W_k for the four objectives are derived from the thesis FAHP **category** weights: W(U_P) = the quality +
efficiency + energy share, W(COM) = the economics share, and the environment share split equally between V_l-poll and
V_WT; renormalized to Σ W_k = 1. The mapping is a documented constant that callers can override — it is a modeling
choice, not thesis-fixed. *Alternative*: equal weights — discards the elicited expert structure the manuscript builds
on; *alternative*: knee-point selection — doesn't use FAHP, weaker narrative link to the thesis.

### D8 — Module layout and entry points

```
src/optimization/__init__.py
src/optimization/evaluation.py        # policy → MC distributions (spec: operating-policy evaluation, CRN)
src/optimization/problem.py           # HdgRobustProblem (pymoo), objective/constraint extraction
src/optimization/run_nsga2.py         # runner: config → NSGA-II → checkpoints (python -m src.optimization.run_nsga2)
src/optimization/mcdm.py              # fuzzy compromise selection + deep MC characterization
src/analysis/manuscript_outputs.py    # figures + LaTeX table from persisted results (python -m ...)
src/analysis/plot_style.py            # shared matplotlib rcParams (300 DPI, serif, paper style)
```

Objective/constraint extraction reads `Indicator` enum positions from `src/sustainability/streams.py` /
`greenscope.py` (never raw integers). `results/` is added to `.gitignore`. Entry points parse a small set of CLI
flags (seed, workers, budget, output dir) with `argparse`; no new CLI framework.

### D9 — Fluxing Fe²⁺ is a renewal trigger, not a constraint

The simulation renews the fluxing bath when Fe²⁺ reaches 5 g/L (thesis rule), so the recorded peak is ≥ 5 g/L at every
renewal regardless of the policy and `E[peak] − 5 ≤ 0` can never hold. The literature supports the 5 g/L level
(≈ 0.5 % Fe) but gives no annual renewal cap, and industry regenerates the bath instead of dumping it
(`docs/LITERATURE.md`). Renewals already cost money and waste, so the optimizer prices them through E[COM] and
E[V_l-poll]. *Alternatives*: cap renewals per year (no literature anchor); measure the post-renewal concentration
(constraint becomes vacuous).

### D10 — Cost scenarios as parameters, sensitivity as post-processing

Prices from 2016–2018 are moved to `CostParameters`: `thesis` (as written, thesis mode), `thesis_corrected` (NH₄OH unit defect fixed; the optimization scenario) and `market2025` (sourced, rebased to the thesis units). Because the COM score is
constant, prices only change the raw COM [USD], so the optimization runs once under thesis prices and the finished
front is re-evaluated under each scenario with identical random numbers (`price_sensitivity`), reporting whether the
compromise design and the baseline-vs-optimum cost saving change. A second full optimization under new prices is
only warranted if the sensitivity shows the compromise moves. Only prices with a comparable sourced basis are updated
(Zn, ZnCl₂, NH₄Cl, HCl); the rest are listed as open in `MATLAB_PORT_NOTES.md`. *Alternative*: silently replace the
thesis prices — rejected by the fidelity policy.

### D11 — Reduced-year search, full-year reporting

The search year (10⁶ pieces) has the same annual fixed costs as the 41.4 M-piece year, so its objectives are not on the
reporting basis. After the search the front is re-evaluated at the full-year budget (`prepare_selection`), the compromise
is selected among the designs that are still feasible there, and Figure 1 and Table 1 share that basis. The hypervolume
stagnation criterion compares the best hypervolume of the last window with the best before it (the hypervolume of a
crowding-truncated population is not monotone) and cannot fire before `min_generations` = 100. *Alternative*: search
at the full-year budget — 50 minutes per generation, infeasible.

### D12 — Weight sensitivity

The fuzzy compromise depends on the objective weights, the front does not. The default weights are the thesis category
weights mapped onto the objectives (D7); `weight_sensitivity` reports the selection under indicator-level and equal
weights and over 10⁴ weight vectors drawn uniformly from the simplex. Note that D7 double counts: U_P already contains the
water, liquid-volume and cost indicators.

## Risks / Trade-offs

- [Wall-clock blow-up even at reduced budget] → Benchmark task runs first and fixes (items, N) to keep a full
  optimization under ~12 h on 8 cores; checkpoint/resume means an interrupted run loses at most one interval.
- [Scaled budget biases extensive objectives] → Same budget for all candidates preserves ranking; deep runs at a
  larger budget quantify the bias at baseline and compromise points before the manuscript numbers are quoted.
- [Policy plumbing accidentally perturbs thesis mode] → `policy=None` default path is byte-for-byte the old code;
  regression test pins a seeded thesis-mode `simulate_year` digest before and after.
- [pymoo API drift (0.6.x)] → Pin `pymoo >=0.6.1,<0.7`; isolate all pymoo imports in `problem.py`/`run_nsga2.py`.
- [loky workers + rng reproducibility] → Workers receive integer child-seed material (not generator objects);
  spec scenario "parallel equals serial" is an explicit test.
- [Fluxing Fe²⁺ ≤ 5 g/L as a constraint is infeasible by construction (renewal trigger → peak ≥ 5 always; observed in a first run)] → Dropped as a constraint; renewals priced via COM/V_l-poll (see D9).
- [Peak Fe²⁺ / defect-rate signals not currently exposed by `YearResult`] → Add accumulators to `LineTotals`
  (defect count, peak concentrations) — additive fields only, no behavioural change in thesis mode.
- [≤15-line method rule vs. pymoo/matplotlib boilerplate] → Figures decompose into per-figure builders plus small
  helpers; rule is a style gate, not a blocker.

## Migration Plan

Additive change; no deployment. Order: contracts in `docs/ARCHITECTURE.md` → policy plumbing (tests green) →
evaluation wrapper → optimizer → MCDM → outputs. Rollback = dropping `src/optimization/`, the two analysis modules,
and the optional `policy` parameters; nothing else depends on them.

## Open Questions

- ~~Exact scaled `items` budget and per-evaluation N~~ — resolved by the benchmark (see D2): items = 10⁶, N = 100
  for optimization; full year for deep runs.
- Whether the manuscript also wants the narrower %Si ∈ [0.15, 0.25] scenario run — exposed as a flag either way;
  decide when generating final outputs.
