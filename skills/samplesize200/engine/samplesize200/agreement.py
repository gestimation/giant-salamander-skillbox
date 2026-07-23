"""Chapter 20 binary agreement, kappa, and ICC sample-size methods."""

from __future__ import annotations

from math import ceil, isfinite, log, sqrt
from statistics import NormalDist
from typing import Any

from .schema_contract import consume_quantity, contracted


def _prob(name: str, value: float, *, closed: bool = False) -> float:
    value = float(value)
    ok = 0 <= value <= 1 if closed else 0 < value < 1
    if not isfinite(value) or not ok:
        interval = "[0, 1]" if closed else "(0, 1)"
        raise ValueError(f"{name} must be a finite probability in {interval}")
    return value


def _width(value: float) -> float:
    value = float(value)
    if not isfinite(value) or not 0 < value < 1:
        raise ValueError("width must be a finite full confidence-interval width in (0, 1)")
    return value


def _count(name: str, value: int, *, minimum: int = 1) -> int:
    if isinstance(value, bool) or int(value) != value or int(value) < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _z(confidence_level: float) -> tuple[float, float]:
    confidence = _prob("confidence_level", confidence_level)
    return confidence, NormalDist().inv_cdf((1 + confidence) / 2)


def _specimen_result(method: str, reference: str, inputs: dict[str, Any], raw: float,
                     *, ratings_per_specimen: int | None = None,
                     warnings: list[str] | None = None,
                     extra: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isfinite(raw) or raw <= 0:
        raise ValueError("inputs do not produce a finite positive specimen count")
    final = ceil(raw)
    result: dict[str, Any] = {
        "method_id": method, "formula_reference": reference, "inputs": inputs,
        "raw_total": raw, "rounded_total": final, "final_total": final,
        "raw_specimens": raw, "rounded_specimens": final, "final_specimens": final,
        "rounding_rule": "ceil the unrounded specimen count once after all formula terms",
        "warnings": list(warnings or ()), "provenance": None,
    }
    if ratings_per_specimen is not None:
        result.update({
            "raters_per_specimen": ratings_per_specimen,
            "final_raters": ratings_per_specimen,
            "final_total_ratings": final * ratings_per_specimen,
        })
    if extra:
        result.update(extra)
    return result


def disagreement_normal(*, disagreement_probability: float, width: float,
                         confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-001: symmetric normal interval, equations 20.2--20.4."""
    p = _prob("disagreement_probability", disagreement_probability)
    w = _width(width)
    confidence, z = _z(confidence_level)
    raw = 4 * p * (1 - p) * z * z / (w * w)
    warnings = ["normal interval can be inaccurate near probability boundaries"] if min(p, 1-p) < .1 else []
    return _specimen_result("AGREE-001", "equations 20.2, 20.3, and 20.4", {
        "disagreement_probability": p, "agreement_probability": 1-p,
        "width": w, "width_definition": "full CI width", "half_width": w/2,
        "confidence_level": confidence, "z_confidence": z,
    }, raw, ratings_per_specimen=2, warnings=warnings)


def disagreement_wilson(*, disagreement_probability: float, width: float,
                         confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-002: Wilson-type disagreement precision, equation 20.5."""
    p = _prob("disagreement_probability", disagreement_probability)
    w = _width(width)
    confidence, z = _z(confidence_level)
    omega = p * (1-p) / (w*w)
    radicand = (2*omega-1)**2 + 1/(w*w) - 1
    raw = ((2*omega-1) + sqrt(radicand)) * z*z
    return _specimen_result("AGREE-002", "equation 20.5", {
        "disagreement_probability": p, "agreement_probability": 1-p,
        "width": w, "width_definition": "full CI width", "half_width": w/2,
        "confidence_level": confidence, "z_confidence": z, "omega": omega,
    }, raw, ratings_per_specimen=2)


def within_rater_error_precision(*, error_probability: float, width: float,
                                  confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-003: within-rater error-probability precision, equations 20.6--20.9."""
    xi = _prob("error_probability", error_probability)
    if xi == .5:
        raise ValueError("error_probability=0.5 makes equation 20.9 singular")
    w = _width(width)
    confidence, z = _z(confidence_level)
    raw = (2*xi*(1-xi)*(1-2*xi*(1-xi)) / ((1-2*xi)**2*w*w)) * z*z
    return _specimen_result("AGREE-003", "equations 20.6, 20.7, 20.8, and 20.9", {
        "error_probability": xi, "width": w, "width_definition": "full CI width",
        "half_width": w/2, "confidence_level": confidence, "z_confidence": z,
    }, raw, extra={
        "raw_repeated_specimens": raw, "rounded_repeated_specimens": ceil(raw),
        "final_repeated_specimens": ceil(raw), "raters_per_specimen": 1,
        "final_raters": 1, "repetitions_per_specimen": 2,
        "raw_total_ratings": 2*raw, "final_total_ratings": 2*ceil(raw),
    })


def _design_constants(theta: float, xi: float, width: float, z: float) -> dict[str, float]:
    f = 2*xi*(1-xi)
    g = (2*f-f*f)/4
    h = theta*(1-theta) + f*(1-f)*(1-2*theta)**2
    b = g*(1-2*f)**2*width**2/(4*z*z)
    c = (h-g)*(1-2*f)**2*width**2/(4*z*z)
    d = (h-g)*f*(1-f)*(1-2*theta)**2/2
    e = h*(h-g) + f*(1-2*theta)**2*(g*(1-f)/2-h*(1-2*f))
    return {"F": f, "G": g, "H": h, "B": b, "C": c, "D": d, "E": e}


def _fixed_design_raw(repeated: float, c: dict[str, float]) -> float:
    denominator = c["C"]*repeated-c["D"]
    numerator = repeated*(c["E"]-c["B"]*repeated)
    if denominator <= 0 or numerator <= 0:
        raise ValueError("repeat count is outside the feasible domain of equation 20.13")
    return numerator/denominator


def two_stage_fixed(*, true_disagreement_probability: float, error_probability: float,
                    width: float, repeated_specimens: int,
                    confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-004: two-stage design for a fixed repeat count, equations 20.10--20.13."""
    theta = _prob("true_disagreement_probability", true_disagreement_probability)
    xi = _prob("error_probability", error_probability)
    if xi == .5:
        raise ValueError("error_probability=0.5 makes the design singular")
    w = _width(width); m = _count("repeated_specimens", repeated_specimens)
    confidence, z = _z(confidence_level)
    constants = _design_constants(theta, xi, w, z)
    raw_n = _fixed_design_raw(m, constants)
    final_n = max(ceil(raw_n), m)
    return _specimen_result("AGREE-004", "equations 20.10, 20.11, 20.12, and 20.13", {
        "true_disagreement_probability": theta, "error_probability": xi,
        "width": w, "width_definition": "full CI width", "half_width": w/2,
        "repeated_specimens": m, "confidence_level": confidence, "z_confidence": z,
    }, raw_n, extra={
        **constants, "raw_stage1_specimens": raw_n, "final_specimens": final_n,
        "final_total": final_n, "final_repeated_specimens": m,
        "final_nonrepeated_specimens": final_n-m, "raters_per_specimen": 2,
        "final_raters": 2,
        "repetitions_per_repeated_specimen": 2,
        "raw_total_ratings": 2*(raw_n+m), "final_total_ratings": 2*(final_n+m),
        "rounding_rule": "ceil N, require N>=m_repeat, then compute 2(N+m_repeat) ratings",
    })


def equal_repetition_design(*, true_disagreement_probability: float, error_probability: float,
                            width: float, confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-005: every specimen is rated twice by both raters, equation 20.14."""
    theta = _prob("true_disagreement_probability", true_disagreement_probability)
    xi = _prob("error_probability", error_probability)
    if xi == .5: raise ValueError("error_probability=0.5 makes equation 20.14 singular")
    w = _width(width); confidence,z = _z(confidence_level)
    f=2*xi*(1-xi)
    raw=4*(theta*(1-theta)*(1-2*f-2*f*f)+3*f*f/4)*z*z/(w*w*(1-2*f)**2)
    result=_specimen_result("AGREE-005", "equation 20.14", {
        "true_disagreement_probability":theta,"error_probability":xi,"width":w,
        "width_definition":"full CI width","half_width":w/2,
        "confidence_level":confidence,"z_confidence":z,
    },raw,extra={"F":f,"raw_repeated_specimens":raw,
        "rounded_repeated_specimens":ceil(raw),"final_repeated_specimens":ceil(raw),
        "final_nonrepeated_specimens":0,"raters_per_specimen":2,"final_raters":2,
        "repetitions_per_specimen":2,"raw_total_ratings":4*raw,
        "final_total_ratings":4*ceil(raw)})
    return result


def optimized_repetition_design(*, true_disagreement_probability: float,
                                error_probability: float, width: float,
                                confidence_level: float = .95,
                                minimum_repeats: int = 1, maximum_repeats: int = 10000) -> dict[str, Any]:
    """AGREE-006: integer rating-minimization design, equations 20.15 and 20.13."""
    theta=_prob("true_disagreement_probability",true_disagreement_probability)
    xi=_prob("error_probability",error_probability)
    if xi==.5: raise ValueError("error_probability=0.5 makes the design singular")
    w=_width(width); confidence,z=_z(confidence_level)
    lo=_count("minimum_repeats",minimum_repeats); hi=_count("maximum_repeats",maximum_repeats)
    if hi<lo: raise ValueError("maximum_repeats must be >= minimum_repeats")
    constants=_design_constants(theta,xi,w,z)
    b,c,d,e=(constants[x] for x in ("B","C","D","E"))
    rad_num=c*e-b*d; rad_den=c*d-b*d
    analytic=None
    if c!=0 and rad_num>=0 and rad_den>0:
        analytic=d/c*(1+sqrt(rad_num/rad_den))
    candidates=[]
    for m in range(lo,hi+1):
        try: raw_n=_fixed_design_raw(m,constants)
        except ValueError: continue
        n=max(ceil(raw_n),m); ratings=2*(n+m)
        candidates.append({"repeated_specimens":m,"raw_specimens":raw_n,
                           "final_specimens":n,"final_total_ratings":ratings})
    if not candidates: raise ValueError("no feasible integer design in the requested search range")
    chosen=min(candidates,key=lambda x:(x["final_total_ratings"],x["final_specimens"],x["repeated_specimens"]))
    result=_specimen_result("AGREE-006","equations 20.15 and 20.13",{
        "true_disagreement_probability":theta,"error_probability":xi,"width":w,
        "width_definition":"full CI width","half_width":w/2,
        "confidence_level":confidence,"z_confidence":z,
        "minimum_repeats":lo,"maximum_repeats":hi,
    },chosen["raw_specimens"],extra={**constants,"analytic_optimum_repeats":analytic,
        "selected_repeated_specimens":chosen["repeated_specimens"],
        "final_repeated_specimens":chosen["repeated_specimens"],
        "final_nonrepeated_specimens":chosen["final_specimens"]-chosen["repeated_specimens"],
        "final_specimens":chosen["final_specimens"],"final_total":chosen["final_specimens"],
        "raters_per_specimen":2,"final_raters":2,"repetitions_per_repeated_specimen":2,
        "raw_total_ratings":2*(chosen["raw_specimens"]+chosen["repeated_specimens"]),
        "final_total_ratings":chosen["final_total_ratings"],"candidate_designs":candidates,
        "search":{"type":"exhaustive integer","minimum":lo,"maximum":hi,
                  "feasible_candidates":len(candidates),"converged":True,
                  "tie_break":"fewest ratings, then specimens, then repeated specimens"},
        "lineage":{"calculation_type":"optimization","parent_method_id":"AGREE-004",
                   "transformation":"evaluate equation 20.13 for every feasible integer m and minimize 2(N+m)"}})
    return result


def cohen_kappa_ci(*, planned_kappa: float, disagreement_probability: float,
                   width: float, confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-007: Cohen-kappa confidence-interval precision, equations 20.16--20.18."""
    k=float(planned_kappa)
    if not isfinite(k) or not -1<k<1: raise ValueError("planned_kappa must be finite and in (-1, 1)")
    p=_prob("disagreement_probability",disagreement_probability); w=_width(width)
    confidence,z=_z(confidence_level)
    bracket=(1-k)*(1-2*k)+k*(2-k)/(2*p*(1-p))
    raw=4*(1-k)*bracket*z*z/(w*w)
    if raw<=0: raise ValueError("inputs are outside the positive-variance domain of equation 20.18")
    return _specimen_result("AGREE-007","equations 20.16, 20.17, and 20.18",{
        "planned_kappa":k,"disagreement_probability":p,"agreement_probability":1-p,
        "width":w,"width_definition":"full CI width","half_width":w/2,
        "confidence_level":confidence,"z_confidence":z,
    },raw,ratings_per_specimen=2,extra={"variance_bracket":bracket})


def icc_ci(*, planned_icc: float, raters: int, width: float,
           confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-008: ICC confidence-interval precision, equations 20.19--20.20."""
    rho=_prob("planned_icc",planned_icc); k=_count("raters",raters,minimum=2)
    w=_width(width); confidence,z=_z(confidence_level)
    raw=8*z*z*(1-rho)**2*(1+(k-1)*rho)**2/(k*(k-1)*w*w)+1
    return _specimen_result("AGREE-008","equations 20.19 and 20.20",{
        "planned_icc":rho,"icc_definition":"between variance / total variance",
        "raters":k,"width":w,"width_definition":"full CI width","half_width":w/2,
        "confidence_level":confidence,"z_confidence":z,
    },raw,ratings_per_specimen=k,extra={"final_raters":k})


def icc_ci_high_correction(*, planned_icc: float, raters: int = 2, width: float,
                           confidence_level: float = .95) -> dict[str, Any]:
    """AGREE-009: k=2, high-ICC correction, equation 20.21."""
    rho=_prob("planned_icc",planned_icc); k=_count("raters",raters,minimum=2)
    if k!=2: raise ValueError("equation 20.21 applies only when raters=2")
    if rho<.7: raise ValueError("equation 20.21 applies only when planned_icc>=0.7")
    parent=icc_ci(planned_icc=rho,raters=k,width=width,confidence_level=confidence_level)
    consumed=consume_quantity(parent,allowed_parent_methods={"AGREE-008"},key="raw_specimens",
                              quantity="specimens",unit="specimen",stage="raw")
    corrected=float(consumed["value"])+5*rho
    result=_specimen_result("AGREE-009","equation 20.21 applied to equation 20.20",{
        **parent["inputs"],"parent_method_id":"AGREE-008",
    },corrected,ratings_per_specimen=k,extra={"uncorrected_raw_specimens":consumed["value"],
        "correction_addend":5*rho,"final_raters":k})
    result["lineage"]={"calculation_type":"correction","parent_method_id":"AGREE-008",
        "consumed_result":consumed,"parent_primary_inputs":parent["inputs"],
        "parent_inference":{"confidence_level":parent["inputs"]["confidence_level"]},
        "transformation":"m_corrected = m_specimens + 5 * planned_icc",
        "child_outputs":[{"key":"raw_specimens","quantity":"specimens","unit":"specimen","stage":"raw"}],
        "parent_source_provenance":parent.get("source_provenance"),
        "parent_validation_evidence":parent.get("validation_evidence")}
    return result


def icc_hypothesis(*, null_icc: float, planned_icc: float, raters: int,
                   alpha: float = .05, power: float = .80, sides: int = 1) -> dict[str, Any]:
    """AGREE-010: ICC superiority hypothesis test, equations 20.22--20.23."""
    rho0=_prob("null_icc",null_icc); rho1=_prob("planned_icc",planned_icc)
    if rho1<=rho0: raise ValueError("planned_icc must be greater than null_icc")
    k=_count("raters",raters,minimum=2); alpha=_prob("alpha",alpha); power=_prob("power",power)
    if sides not in (1,2): raise ValueError("sides must be 1 or 2")
    za=NormalDist().inv_cdf(1-alpha/sides); zp=NormalDist().inv_cdf(power)
    c0=(1+k*rho0/(1-rho0))/(1+k*rho1/(1-rho1))
    raw=1+2*k*(za+zp)**2/((k-1)*log(c0)**2)
    return _specimen_result("AGREE-010","equations 20.22 and 20.23",{
        "null_icc":rho0,"planned_icc":rho1,"effect_direction":"planned_icc > null_icc",
        "raters":k,"alpha":alpha,"power":power,"sides":sides,
        "z_alpha":za,"z_power":zp,"C0":c0,
    },raw,ratings_per_specimen=k,extra={"final_raters":k})


disagreement_normal=contracted(disagreement_normal)
disagreement_wilson=contracted(disagreement_wilson)
within_rater_error_precision=contracted(within_rater_error_precision)
two_stage_fixed=contracted(two_stage_fixed)
equal_repetition_design=contracted(equal_repetition_design)
optimized_repetition_design=contracted(optimized_repetition_design)
cohen_kappa_ci=contracted(cohen_kappa_ci)
icc_ci=contracted(icc_ci)
icc_ci_high_correction=contracted(icc_ci_high_correction)
icc_hypothesis=contracted(icc_hypothesis)
