# Giant Salamander Skillbox 1.0.0

Release tag: `skillbox-2026.08.16`

## Stable promotion

This is the first stable four-skill release of Giant Salamander Skillbox. The published release-candidate bundle was installed and operated successfully in Codex, ChatGPT Work, and Claude Code before promotion.

- Includes `readatable` 0.7.1.
- Includes `reviewcitation` 0.3.4.
- Includes `samplesize200` 1.0.0-rc.9. rc.9 updates product and distribution documentation only; engine 0.6.9 and the numerical methods are unchanged.
- Includes `draftcostsheet` 0.2.2.
- Provides one all-in-one plugin with Codex and Claude Code manifests, plus four single-skill ZIPs.

The accepted rc.4 bundle remains available as an immutable prerelease. Stable promotion uses a new tag, bundle version, filename, and checksums rather than rewriting the accepted prerelease.

## Release assets

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `readatable-0.7.1.zip` | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.9.zip` | 420,979 | `971aa1f7234019df167266e2630344a759905192c11b394da34e07a461544cf5` |
| `draftcostsheet-0.2.2.zip` | 10,302 | `cfbcedb66cb6a398a8ebe5c3dafe9b9fedb22dfbac35ae0f57a9d51c9410fdbc` |
| `giant-salamander-skillbox-1.0.0.zip` | 459,600 | `5ce8be85df34ed54cb8a56fa763dff9ad9867ba5e0e2d52064b6bc721ace846e` |

`SHA256SUMS.txt` SHA-256: `016e0e6c604ff44531b9c91008ffeb5268d9b502a8b73afe201efddf6ec71dba`

## Verification

- Deterministic release build and repository release validation passed.
- Codex plugin manifest validation passed.
- All four skill quick validations passed.
- A representative `samplesize200` engine smoke test passed with engine-compatibility and integrity checks enabled.
- Published immutable single-skill asset hashes are retained; changed bytes use the new `samplesize200` rc.9 filename.

The plugin contains no MCP server, custom UI, developer authentication, developer-operated telemetry, or external write action. `draftcostsheet` and `reviewcitation` may use host-provided web access to read public sources when the user requests current source verification.
