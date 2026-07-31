# GitHub公開前レビュー：skillbox-2026.07.31-rc5

## 判定

`READY_FOR_GITHUB_RELEASE`

3つの配布物を、それぞれ1スキル入りのスキル専用プラグインZIPへ変更しました。
ソース、プラグインマニフェスト、チェックサム、回帰テスト、展開後の実行確認は
合格しています。ChatGPTでの実インストール、表示名、呼び出し、代表操作も
確認済みです。

## 公開予定

- タグ案：`skillbox-2026.07.31-rc5`
- Release名案：`Giant Salamander Skillbox — 2026.07.31 rc5`
- 種別：Pre-release
- 正式配布元：GitHub Releases
- Dropbox配布：廃止

## 対象バージョン

| Skill | Version | Asset |
| --- | --- | --- |
| `readatable` | `0.7.1` | `readatable-0.7.1.zip` |
| `reviewcitation` | `0.3.4` | `reviewcitation-0.3.4.zip` |
| `samplesize200` | `1.0.0-rc.6` | `samplesize200-1.0.0-rc.6.zip` |

## 解決した重要指摘

### P0：ChatGPT WorkのWeb配布形式と旧ZIP形式が異なる

変更前の3つのZIPは、アーカイブ直下に`SKILL.md`を置く単体スキル形式で、
`.codex-plugin/plugin.json`を含んでいませんでした。

2026-07-31に取得したOpenAI公式マニュアルでは、他者がChatGPT WorkのWebで
インストールできる形で再利用可能なスキルを配布する場合、スキルをプラグインに
パッケージする方法が案内されています。スキル専用プラグインの最小構造は次の
とおりです。

```text
plugin-name/
├── .codex-plugin/
│   └── plugin.json
└── skills/
    └── skill-name/
        └── SKILL.md
```

公開用ビルダーを変更し、現在のZIPは次の構造になっています。

```text
.codex-plugin/plugin.json
LICENSE
skills/<skill-name>/SKILL.md
skills/<skill-name>/LICENSE
```

`samplesize200`では、同じスキルディレクトリの下にエンジン、スクリプト、参照資料、
スキーマ、vendored依存関係を格納しています。READMEもこのインストール形式へ
更新しました。

参考：

- <https://developers.openai.com/plugins/build/skills>
- <https://developers.openai.com/plugins/build/plugins>

## レビュー中に修正した指摘

### P1：小文字化後のクイックガイド参照がWindows以外で失敗する

`samplesize200`の実ファイルは
`references/samplesize200_quick_guide_ja.md`へ改名されていましたが、
`scripts/show_help.py`は
`references/samplesize200_QUICK_GUIDE_JA.md`を参照していました。
Windowsでは大文字小文字を区別しないため既存テストを通過していましたが、
大文字小文字を区別する環境ではヘルプ表示に失敗します。

参照を完全な小文字へ修正し、ファイル名を厳密比較する回帰テストと公開物
バリデーターの確認を追加しました。

## 合格した確認

- GitHub公開用ビルド：PASS
- GitHub公開用バリデーター：PASS
- OpenAI plugin-creator検証：3プラグインすべてPASS
- `samplesize200`全テスト：`669 passed`
- `readatable 0.7.1`契約検証：PASS
- 3 ZIPの展開とプラグイン構造確認：PASS
- プラグイン内からの`samplesize200`クイックガイド表示：PASS
- READMEの相対リンク：すべて存在
- 現行ソースの旧大文字スキル表記：0件
- 現行ソースの旧バージョン表記：0件
- 禁止キャッシュ・生成物・個人パス・秘密情報：0件
- ZIPの絶対パス、`..`、危険なパス：0件
- ZIPチェックサム：一致
- Git差分の末尾空白エラー：0件

## 現在の1スキル入りプラグインZIP

| Asset | Files | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `readatable-0.7.1.zip` | 4 | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 4 | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.6.zip` | 118 | 420,763 | `ec04aae11ecc311d71c9bc2a27e6ff1347dce1e5779dd72576b8570940389cbd` |

## ChatGPT実インストール確認

- 3つのZIPをそれぞれ変更せずインストール：PASS
- ChatGPT上の表示名とスキル名が小文字：PASS
- `readatable`の呼び出しと代表操作：PASS
- `reviewcitation`の呼び出しと代表操作：PASS
- `samplesize200`の呼び出しと代表操作：PASS

次バージョンへの更新試験は、更新版を作成した時点で確認します。現在の新規公開を
妨げる項目ではありません。
