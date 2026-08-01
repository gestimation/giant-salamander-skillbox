# Giant Salamander Skillboxのインストール

正式なリリース、ZIP、バージョン、SHA-256チェックサムは、GitHub Releasesで
公開します。Dropboxは配布元として使用しません。

## 初めて使う場合

3スキルをまとめた`giant-salamander-skillbox`のインストールを推奨します。

収録スキル：

- `readatable`：統計表を読みやすく再構成する
- `reviewcitation`：引用と参考文献を点検する
- `samplesize200`：研究に必要なサンプルサイズを設計する

## ZIPによる手動インストール

1. [GitHub Releases](https://github.com/gestimation/giant-salamander-skillbox/releases)を開く。
2. 3スキルを収録した`giant-salamander-skillbox-1.0.0-rc.1.zip`、または必要な
   スキルだけを収録した個別プラグインZIPをダウンロードする。
3. ChatGPT Work、CodexまたはClaude Codeのプラグイン画面で、ZIPを展開・再圧縮
   せず、そのまま指定してインストールする。
4. 新しいチャットまたはタスクで、インストールしたスキル名が表示され、使用できる
   ことを確認する。

統合ZIPと個別ZIPは重複してインストールしません。個別ZIPを複数使用する場合は、
1つずつ指定します。必要に応じてアプリを再起動するか、プラグインを再読み込みします。

## CodexでMarketplaceを使う

GitHub Marketplaceとして`gestimation/giant-salamander-skillbox`を登録し、統合
プラグインをインストールします。

```text
codex plugin marketplace add gestimation/giant-salamander-skillbox
codex plugin add giant-salamander-skillbox@giant-salamander-skillbox
```

インストール後は新しいタスクを開始し、`$readatable`、`$reviewcitation`、
`$samplesize200`を指定して動作を確認します。

## Claude CodeでMarketplaceを使う

Claude Code Desktopでは、チャット入力欄から次のスラッシュコマンドを実行します。

```text
/plugin marketplace add gestimation/giant-salamander-skillbox
/plugin install giant-salamander-skillbox@giant-salamander-skillbox
/reload-plugins
```

明示的に呼び出す場合は次の名前を使用します。

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
