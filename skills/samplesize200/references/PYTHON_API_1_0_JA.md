# samplesize200 canonical Python API 1.0

## 公開API

`scripts/samplesize200_api.py`が1.0のcanonical Python APIです。

- `plan(request, execute=False, output_mode="concise", recompute_hash=True)`
- `calculate(request, output_mode="concise", recompute_hash=True)`

どちらもStudySpec v2のcanonical入力だけを受理し、canonical出力だけを返します。旧フィールド名、旧配置、StudySpec v1は1.0では削除済みです。入力された場合は、暗黙変換せず`DEPRECATED_ALIAS_REMOVED`または`STUDYSPEC_V1_REMOVED`を返します。

## 最小例

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

Calculatorを指定しない場合は`calculator_selection_constraint`自体を省略します。`CalculationRequest`へCalculatorIDやengine IDを置かないでください。

## 責務境界

- StudySpec: 判明済みの研究事実、値、provenance、revision
- CalculationRequest: 求める出力とscenario intent
- CalculatorSelectionConstraint: 明示的に固定するCalculatorID
- ResolutionState: 不足、曖昧性、競合、未対応
- ResolvedCalculationRequest: 選択済みCalculatorとengine route
- ExecutionSpec: 最小の実行入力とfingerprint
- InteractionContext: 会話、表示、入力元schema
- CalculationResult: 結果、丸め、計算trace

StudySpecは「全項目必須」ではなく「存在する値は厳格」です。Calculator固有の必須項目は、選択後に検証されます。

## 状態の処理

- `CALCULATED`: `calculation_result`を利用します。
- `NEEDS_CLARIFICATION`: `resolution_state.issues`と`questions`を利用者へ返します。
- `UNSUPPORTED`: `reason_codes`と`missing_capability`を表示し、別方法へ自動置換しません。
- `INVALID_REQUEST`: schemaまたは削除済み入力を修正してから再送します。

1ユーザー依頼についてauthoritative plannerは1回だけ呼び出してください。`calculate()`の後で同じ依頼を`plan()`へ再送して結果を組み立て直さないでください。

既存のCalculatorID、公開procedure ID、engine ID、ExampleIDの値は1.0でも振り直していません。計算式、計算結果、丸め規則も変更していません。
