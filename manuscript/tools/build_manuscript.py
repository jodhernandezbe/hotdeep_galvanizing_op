"""Write the manuscript draft (title, keywords, introduction, methodology) to a .docx.

Purpose: single source of the manuscript text; rerun after editing to regenerate the Word file.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-03

Run from the repository root: `uv run --with python-docx python manuscript/tools/build_manuscript.py`.
Yellow-highlighted text marks items that still need a decision or a source check.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import docx_builder as w  # noqa: E402

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
OUTPUT = ROOT / "generated" / "HDG_manuscript_generated_draft.docx"

TITLE = (
    "Robust multi-objective optimization of hot-dip galvanizing operating conditions under uncertainty: "
    "a simulation-based sustainability framework with coating quality constraints"
)
KEYWORDS = (
    "Hot-dip galvanizing; Robust optimization under uncertainty; NSGA-II; GREENSCOPE; " "Fuzzy analytic hierarchy process; Zinc"
)

ABSTRACT = (
    "{hl:[Abstract to be written once the final optimization results are available. It should state the decision "
    "addressed, the framework, the headline numbers for the baseline and the selected design, and their implications.]}"
)

INTRODUCTION = [
    (
        "Steel is the backbone of modern infrastructure, and its main weakness is corrosion. World crude steel production "
        "reached 1,882.6 million tonnes in 2024, of which China produced 1,005.1 million tonnes (53%), India 149.6, Japan "
        "84.0, and the United States 79.5 (World Steel Association, 2025). The global cost of corrosion has been estimated "
        "at US$2.5 trillion per year, about 3.4% of the global gross domestic product, and applying corrosion management "
        "best practices could avoid 15 to 35% of that cost (Koch et al., 2016). Among the available protection methods, "
        "hot-dip galvanizing (HDG), which coats steel by immersion in a molten zinc bath at about 450 °C to form a zinc-iron "
        "alloy layer, is one of the most common, and it is used on structural steel, reinforcing bars, and other "
        "infrastructure components (Hegyi et al., 2015; Hernandez-Betancur et al., 2019)."
    ),
    (
        "Galvanizing is also the largest single use of zinc, accounting for 60% of the zinc used by first-use "
        "application, and construction (50%), transport (20%), and infrastructure (15%) are the largest end-use sectors "
        "of zinc (International Lead and Zinc Study Group [ILZSG], 2024). Continuous galvanizing of steel coil is carried "
        "out by large integrated steel producers, whereas batch (general) HDG, the process studied here, is a fragmented "
        "industry of many small plants located close to their markets (ILZSG, 2024). World zinc mine production was an "
        "estimated 13.0 million tonnes in 2025, led by China (4.1 million tonnes), Peru (1.5), and Australia (1.1) (U.S. "
        "Geological Survey [USGS], 2026). Supply security has made zinc a policy concern in steel-consuming economies: the "
        "United States, whose net import reliance for refined zinc was 73% in 2025, retained zinc in its 2025 List of "
        "Critical Minerals (USGS, 2025, 2026). The efficient use of zinc in galvanizing lines is therefore a resource "
        "question for large steel producers and consumers such as China and the United States, as well as for galvanizers "
        "in developing economies, and every kilogram of zinc lost as dross, ash, or spent flux in the line is a kilogram "
        "that must be mined, smelted, and paid for again."
    ),
    (
        "The galvanizing line also generates waste. Degreasing, pickling, and fluxing produce spent solutions, rinse "
        "wastewater, and sludge, and the molten bath produces dross, ash, and zinc splash, in addition to gaseous "
        "emissions (Hernandez-Betancur et al., 2019). The literature on the sustainability of HDG has approached these "
        "burdens from separate angles: cleaner production and zero-emission strategies in plants in China and Austria "
        "(Kong & White, 2010; Fresner et al., 2007), the environmental impacts of steel production and its galvanizing "
        "stage (Tongpool et al., 2010), the management of solid wastes and spent pickling solutions (Lobato et al., 2015), "
        "and the economics of zinc consumption (Akamphon et al., 2012). Studies that combine economic and environmental "
        "dimensions mostly assess the galvanized product, for example reinforcing bars in concrete, rather than the "
        "production process (Hegyi et al., 2015), and Fresner et al. (2007) found that environmental solutions can be "
        "technically feasible without being economically viable, which shows that cost and environmental objectives may "
        "conflict and that a single-objective view is insufficient."
    ),
    (
        "To assess the process rather than the product, Hernandez-Betancur et al. (2019) proposed a framework that combines "
        "17 process-oriented indicators of the GREENSCOPE methodology (Ruiz-Mercado et al., 2012) with a coating quality "
        "indicator based on ISO 1461, weights the indicators and their categories (environment, efficiency, energy, "
        "economy, and quality) with a fuzzy analytic hierarchy process (FAHP; Chang, 1996) applied to a survey of ten "
        "experts, aggregates them into an additive utility (Smith & Ruiz-Mercado, 2014), and represents the random nature "
        "of the steel lots, the operating conditions, and the surroundings with a kinetic Monte Carlo simulation. Applied "
        "to a Colombian galvanizing line that processes about 180 tonnes of steel per month, the framework identified "
        "pickling and fluxing as the critical stages, which together explained 88.7% of the variation in process "
        "sustainability, and estimated a probability of only 45.26% that the process reaches the sustainability "
        "threshold of 80% utility. The authors concluded that these stages could not be improved without a significant "
        "change in the process configuration (Hernandez-Betancur et al., 2019)."
    ),
    (
        "That conclusion was reached by diagnosing one fixed set of operating conditions. It does not show whether the "
        "controllable conditions of the critical stages, such as the acid concentration and dipping time in pickling or "
        "the salt concentration and pH of the flux, can improve the process without changing its configuration, nor which "
        "trade-offs among sustainability utility, manufacturing cost, polluted liquid waste, and water consumption appear "
        "when they are changed together, and any improvement has to hold under the variability of steel lots and ambient "
        "conditions that the line faces every day. Answering these questions requires using the framework prescriptively "
        "instead of diagnostically, that is, as the evaluator of an optimization in which every candidate set of operating "
        "conditions is assessed under uncertainty."
    ),
    (
        "Multi-objective evolutionary algorithms, and NSGA-II in particular (Deb et al., 2002), suit this task because they "
        "return a set of non-dominated trade-off solutions in a single run. When the model is stochastic, the expected "
        "value of each objective can be estimated by Monte Carlo sampling (the sample average approximation; Kleywegt et "
        "al., 2002), and evaluating all candidates with the same random draws (common random numbers) reduces the sampling "
        "noise in the comparison between candidates (Law, 2015). GREENSCOPE indicators have already served as objectives in "
        "the optimization of production chains (Vyhmeister et al., 2018). In the galvanizing literature, optimization has "
        "been applied to the air-knife parameters that set the coating thickness in continuous lines (Wang, 2018), to the "
        "heat treatment of continuous galvanizing of dual-phase steels with multi-objective genetic algorithms (Costa et "
        "al., 2019; Reséndiz-Flores et al., 2021), and to the operation of steel pickling baths (Crișan et al., 2023), "
        "while sustainability studies of batch HDG have examined the recovery of zinc and iron from spent pickling acids "
        "with life cycle assessment (Arguillarena et al., 2022, 2023; Lorenz et al., 2023). A search of the literature "
        "(Supporting Information SI-5) found no study that optimizes the operating conditions of the stages of a "
        "galvanizing line jointly against several sustainability objectives under uncertainty."
    ),
    (
        "This study couples the 2019 framework with NSGA-II to find robust operating conditions for the HDG line. Seven "
        "controllable variables (the temperature of degreasing, the HCl concentration and dipping time in pickling, the "
        "temperature, pH, and salt concentration of the flux, and the temperature of the zinc bath) are optimized for four "
        "expected-value objectives (process utility, manufacturing cost, polluted liquid waste, and water consumption), "
        "subject to constraints on the probability of failing the ISO 1461 thickness requirement and on the accumulation "
        "of iron in the pickling bath. A fuzzy compromise based on the 2019 FAHP weights selects one design from the Pareto "
        "set, the sensitivity of that selection to the objective weights and to raw-material prices is tested, and the "
        "selected design is compared with a baseline design through 1,000 simulated years of production for each. Section "
        "2 describes the methodology, Section 3 presents and discusses the results, and Section 4 gives the conclusions."
    ),
]

[
    (
        "Steel is the backbone of modern infrastructure, and its main weakness is corrosion. World crude steel production "
        "reached 1,882.6 million tonnes in 2024, of which China produced 1,005.1 million tonnes (53%), India 149.6, Japan "
        "84.0, and the United States 79.5 (World Steel Association, 2025). The global cost of corrosion has been estimated "
        "at US$2.5 trillion per year, about 3.4% of the global gross domestic product, and applying corrosion management "
        "best practices could avoid 15 to 35% of that cost (Koch et al., 2016). Among the available protection methods, "
        "hot-dip galvanizing (HDG), which coats steel by immersion in a molten zinc bath at about 450 °C to form a zinc-iron "
        "alloy layer, is one of the most common, and it is used on structural steel, reinforcing bars, and other "
        "infrastructure components (Hegyi et al., 2015; Hernandez-Betancur et al., 2019)."
    ),
    (
        "Galvanizing is also the largest single use of zinc: most of the zinc consumed is used to produce galvanized steel "
        "(U.S. Geological Survey [USGS], 2026), and shares of roughly half or more of global zinc consumption have been "
        "reported {hl:[confirm the share and cite its primary source, for example the International Zinc Association or the "
        "International Lead and Zinc Study Group]}. World zinc mine production was an estimated 13.0 million tonnes in 2025, "
        "led by China (4.1 million tonnes), Peru (1.5), and Australia (1.1) (USGS, 2026). Supply security has made zinc a "
        "policy concern in steel-consuming economies: the United States, whose net import reliance for refined zinc was 73% "
        "in 2025, retained zinc in its 2025 List of Critical Minerals (USGS, 2025, 2026). The efficient use of zinc in "
        "galvanizing lines is therefore a resource question for large steel producers and consumers such as China and the "
        "United States, as well as for galvanizers in developing economies, and every kilogram of zinc lost as dross, ash, "
        "or spent flux in the line is a kilogram that must be mined, smelted, and paid for again."
    ),
    (
        "The galvanizing line also generates waste. Degreasing, pickling, and fluxing produce spent solutions, rinse "
        "wastewater, and sludge, and the molten bath produces dross, ash, and zinc splash, in addition to gaseous "
        "emissions (Hernandez-Betancur et al., 2019). The literature on the sustainability of HDG has approached these "
        "burdens from separate angles: cleaner production and zero-emission strategies in plants in China and Austria "
        "(Kong & White, 2010; Fresner et al., 2007), the environmental impacts of steel production and its galvanizing "
        "stage (Tongpool et al., 2010), the management of solid wastes and spent pickling solutions (Lobato et al., 2015), "
        "and the economics of zinc consumption (Akamphon et al., 2012). Studies that combine economic and environmental "
        "dimensions mostly assess the galvanized product, for example reinforcing bars in concrete, rather than the "
        "production process (Hegyi et al., 2015), and Fresner et al. (2007) found that environmental solutions can be "
        "technically feasible without being economically viable, which shows that cost and environmental objectives may "
        "conflict and that a single-objective view is insufficient."
    ),
    (
        "To assess the process rather than the product, Hernandez-Betancur et al. (2019) proposed a framework that combines "
        "17 process-oriented indicators of the GREENSCOPE methodology (Ruiz-Mercado et al., 2012) with a coating quality "
        "indicator based on ISO 1461, weights the indicators and their categories (environment, efficiency, energy, "
        "economy, and quality) with a fuzzy analytic hierarchy process (FAHP; Chang, 1996) applied to a survey of ten "
        "experts, aggregates them into an additive utility (Smith & Ruiz-Mercado, 2014), and represents the random nature "
        "of the steel lots, the operating conditions, and the surroundings with a kinetic Monte Carlo simulation. Applied "
        "to a Colombian galvanizing line that processes about 180 tonnes of steel per month, the framework identified "
        "pickling and fluxing as the critical stages, which together explained 88.7% of the variation in process "
        "sustainability, and estimated a probability of only 45.26% that the process reaches the sustainability "
        "threshold of 80% utility. The authors concluded that these stages could not be improved without a significant "
        "change in the process configuration (Hernandez-Betancur et al., 2019)."
    ),
    (
        "That conclusion was reached by diagnosing one fixed set of operating conditions. It does not show whether the "
        "controllable conditions of the critical stages, such as the acid concentration and dipping time in pickling or "
        "the salt concentration and pH of the flux, can improve the process without changing its configuration, nor which "
        "trade-offs among sustainability utility, manufacturing cost, polluted liquid waste, and water consumption appear "
        "when they are changed together, and any improvement has to hold under the variability of steel lots and ambient "
        "conditions that the line faces every day. Answering these questions requires using the framework prescriptively "
        "instead of diagnostically, that is, as the evaluator of an optimization in which every candidate set of operating "
        "conditions is assessed under uncertainty."
    ),
    (
        "Multi-objective evolutionary algorithms, and NSGA-II in particular (Deb et al., 2002), suit this task because they "
        "return a set of non-dominated trade-off solutions in a single run. When the model is stochastic, the expected "
        "value of each objective can be estimated by Monte Carlo sampling (the sample average approximation; Kleywegt et "
        "al., 2002), and evaluating all candidates with the same random draws (common random numbers) reduces the sampling "
        "noise in the comparison between candidates (Law, 2015). GREENSCOPE indicators have already served as objectives in "
        "the optimization of production chains (Vyhmeister et al., 2018). In the HDG literature reviewed for this study, "
        "improvements have been analyzed for individual aspects such as zinc consumption (Akamphon et al., 2012), but no "
        "study that optimizes the operating conditions of the whole line against several sustainability objectives under "
        "uncertainty was found {hl:[confirm with a systematic literature search before submission]}."
    ),
    (
        "This study couples the 2019 framework with NSGA-II to find robust operating conditions for the HDG line. A Python "
        "implementation of the process and sustainability models, tested against the 2019 results, evaluates each "
        "candidate. Seven controllable variables (the temperature of degreasing, the HCl concentration and dipping time in "
        "pickling, the temperature, pH, and salt concentration of the flux, and the temperature of the zinc bath) are "
        "optimized for four expected-value objectives (process utility, manufacturing cost, polluted liquid waste, and "
        "water consumption), subject to constraints on the probability of failing the ISO 1461 thickness requirement and on "
        "the accumulation of iron in the pickling bath. A fuzzy compromise based on the 2019 FAHP weights selects one "
        "design from the Pareto set, the sensitivity of that selection to the objective weights and to the 2016 to 2018 "
        "prices is tested, and the selected design is compared with a baseline design through 1,000 simulated years of "
        "production for each. Section 2 describes the methodology, Section 3 presents and discusses the results, and "
        "Section 4 gives the conclusions."
    ),
]

OVERVIEW = (
    "Figure 1 summarizes the approach. A candidate set of operating conditions (the decision vector {i:x}) and a random "
    "draw of the uncertain inputs (steel lots, composition, contamination, and ambient temperature) feed a "
    "stage-resolved simulation of one year of production of the HDG line (Section 2.2). The resulting inventory is "
    "converted into indicator scores and a process utility (Section 2.3). Repeating the simulation for {i:N} random years "
    "gives the expected values of the objectives and of the constraint quantities of that candidate (Section 2.4), and "
    "NSGA-II searches for non-dominated candidates (Section 2.5). The Pareto set is then re-evaluated at full-year "
    "scale, a compromise design is selected with a fuzzy decision rule, and the sensitivity of that choice to weights "
    "and prices is tested (Section 2.6). Finally, the selected design and a baseline design are compared through 1,000 "
    "simulated years each (Section 2.7)."
)
FIG1_CAPTION = (
    "Figure 1. Framework for the robust multi-objective optimization of the hot-dip galvanizing (HDG) line. Operating "
    "conditions (decision vector) and random inputs feed a stage-resolved simulation; indicator scores and the process "
    "utility give the objectives and constraints as Monte Carlo means; NSGA-II proposes new candidates until it "
    "terminates; the Pareto set is re-evaluated at full-year scale, a compromise design is selected, and it is "
    "compared with the baseline design. FAHP = fuzzy analytic hierarchy process; SBX = simulated binary crossover; "
    "CI = confidence interval; E[·] = expected value."
)

PROCESS_1 = (
    "The line modeled is the one analyzed in the 2019 study (Hernandez-Betancur, 2018; Hernandez-Betancur et al., 2019): "
    "a galvanizer that processes about 180 tonnes of steel per month, represented as 41,379,264 pieces per year (Figure "
    "2). Pieces are degreased in a NaOH solution, rinsed, pickled in HCl to remove rust, rinsed again, immersed in a "
    "ZnCl{sub:2}/NH{sub:4}Cl flux solution, dried, and dipped in molten zinc. A random 2% of the pieces is re-processed: "
    "their coating is removed in a dilute HCl bath (dezincification) before they re-enter rinsing, fluxing, and "
    "galvanizing."
)
FIG2_CAPTION = (
    "Figure 2. Process flow diagram of the hot-dip galvanizing line simulated (units U1 to U7). Thick black arrows: flow "
    "of the steel pieces through the line. Thin blue arrows: feeds of chemicals, water, and zinc to each unit. Thin "
    "gray arrows: outputs of each unit (spent solutions, rinse wastewater, hydroxide sludge, dross, and ash), which "
    "the 17 GREENSCOPE indicators account for. Dashed arrows: re-processing loop, in which 2% of the pieces leave "
    "galvanizing, pass through the dezincification bath, and re-enter the line at rinsing 2. Red blocks x1 to x7: "
    "the decision variables, that is, the operating conditions of the unit they touch that the optimizer sets "
    "within the bounds of Table 2 (T = temperature). Orange boxes: random inputs of the simulation (Table 1)."
)
PROCESS_2 = (
    "Each stage is described by mass and energy balances of its bath and of the pieces, together with the phenomena "
    "that govern it: saponification of grease in the degreasing bath; dissolution of iron oxide (FeO) and of steel in "
    "the pickling bath, with rate equations integrated numerically over the dipping time; Butler-Volmer kinetics for the "
    "dissolution of zinc in the dezincification bath (Hernandez-Betancur, 2018); ionic equilibria of Zn(OH){sub:2}, "
    "NH{sub:4}OH, and Fe(OH){sub:2} and regulation of the pH with HCl and NH{sub:4}OH in the flux bath; the heat duties "
    "of the heated baths and of the dryer; and a regression of the coating thickness {i:δ} on the zinc bath temperature "
    "and the silicon content of the steel. Baths are renewed when they reach operating limits (an iron concentration of "
    "150 g/L in the normal pickling bath, an HCl concentration below 10 g/L in the dezincification bath, and an iron "
    "concentration of 5 g/L in the flux bath); the degreasing bath is renewed once a year and the rinsing tanks 54 times "
    "a year. The coating thickness required for each piece depends on its gauge and is the local minimum thickness of "
    "ISO 1461 (35, 45, 55, or 70 µm for gauges below 1.5 mm, from 1.5 to 3 mm, from 3 to 6 mm, and above 6 mm; "
    "International Organization for Standardization, 2009)."
)
PROCESS_3 = (
    "Randomness enters through the steel lots, the state of the fresh baths, and the surroundings (Table 1). In each "
    "simulated year, lots are drawn until the annual number of pieces is reached; the ambient temperature is drawn for "
    "every lot and affects the heat losses of all open tanks. The variables that the optimization controls replace the "
    "corresponding random draws of the 2019 study (Table 2); all other inputs keep the distributions of Table 1."
)
TABLE1_CAPTION = (
    "Table 1. Stochastic inputs of the simulation (Hernandez-Betancur, 2018; Hernandez-Betancur et al., 2019). "
    "{i:U}(a, b) = uniform distribution; {i:N}(μ, σ{sup:2}) = normal distribution. The fresh-bath temperatures, the "
    "HCl concentration of the normal pickling bath, the flux pH and salt concentration, the dipping time, and the zinc "
    "bath temperature are drawn in the 2019 study but are decision variables here (Table 2)."
)
TABLE1_HEADER = ["Input", "Distribution or range", "Note"]
TABLE1_ROWS = [
    [
        "Product family of each lot",
        "10 families, probabilities 0.054 to 0.291",
        "Lot size 46 to 111,600 pieces and piece mass 0.009 to 0.123 kg, uniform within each family",
    ],
    ["Gauge of each piece", "{i:U}(0.3, 32) mm", "Sets the ISO 1461 thickness requirement"],
    ["Silicon content of the steel", "{i:U}(0.15, 0.25) wt%", "Controls the thickness of the zinc coating"],
    ["Rust load", "{i:U}(300, 590) g/m{sup:2}", "Per unit of piece surface"],
    ["Pieces that need degreasing", "30% of the pieces", "Grease and oil: 10 g per tonne of steel"],
    ["Ambient temperature", "{i:N}(22, 2{sup:2}) °C", "Drawn for every lot"],
    ["Fresh bath volume", "{i:U}(12.6, 14.0) m{sup:3}", "Degreasing, pickling, and flux tanks"],
    ["NaOH, fresh degreasing bath", "{i:U}(14, 16) wt%", "Temperature is x{sub:1} (Table 2)"],
    ["HCl, fresh dezincification bath", "{i:U}(2, 4) wt%", "Normal pickling bath: x{sub:2}"],
    [
        "Dross and ash",
        "{i:N}(0.75, 0.083{sup:2}) wt% of the dipped steel each",
        "Zinc content: 95 wt% in dross and 72.5 wt% in ash (normal)",
    ],
    ["Re-processing", "2% of the pieces", "Pieces pass through the dezincification bath"],
]

GREENSCOPE_1 = (
    "Following the 2019 study, the inventory of each simulated year is converted into the 17 GREENSCOPE indicators "
    "selected there (11 environmental, four efficiency, one energy, and one economic indicator) for each of the seven "
    "unit processes (degreasing, rinsing 1, pickling, rinsing 2, fluxing, drying, and galvanizing), plus a quality "
    "indicator based on ISO 1461. Every indicator value {i:x}{sub:i,j} is converted into a score between its worst and "
    "best reference values (Ruiz-Mercado et al., 2012):"
)
EQ1 = "{i:G}{sub:i,j} = 100 ({i:x}{sub:i,j} − {i:x}{sub:worst,i,j}) / ({i:x}{sub:best,i,j} − {i:x}{sub:worst,i,j})"
GREENSCOPE_2 = (
    "The quality score {i:Q} compares the thickness {i:δ}{sub:s} of each piece {i:s} with the thickness {i:δ}{sub:ISO,s} "
    "required for its gauge, weighted by the piece mass {i:m}{sub:s}:"
)
EQ2 = "{i:Q} = 100 Σ{sub:s} {i:m}{sub:s} min(1, {i:δ}{sub:s} / {i:δ}{sub:ISO,s}) / Σ{sub:s} {i:m}{sub:s}"
GREENSCOPE_3 = (
    "The relative weights {i:λ}{sub:i} of the 17 indicators and of the quality category {i:λ}{sub:Q} are those obtained "
    "in the 2019 study with the FAHP applied to ten experts: 0.1433 (environment), 0.1770 (efficiency), 0.1163 (energy), "
    "0.2500 (economy), and 0.3134 (quality) for the categories, with the weights of the individual environmental and "
    "efficiency indicators given in the 2019 study. The additive utility of the process (Smith & Ruiz-Mercado, 2014) "
    "for a simulated year is"
)
EQ3 = "{i:U}{sub:P} = {i:x̄}{sub:std} [ {i:Q} + (1 / ({i:m} {i:λ}{sub:Q})) Σ{sub:j=1}{sup:m} Σ{sub:i=1}{sup:17} {i:λ}{sub:i} {i:G}{sub:i,j} ]"
GREENSCOPE_4 = (
    "where {i:m} = 7 is the number of unit processes and {i:x̄}{sub:std} is the mean thickness required by the standard "
    "over the pieces of the year, which gives {i:U}{sub:P} the scale of a thickness (µm), as in the 2019 study. If all "
    "scores equal 100, the utility reaches its maximum {i:U}{sub:max} = 100 {i:x̄}{sub:std} / {i:λ}{sub:Q}. The process "
    "is considered sustainable in a simulated year if {i:U}{sub:P} ≥ {i:LM}{sub:P} = 0.8 {i:U}{sub:max}, and the "
    "probability of being sustainable, {i:P}{sub:sustainable}, is estimated as the fraction of simulated years that "
    "satisfy this condition. The 2019 study approximated this probability with a normal distribution of {i:U}{sub:P}; "
    "the empirical fraction avoids that assumption. In the formulation of the 2019 study the score of the "
    "manufacturing cost indicator is the same for every unit process (64.39%), because its best and worst reference "
    "values are fixed multiples of the cost itself; prices therefore change the cost in USD but not {i:U}{sub:P}."
)

MODES = (
    "The original MATLAB models (Hernandez-Betancur, 2018) were re-implemented and verified against the 2019 results. "
    "In thesis mode, the re-implementation reproduces the behavior of the original listings, including a few defects of "
    "those listings that change the numbers, so that published results can be recovered: for 100 simulated years it gave "
    "a 95% confidence interval of the mean process utility of 16,408 to 16,988 µm (16,406 to 16,987 µm in the 2019 "
    "study) and a probability of sustainability of 0.453 (0.4526), with fluxing and pickling again as the critical "
    "stages (Supporting Information SI-2). In corrected mode, which is used for every optimization run, the ammonium "
    "and volume balances of the flux bath conserve mass and the bath volume is limited to the tank capacity by "
    "withdrawing the excess as a side stream, as industrial flux baths are maintained instead of being dumped "
    "(Supporting Information SI-2). In a 20-year comparison with the same random numbers, corrected mode changed the "
    "mean process utility from 16,694 to 16,710 µm and the probability of sustainability from 0.452 to 0.456, and the "
    "critical stages did not change."
)

(
    "The original MATLAB models (Hernandez-Betancur, 2018) were ported to Python and tested against the 2019 results. In "
    "thesis mode, the port reproduces the behavior of the original listings, including a few defects of those listings "
    "that change the numbers, so that published results can be recovered: for 100 simulated years it gave a 95% "
    "confidence interval of the mean process utility of 16,408 to 16,988 µm (16,406 to 16,987 µm in the 2019 study) and "
    "a probability of sustainability of 0.453 (0.4526), with fluxing and pickling again as the critical stages "
    "(Supporting Information SI-2). In corrected mode, which is used for every optimization run, the ammonium and "
    "volume balances of the flux bath conserve mass and the bath volume is limited to the tank capacity by withdrawing "
    "the excess as a side stream, as industrial flux baths are maintained instead of being dumped (Supporting "
    "Information SI-2). In a 20-year comparison with the same random numbers, corrected mode changed the mean process "
    "utility from 16,694 to 16,710 µm and the probability of sustainability from 0.452 to 0.456, and the critical "
    "stages did not change."
)

DECISION_1 = (
    "Seven operating variables are controlled (Table 2). The temperature of the degreasing bath ({i:x}{sub:1}), the "
    "temperature, pH, and total salt concentration of the flux ({i:x}{sub:4}, {i:x}{sub:5}, {i:x}{sub:6}; ZnCl{sub:2}/"
    "NH{sub:4}Cl fixed at 60/40), and the HCl concentration of the normal pickling bath ({i:x}{sub:2}) define the state "
    "of the fresh bath at the start of the year and at every renewal, after which the state follows the balances; the "
    "dipping time in the normal pickling bath ({i:x}{sub:3}) and the set-point temperature of the zinc bath ({i:x}{sub:7}) "
    "apply to every piece. The bounds contain the values used in the 2019 study (for example 16 to 18 wt% HCl and 10 to "
    "20 min of dipping). The baseline design holds each variable at the nominal value of the 2019 distributions, "
    "without their random variation, so that the comparison isolates the effect of choosing the set-points."
)
TABLE2_CAPTION = "Table 2. Decision variables, their bounds, and the baseline design (nominal values of the 2019 study)."
TABLE2_HEADER = ["Variable", "Description", "Unit", "Bounds", "Baseline"]
TABLE2_ROWS = [
    ["{i:x}{sub:1}", "Temperature of the fresh degreasing bath", "°C", "40 to 60", "50"],
    ["{i:x}{sub:2}", "HCl concentration of the fresh normal pickling bath", "wt%", "12 to 18", "17"],
    ["{i:x}{sub:3}", "Dipping time in the normal pickling bath", "s", "600 to 1,200", "900"],
    ["{i:x}{sub:4}", "Temperature of the fresh flux bath", "°C", "40 to 60", "50"],
    ["{i:x}{sub:5}", "pH of the fresh flux bath", "–", "4.0 to 5.0", "4.5"],
    ["{i:x}{sub:6}", "Total salt concentration of the flux (ZnCl{sub:2}/NH{sub:4}Cl 60/40)", "g/L", "300 to 500", "400"],
    ["{i:x}{sub:7}", "Temperature of the zinc bath", "°C", "445 to 455", "450"],
]
OBJECTIVES = "The optimization problem has four objectives, all written for minimization, and two inequality constraints:"
EQ4 = "min {i:F}({i:x}) = [ −E[{i:U}{sub:P}], E[COM], E[{i:V}{sub:l-poll}], E[{i:V}{sub:WT}] ]"
EQ5 = "{i:g}{sub:1}({i:x}) = E[{i:φ}{sub:δ}] − 0.02 ≤ 0"
EQ6 = "{i:g}{sub:2}({i:x}) = E[{i:c}{sub:Fe,pick}] − 150 g/L ≤ 0"
CONSTRAINTS = (
    "where COM is the annual cost of manufacture (USD), {i:V}{sub:l-poll} the annual volume of polluted liquid waste "
    "(m{sup:3}), and {i:V}{sub:WT} the annual water consumption (m{sup:3}), each summed over the unit processes. "
    "The first constraint limits the probability of a defect: {i:φ}{sub:δ} is the fraction of pieces of a simulated year "
    "whose coating is thinner than required by ISO 1461 for their gauge, and its expected value must not exceed 2%. The "
    "second limits the peak iron concentration {i:c}{sub:Fe,pick} reached in the normal pickling bath, whose renewal "
    "limit is 150 g/L. The iron limit of the flux bath (5 g/L) is not a constraint but the renewal trigger of the "
    "simulation, so its peak value is at or above 5 g/L every time the bath is renewed regardless of the operating "
    "conditions; the cost and the waste of renewing the bath are instead part of COM and {i:V}{sub:l-poll} "
    "(Supporting Information SI-3)."
)
EXPECTATIONS = (
    "Each expected value is estimated as the mean over {i:N} = 100 simulated years. Sample {i:s} of every candidate uses "
    "the {i:s}-th child seed derived from one base seed (common random numbers), so that candidates are compared under "
    "the same steel lots and ambient temperatures. Draws whose occurrence depends on the operating conditions, such as "
    "those made at bath renewals, use a separate random stream so that the lots and temperatures remain identical "
    "across candidates."
)

SEARCH_1 = (
    "The problem was solved with NSGA-II (Deb et al., 2002) with the settings of Table 3. The initial population was "
    "drawn by Latin hypercube sampling (McKay et al., 1979). The search stops at 150 generations or, not before "
    "generation 100, when the hypervolume of the feasible non-dominated set (Zitzler & Thiele, 1999) stops improving; "
    "because the hypervolume of a population truncated by crowding distance is not monotone, stagnation is declared "
    "when the best hypervolume of the last 15 generations does not exceed the best value before them by more than the "
    "tolerance."
)
TABLE3_CAPTION = "Table 3. Settings of the optimization."
TABLE3_HEADER = ["Parameter", "Value"]
TABLE3_ROWS = [
    ["Population size and offspring per generation", "100"],
    ["Initial population", "Latin hypercube sampling"],
    ["Crossover", "Simulated binary crossover, probability 0.9, distribution index 15"],
    ["Mutation", "Polynomial mutation, probability 0.1 per variable, distribution index 20"],
    ["Constraint handling", "Feasible designs dominate infeasible ones; infeasible designs are ranked by constraint violation"],
    ["Generations", "At most 150; stagnation cannot stop the search before generation 100"],
    [
        "Stagnation criterion",
        "Best hypervolume of the last 15 generations improves by less than 10{sup:−4} (relative) over the best before them",
    ],
    [
        "Hypervolume",
        "Objectives normalized with the ideal and nadir points of the first feasible generation; reference point at 1.1",
    ],
    ["Monte Carlo samples per candidate", "{i:N} = 100 simulated years"],
    ["Simulated year during the search", "10{sup:6} pieces (full year: 41,379,264 pieces)"],
    ["Random seed", "42"],
    ["Checkpoints", "Every 5 generations"],
]
SEARCH_2 = (
    "A full simulated year takes about 3.6 s on the workstation used, whereas a year of 10{sup:6} pieces takes about "
    "0.09 s; the search therefore uses the shorter year. The fixed annual costs of the plant (capital charges and "
    "labor) do not scale with the number of pieces, so the objective values obtained during the search are not on the "
    "reporting basis and the Pareto set is re-evaluated at full-year scale (Section 2.6). The candidates of a "
    "generation are evaluated in parallel. The code and the data needed to regenerate every figure and table are "
    "available at https://github.com/jodhernandezbe/hotdeep-galvanizing-op {hl:[confirm that the repository is public "
    "before submission]} (Supporting Information SI-1)."
)

(
    "A full simulated year takes about 3.6 s on the workstation used, whereas a year of 10{sup:6} pieces takes about "
    "0.09 s; the search therefore uses the shorter year. The fixed annual costs of the plant (capital charges and "
    "labor) do not scale with the number of pieces, so the objective values obtained during the search are not on the "
    "reporting basis and the Pareto set is re-evaluated at full-year scale (Section 2.6). The process and sustainability "
    "models, the optimization, and the generation of figures and tables are implemented in Python; the candidates of a "
    "generation are evaluated in parallel on the processor cores, and every checkpoint stores the population, its "
    "objectives and constraints, and the hypervolume history, so that post-processing does not require new "
    "simulations. The code, the pipeline commands, and the data needed to regenerate every figure and table are "
    "available at https://github.com/jodhernandezbe/hotdeep-galvanizing-op {hl:[confirm that the repository is public "
    "before submission]} (Supporting Information SI-1)."
)
FIG3_CAPTION = (
    "Figure 3. Evaluation of a candidate and search loop of the optimization. Each candidate is simulated for {i:N} = 100 "
    "random years that use common random numbers; the means over the years give its objectives and constraints; NSGA-II "
    "ranks and recombines the candidates until the termination test stops the search, and the feasible non-dominated "
    "set is the result. LHS = Latin hypercube sampling; SBX = simulated binary crossover."
)

SELECTION_1 = (
    "The feasible non-dominated designs of the final population were re-evaluated with 41,379,264 pieces per year, "
    "{i:N} = 100 years, and the same random numbers, and the designs that were no longer feasible at that scale were "
    "discarded. For each objective {i:k}, a linear fuzzy satisfaction membership between the nadir and the utopia "
    "values of the remaining set (Zimmermann, 1978) is defined as"
)
EQ7 = "{i:μ}{sub:k}({i:x}) = ({i:f}{sub:k}{sup:nadir} − {i:f}{sub:k}({i:x})) / ({i:f}{sub:k}{sup:nadir} − {i:f}{sub:k}{sup:utopia})"
SELECTION_2 = "and the compromise design is the one with the highest weighted additive membership"
EQ8 = "{i:μ}{sub:overall}({i:x}) = Σ{sub:k} {i:W}{sub:k} {i:μ}{sub:k}({i:x})"
SELECTION_3 = (
    "The weights {i:W}{sub:k} come from the FAHP category weights of the 2019 study: the weight of {i:U}{sub:P} is the sum "
    "of the efficiency, energy, and quality weights (0.607), the weight of COM is the economy weight (0.250), and the "
    "environment weight is split equally between {i:V}{sub:l-poll} and {i:V}{sub:WT} (0.072 each). Because {i:U}{sub:P} "
    "already integrates indicators of all categories, this mapping gives additional weight to the cost, liquid waste, "
    "and water objectives, and the Pareto set does not depend on the weights, only the selected design does. The "
    "sensitivity of the selection was therefore examined with three alternatives: weights taken from the individual "
    "indicators of the 2019 table (0.708 for {i:U}{sub:P}, 0.250 for COM, 0.018 for {i:V}{sub:l-poll}, and 0.024 for "
    "{i:V}{sub:WT}), equal weights, and 10,000 weight vectors drawn uniformly from the simplex, for which the share of "
    "vectors that select each design and the spread of the selected designs are reported."
)
SELECTION_4 = (
    "The cost of manufacture was calculated with the raw-material prices of the 2019 study (2016 to 2018; "
    "Hernandez-Betancur, 2018) except for ammonium hydroxide: in the original listing the price of the 30 wt% solution "
    "was derived from a price per litre and then used as a price per tonne, which understates it by about three orders "
    "of magnitude, so an industrial price per tonne was used instead (Table 4; Supporting Information SI-4). The "
    "prices of the 2019 study are marketplace quotes for small lots, whereas the available 2025 prices are bulk or "
    "export market values, so the comparison between scenarios mixes the passage of time with the purchasing scale; "
    "it is therefore used as a sensitivity analysis and not as a forecast. To test whether the selection depends on "
    "prices, the Pareto set was re-evaluated with the same random numbers under the 2025 prices (Table 4), and the "
    "compromise design, the cost saving with respect to the baseline, and the rank correlation (Spearman) of COM "
    "across the Pareto set were compared between scenarios. Because prices do not enter {i:U}{sub:P}, "
    "{i:V}{sub:l-poll}, or {i:V}{sub:WT}, only the cost objective changes."
)

(
    "The cost of manufacture was calculated with the prices of the 2019 study (2016 to 2018; Hernandez-Betancur, 2018) "
    "except for ammonium hydroxide: in the original listing the price of the 30 wt% solution was derived from a price "
    "per litre and then used as a price per tonne, which understates it by about three orders of magnitude, so an "
    "industrial price per tonne was used instead (Table 4; Supporting Information SI-4). To test whether the "
    "selection depends on prices, the Pareto set was re-evaluated with the same random numbers under a 2025 scenario "
    "(Table 4), and the compromise design, the cost saving with respect to the baseline, and the rank correlation "
    "(Spearman) of COM across the Pareto set were compared between scenarios. Because prices do not enter {i:U}{sub:P}, "
    "{i:V}{sub:l-poll}, or {i:V}{sub:WT}, only the cost objective changes."
)
TABLE4_CAPTION = (
    "Table 4. Raw-material prices of the cost scenarios (USD per tonne of the commercial product). Thesis = values of "
    "the 2019 study as written in the original listing; Corrected = thesis prices with the ammonium hydroxide unit "
    "corrected (scenario used in the search); 2025 = bulk-market prices of 2025: zinc from the LME annual average "
    "reported by the USGS (2026), NaOH from Argus Media (2025) quotes per dry tonne converted to a 50 wt% solution "
    "(× 0.5), ZnCl{sub:2}, NH{sub:4}Cl, and HCl from IMARC Group (2025, 2026a, 2026b), and NH{sub:4}OH from Intratec "
    "(2026). The IMARC and Intratec pages do not state the concentration or grade, so the HCl and NH{sub:4}OH values "
    "may differ from the cost per tonne of the 37 wt% and 30 wt% solutions of the thesis. Energy, water, labor, and "
    "fixed capital were not updated."
)

(
    "Table 4. Raw-material prices of the cost scenarios (USD per tonne of the commercial product). Thesis = values of "
    "the 2019 study as written in the original listing; Corrected = thesis prices with the ammonium hydroxide unit "
    "corrected (scenario used in the search); 2025 = market prices of 2025 expressed on the same basis (HCl rescaled "
    "from 31 to 37 wt%; NaOH rescaled from a dry-tonne to a 50 wt% solution basis). Energy, water, labor, and fixed "
    "capital were not updated. {hl:[Sources and the two basis conversions to be verified; see Supporting Information SI-4.]}"
)
TABLE4_HEADER = ["Raw material", "Thesis", "Corrected", "2025"]
TABLE4_ROWS = [
    ["Zinc, 99.9 wt%", "2,590", "2,590", "2,866"],
    ["ZnCl{sub:2}", "990", "990", "1,296"],
    ["NH{sub:4}Cl", "150", "150", "260"],
    ["HCl, 37 wt%", "165.5", "165.5", "244"],
    ["NaOH, 50 wt%", "580", "580", "185"],
    ["NH{sub:4}OH, 30 wt%", "38.11", "173", "173"],
]

[
    ["Zinc, 99.9 wt%", "2,590", "2,590", "2,867"],
    ["ZnCl{sub:2}", "990", "990", "1,296"],
    ["NH{sub:4}Cl", "150", "150", "260"],
    ["HCl, 37 wt%", "165.5", "165.5", "265.0"],
    ["NaOH, 50 wt%", "580", "580", "189.5"],
    ["NH{sub:4}OH, 30 wt%", "38.11", "173", "173"],
]

COMPARISON = (
    "The compromise design and the baseline design were each evaluated with 1,000 simulated years of 41,379,264 "
    "pieces under the same random numbers. For both designs, the means, standard deviations, and 95% confidence "
    "intervals of the mean (Student {i:t}) of {i:U}{sub:P} (as a percentage of {i:U}{sub:max}), COM, {i:V}{sub:l-poll}, "
    "{i:V}{sub:WT}, the coating thickness, and the defect fraction {i:φ}{sub:δ} are reported, together with "
    "{i:P}{sub:sustainable}. The scores of the 17 indicators and of the quality indicator, the distributions of the "
    "indicators of the critical stages (pickling and fluxing), and the density of {i:U}{sub:P} relative to the "
    "sustainability threshold are used to explain where the selected design differs from the baseline."
)

RESULTS_PLACEHOLDER = (
    "{hl:[To be written when the optimization has finished. Planned subsections: validation of the re-implemented model against "
    "the 2019 study; the Pareto set and its trade-offs (Figure 4); the compromise design and its sensitivity to weights "
    "and prices; baseline versus optimized design (indicator profile, critical-stage distributions, and probability of "
    "sustainability; Figures 5 to 7 and Table 5); limitations.]}"
)
CONCLUSIONS_PLACEHOLDER = "{hl:[To be written after the results.]}"

REFERENCES = [
    "Akamphon, S., Sukkasi, S., & Boonyongmaneerat, Y. (2012). Reduction of zinc consumption with enhanced corrosion protection in hot-dip galvanized coatings: A process-based cost analysis. {i:Resources, Conservation and Recycling}, {i:58}, 1–7. https://doi.org/10.1016/j.resconrec.2011.10.001",
    "Arguillarena, A., Margallo, M., Arruti-Fernández, A., Pinedo, J., Gómez, P., Ortiz, I., & Urtiaga, A. (2023). Circular economy in hot-dip galvanizing with zinc and iron recovery from spent pickling acids. {i:RSC Advances}, {i:13}(10), 6481–6489. https://doi.org/10.1039/d2ra08195d",
    "Arguillarena, A., Margallo, M., Irabien, Á., & Urtiaga, A. (2022). Life cycle assessment of zinc and iron recovery from spent pickling acids by membrane-based solvent extraction and electrowinning. {i:Journal of Environmental Management}, {i:318}, 115567. https://doi.org/10.1016/j.jenvman.2022.115567",
    "Argus Media. (2025). {i:Argus chlor-alkali and derivatives} (Issue 25-46, 14 November 2025). Argus Media group. https://view.argusmedia.com/rs/584-BUW-606/images/FER-20251114chlor-alkali.pdf",
    "Chang, D.-Y. (1996). Applications of the extent analysis method on fuzzy AHP. {i:European Journal of Operational Research}, {i:95}(3), 649–655. https://doi.org/10.1016/0377-2217(95)00300-2",
    "Costa, P., Altamirano, G., Salinas, A., González-González, D. S., & Goodwin, F. (2019). Optimization of the continuous galvanizing heat treatment process in ultra-high strength dual phase steels using a multivariate model. {i:Metals}, {i:9}(6), 703. https://doi.org/10.3390/met9060703",
    "Crișan, C. A., Timiș, E. C., & Vermeșan, H. (2023). PickT: A decision-making tool for the optimal pickling process operation. {i:Materials}, {i:16}(16), 5567. https://doi.org/10.3390/ma16165567",
    "Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. {i:IEEE Transactions on Evolutionary Computation}, {i:6}(2), 182–197. https://doi.org/10.1109/4235.996017",
    "Fresner, J., Schnitzer, H., Gwehenberger, G., Planasch, M., Brunner, C., Taferner, K., & Mair, J. (2007). Practical experiences with the implementation of the concept of zero emissions in the surface treatment industry in Austria. {i:Journal of Cleaner Production}, {i:15}(13–14), 1228–1239. https://doi.org/10.1016/j.jclepro.2006.07.024",
    "Hegyi, A., Păstrav, M., & Rus, M. (2015). Environmental and economic aspects of anticorrosion protection by hot-dip galvanized method rebars in concrete. {i:Journal of Applied Engineering Sciences}, {i:5}(1), 23–30. https://doi.org/10.1515/jaes-2015-0003",
    "Hernandez-Betancur, J. D., Hernandez, H. F., & Ocampo-Carmona, L. M. (2019). A holistic framework for assessing hot-dip galvanizing process sustainability. {i:Journal of Cleaner Production}, {i:206}, 755–766. https://doi.org/10.1016/j.jclepro.2018.09.177",
    "Hernandez-Betancur, J. D. (2018). {i:Detección de los puntos críticos del proceso de galvanizado por inmersión en caliente: un enfoque hacia la sostenibilidad y el desarrollo sostenible} [Master’s thesis, Universidad Nacional de Colombia]. https://repositorio.unal.edu.co/handle/unal/63201",
    "IMARC Group. (2026a). {i:Ammonium chloride price trend and forecast}. https://www.imarcgroup.com/ammonium-chloride-pricing-report",
    "IMARC Group. (2026b). {i:Hydrochloric acid price index, trend and forecast}. https://www.imarcgroup.com/hydrochloric-acid-pricing-report",
    "IMARC Group. (2025). {i:Zinc chloride prices in the USA stand at USD 1,296/MT amid stable industrial demand}. https://www.imarcgroup.com/news/zinc-chloride-price-index",
    "International Lead and Zinc Study Group. (2024). {i:The world zinc factbook 2024}. ILZSG. https://www.ilzsg.org/wp-content/uploads/SitePDFs/The%20World%20Zinc%20Factbook%202024.pdf",
    "International Organization for Standardization. (2009). {i:Hot dip galvanized coatings on fabricated iron and steel articles — Specifications and test methods} (ISO 1461:2009). ISO.",
    "Intratec. (2026). {i:Ammonium hydroxide prices worldwide}. https://www.intratec.us/chemical-markets/ammonium-hydroxide-price",
    "Kleywegt, A. J., Shapiro, A., & Homem-de-Mello, T. (2002). The sample average approximation method for stochastic discrete optimization. {i:SIAM Journal on Optimization}, {i:12}(2), 479–502. https://doi.org/10.1137/S1052623499363220",
    "Koch, G., Varney, J., Thompson, N., Moghissi, O., Gould, M., & Payer, J. (2016). {i:International measures of prevention, application, and economics of corrosion technologies study}. NACE International.",
    "Kong, G., & White, R. (2010). Toward cleaner production of hot dip galvanizing industry in China. {i:Journal of Cleaner Production}, {i:18}(10–11), 1092–1099. https://doi.org/10.1016/j.jclepro.2010.03.006",
    "Law, A. M. (2015). {i:Simulation modeling and analysis} (5th ed.). McGraw-Hill Education.",
    "Lobato, N. C. C., Villegas, E. A., & Mansur, M. B. (2015). Management of solid wastes from steelmaking and galvanizing processes: A brief review. {i:Resources, Conservation and Recycling}, {i:102}, 49–57. https://doi.org/10.1016/j.resconrec.2015.05.025",
    "Lorenz, M., Seitfudem, G., Randazzo, S., Gueccia, R., Gehring, F., & Prenzel, T. M. (2023). Combining membrane and zero brine technologies in waste acid treatment for a circular economy in the hot-dip galvanizing industry: A life cycle perspective. {i:Journal of Sustainable Metallurgy}, {i:9}(2), 537–549. https://doi.org/10.1007/s40831-023-00668-3",
    "McKay, M. D., Beckman, R. J., & Conover, W. J. (1979). Comparison of three methods for selecting values of input variables in the analysis of output from a computer code. {i:Technometrics}, {i:21}(2), 239–245. https://doi.org/10.1080/00401706.1979.10489755",
    "Reséndiz-Flores, E. O., Altamirano-Guerrero, G., Costa, P. S., Salas-Reyes, A. E., Salinas-Rodríguez, A., & Goodwin, F. (2021). Optimal design of hot-dip galvanized DP steels via artificial neural networks and multi-objective genetic optimization. {i:Metals}, {i:11}(4), 578. https://doi.org/10.3390/met11040578",
    "Ruiz-Mercado, G. J., Smith, R. L., & Gonzalez, M. A. (2012). Sustainability indicators for chemical processes: I. Taxonomy. {i:Industrial & Engineering Chemistry Research}, {i:51}(5), 2309–2328. https://doi.org/10.1021/ie102116e",
    "Smith, R. L., & Ruiz-Mercado, G. J. (2014). A method for decision making using sustainability indicators. {i:Clean Technologies and Environmental Policy}, {i:16}(4), 749–755. https://doi.org/10.1007/s10098-013-0684-5",
    "Tongpool, R., Jirajariyavech, A., Yuvaniyama, C., & Mungcharoen, T. (2010). Analysis of steel production in Thailand: Environmental impacts and solutions. {i:Energy}, {i:35}(10), 4192–4200. https://doi.org/10.1016/j.energy.2010.07.003",
    "U.S. Geological Survey. (2025). {i:Interior Department releases final 2025 list of critical minerals}. https://www.usgs.gov/news/science-snippet/interior-department-releases-final-2025-list-critical-minerals",
    "U.S. Geological Survey. (2026). Zinc. In {i:Mineral commodity summaries 2026}. https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-zinc.pdf",
    "Vyhmeister, E., Ruiz-Mercado, G. J., Torres, A. I., & Posada, J. A. (2018). Optimization of multi-pathway production chains and multi-criteria decision-making through sustainability evaluation: A biojet fuel production case study. {i:Clean Technologies and Environmental Policy}, {i:20}(7), 1697–1719. https://doi.org/10.1007/s10098-018-1576-5",
    "Wang, Y. (2018). Study on influence factors of zinc layer thickness via response surface method, Taguchi method and genetic algorithm. {i:Industrial Engineering & Management}, {i:7}(1). https://doi.org/10.4172/2169-0316.1000245",
    "World Steel Association. (2025). {i:December 2024 crude steel production and 2024 global crude steel production totals} [Press release]. https://worldsteel.org/media/press-releases/2025/december-2024-crude-steel-production-and-2024-global-totals/",
    "Zimmermann, H.-J. (1978). Fuzzy programming and linear programming with several objective functions. {i:Fuzzy Sets and Systems}, {i:1}(1), 45–55. https://doi.org/10.1016/0165-0114(78)90031-3",
    "Zitzler, E., & Thiele, L. (1999). Multiobjective evolutionary algorithms: A comparative case study and the strength Pareto approach. {i:IEEE Transactions on Evolutionary Computation}, {i:3}(4), 257–271. https://doi.org/10.1109/4235.797969",
]


def build() -> Path:
    """Assemble the document and save it.

    Returns:
        Path of the written .docx file.
    """
    doc = w.open_template()
    w.title(doc, TITLE)
    w.centered(doc, "Jose D. Hernandez-Betancur{sup:a,b}")
    w.centered(doc, "{sup:a} Faculty of Mines, Universidad Nacional de Colombia, Medellín 050041, Colombia", size_pt=10)
    w.centered(doc, "{sup:b} Department of Chemical Engineering, Universidad de Salamanca, Salamanca 37008, Spain", size_pt=10)
    w.centered(doc, "*Corresponding Author: jodhernandezbe@unal.edu.co", size_pt=10)
    w.heading(doc, "Abstract", 1, numbered=False)
    w.body(doc, ABSTRACT, indent=False)
    w.keywords(doc, KEYWORDS)
    w.heading(doc, "Introduction", 1, numbered=True)
    for paragraph in INTRODUCTION:
        w.body(doc, paragraph)
    w.heading(doc, "Methodology", 1, numbered=True)
    w.heading(doc, "Overview of the approach", 2, numbered=True)
    w.body(doc, OVERVIEW)
    w.figure(doc, FIGURES / "fig1_framework.png", 5.0)
    w.caption(doc, FIG1_CAPTION)
    w.heading(doc, "Process model and sources of uncertainty", 2, numbered=True)
    w.body(doc, PROCESS_1)
    w.figure(doc, FIGURES / "fig2_hdg_line.png", 6.4)
    w.caption(doc, FIG2_CAPTION)
    w.body(doc, PROCESS_2)
    w.body(doc, PROCESS_3)
    w.caption(doc, TABLE1_CAPTION)
    w.table(doc, TABLE1_HEADER, TABLE1_ROWS, [1.9, 2.1, 2.5], center_from=3)
    w.body(doc, MODES)
    w.heading(doc, "Sustainability assessment", 2, numbered=True)
    w.body(doc, GREENSCOPE_1)
    w.equation(doc, EQ1, 1)
    w.body(doc, GREENSCOPE_2, indent=False)
    w.equation(doc, EQ2, 2)
    w.body(doc, GREENSCOPE_3, indent=False)
    w.equation(doc, EQ3, 3)
    w.body(doc, GREENSCOPE_4, indent=False)
    w.heading(doc, "Optimization problem", 2, numbered=True)
    w.body(doc, DECISION_1)
    w.caption(doc, TABLE2_CAPTION)
    w.table(doc, TABLE2_HEADER, TABLE2_ROWS, [0.8, 3.1, 0.6, 1.1, 0.9], center_from=2)
    w.body(doc, OBJECTIVES)
    w.equation(doc, EQ4, 4)
    w.equation(doc, EQ5, 5)
    w.equation(doc, EQ6, 6)
    w.body(doc, CONSTRAINTS, indent=False)
    w.body(doc, EXPECTATIONS)
    w.heading(doc, "Search algorithm", 2, numbered=True)
    w.body(doc, SEARCH_1)
    w.caption(doc, TABLE3_CAPTION)
    w.table(doc, TABLE3_HEADER, TABLE3_ROWS, [2.4, 4.1], center_from=2)
    w.body(doc, SEARCH_2)
    w.figure(doc, FIGURES / "fig3_optimization_loop.png", 5.2)
    w.caption(doc, FIG3_CAPTION)
    w.heading(doc, "Compromise selection and sensitivity analyses", 2, numbered=True)
    w.body(doc, SELECTION_1)
    w.equation(doc, EQ7, 7)
    w.body(doc, SELECTION_2, indent=False)
    w.equation(doc, EQ8, 8)
    w.body(doc, SELECTION_3, indent=False)
    w.body(doc, SELECTION_4)
    w.caption(doc, TABLE4_CAPTION)
    w.table(doc, TABLE4_HEADER, TABLE4_ROWS, [2.6, 1.3, 1.3, 1.3], center_from=1)
    w.heading(doc, "Comparison of the baseline and the selected design", 2, numbered=True)
    w.body(doc, COMPARISON)
    w.heading(doc, "Results and discussion", 1, numbered=True)
    w.body(doc, RESULTS_PLACEHOLDER, indent=False)
    w.heading(doc, "Conclusions", 1, numbered=True)
    w.body(doc, CONCLUSIONS_PLACEHOLDER, indent=False)
    w.heading(doc, "References", 1, numbered=False)
    for entry in REFERENCES:
        w.reference(doc, entry)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT))
    logger.info("Wrote %s", OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build()
