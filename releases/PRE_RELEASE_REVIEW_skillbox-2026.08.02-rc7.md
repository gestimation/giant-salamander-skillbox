# GitHub公開前レビュー：skillbox-2026.08.02-rc7

## 現在の判定

`RC7_PUBLISHED_AND_CROSS_HOST_ACCEPTED`

公開済みの`samplesize200-1.0.0-rc.6.zip`を置換せず、クイックガイド更新を
`samplesize200-1.0.0-rc.7.zip`として新規生成した。統合プラグインも
`giant-salamander-skillbox-1.0.0-rc.2.zip`へ更新した。

## 対象バージョン

| Component | Version | Asset |
| --- | --- | --- |
| `readatable` | `0.7.1` | `readatable-0.7.1.zip` |
| `reviewcitation` | `0.3.4` | `reviewcitation-0.3.4.zip` |
| `samplesize200` | `1.0.0-rc.7` | `samplesize200-1.0.0-rc.7.zip` |
| `giant-salamander-skillbox` | `1.0.0-rc.2` | `giant-salamander-skillbox-1.0.0-rc.2.zip` |

## 合格した確認

- 同じソースからの2回連続ビルドで全ZIPのSHA-256が一致
- GitHub公開用バリデーター：PASS
- OpenAI/Codexプラグイン構造バリデーター：PASS
- skills.shの`skills` CLIによるローカルRC7検出：PASS（3スキルを過不足なく検出）
- 正本`skills/`と統合プラグイン内コピー：バイト単位で一致
- samplesize200のヘルプ経路から更新済み日本語クイックガイドを取得：PASS
- readatable 0.7.1とreviewcitation 0.3.4の公開済みハッシュ：不変
- 個人パス、キャッシュ、認証情報、コンパイル済み生成物：配布ZIP内になし
- ChatGPTでrc.2統合ZIPのインストールと実行：PASS（ユーザー実地確認）
- Claude Codeでrc.2統合ZIPのインストールと実行：PASS（ユーザー実地確認）
- Codexでrc7タグを参照するMarketplaceからインストールし、3スキルの実行：PASS（ユーザー実地確認）
- Claude Codeでrc7タグを参照するMarketplaceからインストールし、3スキルの実行：PASS（ユーザー実地確認）
- GitHub公開リポジトリに対する`skills` CLIの検出：PASS（3スキルを過不足なく検出）
- GitHub Releasesから全公開アセットを再取得し、ローカル公開候補とのSHA-256一致を確認：PASS
- 日本語版／英語版、全体版／samplesize200版の4チートシートを公開：PASS
- Notionの配布リンクをGitHub Releaseへ更新：PASS（ユーザー実地確認）
- Claude CLIのstrict validator：未実行。Claude Codeデスクトップでの実地試験を代替証跡として記録

## SHA-256

| Asset | SHA-256 |
| --- | --- |
| `readatable-0.7.1.zip` | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.7.zip` | `8b2ef987c1dfd1933bfb9b7be321ccbf0bc3bd1dd60405a2a9f5c52bcbead614` |
| `giant-salamander-skillbox-1.0.0-rc.2.zip` | `f82c6c5a1a03e9e1e8d2685ed92ebe20b84e4ddbd9eb732c575c6cbace1a8879` |

## 公開結果

- Git tag：`skillbox-2026.08.02-rc7`
- GitHub prerelease：<https://github.com/gestimation/giant-salamander-skillbox/releases/tag/skillbox-2026.08.02-rc7>
- GitHub ReleasesをZIPの唯一の正式配布元として使用
- CodexおよびClaude CodeのMarketplaceはrc7タグを参照
- OpenAI申請ポータルへの提出は別工程として継続
