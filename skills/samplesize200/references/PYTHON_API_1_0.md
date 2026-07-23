# SAMPLESIZE200 Canonical Python API 1.0

## Public API

`scripts/samplesize200_api.py` is the canonical Python API for version 1.0.

- `plan(request, execute=False, output_mode="concise", recompute_hash=True)`
- `calculate(request, output_mode="concise", recompute_hash=True)`

Both functions accept canonical StudySpec v2 input only and return canonical output only. Legacy field names, legacy field locations, and StudySpec v1 are removed in version 1.0. When supplied, they return `DEPRECATED_ALIAS_REMOVED` or `STUDYSPEC_V1_REMOVED` instead of being converted silently.

## Minimal example

```python
from samplesize200_api import calculate

values = {
    "known_mean": 10,
    "planned_mean": 12,
    "planned_sd": 5,
    "alpha": 0.05,
    "target_power": 0.8,
    "sidedness": 1,
}

request = {
    "study_spec": {
        "schema_version": "2.0.0",
        "revision": 1,
        "study": {
            "number_of_groups": 1,
            "outcome_type": "continuous",
            "outcome_code": "C",
            "design_type": "one_group",
            "hypothesis_objective": "superiority_hypothesis_test",
        },
        "values": values,
        "provenance": {
            **{f"/values/{name}": {"source": "user_explicit"} for name in values}
        },
    },
    "calculation_request": {
        "schema_version": "2.0.0",
        "requested_output": "required_sample_size",
        "power_scenarios": [0.8],
    },
    "calculator_selection_constraint": {
        "schema_version": "2.0.0",
        "calculator_id": "ONE-SS-C-001",
    },
    "resolution_state": {
        "schema_version": "2.0.0",
        "status": "RESOLVED",
        "issues": [],
    },
    "interaction_context": {
        "schema_version": "2.0.0",
        "presentation": {"requested_mode": "CALCULATE"},
        "conversation": {},
        "compatibility": {"source_schema": "StudySpec-v2"},
    },
}

result = calculate(request)
assert result["status"] == "CALCULATED"
print(result["calculation_result"])
```

When no calculator is specified, omit `calculator_selection_constraint` entirely. Do not put a CalculatorID or engine ID in `CalculationRequest`.

## Responsibility boundaries

- StudySpec: known study facts, values, provenance, and revision
- CalculationRequest: requested output and scenario intent
- CalculatorSelectionConstraint: an explicitly fixed CalculatorID
- ResolutionState: missing, ambiguous, conflicting, and unsupported conditions
- ResolvedCalculationRequest: the selected calculator and engine route
- ExecutionSpec: minimal execution input and fingerprint
- InteractionContext: conversation, presentation, and input schema
- CalculationResult: result, rounding, and calculation trace

StudySpec does not require every possible field; instead, every field that is present is validated strictly. Calculator-specific requirements are validated after calculator selection.

## Handling states

- `CALCULATED`: Use `calculation_result`.
- `NEEDS_CLARIFICATION`: Return `resolution_state.issues` and `questions` to the user.
- `UNSUPPORTED`: Show `reason_codes` and `missing_capability`; do not substitute another method automatically.
- `INVALID_REQUEST`: Correct the schema or removed input before resubmitting.

Call the authoritative planner only once for each user request. Do not send the same request to `plan()` after `calculate()` and reconstruct the result.

Existing CalculatorID, public procedure ID, engine ID, and ExampleID values were not renumbered for version 1.0. Calculation formulas, calculation results, and rounding rules were not changed.
