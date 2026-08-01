# GitHub公開前レビュー：skillbox-2026.08.01-rc6

## 現在の判定

`IMPLEMENTED_PENDING_CROSS_HOST_TESTS`

3スキル同梱プラグイン、Codex／Claude Codeマーケットプレイス、再現可能ビルド、
公開用文書、OpenAI申請原稿、正常系5件・異常系3件の申請テストケースを実装しました。

自動検証とClaude Codeデスクトップでの一括ZIP試験は合格しています。GitHub公開と
OpenAI申請の前に、ChatGPT WorkとCodexでの一括版試験、Codex／Claude Codeの
マーケットプレイス経由試験、および申請者が決めるロゴ、Identity、公開地域の確認が
必要です。

## 公開予定

- タグ案：`skillbox-2026.08.01-rc6`
- Release名案：`Giant Salamander Skillbox — 2026.08.01 rc6`
- 種別：Pre-release
- 正式なリリース記録とZIP配布元：GitHub Releases
- マーケットプレイスの取得先：上記タグへ固定

## 対象バージョン

| Component | Version | Asset |
| --- | --- | --- |
| `readatable` | `0.7.1` | `readatable-0.7.1.zip` |
| `reviewcitation` | `0.3.4` | `reviewcitation-0.3.4.zip` |
| `samplesize200` | `1.0.0-rc.6` | `samplesize200-1.0.0-rc.6.zip` |
| `giant-salamander-skillbox` | `1.0.0-rc.1` | `giant-salamander-skillbox-1.0.0-rc.1.zip` |

## 実装済み

- 一括プラグインに`.codex-plugin/plugin.json`と`.claude-plugin/plugin.json`を収録
- 一括プラグインに3スキルを正本から無変更で収録
- `.agents/plugins/marketplace.json`を追加
- `.claude-plugin/marketplace.json`を追加
- 両マーケットプレイスの取得先を`skillbox-2026.08.01-rc6`へ固定
- 個別3 ZIPを維持
- チートシートをプラグイン内部へ含めない構造を維持
- OpenAI申請原稿、プライバシーポリシー、利用規約、サポート文書を追加
- OpenAI申請用の正常系5件・異常系3件を追加

## 合格した自動確認

- Python構文検査：PASS
- GitHub公開用ビルド：PASS
- 同じソースからの2回連続ビルド：全ZIPのSHA-256が一致
- GitHub公開用バリデーター：PASS
- OpenAI plugin-creator検証：PASS
- 正本`skills/`と一括プラグインのコピー：バイト単位で一致
- 一括ZIPと生成プラグインディレクトリ：バイト単位で一致
- 個別3 ZIP：公開済みSHA-256から変化なし
- 4 ZIPと`SHA256SUMS.txt`：一致
- Git差分の末尾空白エラー：0件
- Claude Codeデスクトップで一括ZIPを変更せずインストール：PASS
- Claude Codeデスクトップで一括プラグインの読み込みと動作：PASS

## 現在のZIP

| Asset | Files | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `readatable-0.7.1.zip` | 4 | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 4 | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.6.zip` | 118 | 420,296 | `126f02f17c51dc041aaad58c3d040958722b1066bbdefd25be28fbb037a6348c` |
| `giant-salamander-skillbox-1.0.0-rc.1.zip` | 125 | 450,061 | `772eeb748cfceb40b5e8d59c0f62469f797767286aa37b13610a4a90a1095896` |

## 公開前に残る確認

- Claude Code CLIを導入した環境で`claude plugin validate --strict`を実行する。
- ChatGPT Workで一括ZIPをインストールし、表示名と3スキルを確認する。
- Codexでマーケットプレイス追加、インストール、新規タスクでの呼び出しを確認する。
- Claude Codeでマーケットプレイス追加、インストール、リロード、3スキル個別の代表操作を確認する。
- Python 3.10以上とSciPy 1.11以上がある環境で`samplesize200`の代表計算を実行する。
- 本番ロゴ、OpenAI Platformの確認済みIdentity、公開地域を決める。
- チートシートのPDFまたはPNGをRelease添付用に確定する。
