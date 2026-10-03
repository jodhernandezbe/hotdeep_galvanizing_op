"""One-off edit of the author's Word manuscript: 2025 prices become the main scenario.

Purpose: rewrite the price paragraph, the Table 4 caption and table, the optimization-settings table and the comparison
paragraph in place, keeping the author's fields (SEQ/REF), bookmarks and formatting. Aborts if the text is not as expected.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03
"""

import copy
import sys
from pathlib import Path
from typing import Any

from docx import Document

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
PATH = Path(__file__).resolve().parents[1] / "HDG_Robust_Optimization_Manuscript_v1.docx"


def run_text(run: Any) -> str:
    """Concatenated text of a run element."""
    return "".join(t.text or "" for t in run.iter(W + "t"))


def set_run_text(run: Any, text: str) -> None:
    """Replace the text of a run, keeping its formatting."""
    nodes = list(run.iter(W + "t"))
    nodes[0].text = text
    nodes[0].set(XML_SPACE, "preserve")
    for extra in nodes[1:]:
        run.remove(extra)


def field_spans(runs: list[Any]) -> list[tuple[int, int]]:
    """Index ranges (begin to end inclusive) of the complex fields among the runs."""
    spans, i = [], 0
    while i < len(runs):
        mark = runs[i].find(W + "fldChar")
        if mark is not None and mark.get(W + "fldCharType") == "begin":
            j = i
            while True:
                end = runs[j].find(W + "fldChar")
                if end is not None and end.get(W + "fldCharType") == "end":
                    break
                j += 1
            spans.append((i, j))
            i = j + 1
        else:
            i += 1
    return spans


def expect(condition: bool, message: str) -> None:
    """Abort without saving when the document is not in the expected state."""
    if not condition:
        sys.exit(f"ABORTED, nothing saved: {message}")


NEW_1 = "The cost of manufacture was calculated with raw-material prices of 2025 ("
NEW_2 = (
    "; Supporting Information SI-4), which are bulk or export market values, except for zinc, which is the annual average "
    "of the London Metal Exchange reported by the USGS (2026). Energy, water, labor, and fixed capital keep the values of "
    "the 2019 study (Hernandez-Betancur, 2018). The optimization itself was run with the prices of the 2019 study (2016 "
    "to 2018), in which the price of ammonium hydroxide was corrected because the original listing converted a price per "
    "litre into a price per tonne (Supporting Information SI-4); the Pareto set was therefore found under those prices "
    "and then re-evaluated at full-year scale with the prices of 2025. To test how much the prices matter, the Pareto set "
    "was also re-evaluated with the same random numbers under the prices of the 2019 study"
)
NEW_3 = (
    ", and the compromise design, the cost saving with respect to the baseline, and the rank correlation (Spearman) of "
    "COM across the Pareto set were compared between the two sets of prices. The prices of the 2019 study are marketplace "
    "quotes for small lots, whereas the prices of 2025 are bulk or export market values, so the comparison mixes the "
    "passage of time with the purchasing scale and is interpreted as a sensitivity analysis, not as a forecast. Because "
    "prices do not enter "
)


def edit_price_paragraph(paragraph: Any) -> None:
    """Rewrite the paragraph that describes the prices, keeping its first REF field to Table 4."""
    runs = paragraph._p.findall(W + "r")
    spans = field_spans(runs)
    expect(len(spans) == 2, "price paragraph does not have the expected two fields")
    (s0, e0), (s1, e1) = spans
    expect(run_text(runs[0]).startswith("The cost of manufacture was calculated"), "price paragraph start changed")
    expect(run_text(runs[e1 + 1]).startswith("), and the compromise design"), "price paragraph tail changed")
    set_run_text(runs[0], NEW_1)
    for run in runs[1:s0]:
        paragraph._p.remove(run)
    set_run_text(runs[e0 + 1], NEW_2)
    for run in runs[e0 + 2 : s1]:
        paragraph._p.remove(run)
    for run in runs[s1 : e1 + 1]:
        paragraph._p.remove(run)
    set_run_text(runs[e1 + 1], NEW_3)


def edit_caption(paragraph: Any) -> None:
    """Rewrite the Table 4 caption after its SEQ field (the subscripts of the formulas stay as separate runs)."""
    runs = paragraph._p.findall(W + "r")
    texts = [run_text(r) for r in runs]
    expect(any("Raw-material prices of the cost scenarios" in t for t in texts), "caption text changed")

    def find(prefix: str, start: int = 0) -> int:
        return next(i for i in range(start, len(texts)) if texts[i].startswith(prefix))

    i_title = find(" Raw-material prices of the cost scenarios")
    set_run_text(runs[i_title], " Raw-material prices of 2025 (USD per ")
    i_a = find("2019", i_title)
    i_d = find(" prices with the ammonium hydroxide")
    expect(i_a < i_d, "caption order changed")
    for k in range(i_a, i_d):
        set_run_text(runs[k], "")
    set_run_text(runs[i_d], "Zinc: LME annual average reported by the USGS (2026). NaOH: Argus Media (2025) quotes per dry ")
    i_nacl = find("% solution (× 0.5), ZnCl")
    set_run_text(runs[i_nacl], "% solution (× 0.5). ZnCl")
    i_cl = find("Cl, and HCl from IMARC Group")
    set_run_text(runs[i_cl], "Cl, and HCl: IMARC Group (2025, 2026a, 2026b). NH")
    i_oh = find("OH from ", i_cl)
    set_run_text(runs[i_oh], "OH: ")
    i_last = len(runs) - 1
    expect(texts[i_last].startswith(". Energy, water, labor, and fixed capital were not updated"), "caption end changed")
    set_run_text(
        runs[i_last],
        ". The prices of the 2019 study, used in the sensitivity analysis, are given in Supporting Information SI-4. "
        "Energy, water, labor, and fixed capital keep the values of the 2019 study.",
    )


def edit_price_table(table: Any) -> None:
    """Keep the raw material and the 2025 price columns only."""
    header = [c.text for c in table.rows[0].cells]
    expect(header == ["Raw material", "2019", "Corrected", "2025"], f"price table header changed: {header}")
    widths = ("5616", "3744")
    for row in table.rows:
        cells = row._tr.findall(W + "tc")
        for gone in (cells[1], cells[2]):
            row._tr.remove(gone)
        for cell, width in zip(row._tr.findall(W + "tc"), widths):
            cell.find(W + "tcPr").find(W + "tcW").set(W + "w", width)
    for grid, width in zip(table._tbl.tblGrid.findall(W + "gridCol"), widths + ("0", "0")):
        grid.set(W + "w", width)
    for extra in table._tbl.tblGrid.findall(W + "gridCol")[2:]:
        table._tbl.tblGrid.remove(extra)
    last = table.rows[0].cells[1]
    set_run_text(list(last._tc.iter(W + "r"))[0], "Price, 2025 (USD/t)")
    for run in list(last._tc.iter(W + "r"))[1:]:
        run.getparent().remove(run)


def edit_settings_table(table: Any) -> None:
    """Add the row that says which prices the search used."""
    labels = [r.cells[0].text for r in table.rows]
    expect("Simulated year during the search" in labels, "settings table changed")
    expect("Prices used in the search" not in labels, "settings row already added")
    source = table.rows[labels.index("Simulated year during the search")]._tr
    clone = copy.deepcopy(source)
    source.addnext(clone)
    for cell, text in zip(clone.findall(W + "tc"), ("Prices used in the search", "Prices of the 2019 study, with the ammonium hydroxide unit corrected")):
        runs = list(cell.iter(W + "r"))
        set_run_text(runs[0], text)
        for extra in runs[1:]:
            extra.getparent().remove(extra)


def edit_comparison(paragraph: Any) -> None:
    """State the prices used in the comparison."""
    first = paragraph._p.findall(W + "r")[0]
    old = "under the same random numbers."
    expect(old in run_text(first), "comparison paragraph changed")
    set_run_text(first, run_text(first).replace(old, "under the same random numbers and with the prices of 2025.", 1))


def main() -> None:
    """Apply every edit and save once all checks passed."""
    document = Document(str(PATH))
    paragraphs = document.paragraphs
    expect(paragraphs[56].text.startswith("The cost of manufacture was calculated"), "paragraph 56 is not the price paragraph")
    expect(paragraphs[57].style.name == "Caption" and "Raw-material prices" in paragraphs[57].text, "paragraph 57 is not the Table 4 caption")
    expect(paragraphs[60].text.startswith("The compromise design and the baseline design"), "paragraph 60 is not the comparison paragraph")
    edit_price_paragraph(paragraphs[56])
    edit_caption(paragraphs[57])
    edit_price_table(document.tables[10])
    edit_settings_table(document.tables[7])
    edit_comparison(paragraphs[60])
    document.save(str(PATH))
    print("saved", PATH)


if __name__ == "__main__":
    main()
