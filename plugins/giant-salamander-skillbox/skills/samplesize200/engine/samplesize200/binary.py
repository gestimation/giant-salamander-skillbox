"""Chapter 3 binary-outcome sample-size formulae."""

from __future__ import annotations

from math import ceil, isfinite, log, sqrt
from typing import Any

from .distributions import critical_values
from .rounding import allocation_rounding
from .schema_contract import contracted, consume_quantity, correction_lineage


def _proportion(name: str, value: float) -> None:
    if not isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be a finite number between 0 and 1 inclusive")


def _base_result(method_id: str, formula_reference: str, inputs: dict[str, Any], raw_total: float) -> dict[str, Any]:
    if not isfinite(raw_total) or raw_total <= 0:
        raise ValueError("inputs do not produce a positive finite sample size")
    return {
        "method_id": method_id,
        "formula_reference": formula_reference,
        "inputs": inputs,
        "raw_total": raw_total,
        "rounded_total": ceil(raw_total),
        "final_total": ceil(raw_total),
        "rounding_rule": "ceil the unrounded sample size",
        "warnings": [],
    }


def one_sample_proportion(*, planned_proportion: float, known_proportion: float,
                          alpha: float = 0.05, power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    _proportion("planned_proportion", planned_proportion)
    _proportion("known_proportion", known_proportion)
    if planned_proportion == known_proportion:
        raise ValueError("planned_proportion must differ from known_proportion for a finite sample size")
    z_alpha, z_power = critical_values(alpha, power, sides)
    numerator = (
        z_alpha * sqrt(known_proportion * (1.0 - known_proportion))
        + z_power * sqrt(planned_proportion * (1.0 - planned_proportion))
    ) ** 2
    raw_total = numerator / (planned_proportion - known_proportion) ** 2
    inputs = {
        "planned_proportion": planned_proportion, "known_proportion": known_proportion,
        "alpha": alpha, "power": power, "sides": sides,
        "z_alpha": z_alpha, "z_power": z_power,
    }
    return _base_result("ONE-001", "equation 3.6 (two-sided) / 3.7 (one-sided)", inputs, raw_total)


def two_sample_proportions(*, control_proportion: float, treatment_proportion: float,
                           allocation_ratio: float = 1.0, alpha: float = 0.05,
                           power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    _proportion("control_proportion", control_proportion)
    _proportion("treatment_proportion", treatment_proportion)
    if not isfinite(allocation_ratio) or allocation_ratio <= 0:
        raise ValueError("allocation_ratio must be a finite number greater than 0")
    delta = treatment_proportion - control_proportion
    if delta == 0:
        raise ValueError("control and treatment proportions must differ for a finite sample size")
    z_alpha, z_power = critical_values(alpha, power, sides)
    phi = allocation_ratio
    pooled = (control_proportion + phi * treatment_proportion) / (1.0 + phi)
    term_null = z_alpha * sqrt((1.0 + phi) * pooled * (1.0 - pooled))
    term_alt = z_power * sqrt(
        phi * control_proportion * (1.0 - control_proportion)
        + treatment_proportion * (1.0 - treatment_proportion)
    )
    raw_total = ((1.0 + phi) / phi) * (term_null + term_alt) ** 2 / delta ** 2
    inputs = {
        "control_proportion": control_proportion, "treatment_proportion": treatment_proportion,
        "allocation_ratio": phi, "alpha": alpha, "power": power, "sides": sides,
        "delta": delta, "pooled_proportion": pooled, "z_alpha": z_alpha, "z_power": z_power,
    }
    result = _base_result("TWO-001", "equations 3.2 and 3.3", inputs, raw_total)
    result.update(allocation_rounding(raw_total, phi))
    return result


def two_sample_odds_ratio(*, control_proportion: float, odds_ratio: float,
                          allocation_ratio: float = 1.0, alpha: float = 0.05,
                          power: float = 0.80, sides: int = 2) -> dict[str, Any]:
    _proportion("control_proportion", control_proportion)
    if control_proportion in (0.0, 1.0):
        raise ValueError("control_proportion must be strictly between 0 and 1 for an odds-ratio calculation")
    if not isfinite(odds_ratio) or odds_ratio <= 0:
        raise ValueError("odds_ratio must be a finite number greater than 0")
    if odds_ratio == 1:
        raise ValueError("odds_ratio must differ from 1 for a finite sample size")
    if not isfinite(allocation_ratio) or allocation_ratio <= 0:
        raise ValueError("allocation_ratio must be a finite number greater than 0")
    z_alpha, z_power = critical_values(alpha, power, sides)
    phi = allocation_ratio
    treatment = odds_ratio * control_proportion / (1.0 - control_proportion + odds_ratio * control_proportion)
    pooled = (control_proportion + phi * treatment) / (1.0 + phi)
    raw_total = ((1.0 + phi) ** 2 / phi) * (z_alpha + z_power) ** 2 / (
        log(odds_ratio) ** 2 * pooled * (1.0 - pooled)
    )
    inputs = {
        "control_proportion": control_proportion, "odds_ratio": odds_ratio,
        "treatment_proportion": treatment, "allocation_ratio": phi,
        "alpha": alpha, "power": power, "sides": sides,
        "delta": treatment - control_proportion, "pooled_proportion": pooled,
        "z_alpha": z_alpha, "z_power": z_power,
    }
    result = _base_result("TWO-002", "equations 3.1, 3.3, and 3.4", inputs, raw_total)
    result.update(allocation_rounding(raw_total, phi))
    return result


def fisher_exact_correction(base_result: dict[str, Any]) -> dict[str, Any]:
    if base_result.get("method_id") not in {"TWO-001", "TWO-002"}:
        raise ValueError("TWO-003 requires a TWO-001 or TWO-002 base result")
    consumed = consume_quantity(
        base_result, allowed_parent_methods={"TWO-001", "TWO-002"},
        key="raw_total", quantity="participants", unit="participants", stage="raw",
    )
    base_inputs = base_result.get("inputs", {})
    phi = float(base_inputs["allocation_ratio"])
    delta = abs(float(base_inputs["delta"]))
    if delta == 0:
        raise ValueError("base result must have a nonzero planned difference")
    raw_control = float(base_result["raw_total"]) / (1.0 + phi)
    corrected_control = raw_control * (
        1.0 + sqrt(1.0 + 2.0 * (1.0 + phi) / (phi * raw_control * delta))
    ) ** 2 / 4.0
    raw_total = corrected_control * (1.0 + phi)
    result = _base_result(
        "TWO-003", "equation 3.5",
        {"base_method_id": base_result["method_id"], "base_raw_total": base_result["raw_total"],
         "allocation_ratio": phi, "delta": base_inputs["delta"]}, raw_total,
    )
    result.update(allocation_rounding(raw_total, phi))
    result["lineage"] = correction_lineage(
        parent_result=base_result,
        consumed=consumed,
        transformation="equation 3.5 Fisher exact-test sample-size correction",
        child_outputs=[
            {"key": "raw_total", "quantity": "participants", "unit": "participants", "stage": "raw"},
            {"key": "final_total", "quantity": "participants", "unit": "participants", "stage": "final"},
        ],
    )
    if result["final_total"] < base_result["final_total"]:
        raise AssertionError("Fisher correction cannot reduce final sample size")
    return result


one_sample_proportion = contracted(one_sample_proportion)
two_sample_proportions = contracted(two_sample_proportions)
two_sample_odds_ratio = contracted(two_sample_odds_ratio)
fisher_exact_correction = contracted(fisher_exact_correction)
