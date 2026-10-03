# Manuscript

Draft of the journal article on the robust multi-objective optimization of the hot-dip galvanizing line.

| Path | What it is |
|---|---|
| `HDG_Robust_Optimization_Manuscript_v1.docx` | **The working manuscript, edited by the author in Word (real captions, cross-references). Never regenerated or overwritten by scripts** |
| `generated/` | Output of `tools/build_manuscript.py` (plain first draft); kept apart so the working file is never overwritten |
| `backups/` | Timestamped copies of the working manuscript made before any automated edit |
| `figures/*.drawio` | Editable sources of the three flow figures (open at https://app.diagrams.net or in the desktop app) |
| `figures/*.png` | The same figures as images (300 dpi), as inserted in the .docx |
| `tools/make_figures.py` | Generates each `.drawio` and its `.png` from one specification |
| `tools/build_manuscript.py` | Holds the text and builds the .docx with the formatting of the TRI-GraphRAG manuscript v11 |
| `REFERENCE_CHECKLIST.md` | Verification status of every reference and the open claims |
| `references/` | PDFs of the thesis and the 2019 paper (ignored by git: copyrighted) |

Bibliography for the whole project: `../docs/references.bib` and `../docs/LITERATURE.md`.

## Rebuilding

```bash
python manuscript/tools/make_figures.py                                    # figures (.drawio + .png)
uv run --with python-docx python manuscript/tools/build_manuscript.py      # Word file
```

Yellow highlight in the .docx marks text that needs a decision or a source check. If you edit a figure in draw.io and
export it again as PNG with the same name, rebuilding the .docx picks it up; if you also change the Python
specification, the generated `.drawio` is overwritten, so keep one source of truth.

The numbers in the text come from the code and from the final run; when the optimization finishes, the placeholders in
the Results and the abstract are filled from `results/` (see `../OPTIMIZATION.md`).
