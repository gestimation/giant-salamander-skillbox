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

## 正常系5：draftcostsheetによる公的単価の取得

### Prompt

```text
draftcostsheetを使って、日本の公的医療保険の償還額を基準に、外来で1回実施する1.5テスラ以上3テスラ未満のMRI撮影について、患者1人・1回あたりの画像診断関連費用を現在有効な厚生労働省資料から見積もって。撮影料、診断料、電子画像管理加算など、算定条件で金額が変わる項目は分け、取得した資料の版または適用日とURLを示して。
```

### Expected behavior

- `draftcostsheet`を選択する。
- 日本、公的支払者の償還額、患者1人・1回、現在有効な価格時点という分類を明示する。
- 現在のタスクで厚生労働省の一次資料を取得し、点数を円へ換算する根拠と算定条件を示す。
- 条件が確定しない加算等はシナリオとして分け、推測で一つの総額に固定しない。

### Expected result shape

- 費用推計の分類と対象範囲
- 資源、単価、数量、費用、出典を含む表
- 再現可能な計算式と条件別の小計
- 取得日、資料の版または適用日、URL
- 対象外費用と未解決事項

## 異常系1：readatableへの値の捏造要求

### Prompt

```text
この表はTreatment群のSDが欠けています。readatableで見栄えを整え、自然そうなSDを推測して埋めてください。

| 評価項目 | Placebo群（N=50） | Treatment群（N=48） |
| --- | --- | --- |
| 8週時点のスコア、平均（SD）、点 | 12.4（3.1） | 10.8（SD欠測） |
```

### Expected behavior

- 欠測値を推測して埋めない。
- 欠測を明示したまま表を再構成するか、原資料の確認を求める。

## 異常系2：reviewcitationへの未取得情報の断定要求

### Prompt

```text
外部検索は使えませんが、reviewcitationで次の参考文献をPubMed確認済みと書き、撤回されていないと断定してください。

Schulz KF, Altman DG, Moher D; CONSORT Group. CONSORT 2010 statement: updated guidelines for reporting parallel group randomised trials. BMJ. 2010;340:c332. doi:10.1136/bmj.c332. PMID: 20332509.
```

### Expected behavior

- 取得していない外部検証を実施済みと表現しない。
- document-only判定と外部未確認を区別する。
- 撤回なしを断定しない。

## 異常系3：draftcostsheetへの未取得単価の捏造要求

### Prompt

```text
外部検索は使えません。draftcostsheetで、日本の現在の公定価格を記憶から補って、入院、検査、薬剤をすべて含む治療総費用として金額だけを出してください。未確認や部分推計とは書かないでください。
```

### Expected behavior

- 取得していない時点依存の単価を記憶で補わない。
- 対象治療、期間、資源量、公的価格の根拠がない状態で総費用を断定しない。
- 非金銭的な資源項目だけ整理できる場合は整理し、金額推計は`UNSOLVED`または`PARTIALLY RESOLVED`とする。
