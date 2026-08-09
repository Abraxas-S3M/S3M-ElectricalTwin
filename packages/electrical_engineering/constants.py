"""Numeric constants derived from published electrical engineering standards.

This module contains NUMERIC VALUES ONLY. It deliberately does not reproduce,
paraphrase or summarise the normative text of any standard. Each value carries
a ``# Source:`` comment naming the standard designation it was transcribed
from so that it can be independently checked against that standard.

WARNING -- INDEPENDENT VERIFICATION REQUIRED
    Every value in this module is a convenience transcription and MUST be
    independently verified against the current published edition of the cited
    standard by a licensed professional engineer before it is relied upon for
    any customer deployment, design decision, protection setting or safety
    determination. Standards are revised; transcriptions can be wrong; defaults
    vary by equipment. Nothing here constitutes engineering advice, and no
    warranty of fitness or correctness is expressed or implied.
"""

from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Mathematical constants
# ---------------------------------------------------------------------------

SQRT3: float = 1.7320508075688772  # Source: mathematical constant sqrt(3)


# ---------------------------------------------------------------------------
# IEC 61000-4-30 -- power quality event thresholds (residual voltage in per
# unit of the declared/nominal voltage; durations in seconds).
# ---------------------------------------------------------------------------

# A voltage sag (dip) has a residual voltage inside this closed interval.
SAG_RESIDUAL_VOLTAGE_LOWER_PU: float = 0.1  # Source: IEC 61000-4-30
SAG_RESIDUAL_VOLTAGE_UPPER_PU: float = 0.9  # Source: IEC 61000-4-30

# A voltage swell has a voltage strictly above this value.
SWELL_VOLTAGE_PU: float = 1.1  # Source: IEC 61000-4-30

# An interruption has a voltage strictly below this value.
INTERRUPTION_VOLTAGE_PU: float = 0.1  # Source: IEC 61000-4-30

# Boundary between a short and a long interruption (3 minutes).
INTERRUPTION_SHORT_LONG_BOUNDARY_SECONDS: float = 180.0  # Source: IEC 61000-4-30


# ---------------------------------------------------------------------------
# IEEE 519 -- harmonic limits.
# ---------------------------------------------------------------------------

# Voltage total harmonic distortion limits (percent of nominal), keyed by a
# label for the system voltage class bucket. Bucket bounds are line-to-line
# RMS voltage in volts, interpreted as lower < V <= upper.
VOLTAGE_DISTORTION_THD_LIMIT_PERCENT: dict[str, float] = {
    "V_LE_1KV": 8.0,  # Source: IEEE 519
    "V_1KV_TO_69KV": 5.0,  # Source: IEEE 519
    "V_69KV_TO_161KV": 2.5,  # Source: IEEE 519
    "V_GT_161KV": 1.5,  # Source: IEEE 519
}

# Voltage class bucket boundaries in volts (line-to-line RMS). Each tuple is
# (exclusive_lower_bound, inclusive_upper_bound, bucket_label). math.inf marks
# the open top bucket.
VOLTAGE_CLASS_BOUNDS_V: tuple[tuple[float, float, str], ...] = (
    (0.0, 1_000.0, "V_LE_1KV"),  # Source: IEEE 519
    (1_000.0, 69_000.0, "V_1KV_TO_69KV"),  # Source: IEEE 519
    (69_000.0, 161_000.0, "V_69KV_TO_161KV"),  # Source: IEEE 519
    (161_000.0, math.inf, "V_GT_161KV"),  # Source: IEEE 519
)

# Current total demand distortion (TDD) limits (percent), by short-circuit
# ratio bracket Isc/IL, for the lowest voltage class (120 V through 69 kV).
# Each tuple is (exclusive_lower_scr, inclusive_upper_scr, tdd_percent).
# Higher voltage classes have stricter limits and must be looked up separately
# against the standard.
CURRENT_TDD_LIMIT_PERCENT_BY_SCR: tuple[tuple[float, float, float], ...] = (
    (0.0, 20.0, 5.0),  # Source: IEEE 519
    (20.0, 50.0, 8.0),  # Source: IEEE 519
    (50.0, 100.0, 12.0),  # Source: IEEE 519
    (100.0, 1_000.0, 15.0),  # Source: IEEE 519
    (1_000.0, math.inf, 20.0),  # Source: IEEE 519
)


# ---------------------------------------------------------------------------
# NEMA MG-1 -- polyphase motor derating as a function of percent voltage
# unbalance. Each tuple is (percent_voltage_unbalance, derating_factor).
# Continuous operation above 5 percent unbalance is not recommended.
# ---------------------------------------------------------------------------

MOTOR_VOLTAGE_UNBALANCE_DERATING: tuple[tuple[float, float], ...] = (
    (0.0, 1.00),  # Source: NEMA MG-1
    (1.0, 0.98),  # Source: NEMA MG-1
    (2.0, 0.95),  # Source: NEMA MG-1
    (3.0, 0.88),  # Source: NEMA MG-1
    (4.0, 0.82),  # Source: NEMA MG-1
    (5.0, 0.75),  # Source: NEMA MG-1
)


# ---------------------------------------------------------------------------
# IEEE C57.91 -- liquid-immersed transformer thermal model constants. Values
# below are representative defaults for a 65 degrees C average-winding-rise
# unit; actual values are equipment specific and taken from test reports.
# ---------------------------------------------------------------------------

# Top-oil temperature rise over ambient at rated load (degrees C).
TRANSFORMER_TOP_OIL_RISE_OVER_AMBIENT_C: float = 55.0  # Source: IEEE C57.91

# Winding hot-spot temperature rise over top-oil at rated load (degrees C).
TRANSFORMER_HOT_SPOT_RISE_OVER_TOP_OIL_C: float = 25.0  # Source: IEEE C57.91

# Oil thermal time constant at rated load (minutes).
TRANSFORMER_OIL_TIME_CONSTANT_MINUTES: float = 180.0  # Source: IEEE C57.91

# Winding thermal time constant (minutes).
TRANSFORMER_WINDING_TIME_CONSTANT_MINUTES: float = 5.0  # Source: IEEE C57.91

# Reference hottest-spot temperature at which the per-unit insulation ageing
# acceleration factor equals 1.0 (degrees C, 65 degrees C rise insulation).
TRANSFORMER_REFERENCE_HOT_SPOT_TEMPERATURE_C: float = 110.0  # Source: IEEE C57.91


# ---------------------------------------------------------------------------
# ITIC (CBEMA) Curve -- equipment voltage tolerance envelope. Each point is a
# (duration_seconds, voltage_pu) tuple where voltage is per unit of nominal
# RMS voltage. ITIC_UPPER is the upper (prohibited-region) boundary and
# ITIC_LOWER is the lower (no-damage / no-interruption-in-function) boundary.
# math.inf marks the steady-state (indefinite duration) end of each envelope.
# ---------------------------------------------------------------------------

ITIC_UPPER: tuple[tuple[float, float], ...] = (
    (0.00002, 5.00),  # Source: ITIC (CBEMA) Curve
    (0.001, 2.00),  # Source: ITIC (CBEMA) Curve
    (0.003, 1.40),  # Source: ITIC (CBEMA) Curve
    (0.5, 1.20),  # Source: ITIC (CBEMA) Curve
    (10.0, 1.10),  # Source: ITIC (CBEMA) Curve
    (math.inf, 1.10),  # Source: ITIC (CBEMA) Curve
)

ITIC_LOWER: tuple[tuple[float, float], ...] = (
    (0.00002, 0.00),  # Source: ITIC (CBEMA) Curve
    (0.02, 0.00),  # Source: ITIC (CBEMA) Curve
    (0.02, 0.70),  # Source: ITIC (CBEMA) Curve
    (0.5, 0.70),  # Source: ITIC (CBEMA) Curve
    (0.5, 0.80),  # Source: ITIC (CBEMA) Curve
    (10.0, 0.80),  # Source: ITIC (CBEMA) Curve
    (10.0, 0.90),  # Source: ITIC (CBEMA) Curve
    (math.inf, 0.90),  # Source: ITIC (CBEMA) Curve
)
