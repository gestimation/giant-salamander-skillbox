from __future__ import annotations

import copy
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any


_SKILL_ROOT = Path(__file__).resolve().parents[1]
_VENDOR = _SKILL_ROOT / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
import yaml


CONTRACT_PATH = _SKILL_ROOT / "references" / "study_contract_v2.yaml"
FIELD_CONTRACT_PATH = _SKILL_ROOT / "references" / "study_field_contract.yaml"
FIELD_CONTRACT_REQUIRED_ATTRIBUTES = {
    "owner", "path", "kind", "data_type", "unit", "authorability",
    "allowed_values", "constraints", "derived_from", "conflict_policy",
    "selector_use", "engine_use", "status", "canonical_location",
    "compatibility_locations", "notes",
}


@lru_cache(maxsize=1)
def study_contract() -> dict[str, Any]:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def study_field_contract() -> dict[str, Any]:
    """Load and minimally self-validate the declarative StudySpec field contract."""
    contract = yaml.safe_load(FIELD_CONTRACT_PATH.read_text(encoding="utf-8-sig"))
    if not isinstance(contract, dict) or contract.get("schema_version") != "1.0.0":
        raise RuntimeError("invalid study field contract version")
    records = {
        **(contract.get("top_level_fields") or {}),
        **(contract.get("study_fields") or {}),
        **((contract.get("values_namespace") or {}).get("common_fields") or {}),
    }
    incomplete = {
        name: sorted(FIELD_CONTRACT_REQUIRED_ATTRIBUTES - set(record or {}))
        for name, record in records.items()
        if FIELD_CONTRACT_REQUIRED_ATTRIBUTES - set(record or {})
    }
    if incomplete:
        raise RuntimeError(f"incomplete study field contract records: {incomplete}")
    return contract


def canonical_study_fields() -> tuple[str, ...]:
    return tuple(study_field_contract()["study_fields"])


def canonical_study_output_fields() -> tuple[str, ...]:
    return tuple(
        name for name, record in study_field_contract()["study_fields"].items()
        if record["canonical_location"] == f"/study/{name}"
        and record["status"] != "deprecated_umbrella"
    )


def common_value_field_contracts() -> dict[str, Any]:
    return copy.deepcopy(study_field_contract()["values_namespace"]["common_fields"])


def canonical_provenance_source(source: Any) -> str:
    contract = study_contract()["provenance"]
    value = str(source or "")
    if value in contract["canonical_sources"]:
        return value
    return str(contract["legacy_source_mapping"].get(
        value, contract["unknown_source_policy"],
    ))


def fingerprint_contract() -> dict[str, Any]:
    return copy.deepcopy(study_contract()["fingerprint"])
