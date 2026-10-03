"""Tests of the manuscript figure/table generation from persisted stub results.

Purpose: spec analysis/manuscript-outputs (style, completeness, deterministic regeneration, no simulation).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

import hashlib
import json
import shutil
import subprocess  # nosec B404  (used only to drive pdflatex on the generated table)
from pathlib import Path

import pytest

from src.analysis.manuscript_outputs import generate_all, table_summary
from src.optimization.mcdm import characterize_designs, select_compromise
from src.optimization.run_nsga2 import RunConfig, run
from src.process.operating_policy import OperatingPolicy

OPTIMAL = OperatingPolicy(55.0, 15.0, 900.0, 45.0, 4.2, 350.0, 452.0)
EXPECTED_FIGURES = (
    "figure1_pareto",
    "figure2_radar",
    "figure3_critical_stage_boxplots",
    "figure4_utility_density",
)


@pytest.fixture(scope="module")
def stub_results(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("stub_results")
    config = RunConfig(
        seed=4,
        pop_size=8,
        n_generations=2,
        n_mc_samples=2,
        items=50_000,
        checkpoint_every=1,
        out_dir=str(root / "checkpoints"),
    )
    run_dir = run(config)
    mc_dir = root / "mc"
    _make_mcdm_outputs(run_dir, mc_dir)
    return run_dir, mc_dir


def _make_mcdm_outputs(run_dir: Path, mc_dir: Path) -> None:
    from src.optimization.front_evaluation import reevaluate_front
    from src.optimization.mcdm import _save_compromise, _save_front
    from src.optimization.run_nsga2 import load_checkpoint

    checkpoint = load_checkpoint(run_dir)
    config, x = checkpoint["config"], checkpoint["opt_X"]
    objectives, constraints, masses = reevaluate_front(x, config["cost_scenario"], config["seed"], 2, 50_000)
    _save_front(mc_dir, x, objectives, constraints, masses, 50_000)
    _save_compromise(mc_dir, select_compromise(x, objectives[:-1]))
    characterize_designs(OPTIMAL, base_seed=4, n_samples=3, items=50_000, out_dir=mc_dir)


def test_generate_all_writes_every_output(stub_results: tuple[Path, Path], tmp_path: Path) -> None:
    _, mc_dir = stub_results
    generate_all(mc_dir, tmp_path)
    for stem in EXPECTED_FIGURES:
        assert (tmp_path / "figures" / f"{stem}.pdf").exists()
        assert (tmp_path / "figures" / f"{stem}.png").exists()
    assert (tmp_path / "tables" / "table1_summary.tex").exists()


def test_regeneration_is_deterministic_and_simulation_free(
    stub_results: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, mc_dir = stub_results

    def _forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("manuscript outputs must not re-run the simulator")

    monkeypatch.setattr("src.process.simulation.simulate_year", _forbidden)
    first, second = tmp_path / "a", tmp_path / "b"
    generate_all(mc_dir, first)
    generate_all(mc_dir, second)
    for path in sorted((first / "figures").iterdir()):
        assert _digest(path) == _digest(second / "figures" / path.name), path.name
    assert _digest(first / "tables" / "table1_summary.tex") == _digest(second / "tables" / "table1_summary.tex")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_table_structure_is_booktabs_latex(stub_results: tuple[Path, Path], tmp_path: Path) -> None:
    _, mc_dir = stub_results
    table = table_summary(json.loads((mc_dir / "summary.json").read_text()), tmp_path)
    text = table.read_text()
    for required in (r"\begin{table}", r"\toprule", r"\midrule", r"\bottomrule", r"\end{table}"):
        assert required in text
    assert text.count(r"\begin{tabular}") == text.count(r"\end{tabular}") == 1
    assert text.count("{") == text.count("}")


@pytest.mark.skipif(shutil.which("pdflatex") is None, reason="pdflatex not installed")
def test_table_compiles_with_pdflatex(stub_results: tuple[Path, Path], tmp_path: Path) -> None:
    _, mc_dir = stub_results
    table = table_summary(json.loads((mc_dir / "summary.json").read_text()), tmp_path)
    document = tmp_path / "doc.tex"
    document.write_text(
        "\\documentclass{article}\n\\usepackage{booktabs}\n\\usepackage{amsmath}\n"
        f"\\begin{{document}}\n\\input{{{table.name}}}\n\\end{{document}}\n"
    )
    completed = subprocess.run(  # nosec B603 B607
        ["pdflatex", "-interaction=nonstopmode", document.name], cwd=tmp_path, capture_output=True, check=False
    )
    assert completed.returncode == 0, completed.stdout.decode()[-2000:]
