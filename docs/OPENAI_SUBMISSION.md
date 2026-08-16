# OpenAI Plugins Directory申請原稿

この文書は、`Giant Salamander Skillbox`をSkills-onlyプラグインとして申請する際に、
OpenAI Platformへ転記するための原稿です。公開表示の主言語は英語とし、日本語版も
併記します。申請対象はGitHub Releaseと同一内容の
`giant-salamander-skillbox-1.0.0.zip`です。

## 1. Submission type

- Submission type: Skills only
- Plugin ID: `giant-salamander-skillbox`
- Version: `1.0.0`
- Developer identity: `gestimation`
- Category: Productivity
- Supported languages: English and Japanese
- Authentication: None
- MCP server: None
- External write actions: None
- Test account or credentials: Not required

## 2. Public listing copy — English

### Plugin name

```text
Giant Salamander Skillbox
```

### Short description

```text
Tables, citations, size & cost
```

### Long description

```text
Giant Salamander Skillbox combines readatable for reconstructing statistical tables, reviewcitation for checking citations and public bibliographic records when host web access is available, and samplesize200 for validated sample-size, event, power, and detectable-effect calculations. It also includes draftcostsheet for traceable medical-cost sheets using authoritative unit-cost sources when host web access is available. No separate gestimation account or authentication is required, and user content is not sent to a gestimation-operated server.
```

## 3. 公開表示用文面 — 日本語

### プラグイン名

```text
Giant Salamander Skillbox
```

### 短い説明

```text
統計表・引用・研究規模・医療費推計を支援します。
```

### 詳しい説明

```text
Giant Salamander Skillboxは、統計表を再構成するreadatable、ホスト環境のウェブアクセスが利用できる場合に引用と公開書誌情報を点検するreviewcitation、検証済みの方法でサンプルサイズ、イベント数、達成検出力、検出可能差を計算するsamplesize200、ならびに公的単価資料を用いて追跡可能な医療費シートを作成するdraftcostsheetをまとめた研究支援プラグインです。gestimationの別アカウントや独自認証は不要で、利用者のコンテンツをgestimationが運用するサーバーへ送信しません。
```

## 4. Listing metadata

- Website: <https://github.com/gestimation/giant-salamander-skillbox>
- Support: <https://github.com/gestimation/giant-salamander-skillbox/issues>
- Support email: `gestimation@gmail.com`
- Privacy policy: <https://github.com/gestimation/giant-salamander-skillbox/blob/main/docs/PRIVACY.md>
- Terms of service: <https://github.com/gestimation/giant-salamander-skillbox/blob/main/docs/TERMS.md>
- Logo: `branding/openai-submission/final/giant-salamander-skillbox-logo-1024-background.png`
- Screenshots: None; the plugin has no custom UI.

## 5. Starter prompts — English

1. `Use readatable to reconstruct this statistical table while preserving headers, units, sample sizes, and footnotes.`
2. `Use reviewcitation to reconcile in-text citations with the reference list and flag items needing verification.`
3. `Use samplesize200 for study size or draftcostsheet for a source-linked medical-cost sheet.`

## 6. スタータープロンプト — 日本語

1. `readatableを使って、この統計表を見出し、単位、対象者数、脚注を保った読みやすいMarkdown表に再構成して。`
2. `reviewcitationを使って、本文中の引用と参考文献一覧を照合し、バンクーバー系書式を点検して、確認が必要な項目を報告して。`
3. `samplesize200で研究規模を設計するか、draftcostsheetで出典付きの医療費シートを作成して。`

## 7. Data handling and external access — English

### Concise portal answer

```text
No user content is transmitted to or retained by gestimation. The plugin has no developer-operated server, user account, authentication system, telemetry, or external write action. Processing occurs in the execution environment provided by ChatGPT or Codex. When the user requests external verification, reviewcitation may use host-provided web search to consult public sources such as PubMed, and draftcostsheet may consult public clinical and unit-cost sources. samplesize200 runs bundled calculation scripts in the host-provided execution environment. Data handled by ChatGPT, Codex, web search providers, or other host-provided services remains subject to those providers' terms and retention policies.
```

### Permissions and external services

- Developer-operated storage: None
- Developer-operated telemetry or analytics: None
- Developer authentication: None
- External write actions: None
- External read access: Only when requested and available through host-provided tools; for example, PubMed verification by `reviewcitation` or public unit-cost retrieval by `draftcostsheet`
- Sensitive data requirement: None. Users should avoid sharing information they are not authorized to process in their host environment.

## 8. データ処理と外部アクセス — 日本語

```text
利用者のコンテンツをgestimationへ送信またはgestimationが管理する環境へ保存することはありません。本プラグインには、開発者が運用するサーバー、利用者アカウント、独自認証、遠隔計測、外部への書き込み操作がありません。処理はChatGPTまたはCodexが提供する実行環境で行われます。利用者が外部確認を依頼した場合、reviewcitationはホスト環境のウェブ検索を使ってPubMedなどの公開情報を参照し、draftcostsheetは公開された臨床資料や単価資料を参照することがあります。samplesize200は同梱された計算スクリプトをホスト環境で実行します。ChatGPT、Codex、検索サービスなどが取り扱うデータには、各サービスの利用規約および保存方針が適用されます。
```

## 9. Reviewer notes — English

```text
This is a skills-only plugin with no MCP server and no custom UI. It requires no authentication, test account, demo credentials, or external setup, and it performs no external write actions. The four-skill release candidate was installed and exercised successfully in ChatGPT, Codex, and Claude Code before stable promotion; the stable package changes release metadata and product documentation, not skill behavior or numerical methods. Web-enabled test cases use host-provided search to verify public bibliographic or unit-cost sources; the remaining test cases require no developer-operated service. The plugin includes four independently triggered skills: readatable, reviewcitation, samplesize200, and draftcostsheet.
```

## 10. Release notes — English

```text
Giant Salamander Skillbox 1.0.0 is the first stable four-skill bundle. It contains readatable 0.7.1, reviewcitation 0.3.4, samplesize200 1.0.0-rc.9, and draftcostsheet 0.2.2. The release-candidate bundle was installed and exercised successfully in ChatGPT Work, Codex, and Claude Code before stable promotion. samplesize200 rc.9 changes only product and distribution documentation; its engine remains 0.6.9 and its numerical methods are unchanged. The submitted bundle is reproducibly built from the public GitHub release sources. It contains no MCP server, custom UI, authentication, developer-operated telemetry, or external write action. No test account or setup is required.
```

## 11. 公開地域

申請画面では、サポートと法的文書を提供できる範囲として、OpenAIが選択可能にしている
すべての国・地域を選ぶ方針とします。特定地域で追加条件が表示された場合は、条件を
確認してからその地域を選択します。

## 12. Test cases

- Portal entry copy in English: [OPENAI_TEST_CASES_EN.md](OPENAI_TEST_CASES_EN.md)
- Japanese reference: [OPENAI_TEST_CASES.md](OPENAI_TEST_CASES.md)

正常系5件、異常系3件を登録します。各ケースには、利用者のプロンプト、期待する動作、
期待する成果物の形、再現に必要なデータ、または安全なフォールバックの理由を含めます。

## 13. Portal-only settings

- OpenAI Platformで確認済みの`gestimation`のDeveloper Identityを選択する。
- `Apps Management: Write`権限を持つ組織から申請する。
- 本番用ロゴをアップロードし、縮小表示と正方形クロップを確認する。
- Submission typeで`Skills only`を選択する。
- 最終ZIPをアップロードし、スキルの自動スキャン結果を確認する。
- 公開地域、スタータープロンプト、テストケース、リリースノートを登録する。
- 公開文面、ZIP、ポリシーURLが一致していることを確認してからattestationを行う。

Identity、公開地域、attestationは申請者の法的・アカウント上の選択であるため、
リポジトリのビルド処理では自動決定しません。
