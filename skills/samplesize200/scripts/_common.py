from __future__ import annotations

import hashlib
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

_SKILL_ROOT_FOR_VENDOR = Path(__file__).resolve().parents[1]
_VENDOR = _SKILL_ROOT_FOR_VENDOR / "vendor"
if str(_VENDOR) not in sys.path:
    sys.path.insert(0, str(_VENDOR))
import yaml


SKILL_ROOT = _SKILL_ROOT_FOR_VENDOR
REFERENCES = SKILL_ROOT / "references"
ENGINE_DIR = SKILL_ROOT / "engine"
EXPECTED_ENGINE_VERSION = "0.6.8"
EXPECTED_ENGINE_HASH = "ccbe5d0105f32aa812e40e8b445cf1b45b7fbea1db62f1691916b43125817d6b"


class SkillContractError(ValueError):
    def __init__(self, code: str, message: str, **details: Any):
        self.payload = {"code": code, "message": message, **details}
        super().__init__(message)


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8-sig"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


@lru_cache(maxsize=1)
def catalog() -> dict[str, Any]:
    data = load_yaml(REFERENCES / "procedure_catalog.yaml")
    for item in data.get("procedures", []):
        optional = {x["name"]: x.get("default") for x in item.get("optional_inputs", [])}
        required = set(item.get("required_inputs", []))
        confirmations = set(item.get("explicit_confirmation_inputs", []))
        requirements = []
        for contract in item.get("input_contracts", []):
            name = contract["name"]
            defaultable = name in optional and optional[name] is not None
            if name in {"alpha", "power", "sides", "allocation_ratio"}:
                defaultable = True
            conditional = None
            if item.get("public_id") in {"TWO-S-001", "TWO-S-002"} and name in {
                "standard_event_probability", "treatment_event_probability"
            }:
                conditional = ["calculation_target == required_sample_size"]
            requirement = {
                "name": name,
                "required": name in required or name in confirmations,
                "defaultable": defaultable,
                "conditional_on": conditional,
                "default_value": optional.get(name),
                "default_values": [0.80, 0.90, 0.95] if name == "power" else None,
                "ask_user_when": "required for the selected target and no confirmed or policy default value is available",
            }
            contract["parameter_requirement"] = requirement
            requirements.append(requirement)
        item["parameter_requirements"] = requirements
    return data


@lru_cache(maxsize=1)
def calculation_target_contracts() -> dict[str, Any]:
    return load_yaml(REFERENCES / "calculation_target_contracts.yaml")


@lru_cache(maxsize=1)
def research_example_index() -> dict[str, Any]:
    """Load only the small post-calculation offer index."""
    return load_json(REFERENCES / "research_example_presence_index.json")


@lru_cache(maxsize=1)
def research_example_catalog() -> dict[str, Any]:
    """Load detailed examples only after the user requests them."""
    return load_json(REFERENCES / "research_example_catalog.json")


@lru_cache(maxsize=1)
def default_policy() -> dict[str, Any]:
    return load_yaml(REFERENCES / "default_policy.yaml")


def procedure_input_contract(item: dict[str, Any], calculation_target: str) -> dict[str, Any]:
    """Return target-specific required/defaultable input metadata."""
    base = {
        "required_inputs": list(item.get("required_inputs", [])),
        "optional_inputs": list(item.get("optional_inputs", [])),
        "input_contracts": list(item.get("input_contracts", [])),
        "engine_method_id": None,
    }
    if calculation_target == "required_sample_size":
        return base
    if calculation_target in {"power", "detectable_effect"}:
        target = calculation_target_contracts()["targets"][calculation_target]
        model = str(item["engine_id"]).partition(".")[0]
        if model not in set(target["supported_model_ids"]):
            raise SkillContractError(
                "CALCULATION_TARGET_UNSUPPORTED",
                f"{calculation_target} is not available for {item['public_id']}",
                calculation_target=calculation_target,
                public_id=item["public_id"],
                model_id=model,
            )
        excluded = {"power", "allocation_ratio", "control_to_treatment_ratio",
                    "controls_per_case", "search_limit"}
        if calculation_target == "detectable_effect":
            excluded.update(target.get("effect_inputs_by_model", {}).get(model, []))
        required = [name for name in base["required_inputs"] if name not in excluded]
        optional = [row for row in base["optional_inputs"] if row["name"] not in excluded]
        contracts = [row for row in base["input_contracts"] if row["name"] not in excluded]

        def add_contract(name: str, data_type: str, *, required_input: bool = False,
                         default: Any = None) -> None:
            if name in {row["name"] for row in contracts}:
                return
            contracts.append({
                "name": name, "data_type": data_type, "required": required_input,
                "default": default, "unit": "participant" if name.startswith("n") else "dimensionless",
                "role": "realized_design", "allowed_range": None,
                "source": f"SAMPLESIZE200 Alpha 0.6.8 {calculation_target} contract",
            })
            if required_input:
                required.append(name)
            else:
                optional.append({"name": name, "default": default})

        independent = set(target["independent_two_group_model_ids"])
        if model in independent:
            if model in set(target["standard_treatment_model_ids"]):
                group_keys = target["group_count_inputs"]["standard_treatment"]
            elif model in set(target["standard_test_model_ids"]):
                group_keys = target["group_count_inputs"]["standard_test"]
            else:
                group_keys = target["group_count_inputs"]["control_treatment"]
            for name in ["n", "total_n", "per_group_n", *group_keys]:
                add_contract(name, "integer")
            add_contract("allocation_ratio", "any")
            add_contract("allocation_ratio_direction", "string")
            if model == "TWO-015":
                add_contract("control_to_treatment_ratio", "any")
        else:
            for name in target["design_inputs"][model]:
                add_contract(name, "integer", required_input=True)
            if model in {"TWO-023", "TWO-026", "TWO-029", "TWO-030", "MARGIN-002", "MARGIN-005"}:
                add_contract("subjects_per_pair", "integer", default=1)
                add_contract("even_sequence", "boolean", default=False)
        if calculation_target == "detectable_effect":
            add_contract("target_power", "number", required_input=True)
            if model in set(target.get("direction_required_model_ids", [])):
                add_contract("direction", "string", required_input=True)
            elif model in set(target.get("direction_optional_model_ids", [])):
                add_contract("direction", "string")
        return {
            "required_inputs": list(dict.fromkeys(required)),
            "optional_inputs": optional,
            "input_contracts": contracts,
            "engine_method_id": model,
        }
    if calculation_target == "attrition_adjusted_sample_size":
        target = calculation_target_contracts()["targets"]["attrition_adjusted_sample_size"]
        attrition_inputs = target.get("procedures", {}).get(item["public_id"])
        if attrition_inputs is None:
            raise SkillContractError(
                "CALCULATION_TARGET_UNSUPPORTED",
                f"attrition_adjusted_sample_size is not available for {item['public_id']}",
                calculation_target=calculation_target,
                public_id=item["public_id"],
            )
        required = list(dict.fromkeys([*base["required_inputs"], *attrition_inputs]))
        return {**base, "required_inputs": required}
    if calculation_target != "required_events":
        raise SkillContractError(
            "CALCULATION_TARGET_UNSUPPORTED",
            f"unknown calculation target: {calculation_target}",
            calculation_target=calculation_target,
        )
    target = calculation_target_contracts()["targets"]["required_events"]
    override = target.get("procedures", {}).get(item["public_id"])
    if override is None:
        raise SkillContractError(
            "CALCULATION_TARGET_UNSUPPORTED",
            f"required_events is not available for {item['public_id']}",
            calculation_target=calculation_target,
        )
    names = set(override["required_inputs"]) | {x["name"] for x in override.get("optional_inputs", [])}
    return {
        "required_inputs": list(override["required_inputs"]),
        "optional_inputs": list(override.get("optional_inputs", [])),
        "input_contracts": [x for x in item.get("input_contracts", []) if x["name"] in names],
        "engine_method_id": override["engine_method_id"],
    }


@lru_cache(maxsize=1)
def catalog_indexes() -> dict[str, dict[str, Any]]:
    items = catalog()["procedures"]
    return {
        "procedure_key": {x["procedure_key"]: x for x in items},
        "public_id": {x["public_id"]: x for x in items},
        "engine_id": {x["engine_id"]: x for x in items},
    }


def resolve_procedure(identifier: str) -> dict[str, Any]:
    indexes = catalog_indexes()
    for index in indexes.values():
        if identifier in index:
            return index[identifier]
    aliases: dict[str, list[dict[str, Any]]] = {}
    for item in indexes["engine_id"].values():
        for alias in item.get("legacy_ids", []):
            aliases.setdefault(alias, []).append(item)
    matches = aliases.get(identifier, [])
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise SkillContractError(
            "LEGACY_MAPPING_AMBIGUOUS", f"legacy ID {identifier} has multiple candidates",
            legacy_id=identifier,
            candidates=[{"procedure_key": x["procedure_key"], "public_id": x["public_id"], "engine_id": x["engine_id"]} for x in matches],
        )
    raise SkillContractError("UNKNOWN_PROCEDURE", f"unknown procedure identifier: {identifier}")


def engine_root() -> Path:
    """Return only the runtime bundled inside this skill."""
    return ENGINE_DIR.resolve()


def _runtime_hash(package: Path) -> dict[str, Any]:
    files = sorted(
        (
            p for p in package.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".pyo"}
        ),
        key=lambda p: p.relative_to(package).as_posix(),
    )
    digest = hashlib.sha256()
    per_file = {}
    total = 0
    for path in files:
        relative = path.relative_to(package).as_posix()
        data = path.read_bytes()
        total += len(data)
        per_file[relative] = hashlib.sha256(data).hexdigest()
        digest.update(relative.encode("utf-8")); digest.update(b"\n"); digest.update(data)
    return {"files": len(files), "bytes": total, "sha256": digest.hexdigest(), "per_file_sha256": per_file}


def validate_engine_compatibility(root: Path | None = None, *, recompute_hash: bool = True) -> dict[str, Any]:
    root = (root or engine_root()).resolve()
    manifest_path = root / "ENGINE_MANIFEST.yaml"
    package = root / "samplesize200"
    missing = [str(p.relative_to(root)) for p in (manifest_path, package / "__init__.py", package / "cli.py") if not p.exists()]
    if missing:
        raise SkillContractError("ENGINE_NOT_FOUND", "bundled engine files are missing", missing=missing)
    manifest = load_yaml(manifest_path)
    if str(manifest.get("engine_version")) != EXPECTED_ENGINE_VERSION or str(manifest.get("source_release_scoped_sha256")) != EXPECTED_ENGINE_HASH:
        raise SkillContractError("ENGINE_COMPATIBILITY_ERROR", "bundled engine identity does not match", expected_version=EXPECTED_ENGINE_VERSION, expected_source_hash=EXPECTED_ENGINE_HASH)
    actual = None
    if recompute_hash:
        actual = _runtime_hash(package)
        if actual["sha256"] != manifest.get("bundled_runtime_sha256") or actual["per_file_sha256"] != manifest.get("per_file_sha256"):
            raise SkillContractError("ENGINE_INTEGRITY_ERROR", "bundled runtime content hash does not match", expected=manifest.get("bundled_runtime_sha256"), actual=actual["sha256"])
    return {"compatible": True, "engine_root": str(root), "version": EXPECTED_ENGINE_VERSION, "source_release_scoped_sha256": EXPECTED_ENGINE_HASH, "bundled_runtime_sha256": manifest.get("bundled_runtime_sha256"), "recomputed": actual, "final_public_api": False}


def emit(value: Any) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(value, ensure_ascii=False, indent=2))
