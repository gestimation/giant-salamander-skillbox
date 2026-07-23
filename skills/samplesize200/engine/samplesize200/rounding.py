"""Auditable rounding and allocation-block adjustment."""

from fractions import Fraction
from math import ceil, isfinite


def _smallest_ratio_consistent_with_input(value: float) -> Fraction:
    """Infer the smallest integer ratio consistent with displayed precision.

    For example, 0.4286 is a four-decimal representation of 3/7, not a request
    for an impractical 2143:5000 allocation block.
    """
    if not isfinite(value) or value <= 0:
        raise ValueError("allocation_ratio must be a finite number greater than 0")
    text = str(value).lower()
    if "e" in text:
        tolerance = max(abs(value) * 1e-12, 1e-15)
    else:
        decimals = len(text.partition(".")[2])
        tolerance = 0.5 * 10 ** (-decimals) if decimals else 0.0
    for denominator in range(1, 10_001):
        numerator = max(1, round(value * denominator))
        candidate = Fraction(numerator, denominator)
        if abs(float(candidate) - value) <= tolerance:
            return candidate
    return Fraction(str(value)).limit_denominator(10_000)


def allocation_block(allocation_ratio: float) -> tuple[int, int]:
    """Return the smallest control:treatment integer block for treatment/control."""
    ratio = _smallest_ratio_consistent_with_input(allocation_ratio)
    return ratio.denominator, ratio.numerator


def allocation_rounding(raw_total: float, allocation_ratio: float) -> dict[str, int | float | str]:
    """Round N where allocation_ratio is treatment/control.

    The simple group ceilings are retained separately. The final allocation uses
    the smallest rational block (denominator:numerator) inferred from the input.
    """
    if not isfinite(allocation_ratio) or allocation_ratio <= 0:
        raise ValueError("allocation_ratio must be a finite number greater than 0")
    raw_control = raw_total / (1.0 + allocation_ratio)
    raw_treatment = allocation_ratio * raw_control
    rounded_control = ceil(raw_control)
    rounded_treatment = ceil(raw_treatment)
    control_block, treatment_block = allocation_block(allocation_ratio)
    blocks = ceil(max(raw_control / control_block, raw_treatment / treatment_block))
    final_control = blocks * control_block
    final_treatment = blocks * treatment_block
    return {
        "raw_group_control": raw_control,
        "raw_group_treatment": raw_treatment,
        "rounded_total": ceil(raw_total),
        "rounded_group_control": rounded_control,
        "rounded_group_treatment": rounded_treatment,
        "final_group_control": final_control,
        "final_group_treatment": final_treatment,
        "final_total": final_control + final_treatment,
        "rounding_rule": (
            "ceil raw total; ceil each raw group separately; final values use the "
            f"smallest inferred allocation block {control_block}:{treatment_block}"
        ),
    }
