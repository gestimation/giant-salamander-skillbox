# OpenAI Plugins Directory申請資料

この文書は`Giant Salamander Skillbox`をSkills-onlyプラグインとして申請する際の
入力原稿です。申請対象はGitHub Releaseと同一内容の
`giant-salamander-skillbox-1.0.0-rc.1.zip`です。

## 申請区分

- Submission type：Skills only
- Plugin ID：`giant-salamander-skillbox`
- Version：`1.0.0-rc.1`
- Developer：`gestimation`
- Category：Productivity
- Authentication：なし
- MCP server：なし
- External write actions：なし

## 公開表示

- Plugin name：Giant Salamander Skillbox
- Short description：研究の表・引用・標本サイズを検証します。
- Long description：統計表を読みやすく再構成するreadatable、科学文書の引用と参考文献を点検するreviewcitation、検証済み計算方法で研究規模を設計するsamplesize200をまとめた研究支援プラグインです。
- Website：<https://github.com/gestimation/giant-salamander-skillbox>
- Support：<https://github.com/gestimation/giant-salamander-skillbox/issues>
- Privacy policy：<https://github.com/gestimation/giant-salamander-skillbox/blob/main/docs/PRIVACY.md>
- Terms of service：<https://github.com/gestimation/giant-salamander-skillbox/blob/main/docs/TERMS.md>

## Starter prompts

1. この統計表を読みやすいMarkdown表に再構成して
2. この文書の引用と参考文献を標準レビューして
3. この研究計画に必要なサンプルサイズを計算して

## データと外部アクセスの説明

プラグイン開発者が運用するサーバーへの送信、利用者アカウント、独自認証、遠隔計測は
ありません。`reviewcitation`の標準レビューでは、利用者の依頼に応じてホスト環境の
検索機能からPubMedなどの公開情報を確認することがあります。`samplesize200`の計算は
同梱スクリプトを利用者の実行環境で実行します。

## 申請時のリリースノート

Initial public submission of Giant Salamander Skillbox, a skills-only plugin
containing readatable 0.7.1, reviewcitation 0.3.4, and samplesize200
1.0.0-rc.6. The submitted bundle is reproducibly built from the public GitHub
release sources and contains no MCP server, authentication, telemetry, or
external write action.

## 申請者がポータルで設定する項目

- OpenAI Platformで確認済みの個人または事業者Identityを選択する。
- `Apps Management: Write`権限を持つ組織から申請する。
- 本番用ロゴをアップロードする。
- 公開対象の国・地域を選択する。
- [申請テストケース](OPENAI_TEST_CASES.md)の正常系5件、異常系3件を登録する。
- 最終ZIPをローカル実機試験後にアップロードする。

ロゴ、Identity、公開地域は申請者の法的・ブランド上の選択であるため、リポジトリの
ビルド処理では自動決定しません。
