# Project Configuration

Python port of the MATLAB models from the 2018 master's thesis on hot-dip galvanizing (HDG) sustainability: Monte Carlo
simulation of the HDG line (degreasing → rinsing → pickling → rinsing → fluxing → drying → galvanizing), GREENSCOPE
sustainability indicators with fuzzy-AHP weights, and critical-point analysis via hierarchical partitioning. The goal of
the repo is robust optimization under uncertainty of the process (see `OPTIMIZATION.md`).

## Domain Rules
- **Fidelity policy**: equations follow the thesis MATLAB (`docs/matlab_reference/`). Result-changing defects of the
  listings are preserved behind `preserve_thesis_quirks` (default `True`, reproduces thesis chapter 4); `False` gives the
  mass-conserving, physically bounded model. Never silently change thesis-mode numerics — document every deviation in
  `docs/MATLAB_PORT_NOTES.md` and check it against the validation table there
- **Contracts**: module boundaries and dataclass signatures are defined in `docs/ARCHITECTURE.md`; change them there first
- **Randomness**: every stochastic function takes `rng: np.random.Generator` explicitly; never use global random state
- **Units in names**: suffix quantities with units (`mass_kg`, `volume_m3`, `temperature_c`, `heat_j`, `thickness_um`)
- **Indices**: compound/stream/unit-process positions come from the enums in `src/sustainability/streams.py`, never raw
  integers

## Code Style & Standards
- **Type hints**: Required using `typing` module for all functions/methods/classes
- **Imports**: Absolute imports only, grouped (stdlib, third-party, local)
- **Line length**: Max 128 characters (black config)
- **Trailing commas**: Always place a trailing comma after the last argument in any
  function/method signature or call that spans multiple lines (i.e. has many arguments),
  and in multi-line collections/attributes, so black keeps one argument per line
- **Linting**: `black`, `flake8`, `isort`, `pyright`, `pydocstyle`, `bandit`
- **Space before comment**: Before a "#" comment, leave two spaces following PEP conventions
- **Maximum number of lines**: The maximum number of lines for a method should not be above 15, at least, it justifies it
- **SOLID and DRY principles**: Follow the DRY principle; extract reusable functions and avoid code duplication

## Project Structure
- `src/`: Core package modules
- `tests/`: Mirror src/ structure with `test_`-prefixed files
- `data/`: Data storage (git-ignored by default)

## Code Conventions
- **Absolute imports only**: never use relative imports; import from the package
  root (e.g. `from src.module.submodule import MyClass`)
- **Functions**: Single responsibility, keep small and focused
- **Constants**: UPPER_CASE module-level
- **SOLID / DRY**: Extract common patterns into utilities; avoid repeating logic
- Use `logger = logging.getLogger(__name__)` in each module
- DataFrame operations: always `.copy()` before modifications

## Documentation Standards
- **Public functions/methods/classes only**: Full Google-style docstrings with Args/Returns.
  "Public" means no leading underscore and reachable from outside its defining module/class
- **Private/internal methods (leading underscore) and local helpers**: Do NOT add a docstring,
  by default. Only add one if the logic is genuinely non-obvious (e.g. a non-trivial algorithm
  or an implementation detail a reader could not infer from the name and body)
- **Module headers**: Include purpose, author, date
- Omit `Returns` when return type is `None`; omit `Args` when no params beyond `self`
- **Inline (`#`) comments: avoid by default.** Code and config should be self-explanatory through
  naming and structure. Only add an inline comment when it captures a WHY that isn't derivable
  from the code itself (a non-obvious constraint, a workaround for a specific bug/limitation, a
  subtle invariant). Never add comments that restate WHAT the code does

## Error Handling
- Use specific exceptions with descriptive messages
- Log errors before raising: `logger.error(f"Error: {e}")`
- Validate inputs early in functions

## Data Handling
- **Never commit large data files** to git (data/ and similar are ignored)
- **Validate file encodings** (handle encoding issues proactively)
- **Secure credentials** via environment variables only (`.env` is git-ignored)
- Process large files in chunks; set deterministic seeds for reproducibility

## Key Commands
```bash
poetry install                 # Install deps and dev tooling
poetry run pytest --verbose    # Run all tests
poetry run pyright             # Type check
poetry run black src/ tests/   # Format code
poetry run pre-commit run --all-files  # Run all hooks
```

## Dependencies
- Dev: black, flake8, isort, pyright, pydocstyle, bandit, yamllint, pytest
- Core: numpy, scipy (ODE integration, distributions, t/normal statistics), pandas (data handling for the
  optimization work), python-dotenv
