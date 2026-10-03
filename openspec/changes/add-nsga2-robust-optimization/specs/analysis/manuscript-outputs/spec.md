# Spec Delta: analysis/manuscript-outputs

## Purpose

Generate the publication-ready figures and LaTeX tables of the manuscript from persisted optimization and Monte Carlo
results, comparing baseline and optimized operation.

## ADDED Requirements

### Requirement: Publication figure style

All figures SHALL be rendered at 300 DPI with a serif font family in a paper-style (non-default) matplotlib theme,
with labeled axes including units, and saved as both PDF (vector) and PNG under `results/figures/`.

#### Scenario: Style applied to every figure

- WHEN the output generator runs
- THEN every file in `results/figures/` exists in PDF and PNG form, rendered at 300 DPI with serif fonts

### Requirement: Figure 1 — Pareto frontier projection

The generator SHALL plot the final Pareto front projected on E[U_P] vs. E[COM], with marker color encoding
E[V_l-poll] (labeled colorbar) and marker size encoding E[V_WT] (size legend), and SHALL distinctly mark and label
the utopia point, the nadir point, and the fuzzy best-compromise solution.

#### Scenario: Annotated trade-off plot

- WHEN Figure 1 is generated from a run's final checkpoint and MCDM result
- THEN the plot contains every non-dominated solution plus three visually distinct annotated markers for utopia,
  nadir, and compromise

### Requirement: Figure 2 — Radar comparison over 18 indicators

The generator SHALL produce a radar (spider) chart of the 17 GREENSCOPE indicator scores plus the ISO-quality score,
normalized to [0, 100] %, overlaying the baseline and optimized mean scores with a legend and readable indicator
labels.

#### Scenario: Two closed polygons over 18 axes

- WHEN Figure 2 is generated from the deep Monte Carlo datasets
- THEN the chart shows 18 labeled axes and two closed, visually distinct polygons (baseline, optimized)

### Requirement: Figure 3 — Critical-stage boxplots

The generator SHALL produce grouped boxplots comparing baseline vs. optimized distributions of V_l-poll, V_l-spec,
AAE, W_RM, V_WT, and COM for the critical stages (pickling and fluxing), from the N = 1000 samples.

#### Scenario: Paired boxes per indicator

- WHEN Figure 3 is generated
- THEN each of the six indicators shows one baseline box and one optimized box side by side, each summarizing 1000
  samples

### Requirement: Figure 4 — Sustainability utility density

The generator SHALL plot Gaussian kernel density estimates of U_P for baseline and optimized designs on one axis,
mark the LM_P = 80 % threshold, shade each curve's area above the threshold, and annotate both P_sustainable values.

#### Scenario: Threshold shading and probabilities

- WHEN Figure 4 is generated
- THEN both densities, a vertical threshold line at 80 %, shaded exceedance areas, and two annotated P_sustainable
  values are present

### Requirement: Table 1 — LaTeX summary table

The generator SHALL write a compilable LaTeX table to `results/tables/` summarizing, for baseline and optimized
designs: the seven decision-variable values, headline indicators (U_P, COM, V_l-poll, V_WT, coating thickness) as
mean ± standard deviation with 95 % confidence intervals, and P_sustainable.

#### Scenario: Compilable table

- WHEN Table 1 is generated
- THEN the `.tex` file compiles standalone inside a minimal LaTeX document (booktabs-style tabular, no undefined
  commands beyond booktabs/amsmath)

### Requirement: Deterministic regeneration from persisted results

Figures and tables SHALL be reproducible from persisted checkpoints and Monte Carlo datasets alone — regenerating
outputs SHALL NOT re-run the simulator or optimizer.

#### Scenario: Regeneration without simulation

- WHEN the output generator is invoked twice on the same persisted results
- THEN both invocations complete without calling the simulator and produce the same figures and tables
