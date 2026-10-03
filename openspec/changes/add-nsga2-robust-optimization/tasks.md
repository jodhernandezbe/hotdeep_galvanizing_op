# Tasks: add-nsga2-robust-optimization

## 1. Groundwork

- [x] 1.1 Update `docs/ARCHITECTURE.md` with the `OperatingPolicy` contract, the evaluation-wrapper contract, and the
  `src/optimization/` module contracts (contracts change there first, per project rules)
- [x] 1.2 Add `pymoo (>=0.6.1,<0.7)`, `matplotlib (>=3.8,<4.0)`, `joblib (>=1.3,<2.0)` to `pyproject.toml`; run
  `poetry lock`/install; add `results/` to `.gitignore`
- [x] 1.3 Benchmark `simulate_year` in corrected mode vs. `items` (10⁴–10⁷) and fix the scaled optimization budget
  (items, N per evaluation) targeting ≤ ~2 s per year-sample; record the chosen values in `design.md` (D2)
- [x] 1.4 Capture a seeded thesis-mode `simulate_year` regression digest (hash of key `YearResult` arrays) as a test,
  to pin baseline behaviour before any plumbing changes

## 2. Operating-policy injection (spec: simulation/operating-policy)

- [x] 2.1 Create `src/process/operating_policy.py`: frozen `OperatingPolicy` dataclass, bounds constants,
  `__post_init__` validation with named-variable errors, `to_array()`/`from_array()`
- [x] 2.2 Thread optional `policy` through `initial_conditions` (degreasing T, HCl %, fluxing T/pH/salt at 60/40) for
  initial fills and bath renewals, defaults preserving current draws
- [x] 2.3 Thread dipping time into `pickle_normal` integration horizon and galvanizing setpoint into
  `draw_bath_temperature`/zinc-bath thermal target, defaults preserving current behaviour
- [x] 2.4 Extend `LineTotals`/`YearResult` with additive accumulators: coating-defect count, peak pickling Fe²⁺
  [g/L], peak fluxing Fe²⁺ [g/L]
- [x] 2.5 Add `policy: OperatingPolicy | None = None` to `simulate_year` and plumb to all injection points
- [x] 2.6 Tests: bounds validation, policy round-trip, policy-vs-default divergence, thesis-mode digest unchanged
  (1.4), full existing suite green

## 3. Stochastic evaluation wrapper (spec: simulation/operating-policy)

- [x] 3.1 Create `src/optimization/evaluation.py`: `PolicyEvaluation` frozen dataclass (per-sample arrays for U_P,
  COM, V_l-poll, V_WT, defect fraction, peak Fe²⁺ pair) and `evaluate_policy(policy, base_seed, n_samples, items,
  ...)` using `SeedSequence.spawn` CRN (D3)
- [x] 3.2 Implement objective/constraint extraction from `YearEvaluation`/`GreenscopeResult` using the `Indicator`
  and `UnitProcess` enums (COM, V_l-poll, V_WT, V_l-spec, AAE, W_RM helpers — reused later by MCDM and figures)
- [x] 3.3 Tests: array lengths, seed determinism, paired sampling across two policies (same lot/ambient draws),
  extraction against a hand-checked `GreenscopeResult`

## 4. NSGA-II problem and runner (spec: optimization/nsga2)

- [x] 4.1 Create `src/optimization/problem.py`: `HdgRobustProblem(Problem)` — 7 vars, 4 objectives, 3 constraints,
  bounds from `OperatingPolicy`, batch `_evaluate` with joblib over (candidate, sample) pairs (D4)
- [x] 4.2 Implement hypervolume-stagnation `Termination` (fixed reference point, sliding window, tolerance) combined
  with `n_max_gen` (D5)
- [x] 4.3 Create `src/optimization/run_nsga2.py`: argparse config (seed, workers, budget, pop/gen, output dir),
  NSGA-II assembly per D5, per-interval `.npz` + JSON checkpointing, resumable post-processing loader (D6)
- [x] 4.4 Tests: tiny-budget end-to-end run (pop 8, 3 gens, N 4) — shapes, feasibility flags, checkpoint files load
  back to identical X/F/G; parallel(4) == serial(1) on a seeded generation; seeded rerun reproduces the front
- [ ] 4.5 Smoke-run the real configuration for a few generations on all cores; verify worker saturation and
  checkpoint cadence; then launch and complete the full optimization run (pop 100, budget per 1.3)

## 5. MCDM selection and deep characterization (spec: optimization/mcdm-selection)

- [x] 5.1 Create `src/optimization/mcdm.py`: non-dominated filtering, linear μ_k memberships with utopia==nadir
  guard, FAHP-derived objective weights per D7 (overridable), `select_compromise()` returning solution + memberships
  + utopia/nadir
- [x] 5.2 Implement deep characterization: N = 1000 paired (CRN) evaluations of baseline vs. compromise at the
  validation budget, persisting `.npz` datasets with all manuscript quantities incl. P(U_P ≥ 80 %) and 95 % CIs
- [x] 5.3 Tests: compromise on a synthetic 2-point front, membership bounds, degenerate objective, weight
  normalization; deep-run dataset schema on a tiny N
- [ ] 5.4 Run the real MCDM selection on the final front and the two N = 1000 deep runs; sanity-check budget
  insensitivity at the compromise point (D2 risk)

## 6. Manuscript outputs (spec: analysis/manuscript-outputs)

- [x] 6.1 Create `src/analysis/plot_style.py` (300 DPI, serif, paper rcParams; PDF+PNG save helper) and the
  `results/figures/`, `results/tables/` layout
- [x] 6.2 Figure 1: Pareto E[U_P] vs E[COM] projection, color = V_l-poll, size = V_WT, annotated utopia/nadir/
  compromise markers
- [x] 6.3 Figure 2: 18-axis radar chart (17 GREENSCOPE scores + ISO quality), baseline vs. optimized means
- [x] 6.4 Figure 3: grouped baseline/optimized boxplots for V_l-poll, V_l-spec, AAE, W_RM, V_WT, COM (pickling +
  fluxing stages)
- [x] 6.5 Figure 4: U_P Gaussian KDEs with LM_P = 80 % line, exceedance shading, annotated P_sustainable values
- [x] 6.6 Table 1: LaTeX summary (decision variables, mean ± std, 95 % CIs, P_sustainable, baseline vs. optimized);
  verify it compiles in a minimal document
- [x] 6.7 `src/analysis/manuscript_outputs.py` entry point: regenerate everything from persisted results only (no
  simulator calls); test regeneration determinism with a stub dataset
- [ ] 6.8 Generate the final figures and tables from the real run outputs

## 7. Finalization

- [x] 7.1 Update `OPTIMIZATION.md` with the concrete formulation (variables, objectives, constraints, algorithm,
  chosen budgets) and how to reproduce the pipeline end to end
- [x] 7.2 Full quality gate: `poetry run pytest --verbose`, `pyright`, `pre-commit run --all-files`; fix fallout
- [ ] 7.3 Review generated figures/tables against the spec scenarios and the manuscript checklist (DPI, fonts,
  units, labels)

## 8. Cost scenarios (prices from 2016-2018) and references

- [x] 8.1 Move the thesis prices to `CostParameters` (`src/sustainability/costs.py`) with `thesis` and `market2025` scenarios; thread `costs` through GREENSCOPE, utility, evaluation, problem and runner (default = thesis, bit-identical)
- [x] 8.2 `src/optimization/price_sensitivity.py`: re-evaluate a finished front under each scenario with common random numbers and compare compromises
- [x] 8.3 Tests (thesis default identical, prices move COM only, reproduction of the checkpoint) and docs (ARCHITECTURE, MATLAB_PORT_NOTES, design D10)
- [x] 8.4 `docs/LITERATURE.md` and `docs/references.bib` (thesis, JCP 2019 paper, methods, fluxing/pickling, prices) and README citation
- [ ] 8.5 Run the price sensitivity on the final front (after 4.5) and report whether the compromise moves
- [ ] 8.6 Confirm the NH₄OH price units against the thesis text; if it is a USD/kg value used as USD/t, add it as a documented scenario
- [ ] 8.7 Complete the bibliography: read the JCP paper full text, add the primary sources still pending, verify the `[memory]` entries (DOIs, pages)
- [x] 8.8 Fix the hypervolume-stagnation criterion (best-of-window vs best-before; `min_generations`=100) and record the real termination reason; the first full run had stopped at generation 28 with only 0.15–3.6 % objective spread
- [x] 8.9 Unit fixes: NH₄OH price (`thesis_corrected`), HCl 37 % and NaOH 50 % solution bases in `market2025`; scenario default follows the fidelity mode
- [x] 8.10 Re-evaluate the front at the full-year budget before selecting among feasible designs (`prepare_selection`); Figure 1 uses that basis
- [x] 8.11 Weight sensitivity (`weight_sensitivity.py`): category-mapped, indicator-level, equal, simplex sweep
- [ ] 8.12 Relaunch the full optimization (≥ 100 generations) and finish 4.5, then run `mcdm`, `price_sensitivity`, `weight_sensitivity` and `manuscript_outputs` on the result

