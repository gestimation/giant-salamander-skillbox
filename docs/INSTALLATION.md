# Giant Salamander Skillboxのインストール

正式なリリース、ZIP、バージョン、SHA-256チェックサムは、GitHub Releasesで
公開します。Dropboxは配布元として使用しません。

## 初めて使う場合

3スキルをまとめた`giant-salamander-skillbox`のインストールを推奨します。

収録スキル：

- `readatable`：統計表を読みやすく再構成する
- `reviewcitation`：引用と参考文献を点検する
- `samplesize200`：研究に必要なサンプルサイズを設計する

## ChatGPT Work／CodexでZIPを使う

1. [GitHub Releases](https://github.com/gestimation/giant-salamander-skillbox/releases)を開く。
2. `giant-salamander-skillbox-1.0.0-rc.1.zip`をダウンロードする。
3. ZIPを展開せず、そのままプラグインとしてインストールする。
4. 新しいタスクでスキル名を指定して試す。

必要なスキルだけを使う場合は、個別のZIPも選べます。

## Codexでマーケットプレイスを使う

```text
codex plugin marketplace add gestimation/giant-salamander-skillbox
codex plugin add giant-salamander-skillbox@giant-salamander-skillbox
```

インストール後は新しいタスクを開始し、`$readatable`、`$reviewcitation`、
`$samplesize200`を指定して動作を確認します。

## Claude Codeでマーケットプレイスを使う

```text
claude plugin marketplace add gestimation/giant-salamander-skillbox
claude plugin install giant-salamander-skillbox@giant-salamander-skillbox
```

開いているセッションでは`/reload-plugins`を実行します。明示的に呼び出す場合は
次の名前を使用します。

```text
/giant-salamander-skillbox:readatable
/giant-salamander-skillbox:reviewcitation
/giant-salamander-skillbox:samplesize200
```

## 実行環境

`readatable`と`reviewcitation`は指示中心のスキルです。`samplesize200`は実行環境に
Python 3.10以上とSciPy 1.11以上を必要とします。依存関係がない場合は、計算結果を
推測せず、不足している実行環境を確認してください。

## 更新と真正性の確認

マーケットプレイスの各プラグイン取得先は、GitHub Releaseに対応する不変のGitタグへ
固定します。ZIPの真正性は、同じReleaseにある`SHA256SUMS.txt`と照合できます。

公開済みZIPは同じファイル名のまま置換しません。変更時は必ずバージョンを更新します。
