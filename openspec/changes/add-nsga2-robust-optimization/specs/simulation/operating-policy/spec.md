# Spec Delta: simulation/operating-policy

## Purpose

Expose the HDG process simulator as a parameterized function of an explicit operating-policy vector, and provide a
stochastic evaluator that maps a policy to Monte Carlo distributions of the optimization objectives and constraint
quantities.

## ADDED Requirements

### Requirement: Explicit decision-variable vector with box bounds

The simulator SHALL accept an operating policy of exactly seven decision variables, validated against these box bounds
at construction time:

| Variable | Bounds | Units |
|---|---|---|
| Degreasing temperature | [40.0, 60.0] | °C |
| Pickling HCl concentration (normal bath) | [12.0, 18.0] | % wt |
| Pickling dipping time | [600, 1200] | s |
| Fluxing temperature | [40.0, 60.0] | °C |
| Fluxing target pH | [4.0, 5.0] | — |
| Fluxing total salt concentration (ZnCl₂/NH₄Cl fixed at 60/40) | [300.0, 500.0] | g/L |
| Galvanizing bath temperature | [445.0, 455.0] | °C |

A value outside its bound SHALL raise a `ValueError` naming the offending variable.

#### Scenario: Out-of-bounds policy rejected

- WHEN an operating policy is constructed with pickling HCl concentration 25.0 % wt
- THEN construction fails with a `ValueError` whose message names the HCl concentration variable and its bounds

#### Scenario: In-bounds policy accepted

- WHEN an operating policy is constructed with all seven values inside their bounds
- THEN the policy is created and each value is retrievable with its unit-suffixed name

### Requirement: Default policy reproduces baseline behaviour

When no operating policy is supplied, the simulator SHALL behave exactly as before this change: in thesis mode
(`preserve_thesis_quirks=True`) all existing validation results and the existing test suite SHALL remain unchanged.

#### Scenario: Thesis-mode numerics untouched

- WHEN the yearly simulation runs in thesis mode with no policy argument and a fixed seed
- THEN its outputs are bit-identical to the outputs produced before this change with the same seed

### Requirement: Stochastic evaluation of a policy

The system SHALL provide an evaluation function that, given an operating policy, a random generator, and a sample count
N (default in [100, 500]), returns per-sample arrays (length N) of at least: global process utility U_P, cost of
manufacture COM [USD], polluted liquid volume V_l-poll [m³], total water intake V_WT [m³], coating-defect fraction
P(δ < δ_ISO), peak pickling Fe²⁺ concentration [g/L], and peak fluxing Fe²⁺ concentration [g/L].

#### Scenario: Distribution shapes and determinism

- WHEN a policy is evaluated with N = 100 and a generator seeded with a fixed seed
- THEN every returned array has length 100, and repeating the call with the same seed returns identical arrays

### Requirement: Common random numbers across policies

The evaluator SHALL support evaluating different policies against the same uncertainty realizations: when two policies
are evaluated with generators seeded identically, the i-th Monte Carlo sample of each SHALL use the same draws for the
stochastic inputs (steel lots, contamination, ambient temperature), so that objective differences reflect the policy and
not sampling noise.

#### Scenario: Paired sampling

- WHEN two different policies are evaluated with the same seed and N = 50
- THEN the sequence of sampled steel-lot sizes and ambient temperatures is identical in both evaluations
