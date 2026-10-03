# Spec Delta: optimization/nsga2

## Purpose

Multi-objective NSGA-II optimization of the HDG operating policy under process uncertainty, with constrained
minimization, parallel evaluation, checkpointing, and hypervolume-based termination.

## ADDED Requirements

### Requirement: Constrained four-objective minimization problem

The optimization problem SHALL minimize the vector
F(x) = [ -E[U_P], E[COM], E[V_l-poll], E[V_WT] ] over the seven-variable policy space (bounds per
`simulation/operating-policy`), subject to the inequality constraints (g ≤ 0 feasible):

1. g₁: P(δ < δ_ISO) - 0.02 ≤ 0 (UNE-EN ISO 1461 defect probability at most 2 %)
2. g₂: E[peak pickling Fe²⁺] - 150 g/L ≤ 0

The fluxing-bath Fe²⁺ limit (5 g/L) SHALL act as the bath-renewal trigger of the simulation and SHALL NOT be a
constraint: it is exceeded by construction at every renewal, and the literature gives no annual renewal cap. The cost
and waste of renewals are captured by E[COM] and E[V_l-poll].

Expectations SHALL be Monte Carlo estimates over N ≥ 100 uncertainty samples per evaluation.

#### Scenario: Evaluation returns objectives and constraints

- WHEN the problem evaluates a feasible in-bounds policy vector
- THEN it returns 4 finite objective values and 2 finite constraint values, with g values ≤ 0 when the simulated
  distributions satisfy the quality and pickling-bath exhaustion limits

#### Scenario: Infeasible policy penalized

- WHEN a policy yields a coating-defect probability above 2 %
- THEN g₁ is positive and the solution ranks below any feasible solution under constrained non-dominated sorting

### Requirement: NSGA-II configuration

The solver SHALL run NSGA-II with population size 100, 100 offspring per generation, simulated binary crossover
(probability 0.9, η = 15), polynomial mutation (probability 0.1 per variable, η = 20), and SHALL terminate at a
configurable generation budget in [100, 200] or earlier, but not before a configurable minimum number of generations (default 100), when the best hypervolume of the
last window of generations does not improve on the best before it by more than a configurable relative tolerance.

#### Scenario: Early termination on hypervolume stagnation

- WHEN the minimum number of generations has elapsed and the best normalized hypervolume of the last window of
  generations improves on the earlier best by less than the tolerance
- THEN the run stops before the generation budget and records the termination reason

### Requirement: Parallel evaluation

Population evaluations SHALL be distributed across a configurable number of CPU processes, and a single-process mode
SHALL remain available for debugging. Parallel and serial evaluation of the same seeded population SHALL produce the
same objective values.

#### Scenario: Parallel equals serial

- WHEN one generation of a seeded population is evaluated with 1 worker and with 4 workers
- THEN the resulting objective and constraint matrices are identical

### Requirement: Checkpointing and reproducibility

The runner SHALL persist, at a configurable generation interval and at termination: the current population (X, F, G),
the non-dominated set, the evaluation count, and the run configuration (seed, N, algorithm parameters), under
`results/checkpoints/`. A completed or interrupted run SHALL be reloadable for post-processing from its checkpoint
files alone. Runs with the same seed and configuration SHALL reproduce the same final front.

#### Scenario: Post-processing from checkpoint

- WHEN a run finishes and the Python session ends
- THEN a new session can load the final checkpoint and recover the Pareto-optimal X, F, G and the run configuration
  without re-running any simulation
