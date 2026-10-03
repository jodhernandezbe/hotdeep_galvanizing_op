# Proposal: add-nsga2-robust-optimization

## Why

The Python port of the thesis HDG models (process simulation, GREENSCOPE indicators, fuzzy-AHP utility) is complete and
validated, but it can only *assess* the plant as operated in the thesis: `simulate_year` draws every operating condition
internally and exposes no decision variables. The repo's stated goal (`OPTIMIZATION.md`) is robust optimization under
uncertainty — finding operating conditions that trade off sustainability utility, manufacturing cost, hazardous liquid
waste, and freshwater intake while meeting UNE-EN ISO 1461 coating quality. This change couples the existing simulator to
NSGA-II (`pymoo`), adds a fuzzy compromise decision-maker to pick an operating point from the Pareto front, and produces
the publication-ready figures and LaTeX tables for the manuscript.

## What Changes

- **Operating-policy injection**: the process simulator accepts an explicit vector of 7 decision variables
  (degreasing temperature, pickling HCl concentration and dipping time, fluxing temperature/pH/salt concentration,
  galvanizing temperature) with defaults that reproduce current baseline behaviour. Corrected mode
  (`preserve_thesis_quirks=False`) is the optimization substrate; thesis mode stays untouched for validation.
- **Stochastic evaluation wrapper**: a function mapping a decision vector `x` to Monte Carlo distributions
  (N = 100–500 per evaluation) of the objectives `[-E[U_P], E[COM], E[V_l-poll], E[V_WT]]` and the constraint
  quantities (coating-defect probability, pickling Fe²⁺; peak fluxing Fe²⁺ is recorded but not constrained), using common random numbers for
  variance reduction across evaluations.
- **NSGA-II problem and runner**: `pymoo` problem definition with box bounds, 4 objectives, 2 inequality constraints;
  NSGA-II (pop 100, SBX η=15 p=0.9, PM η=20 p=0.1), parallel evaluation across CPU cores (`joblib`), hypervolume-based
  termination, and per-generation checkpointing to disk.
- **Fuzzy compromise MCDM**: normalize the Pareto objectives into fuzzy satisfaction memberships, weight them with the
  FAHP category weights already in `src/sustainability/thesis_weights.py`, and select the best compromise solution;
  then run deep Monte Carlo (N = 1000) for baseline and optimal designs.
- **Manuscript outputs**: publication-style matplotlib figures (Pareto projections with utopia/nadir/compromise,
  18-indicator radar chart, critical-stage boxplots, U_P kernel density with the LM_P = 80 % sustainability threshold)
  and a LaTeX summary table, written under `results/figures/` and `results/tables/`.
- **New dependencies**: `pymoo`, `matplotlib`, `joblib` added to `pyproject.toml`.

Assumptions recorded (minor, per request wording):
- New modules live inside the package per project structure: `src/optimization/` (problem, NSGA-II runner, MCDM) and
  `src/analysis/manuscript_outputs.py`, each runnable as `python -m src.optimization.run_nsga2` etc., rather than
  top-level `optimization/` and `analysis/` directories.
- %Si is sampled per piece by the existing `steel_lots` distributions (thesis ranges); the narrower [0.15, 0.25] band is
  exposed as an optional scenario toggle, not the default.
- The ZnCl₂/NH₄Cl ratio stays fixed at 60/40 (thesis value); only total salt concentration is a decision variable.
- "Run the entire pipeline" is part of the implementation tasks (a reduced-budget smoke run plus the full run), not of
  this planning change.

## Capabilities

### New Capabilities

- `simulation/operating-policy`: the process simulator and Monte Carlo evaluator accept an explicit decision-variable
  vector and return objective/constraint distributions for that operating point.
- `optimization/nsga2`: multi-objective NSGA-II optimization of the operating policy under uncertainty, with parallel
  evaluation, checkpointing, and hypervolume-based termination.
- `optimization/mcdm-selection`: fuzzy compromise decision-making over the Pareto front using FAHP weights, plus deep
  Monte Carlo characterization of baseline and optimal designs.
- `analysis/manuscript-outputs`: publication-ready figures and LaTeX tables comparing baseline vs. optimized operation.

### Modified Capabilities

(none — `openspec/specs/` is empty; all capabilities are new)

## Impact

- **Code**: new package `src/optimization/`; new module `src/analysis/manuscript_outputs.py`; signature extensions in
  `src/process/initial_conditions.py`, `src/process/simulation.py`, `src/process/pickling.py`, `src/process/fluxing.py`,
  `src/process/galvanizing.py`, `src/process/degreasing.py` to accept the operating policy (defaults keep current
  behaviour → existing 142 tests must stay green); extraction helpers over `GreenscopeResult`/`YearEvaluation` for COM,
  V_l-poll, V_WT.
- **Contracts**: `docs/ARCHITECTURE.md` gains the operating-policy dataclass and the optimization module contracts
  (contracts change there first, per project rules).
- **Dependencies**: `pymoo (>=0.6)`, `matplotlib (>=3.8)`, `joblib (>=1.3)` added to core dependencies.
- **Outputs**: new git-ignored `results/` tree (checkpoints, figures, tables).
- **Docs**: `OPTIMIZATION.md` updated with the concrete formulation; `docs/MATLAB_PORT_NOTES.md` untouched (no
  thesis-mode numeric change).
