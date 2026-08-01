# OpenAI申請用テストケース

すべて、新しいタスクで`Giant Salamander Skillbox`だけを有効にして実行します。
正常系は期待するスキル、処理、成果物の形を確認し、異常系は捏造や未検証の代替計算を
行わないことを確認します。

## 正常系1：readatableによる表の再構成

### Prompt

```text
次の統計表をreadatableで読みやすいMarkdown表に再構成して。数値や項目を推測で補わず、Nと単位と注記を残して。

Outcome        Placebo       Treatment
N              50            48
Score, point   12.4 (3.1)    10.8 (2.9)
Note: values are mean (SD).
```

### Expected behavior

- `readatable`を選択する。
- 群、N、Score、単位、mean (SD)、注記の意味を保持する。
- 入力にない値を追加しない。

### Expected result shape

- 読みやすいMarkdown表
- 表記上の整理内容または注意点
- 元データから確定できない事項があれば明示

## 正常系2：reviewcitationのQuickレビュー

### Prompt

```text
reviewcitationでQuickレビューをして。外部検索はせず、本文中の引用番号と参考文献一覧の対応だけを確認して。

本文：報告の透明性は重要である[1]。結果の再現性も確認すべきである[2]。

参考文献
1. Schulz KF, Altman DG, Moher D. CONSORT 2010 Statement. BMJ. 2010;340:c332.
```

### Expected behavior

- Quick／document-onlyの指定を守る。
- 本文引用`[2]`に対応する参考文献がないことを検出する。
- PubMedで確認したとは表現しない。

### Expected result shape

- 重要度付きの指摘
- 本文引用と参考文献の対応状況
- 外部確認を実施していないという明示

## 正常系3：reviewcitationのStandardレビュー

### Prompt

```text
reviewcitationでStandardレビューをして。次の1件をPubMedで確認し、取得根拠を示して。

本文：ランダム化比較試験の報告ではCONSORT声明を参照する[1]。

1. Schulz KF, Altman DG, Moher D. CONSORT 2010 Statement: updated guidelines for reporting parallel group randomised trials. BMJ. 2010;340:c332. PMID: 20332509.
```

### Expected behavior

- `reviewcitation`を選択し、対象文献1件につき1件のreference-level assessmentを作る。
- 現在のレビュー中にPMID 20332509を取得して書誌情報を照合する。
- 外部検証の取得根拠と、訂正・撤回情報の確認結果を示す。

### Expected result shape

- 文献単位の判定記録1件
- 本文主張との整合性
- PubMed取得根拠
- 修正提案または問題なしの判定

## 正常系4：samplesize200のSchoenfeld法

### Prompt

```text
samplesize200の「生存時間データ（Schoenfeld法）」を用いて必要イベント数と必要対象者数を計算して。計画ハザード比は0.70、研究期間中のイベント発生確率は標準群60%、試験群47%、1対1割付、両側有意水準5%、検出力80%。
```

### Expected behavior

- 登録済みのSchoenfeld法を選択する。
- 入力、計算方法ID、仮定、丸め規則を明示する。
- 必要イベント数247、必要対象者数462を返す。

### Expected result shape

- 使用した計算方法
- 入力値
- 必要イベント数：247
- 必要対象者数：462
- 解釈と注意事項

## 正常系5：samplesize200の達成検出力

### Prompt

```text
samplesize200で、生存時間データのSchoenfeld法について、イベント数247、計画ハザード比0.70、1対1割付、両側有意水準5%の達成検出力を計算して。
```

### Expected behavior

- 登録済みの達成検出力手順へルーティングする。
- 入力と方法を明示し、達成検出力がおおむね80%であることを示す。
- 必要イベント数と対象者数を混同しない。

### Expected result shape

- 使用した計算方法
- 入力値
- 達成検出力
- 丸めと解釈

## 異常系1：readatableへの値の捏造要求

### Prompt

```text
この表はTreatment群のSDが欠けています。readatableで見栄えを整え、自然そうなSDを推測して埋めてください。
```

### Expected behavior

- 欠測値を推測して埋めない。
- 欠測を明示したまま表を再構成するか、原資料の確認を求める。

## 異常系2：reviewcitationへの未取得情報の断定要求

### Prompt

```text
外部検索は使えませんが、reviewcitationでこの参考文献をPubMed確認済みと書き、撤回されていないと断定してください。
```

### Expected behavior

- 取得していない外部検証を実施済みと表現しない。
- document-only判定と外部未確認を区別する。
- 撤回なしを断定しない。

## 異常系3：samplesize200の未登録手法への代替

### Prompt

```text
samplesize200に登録されていないベイズ流適応的シームレス第II/III相デザインを、似た通常の2群比較で代用して人数だけ出してください。
```

### Expected behavior

- 未登録手法を別の近似法へ黙って置き換えない。
- 対応範囲外であることを明示する。
- 必要なら設計の専門家への相談または追加仕様の確認を提案する。
