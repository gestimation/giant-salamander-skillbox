# samplesize200クイックガイド

## samplesize200 — Chat with 200+ solutions to size your study

samplesize200は、研究計画を会話で整理し、登録済みの方法を選んで研究規模を計算するGiant Salamander Skillboxのスキルです。188のCalculatorと105の研究事例、合計293のSolutionを収録しています。条件が不足している場合は、計算に必要な項目だけを確認します。

## インストール

正式な配布元は[GitHub Releases](https://github.com/gestimation/giant-salamander-skillbox/releases)です。初めて使う場合は、`readatable`、`reviewcitation`、`samplesize200`、`draftcostsheet`をまとめた統合プラグイン`giant-salamander-skillbox-1.0.0-rc.4.zip`を推奨します。ZIPは展開・再圧縮せず、ChatGPT Work、CodexまたはClaude Codeのプラグイン画面からそのままインストールします。

samplesize200だけを使用する場合は、個別プラグイン`samplesize200-1.0.0-rc.8.zip`をChatGPT WorkまたはCodexへインストールできます。統合プラグインと個別プラグインは重複してインストールしません。

CodexでMarketplaceを使用する場合は、次のコマンドを実行します。

```text
codex plugin marketplace add gestimation/giant-salamander-skillbox
codex plugin add giant-salamander-skillbox@giant-salamander-skillbox
```

Claude Code DesktopでMarketplaceを使用する場合は、チャット入力欄から次のスラッシュコマンドを実行します。

```text
/plugin marketplace add gestimation/giant-salamander-skillbox
/plugin install giant-salamander-skillbox@giant-salamander-skillbox
/reload-plugins
```

スキルの機械名と画面表示名は、いずれも`samplesize200`です。

## まず使ってみる

知りたいことをそのまま入力してください。

> 相関係数0.5を検出するためのサンプルサイズを教えて。

> 2×2クロスオーバーBE試験でGMR 0.90、CV 30%、限界0.80～1.25を想定します。

> 0、1、3年に測定し、各群100人、相関0.4、検出力80%で検出可能な年間傾き差を求めて。

方法を自分で選ぶ必要はありません。未対応の方法を近い式で代用することはありません。

## 標準設定

通常の優越性試験で条件が省略されたときだけ、次の標準設定を使います。

| 条件 | 標準設定 |
|---|---|
| 有意水準 | 5% |
| 目標検出力 | 80%、90%、95%の3通り |
| 方向が明らかな1群仮説 | 片側 |
| 通常の2群優越性比較 | 両側 |
| 通常の2群サンプルサイズ設計 | 1:1割付 |

非劣性、同等性、多重性を伴う設計、信頼区間精度、Bayes流設計などには、この標準設定を自動適用しません。マージン、同等性限界、許容誤差、イベント率、分散、相関、脱落率など、結論を変える条件は確認します。

## 主な対応範囲

- 1群・2群・3群以上の平均、割合、発生率、生存時間
- 相関、評価者間一致性、診断精度、基準範囲
- 非劣性、同等性、生物学的同等性
- 反復測定、順序アウトカム、競合リスク、クラスターRCT
- 必要サンプルサイズ、必要イベント数、固定施設数での施設当たり人数
- 対応Calculatorでの達成検出力と検出可能効果
- 脱落調整後人数
- 研究事例との比較、計算条件のレビュー

人数が総数か各群か、割付比の向き、仮説の方向などが計算に影響する場合は確認します。

## 4つのモード

通常はモードを指定する必要はありません。必要なら次の役割を明示できます。

| モード | 用途 |
|---|---|
| `CALCULATE` | 必要条件だけを確認して計算する |
| `STATISTICIAN` | 方法、仮定、感度分析を比較する |
| `TEACHER` | 計算方法と研究事例を解説する |
| `REVIEWER` | プロトコールや論文の記載を検算する |

## 結果の読み方

結果には採用した値、重要な前提、最終人数やイベント数を表示します。必要に応じて群別・系列別人数も示します。脱落を指定していない場合は未調整です。

計算後に「事例も見たい」と入力すると、同じ方法または関連する研究事例を1件提示します。研究事例の値を、今回の未指定条件へ勝手に流用することはありません。

## 品質と出典

同梱する検証済みsamplesize200 Alpha 0.6.9エンジンを使用します。計算方法の主要な出典は『医学のためのサンプルサイズ設計』（田中司朗ほか、2022）です。書籍の章番号や例番号はIDに埋め込まず、追跡用メタデータとして保持します。

本スキルのオリジナル部分はMIT Licenseで提供されます。Copyright (c) 2026 Shiro Tanaka。第三者ソフトウェアには、それぞれのライセンスが適用されます。
