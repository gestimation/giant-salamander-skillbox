# samplesize200 1.0 Solution catalog

## 命名

samplesize200では、研究課題を解決する機能全体をSolutionと捉えます。
計算方法の識別子はCalculatorID、研究事例の識別子はExampleIDです。
汎用的な`SolutionID`という値は予約語であり、1.0では発行しません。
したがって、1.0のSolutionはCalculator 188件と研究事例105件の合計293件です。

CalculatorIDは`<family>-<output>-<outcome>-<sequence>`を基本とします。
たとえば`ONE-SS-C-001`は1群・必要サンプルサイズ・連続アウトカム、
`ONE-PW-C-001`は同じ計算方法の達成検出力、`ONE-ES-C-001`は検出可能効果です。
`B`や`C`は書籍の章ではなくアウトカム種別を表します。

## 公開範囲

| requested_output | Calculator数 | 意味 |
|---|---:|---|
| `required_sample_size` | 126 | 必要サンプルサイズ |
| `required_events` | 2 | 必要イベント数 |
| `required_cluster_size` | 2 | 施設数固定時などの必要クラスター内人数 |
| `attrition_adjusted_sample_size` | 12 | 脱落調整後サンプルサイズ |
| `achieved_power` | 30 | 固定した実施人数で達成する検出力 |
| `detectable_effect` | 16 | 固定した実施人数と目標検出力から逆算する効果 |
| Calculator小計 | 188 | 登録済みCalculatorID |

研究事例は105 ExampleID、Calculatorとの計算リンクは258件です。研究事例は
Calculatorと同じSolutionの一種ですが、計算器のIDとは独立しています。
書籍章番号や例番号はExampleIDに埋め込まず、関連メタデータとして保持します。

| Solution種別 | 件数 |
|---|---:|
| Calculator | 188 |
| 研究事例 | 105 |
| Solution合計 | 293 |

## 全件一覧

- `CALCULATORS_1_0.csv`: 188 CalculatorID、既存公開ID、engine ID、Pythonで指定する
  `requested_output`とengine target、関連ExampleID、書籍章・例番号。
- `EXAMPLES_1_0.csv`: 105 ExampleID、関連CalculatorID、既存公開ID、書籍章・例番号、
  検証状態。
- `solution_identifier_registry.json`: 上記のcanonical機械可読レジストリと258リンク。

既存のCalculatorID、ExampleID、公開ID、engine IDは1.0移行時にも振り直しません。
