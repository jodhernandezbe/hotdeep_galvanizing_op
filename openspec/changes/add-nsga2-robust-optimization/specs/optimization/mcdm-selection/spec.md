# Spec Delta: optimization/mcdm-selection

## Purpose

Select a single best-compromise operating point from the NSGA-II Pareto front via fuzzy satisfaction memberships
weighted with the FAHP weights, and characterize baseline vs. optimal designs with deep Monte Carlo simulation.

## ADDED Requirements

### Requirement: Fuzzy compromise selection over the Pareto front

Given a set of solutions with objective values, the selector SHALL (1) keep only the non-dominated subset, (2) map each
objective k of each solution to a linear satisfaction membership μ_k ∈ [0, 1] with μ_k = 1 at the utopia value and
μ_k = 0 at the nadir value of the front, (3) compute the weighted additive score μ_overall = Σ_k W_k μ_k using
normalized weights derived from the thesis FAHP weight vectors, and (4) return the solution with the highest
μ_overall together with the per-objective memberships, the utopia point, and the nadir point.

#### Scenario: Compromise solution identified

- WHEN the selector runs on a front of at least two non-dominated solutions with distinct objective values
- THEN it returns exactly one compromise solution with μ_overall equal to the maximum weighted score, and every
  reported membership lies in [0, 1]

#### Scenario: Degenerate objective handled

- WHEN one objective takes the same value on every front member (utopia = nadir)
- THEN selection completes without division-by-zero and that objective contributes a constant membership

### Requirement: Cost-scenario sensitivity

The system SHALL provide named cost scenarios for the manufacturing-cost indicator, with the thesis (2016–2018)
prices as the default, and SHALL be able to re-evaluate a finished Pareto front under each scenario using the same
random numbers. The report SHALL state, per scenario, the compromise design, the baseline-vs-compromise cost saving,
whether the compromise equals the reference scenario's, and the rank correlation of COM across the front. Re-evaluating
under the scenario the run used SHALL reproduce the run's objectives.

#### Scenario: Prices change cost only

- WHEN the same policy and seeds are evaluated under the thesis and the 2025 scenarios
- THEN COM differs while U_P, V_l-poll and V_WT are identical

#### Scenario: Reproduction check

- WHEN a finished run is re-evaluated under its own cost scenario with its own seed, sample count and budget
- THEN the re-evaluated objectives equal the checkpoint's objectives exactly

### Requirement: Deep Monte Carlo characterization of baseline and optimum

The system SHALL run an N = 1000 Monte Carlo evaluation for both the baseline policy and the selected compromise
policy under common random numbers, and persist per-sample results sufficient for the manuscript outputs: U_P, COM,
V_l-poll, V_WT, V_l-spec, AAE, W_RM for the pickling and fluxing stages, the 17 GREENSCOPE process scores plus the
quality score, coating thickness statistics, and the sustainability probability P(U_P ≥ LM_P) with LM_P = 80 %.

#### Scenario: Paired baseline/optimal distributions

- WHEN the deep characterization runs with a fixed seed
- THEN it produces two persisted datasets of 1000 samples each (baseline and optimal), evaluated against identical
  uncertainty realizations, each including P_sustainable and 95 % confidence intervals for the headline indicators
