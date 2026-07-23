---
name: samplesize200
description: Plan, calculate, teach, and review study-size designs with SAMPLESIZE200, a Giant Salamander Skillbox skill containing 188 validated calculators and 105 research examples. Use for required sample size, required events, fixed-cluster size, attrition adjustment, achieved power, detectable effect, method selection, research-example comparison, or protocol calculation review. Use only registered procedures; never replace an unsupported method with an unvalidated approximation.
---

# SAMPLESIZE200

**Product version 1.0.0-rc.4**

**Bundled validated engine: SAMPLESIZE200 Alpha 0.6.8**

SAMPLESIZE200 is part of the Giant Salamander Skillbox. It provides 293 solutions: 188 CalculatorIDs and 105 ExampleIDs. Always use the bundled SAMPLESIZE200 Alpha 0.6.8 engine through the supplied scripts. Never reproduce the final calculation yourself. Stop on an integrity mismatch, missing dependency, or unregistered capability.

## Public contract

Accept only the canonical StudySpec v2 envelope:

- `StudySpec` contains known study facts, strict present values, provenance, and revision.
- `CalculationRequest` contains only `requested_output` and scenario intent.
- `CalculatorSelectionConstraint` may contain only an explicitly requested `calculator_id`.
- `ResolutionState` contains typed missing, ambiguous, conflicting, or unsupported issues.
- `InteractionContext` contains only conversation and presentation state plus `compatibility.source_schema=StudySpec-v2`.
- `ResolvedCalculationRequest` owns the selected CalculatorID and engine route.
- `ExecutionSpec` owns the deterministic executable payload and fingerprint.
- `CalculationResult` owns values, rounding, and trace.

Do not place unresolved state, selection results, engine routes, or conversation state in StudySpec. A StudySpec is sparse: not every field is required, but every present field is validated strictly. The selected Calculator defines its required values.

The 1.0 reader and writer are canonical-only. Do not emit or accept removed names or a flat StudySpec v1. Removed input must return the planner's structured `DEPRECATED_ALIAS_REMOVED` or `STUDYSPEC_V1_REMOVED` error. Existing CalculatorID, public procedure ID, engine ID, and ExampleID values remain unchanged.

The six canonical outputs are:

- `required_sample_size`
- `required_events`
- `required_cluster_size`
- `attrition_adjusted_sample_size`
- `achieved_power`
- `detectable_effect`

Use `calculator_selection_constraint`, never an identity field inside `CalculationRequest`.

Omit `calculator_selection_constraint` for an ordinary natural-language request.
Populate it only when the user explicitly requests a registered CalculatorID or an
application integration supplies one. Never copy a public procedure ID, engine
procedure ID, engine model ID, procedure key, ExampleID, or a generated guess into
`calculator_selection_constraint.calculator_id`.

## Modes

- `CALCULATE`: ask only for unresolved required inputs and return a concise result.
- `STATISTICIAN`: compare registered candidates, assumptions, and explicit sensitivity scenarios.
- `TEACHER`: explain the selected method using labelled exact or related examples.
- `REVIEWER`: reproduce all reported conditions and classify discrepancies without filling gaps.

Keep one StudySpec when the user changes modes.

## Routine calculation

1. Interpret the request into one canonical StudySpec v2 envelope. Preserve prior explicit facts on follow-up turns.
2. Determine the canonical `requested_output`. Distinguish target power for planning from achieved power for a fixed design.
3. Call `scripts/assistant_calculate.py --study-spec <json-file>` exactly once for one user request. It invokes the authoritative planner once and executes all declared scenarios. Do not call `plan_request.py` again to reconstruct the answer.
4. On `NEEDS_CLARIFICATION`, ask only the returned questions. Translate internal field names into ordinary language; do not expose identifiers such as `planned_intercept_sd` in the question.
5. On `UNSUPPORTED`, stop and preserve `error`, `reason_codes`, `unsupported_reason`, `missing_capability`, and the bounded related-procedure list. Do not substitute a nearby method.
6. On `CALCULATED`, show one `採用値：` line, then short `前提：` lines for defaults that matter, then the final result. Use the returned group or sequence allocation.
7. Offer at most one relevant research example after a successful calculation. Load its details only if the user asks.

Validate identifier constraints before the authoritative planner call. A
wrong-namespace identifier is an `INVALID_REQUEST`, not permission to execute a
mapped CalculatorID. Preserve the StudySpec, show the typed diagnostic, and never
call the authoritative planner a second time for the same user request.

Wrapper and environment failures preserve all confirmed StudySpec values. Do not
ask the user to repeat unchanged scientific inputs merely to trigger execution.
Distinguish pre-launch, child-process, and post-processing failures from a
statistical calculation failure.

Use `scripts/plan_request.py --study-spec <json-file> --execute --output-mode detailed|qc` only when the user explicitly requests detailed or QC output. Use `scripts/samplesize200_api.py` for the canonical Python API.

## Natural-language boundary

The language adapter may make deterministic semantic implications explicit, but it must not choose a CalculatorID or invent statistical inputs.

- Normalize two-group repeated-measures wording to `design_type=repeated_measures_two_group`, `repeated_measures=true`, and continuous measurements to `outcome_type=repeated_continuous`.
- Normalize paired binary wording to `design_type=paired_two_group`, `paired_or_independent=paired`, and `outcome_type=paired_binary_ordinal_or_continuous`.
- For multiple treatments sharing one control, set `comparison_scope=shared_control`; infer multiple confirmatory comparisons only when that relationship is stated. Never invent a multiplicity strategy.
- When a request changes to `achieved_power`, discard an analysis method that was merely inferred. Preserve a method only when the user explicitly named it.
- Do not infer whether an unlabeled sample size is total or per group. Ask when this changes the calculation.

For a two-sided longitudinal `detectable_effect` calculation, report the positive detectable magnitude and do not ask for a sign. For a one-sided request, direction remains a required scientific fact. Ask for a measurement standard deviation in user language rather than exposing `planned_intercept_sd`.

## Defaults

Defaults apply only to ordinary superiority designs where the policy declares them safe:

- one-group directional hypothesis: one-sided alpha 0.05;
- ordinary two-group superiority: two-sided alpha 0.05;
- ordinary two-group sample-size planning: 1:1 allocation;
- missing target power: 80%, 90%, and 95% sensitivity scenarios.

Do not apply these hypothesis defaults to noninferiority, equivalence, multiplicity-sensitive, group-sequential, Bayesian, confidence-interval precision, or other non-power designs. Never invent a noninferiority margin, equivalence limits, confidence-interval width, prevalence, event rate, variance, correlation, or attrition rate.

For ordinary proportional-hazards required events, use registered Schoenfeld `TWO-S-001` unless the user explicitly requests Freedman or asks to compare methods.

## Capability boundaries

Check support before asking method-specific numeric inputs. Cohen-kappa hypothesis-test sample size or achieved power is unregistered; return `NO_VALIDATED_PROCEDURE`. Do not redirect it to the kappa confidence-interval precision calculator `AGREE-N-001`.

Achieved power and detectable effect are available only for CalculatorIDs registered for those outputs. Never reinterpret an unsupported achieved-power request as sample-size planning.

For registered multi-group wrappers, preserve the parent two-group method and reconstruction rule. Do not describe maximum pairwise procedures as omnibus tests, shared-control calculations as automatically simultaneous, or factorial main effects as interactions. Preserve Schoenfeld versus Freedman and cause-specific versus subdistribution hazard choices when they are scientifically material.

## Research examples

The ordinary calculation path may read only `references/research_example_presence_index.json`. A missing or malformed example index must not invalidate a successful calculation.

- `EXACT` requires the same procedure, output, and normalized formula reference.
- `SAME_METHOD_DIFFERENT_OPERATION` means the output differs.
- `RELATED` requires a curated design relationship.
- Example values are explanation-only and must never become StudySpec values or defaults.
- Display the study title in ordinary responses. Keep book chapter and example number as metadata for traceability.
- Research examples from books and articles are the same user-facing Solution category, while retaining exact source metadata internally.

Use `scripts/assistant_example.py` for one requested example and `scripts/retrieve_example.py` only when the user requests all cases or QC detail.

## Help and references

For explicit help, call `scripts/show_help.py --reason explicit_help_request`. For broad workflow confusion, call it with `--reason workflow_confusion`; preserve confirmed facts and offer a clean restart. Do not show the full guide for one missing number.

Authoritative contracts and catalogs:

- `references/study_contract_v2.yaml`
- `references/study_field_contract.yaml`
- `references/naming_contract.yaml`
- `references/calculation_target_contracts.yaml`
- `references/procedure_catalog.yaml`
- `references/SOLUTION_CATALOG_1_0_JA.md`
- `references/PYTHON_API_1_0_JA.md`

Formulas, calculated values, and rounding rules are unchanged from the bundled validated engine. Trial reports are conversation-local and must not contain unnecessary personal information.
