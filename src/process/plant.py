"""State of the hot-dip galvanizing line: baths, their renewal ledgers and the yearly accumulators.

Purpose: replace the dozens of loose MATLAB variables of the HDG simulation by small cohesive objects (annex D.3).
Author: Jose D. Hernandez-Betancur
Date: 2026-10-02
"""

from dataclasses import dataclass, field

import numpy as np

from src.process.initial_conditions import BathInitialCondition
from src.process.operating_policy import OperatingPolicy


@dataclass
class BathLedger:
    """Mass and composition of the batches of a bath that entered and left service during the year.

    Compositions are accumulated as sums of the % wt vectors; average them with the batch counts.
    """

    initial_mass_kg: float
    initial_composition_sum: np.ndarray
    n_initial: int = 1
    final_mass_kg: float = 0.0
    final_composition_sum: np.ndarray = field(default_factory=lambda: np.zeros(0))
    n_final: int = 0

    def __post_init__(self) -> None:
        """Size the final composition accumulator like the initial one."""
        self.initial_composition_sum = np.array(self.initial_composition_sum, dtype=float)
        self.final_composition_sum = np.zeros_like(self.initial_composition_sum)

    def commission(self, mass_kg: float, composition_wt: np.ndarray) -> None:
        """Register a fresh batch entering service.

        Args:
            mass_kg: Batch mass [kg].
            composition_wt: Batch composition [% wt].
        """
        self.initial_mass_kg += mass_kg
        self.initial_composition_sum += composition_wt
        self.n_initial += 1

    def retire(self, mass_kg: float, composition_wt: np.ndarray) -> None:
        """Register a batch leaving service.

        Args:
            mass_kg: Batch mass [kg].
            composition_wt: Batch composition [% wt].
        """
        self.final_mass_kg += mass_kg
        self.final_composition_sum += composition_wt
        self.n_final += 1

    @property
    def mean_initial_composition_wt(self) -> np.ndarray:
        """Average composition of the fresh batches [% wt]."""
        return self.initial_composition_sum / self.n_initial

    @property
    def mean_final_composition_wt(self) -> np.ndarray:
        """Average composition of the spent batches [% wt]."""
        return self.final_composition_sum / self.n_final


@dataclass
class Bath:
    """A process tank with its current content and its ledger."""

    mass_kg: float
    composition_wt: np.ndarray
    volume_m3: float
    temperature_c: float
    ledger: BathLedger
    ph: float | None = None
    last_heat_j: float = 0.0
    capacity_m3: float | None = None

    @classmethod
    def from_initial_condition(cls, initial: BathInitialCondition, temperature_c: float) -> "Bath":
        """Create a bath from a fresh batch.

        Args:
            initial: Fresh batch description.
            temperature_c: Temperature to use when the batch does not define one [degC].

        Returns:
            New bath whose ledger holds the first batch.
        """
        temperature = initial.temperature_c if initial.temperature_c is not None else temperature_c
        return cls(
            mass_kg=initial.mass_kg,
            composition_wt=np.array(initial.composition_wt, dtype=float),
            volume_m3=initial.volume_m3,
            temperature_c=temperature,
            ledger=BathLedger(initial.mass_kg, initial.composition_wt),
            ph=initial.ph,
            capacity_m3=initial.volume_m3,
        )

    def retire(self) -> None:
        """Send the current batch to the spent ledger."""
        self.ledger.retire(self.mass_kg, self.composition_wt)

    def renew(self, initial: BathInitialCondition, temperature_c: float, keep_ph: bool = False) -> None:
        """Retire the current batch and put a fresh one in service.

        Args:
            initial: Fresh batch description.
            temperature_c: Temperature to use when the batch does not define one [degC].
            keep_ph: Keep the previous pH value instead of taking the fresh batch's.
        """
        self.retire()
        self.mass_kg = initial.mass_kg
        self.composition_wt = np.array(initial.composition_wt, dtype=float)
        self.volume_m3 = initial.volume_m3
        self.temperature_c = initial.temperature_c if initial.temperature_c is not None else temperature_c
        self.ph = self.ph if keep_ph or initial.ph is None else initial.ph
        self.last_heat_j = 0.0
        self.capacity_m3 = initial.volume_m3
        self.ledger.commission(initial.mass_kg, initial.composition_wt)

    def bleed_to(self, capacity_m3: float) -> np.ndarray:
        """Withdraw the excess over the tank capacity, keeping the composition.

        Args:
            capacity_m3: Physical volume the tank can hold [m3].

        Returns:
            Component masses withdrawn [kg], zeros when the bath fits in the tank.
        """
        if self.volume_m3 <= capacity_m3:
            return np.zeros_like(self.composition_wt)
        bled_kg = self.mass_kg * (1 - capacity_m3 / self.volume_m3)
        self.mass_kg -= bled_kg
        self.volume_m3 = capacity_m3
        return 0.01 * self.composition_wt * bled_kg

    def mix_in(self, mass_kg: float, composition_wt: np.ndarray) -> None:
        """Add dragged-out solution to the bath, mixing compositions by mass.

        Args:
            mass_kg: Mass added [kg].
            composition_wt: Composition of the added solution [% wt].
        """
        total_kg = self.mass_kg + mass_kg
        self.composition_wt = (self.composition_wt * self.mass_kg + composition_wt * mass_kg) / total_kg
        self.mass_kg = total_kg


@dataclass
class LineTotals:
    """Yearly accumulators of the line (all masses in kg, heats in J)."""

    steel_kg: float = 0.0
    rust_kg: float = 0.0
    grease_and_oil_kg: float = 0.0
    grease_mw_sum: float = 0.0
    n_lots: int = 0
    steel_surface_kg: float = 0.0
    saponified_kg: float = 0.0
    remaining_grease_kg: float = 0.0
    zinc_coating_kg: float = 0.0
    dross_kg: float = 0.0
    ash_kg: float = 0.0
    molten_zinc_kg: float = 0.0
    hcl_added_kg: float = 0.0
    nh4oh_added_kg: float = 0.0
    quality_mass_weighted: float = 0.0
    standard_thickness_sum_um: float = 0.0
    n_quality_pieces: int = 0
    n_defective_pieces: int = 0
    thickness_sum_um: float = 0.0
    peak_pickling_fe2_g_per_l: float = 0.0
    peak_fluxing_fe2_g_per_l: float = 0.0
    degreasing_heat_j: float = 0.0
    fluxing_heat_j: float = 0.0
    drying_heat_j: float = 0.0
    galvanizing_heat_j: float = 0.0


@dataclass
class Plant:
    """All tanks of the line plus the yearly accumulators."""

    degreasing: Bath
    rinse_1: Bath
    normal_pickling: Bath
    abnormal_pickling: Bath
    rinse_2: Bath
    fluxing: Bath
    zinc_bath_temperature_c: float
    zinc_bath_mass_kg: float
    preserve_thesis_quirks: bool = True
    policy: OperatingPolicy | None = None
    renewal_rng: np.random.Generator | None = None
    totals: LineTotals = field(default_factory=LineTotals)
    fluxing_bleed_kg: np.ndarray = field(default_factory=lambda: np.zeros(9))
