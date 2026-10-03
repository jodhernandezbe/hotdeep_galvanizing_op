# Reference checklist (manuscript v1)

Status of every reference in the draft. **Verified** = bibliographic data checked against Crossref (title, authors,
journal, volume, pages, year, DOI) on 2026-10-03. That confirms the reference exists and is spelled correctly; it does
**not** confirm that it says what the sentence claims, which only reading the paper does.

| Reference | Status | What the draft uses it for | Still to do |
|---|---|---|---|
| Hernandez-Betancur et al. (2019), *J. Clean. Prod.* 206 | Verified; **full text read** | Framework, weights, 45.26 %, critical stages, 88.7 % | Compare its numbers with the Python port in the Results |
| Hernandez-Betancur (2018), thesis, UNAL | Repository record and thesis text read | Models, Butler–Volmer, ISO 1461 table, prices | — |
| Chang (1996) | Verified | FAHP | — |
| Deb et al. (2002) | Verified | NSGA-II | — |
| Fresner et al. (2007) | Verified | Cleaner-production study | Read it: the "feasible but not economically viable" claim is taken from the description in the 2019 paper |
| Hegyi et al. (2015) | Verified | Product-level assessment (rebars) | — |
| Kleywegt et al. (2002) | Verified | Sample average approximation | — |
| Kong & White (2010) | Verified | Cleaner production in China | — |
| Lobato et al. (2015) | Verified | Solid-waste management | — |
| McKay et al. (1979) | Verified | Latin hypercube sampling | — |
| Ruiz-Mercado et al. (2012) | Verified | GREENSCOPE | — |
| Smith & Ruiz-Mercado (2014) | Verified (online 2013) | Additive utility | — |
| Tongpool et al. (2010) | Verified | Environmental impacts of steel production | Read it: "galvanizing stage" comes from the 2019 paper |
| Vyhmeister et al. (2018) | Verified | GREENSCOPE as optimization objectives | Read it: the use of GREENSCOPE objectives comes from a search snippet |
| Zimmermann (1978) | Verified | Fuzzy memberships | — |
| Zitzler & Thiele (1999) | Verified | Hypervolume | — |
| Akamphon et al. (2012) | Verified | Zinc consumption analysis | — |
| U.S. Geological Survey (2026), Zinc | **Read** (primary) | Zinc production, import reliance, galvanizing as leading use | — |
| World Steel Association (2025) | Figures read from search results; page not machine-readable | Steel production figures | Check the numbers on worldsteel.org |
| U.S. Geological Survey (2025), critical minerals list | Seen via search; page returned HTTP 403 | Zinc retained on the 2025 list | Replace with the Federal Register notice |
| ILZSG (2024), World Zinc Factbook | **Read** (primary, p. 36 and 40) | Galvanizing 60 % of zinc use; end-use sectors; batch HDG is fragmented | Year of the shares is not printed on the page |
| Wang (2018); Costa et al. (2019); Reséndiz-Flores et al. (2021); Crișan et al. (2023); Lorenz et al. (2023); Arguillarena et al. (2023) | Verified in Crossref; abstracts read | Related optimization and assessment work in galvanizing | Read the full texts before describing them further |
| Arguillarena et al. (2022) | Verified in Crossref; abstract not read | LCA of zinc and iron recovery from spent pickling acids | Read the abstract |
| Argus Media (2025), chlor-alkali issue 25-46 | **Read** (primary) | NaOH price basis: 340 to 400 USD per dry metric tonne FOB US Gulf | — |
| IMARC Group (2025, 2026a, 2026b) | Pages read; they state region and period only | ZnCl₂, NH₄Cl and HCl prices | Concentration and grade are not stated; pages are updated over time, so archive a copy |
| Intratec (2026) | Page read (Jan 2026: 190 USD/t; +11 % year on year) | NH₄OH price | Concentration not stated; the 173 USD/t (Sep 2025) value comes from a search snippet |
| Koch et al. (2016), NACE IMPACT | **Written from memory** (authors, title); figures seen in secondary pages | US$2.5 trillion, 3.4 % of GDP, 15 to 35 % savings | Verify authors, title and figures against the report |
| Law (2015) | **Written from memory** | Common random numbers | Verify edition and publisher |
| ISO 1461:2009 | **Written from memory**; the thesis cites the Spanish adoption (UNE-EN ISO 1461) | Thickness requirements | Confirm the edition the thesis used |

## Claims that were open in the first draft

1. **Zinc used for galvanizing** — resolved. Primary source: ILZSG (2024), p. 36: galvanizing 60 % of zinc by first use.
   The draft now cites it, with the end-use sectors and the batch-vs-continuous distinction.
2. **No study optimizes the whole line under uncertainty** — resolved by a documented search (OpenAlex, 16 queries,
   2026-10-03; protocol and closest hits in `docs/LITERATURE.md`). The statement is now worded as "a search ... found no
   study", citing the closest work. A Scopus or Web of Science repeat with the same queries is still advisable.
3. **Repository URL** — still open: confirm that it is public before submission (highlighted in the .docx).
4. **Table 4 prices and conversions** — resolved. Zinc is now the USGS-reported LME annual price (2866 USD/t, was 2867).
   NaOH keeps the dry-to-solution conversion (× 0.5) because Argus states the dry basis explicitly (price 185, mid-point
   of 340 to 400). The HCl rescaling (× 37/31) was removed because no source states the concentration; the IMARC value
   (244 USD/t) is used as published, with the possible understatement (up to about 15 %) written in the caption. The
   thesis prices are marketplace quotes and the 2025 prices are bulk indices, so the scenario is described as a
   sensitivity analysis, not a time update.

## Still to check

- Koch et al. (2016), Law (2015) and ISO 1461:2009 were written from memory (see the table).
- IMARC pages change over time: save a PDF of each page used for Table 4.
- The Supporting Information sections cited in the text have not been written.

## Supporting Information sections cited in the text (not yet written)

SI-1 code repository and reproducibility; SI-2 validation of the Python port and corrected mode (flux-bath side stream,
with the patent sources); SI-3 bath limits and the flux-bath iron limit; SI-4 cost scenarios and price sources; SI-5 literature search on optimization of galvanizing (queries, database, date, closest works).
