"""Compound and stream indexing for the GREENSCOPE mass-balance matrices.

Purpose: name the columns (compounds) and rows (streams) of the input/output stream matrices.
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from enum import IntEnum


class Compound(IntEnum):
    """Column index (0-based) of each compound in the stream matrices."""

    STEEL = 0
    TRIGLYCERIDE = 1
    WUSTITE = 2
    SODIUM_HYDROXIDE = 3
    WATER = 4
    GLYCEROL = 5
    SODIUM_CARBOXYLATES = 6
    HYDROCHLORIC_ACID = 7
    IRON_DICHLORIDE = 8
    ZINC = 9
    ZINC_DICHLORIDE = 10
    AMMONIUM_CHLORIDE = 11
    AMMONIUM_HYDROXIDE = 12
    ZINC_HYDROXIDE = 13
    FERROUS_HYDROXIDE = 14
    DROSS = 15
    ASH = 16


class InputStream(IntEnum):
    """Row index (0-based) of each input stream."""

    STEEL_PIECE = 0
    DEGREASING_SOLUTION = 1
    DEGREASING_WATER = 2
    RINSING_1_WATER = 3
    PICKLING_SOLUTION = 4
    PICKLING_WATER = 5
    RINSING_2_WATER = 6
    FLUXING_SALTS = 7
    FLUXING_WATER = 8
    FLUXING_NH4OH = 9
    FLUXING_HCL = 10
    MOLTEN_ZINC = 11


class OutputStream(IntEnum):
    """Row index (0-based) of each output stream."""

    SPENT_DEGREASING = 0
    REMAINING_GREASE = 1
    RINSING_1_WASTEWATER = 2
    SPENT_PICKLING = 3
    RINSING_2_WASTEWATER = 4
    SPENT_FLUXING = 5
    HYDROXIDE_SLUDGE = 6
    DROSS = 7
    ASH = 8
    GALVANIZED_STEEL = 9


class UnitProcess(IntEnum):
    """Index (0-based) of each unit process in the energy vector and indicator matrices."""

    DEGREASING = 0
    RINSING_1 = 1
    PICKLING = 2
    RINSING_2 = 3
    FLUXING = 4
    DRYING = 5
    GALVANIZING = 6


N_COMPOUNDS = len(Compound)
N_INPUT_STREAMS = len(InputStream)
N_OUTPUT_STREAMS = len(OutputStream)
N_UNIT_PROCESSES = len(UnitProcess)
N_INDICATORS = 17
