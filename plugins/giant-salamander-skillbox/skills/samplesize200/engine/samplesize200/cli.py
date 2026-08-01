"""JSON command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .binary import fisher_exact_correction, one_sample_proportion, two_sample_odds_ratio, two_sample_proportions
from .continuous import (
    one_sample_mean, two_sample_mean_exact, two_sample_mean_guenther,
    two_sample_mean_satterthwaite, wmw_efficiency, wmw_superiority,
)
from .rates import (
    adverse_event_observation, known_background_increase, matched_case_control,
    two_group_negative_binomial_rates, two_group_poisson_rates,
    unknown_background_comparison,
)
from .ordinal import (
    equal_category_approximation, mann_whitney_nonproportional,
    many_category_approximation, proportional_odds,
)
from .paired import (
    discordant_count_conversion, matched_case_control_correction, mcnemar_direct,
    paired_continuous_normal, paired_continuous_t, paired_ordinal_binary,
    paired_ordinal_compromise, paired_ordinal_signed_rank,
)
from .confidence import (
    finite_population_correction, one_proportion_normal_absolute,
    one_mean_absolute, one_mean_relative, one_proportion_normal_relative,
    one_proportion_wilson, paired_mean_difference, paired_proportion_difference,
    two_mean_difference, two_proportion_normal_difference,
    two_proportion_odds_ratio_relative, two_proportion_wilson_difference,
)
from .longitudinal import repeated_post_mean, repeated_slope, repeated_weighted_contrast
from .survival import events_to_participants, freedman_events, schoenfeld_events
from .competing import (
    cause_specific_hazard_competing_risk, subdistribution_accrual_integration,
    subdistribution_fixed_censoring,
)
from .correlation import (
    correlation_detection, pearson_ci_initial, pearson_ci_refined,
    spearman_ci_initial, spearman_ci_refined,
)
from .agreement import (
    disagreement_normal, disagreement_wilson, within_rater_error_precision,
    two_stage_fixed, equal_repetition_design, optimized_repetition_design,
    cohen_kappa_ci, icc_ci, icc_ci_high_correction, icc_hypothesis,
)
from .diagnostics import (
    normal_reference_interval_precision, rank_reference_interval_precision,
    single_accuracy_large_sample, single_accuracy_exact,
    independent_accuracy_comparison, paired_accuracy_comparison, roc_auc_ci_width,
)


METHODS = {
    "ONE-001": one_sample_proportion,
    "TWO-001": two_sample_proportions,
    "TWO-002": two_sample_odds_ratio,
    "ONE-002": one_sample_mean,
    "TWO-008": two_sample_mean_exact,
    "TWO-009": two_sample_mean_guenther,
    "TWO-010": two_sample_mean_satterthwaite,
    "TWO-011": wmw_efficiency,
    "TWO-012": wmw_superiority,
    "ONE-003": adverse_event_observation,
    "ONE-004": known_background_increase,
    "TWO-013": two_group_poisson_rates,
    "TWO-014": two_group_negative_binomial_rates,
    "TWO-015": unknown_background_comparison,
    "TWO-016": matched_case_control,
    "TWO-004": proportional_odds,
    "TWO-005": equal_category_approximation,
    "TWO-006": many_category_approximation,
    "TWO-007": mann_whitney_nonproportional,
    "TWO-023": mcnemar_direct,
    "TWO-024": discordant_count_conversion,
    "TWO-025": matched_case_control_correction,
    "TWO-026": paired_ordinal_signed_rank,
    "TWO-027": paired_ordinal_binary,
    "TWO-028": paired_ordinal_compromise,
    "TWO-029": paired_continuous_normal,
    "TWO-030": paired_continuous_t,
    "CI-001": one_proportion_normal_absolute,
    "CI-002": one_proportion_normal_relative,
    "CI-003": one_proportion_wilson,
    "CI-004": finite_population_correction,
    "CI-005": two_proportion_normal_difference,
    "CI-006": two_proportion_wilson_difference,
    "CI-007": two_proportion_odds_ratio_relative,
    "CI-008": paired_proportion_difference,
    "CI-009": one_mean_absolute,
    "CI-010": one_mean_relative,
    "CI-011": two_mean_difference,
    "CI-012": paired_mean_difference,
    "TWO-031": repeated_post_mean,
    "TWO-032": repeated_slope,
    "TWO-033": repeated_weighted_contrast,
    "TWO-017": schoenfeld_events,
    "TWO-018": freedman_events,
    "TWO-019": events_to_participants,
    "TWO-020": cause_specific_hazard_competing_risk,
    "TWO-021": subdistribution_fixed_censoring,
    "TWO-022": subdistribution_accrual_integration,
    "CORR-001": correlation_detection,
    "CORR-002": pearson_ci_initial,
    "CORR-003": pearson_ci_refined,
    "CORR-004": spearman_ci_initial,
    "CORR-005": spearman_ci_refined,
    "AGREE-001": disagreement_normal,
    "AGREE-002": disagreement_wilson,
    "AGREE-003": within_rater_error_precision,
    "AGREE-004": two_stage_fixed,
    "AGREE-005": equal_repetition_design,
    "AGREE-006": optimized_repetition_design,
    "AGREE-007": cohen_kappa_ci,
    "AGREE-008": icc_ci,
    "AGREE-009": icc_ci_high_correction,
    "AGREE-010": icc_hypothesis,
    "DIAG-001": normal_reference_interval_precision,
    "DIAG-002": rank_reference_interval_precision,
    "DIAG-003": single_accuracy_large_sample,
    "DIAG-004": single_accuracy_exact,
    "DIAG-005": independent_accuracy_comparison,
    "DIAG-006": paired_accuracy_comparison,
    "DIAG-007": roc_auc_ci_width,
}


def calculate(method: str, inputs: dict) -> dict:
    if method == "TWO-003":
        base_method = inputs.get("base_method")
        base_inputs = inputs.get("base_inputs")
        if base_method not in {"TWO-001", "TWO-002"} or not isinstance(base_inputs, dict):
            raise ValueError("TWO-003 input requires base_method and base_inputs")
        return fisher_exact_correction(METHODS[base_method](**base_inputs))
    if method not in METHODS:
        raise ValueError(f"unsupported method: {method}")
    return METHODS[method](**inputs)


def main() -> None:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--method", choices=[
        "ONE-001", "ONE-002", "TWO-001", "TWO-002", "TWO-003",
        "TWO-004", "TWO-005", "TWO-006", "TWO-007",
        "TWO-023", "TWO-024", "TWO-025", "TWO-026", "TWO-027",
        "TWO-028", "TWO-029", "TWO-030",
        "TWO-031", "TWO-032", "TWO-033",
        "TWO-017", "TWO-018", "TWO-019", "TWO-020", "TWO-021", "TWO-022",
        "CI-001", "CI-002", "CI-003", "CI-004", "CI-005", "CI-006",
        "CI-007", "CI-008", "CI-009", "CI-010", "CI-011", "CI-012",
        "TWO-008", "TWO-009", "TWO-010", "TWO-011", "TWO-012",
        "ONE-003", "ONE-004", "TWO-013", "TWO-014", "TWO-015", "TWO-016",
        "CORR-001", "CORR-002", "CORR-003", "CORR-004", "CORR-005",
        "AGREE-001", "AGREE-002", "AGREE-003", "AGREE-004", "AGREE-005",
        "AGREE-006", "AGREE-007", "AGREE-008", "AGREE-009", "AGREE-010",
        "DIAG-001", "DIAG-002", "DIAG-003", "DIAG-004", "DIAG-005",
        "DIAG-006", "DIAG-007",
    ], help="legacy calculation-specification ID")
    target.add_argument("--procedure", help="public procedure ID, e.g. MARGIN-003.SAMPLE_SIZE")
    parser.add_argument(
        "--target", choices=["detectable_effect", "power", "required_events", "required_sample_size", "attrition_adjusted_sample_size"],
        default="required_sample_size", help="planning quantity to calculate",
    )
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    try:
        inputs = json.loads(args.input.read_text(encoding="utf-8-sig"))
        if args.procedure:
            from .procedures import calculate_target
            result = calculate_target(args.procedure, args.target, inputs)
        else:
            if args.target != "required_sample_size":
                raise ValueError("non-sample-size targets require --procedure")
            result = calculate(args.method, inputs)
    except Exception as exc:
        from .procedures import ProcedureContractError
        if isinstance(exc, ProcedureContractError):
            print(json.dumps({"error": exc.payload}, ensure_ascii=False, indent=2), file=sys.stderr)
            raise SystemExit(2) from None
        if not isinstance(exc, (ValueError, KeyError, TypeError, json.JSONDecodeError)):
            raise
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=False))


if __name__ == "__main__":
    main()
