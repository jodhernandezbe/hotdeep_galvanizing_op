# Hot-Dip Galvanizing Operations

Simulation and sustainability assessment of an industrial hot-dip galvanizing (HDG) line, ported from the MATLAB code of
the master's thesis *"Detección de los puntos críticos del proceso de galvanizado por inmersión en caliente: un enfoque
hacia la sostenibilidad y el desarrollo sostenible"* (J. D. Hernández Betancur, Universidad Nacional de Colombia, 2018),
whose framework was published as J. D. Hernández-Betancur, H. F. Hernández and L. M. Ocampo-Carmona, "A holistic
framework for assessing hot-dip galvanizing process sustainability", *Journal of Cleaner Production* 206 (2019) 755–766,
[doi:10.1016/j.jclepro.2018.09.177](https://doi.org/10.1016/j.jclepro.2018.09.177). Sources and BibTeX entries for the
manuscript: [docs/LITERATURE.md](./docs/LITERATURE.md) and [docs/references.bib](./docs/references.bib).

The end goal of this repository is **robust optimization under uncertainty** of the HDG process (see
[OPTIMIZATION.md](./OPTIMIZATION.md)): decision variables (pickling, fluxing and thermal conditions), stochastic inputs
(steel mass/gauge/silicon, rust and grease contamination, ambient temperature) and objectives built on the process
utility, critical-stage indicators and the UNE-EN ISO 1461 coating-thickness requirement.

## What it does

- **Process mimic** (`src/process/`): Monte Carlo simulation of a production year — random steel lots; degreasing,
  rinsing, pickling (HCl kinetics as ODEs), fluxing (ZnCl2/NH4Cl equilibria with pH control), drying and galvanizing
  (silicon-dependent coating-thickness kinetics) with mass/energy balances and bath-renewal logic.
- **Sustainability layer** (`src/sustainability/`): the 17 selected GREENSCOPE indicators per unit process, fuzzy-AHP
  weighting of indicators and categories (thesis Table 4-1 weights included), and the additive utility of each unit
  process and of the whole line.
- **Analysis** (`src/analysis/`): Monte Carlo driver, hierarchical partitioning (Chevan & Sutherland) of the process
  utility over the unit processes, Pareto selection of critical stages, and the probability that the process is
  sustainable.

A full-scale year (41.4 M pieces) simulates in ~6 s; 100 years reproduce the thesis chapter-4 results (critical stages:
fluxing and pickling; P(sustainable) ≈ 0.45).

### Thesis mode vs corrected mode

Every entry point takes `preserve_thesis_quirks` (default `True`):

- `True` — numerically faithful to the thesis MATLAB listings, including their known defects; reproduces chapter 4.
- `False` — mass-conserving balances, honest fluxing volume/pH bookkeeping and a tank-capacity overflow bleed; the
  physically sound choice for optimization work.

All quirks, fixes and the validation table are documented in [docs/MATLAB_PORT_NOTES.md](./docs/MATLAB_PORT_NOTES.md);
module contracts are in [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md); the verbatim MATLAB listings are in
`docs/matlab_reference/`.

## Quickstart

```python
import numpy as np

from src.analysis.monte_carlo import analyze_critical_points, run_monte_carlo
from src.sustainability.thesis_weights import thesis_indicator_weights

weights = thesis_indicator_weights()
result = run_monte_carlo(weights, np.random.default_rng(7), n_samples=100)
analysis = analyze_critical_points(result, quality_weight=weights[17])

print(analysis.critical_units)              # 0-based unit indices, most influential first
print(analysis.assessment.probability)      # P(process is sustainable)
```

## Setup

### Prerequisites
- Python 3.12+
- Poetry (for dependency management)
- Pre-commit (for git hooks)

### Installation

1. Install dependencies with Poetry:
```bash
poetry install
```

2. Initialize pre-commit hooks:
```bash
pre-commit install
```

### Running Tests

```bash
poetry run pytest --verbose
```

### Code Quality

Format code:
```bash
poetry run black src/ tests/
```

Run type checking:
```bash
poetry run pyright
```

Run all pre-commit hooks:
```bash
poetry run pre-commit run --all-files
```

## Project Structure

```
.
├── src/
│   ├── common/           # Shared physical constants and molar masses
│   ├── process/          # HDG line simulation (baths, kinetics, lots, plant state)
│   ├── sustainability/   # GREENSCOPE indicators, fuzzy AHP, stream assembly, utilities
│   └── analysis/         # Monte Carlo, hierarchical partitioning, critical points
├── tests/                # Test suite mirroring src/
├── docs/
│   ├── ARCHITECTURE.md       # Module contracts and conventions
│   ├── MATLAB_PORT_NOTES.md  # Fidelity policy, quirks, validation vs thesis
│   └── matlab_reference/     # Verbatim MATLAB listings from thesis annex D
├── OPTIMIZATION.md       # Optimization-under-uncertainty framing (goal of the repo)
├── pyproject.toml        # Poetry configuration
├── CLAUDE.md             # Development guidelines
└── README.md             # This file
```

## Code Standards

See [CLAUDE.md](./CLAUDE.md) for detailed development guidelines including:
- Type hints and imports
- Code style and linting
- Documentation standards
- Error handling
- SOLID and DRY principles
