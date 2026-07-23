"""SAMPLESIZE200 Alpha 0.6.8; public interfaces remain provisional."""

from ._version import VERSION

__version__ = VERSION

from .binary import fisher_exact_correction, one_sample_proportion, two_sample_odds_ratio, two_sample_proportions
from .continuous import (
    NORMAL_WMW_EFFICIENCY, one_sample_mean, superiority_probability_from_effect,
    two_sample_mean_exact, two_sample_mean_guenther, two_sample_mean_satterthwaite,
    wmw_efficiency, wmw_superiority,
)
from .rates import (
    adverse_event_observation, bonferroni_alpha, known_background_increase,
    matched_case_control, two_group_negative_binomial_rates,
    two_group_poisson_rates, unknown_background_comparison,
)
from .ordinal import equal_category_approximation, mann_whitney_nonproportional, many_category_approximation, proportional_odds
from .paired import (
    discordant_count_conversion, matched_case_control_correction, mcnemar_direct,
    paired_continuous_normal, paired_continuous_t, paired_ordinal_binary,
    paired_ordinal_compromise, paired_ordinal_signed_rank,
)
from .confidence import (
    finite_population_correction, one_mean_absolute, one_mean_relative,
    one_proportion_normal_absolute, one_proportion_normal_relative,
    one_proportion_wilson, paired_mean_difference, paired_proportion_difference,
    two_mean_difference, two_proportion_normal_difference,
    two_proportion_odds_ratio_relative, two_proportion_wilson_difference,
)
from .longitudinal import repeated_post_mean, repeated_slope, repeated_weighted_contrast
from .survival import events_to_participants, freedman_events, schoenfeld_events
from .competing import (
    cause_hazards_from_cifs, cause_specific_hazard_competing_risk,
    subdistribution_accrual_integration, subdistribution_fixed_censoring,
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
from .margin import MARGIN_PROCEDURES
from .one_survival import one_sample_survival_arcsine
from .procedures import calculate_procedure, calculate_target
from .power import calculate_power, previous_feasible_design
from .power_design import calculate_power_request, resolve_power_design
from .detectable_effect import calculate_detectable_effect
from .detectable_effect_design import (
    calculate_detectable_effect_request, resolve_detectable_effect_design,
)

__all__ = [
    "one_sample_proportion",
    "two_sample_proportions",
    "two_sample_odds_ratio",
    "fisher_exact_correction",
    "one_sample_mean",
    "two_sample_mean_exact",
    "two_sample_mean_guenther",
    "two_sample_mean_satterthwaite",
    "wmw_efficiency",
    "wmw_superiority",
    "superiority_probability_from_effect",
    "NORMAL_WMW_EFFICIENCY",
    "two_group_poisson_rates",
    "two_group_negative_binomial_rates",
    "adverse_event_observation",
    "known_background_increase",
    "unknown_background_comparison",
    "matched_case_control",
    "bonferroni_alpha",
    "proportional_odds", "equal_category_approximation", "many_category_approximation",
    "mann_whitney_nonproportional", "mcnemar_direct", "discordant_count_conversion",
    "matched_case_control_correction", "paired_ordinal_signed_rank",
    "paired_ordinal_binary", "paired_ordinal_compromise", "paired_continuous_normal",
    "paired_continuous_t", "one_proportion_normal_absolute",
    "one_proportion_normal_relative", "one_proportion_wilson",
    "finite_population_correction", "two_proportion_normal_difference",
    "two_proportion_wilson_difference", "two_proportion_odds_ratio_relative",
    "paired_proportion_difference", "one_mean_absolute", "one_mean_relative",
    "two_mean_difference", "paired_mean_difference",
    "repeated_post_mean", "repeated_slope", "repeated_weighted_contrast",
    "schoenfeld_events", "freedman_events", "events_to_participants",
    "cause_hazards_from_cifs", "cause_specific_hazard_competing_risk",
    "subdistribution_fixed_censoring", "subdistribution_accrual_integration",
    "correlation_detection", "pearson_ci_initial", "pearson_ci_refined",
    "spearman_ci_initial", "spearman_ci_refined",
    "disagreement_normal", "disagreement_wilson", "within_rater_error_precision",
    "two_stage_fixed", "equal_repetition_design", "optimized_repetition_design",
    "cohen_kappa_ci", "icc_ci", "icc_ci_high_correction", "icc_hypothesis",
    "normal_reference_interval_precision", "rank_reference_interval_precision",
    "single_accuracy_large_sample", "single_accuracy_exact",
    "independent_accuracy_comparison", "paired_accuracy_comparison", "roc_auc_ci_width",
    "MARGIN_PROCEDURES", "one_sample_survival_arcsine", "calculate_procedure", "calculate_target",
    "calculate_power", "calculate_power_request", "resolve_power_design",
    "calculate_detectable_effect", "calculate_detectable_effect_request",
    "resolve_detectable_effect_design",
    "previous_feasible_design",
]
