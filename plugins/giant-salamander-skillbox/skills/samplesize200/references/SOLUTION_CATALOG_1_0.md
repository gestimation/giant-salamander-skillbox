# samplesize200 1.0 Solution Catalog

## Naming

samplesize200 uses the term Solution for the complete set of capabilities that address research questions. CalculatorID identifies a calculation method, and ExampleID identifies a research example. The generic value `SolutionID` is reserved and is not issued in version 1.0. Version 1.0 therefore contains 293 solutions: 188 calculators and 105 research examples.

CalculatorID generally follows `<family>-<output>-<outcome>-<sequence>`. For example, `ONE-SS-C-001` denotes a one-group required-sample-size calculator for a continuous outcome. `ONE-PW-C-001` denotes achieved power for the same calculation method, and `ONE-ES-C-001` denotes detectable effect. Codes such as `B` and `C` indicate outcome types, not book chapters.

## Public scope

| requested_output | Calculators | Meaning |
|---|---:|---|
| `required_sample_size` | 126 | Required sample size |
| `required_events` | 2 | Required number of events |
| `required_cluster_size` | 2 | Required within-cluster size when the number of clusters is fixed |
| `attrition_adjusted_sample_size` | 12 | Attrition-adjusted sample size |
| `achieved_power` | 30 | Power achieved with a fixed implementation size |
| `detectable_effect` | 16 | Effect obtained by inversion from a fixed implementation size and target power |
| Calculator subtotal | 188 | Registered CalculatorIDs |

The catalog contains 105 ExampleIDs and 258 calculation links between research examples and calculators. Research examples are Solutions, but their identifiers are independent of calculator identifiers. Book chapter and example numbers are not embedded in ExampleIDs; they are retained as related metadata.

| Solution type | Count |
|---|---:|
| Calculator | 188 |
| Research example | 105 |
| Total Solutions | 293 |

## Complete listings

- `CALCULATORS_1_0.csv`: 188 CalculatorIDs, existing public IDs, engine IDs, Python `requested_output` values and engine targets, related ExampleIDs, and book chapter and example numbers.
- `EXAMPLES_1_0.csv`: 105 ExampleIDs, related CalculatorIDs, existing public IDs, book chapter and example numbers, and validation status.
- `solution_identifier_registry.json`: the canonical machine-readable registry for the entries above and their 258 links.

Existing CalculatorIDs, ExampleIDs, public IDs, and engine IDs were not renumbered during the version 1.0 transition.
