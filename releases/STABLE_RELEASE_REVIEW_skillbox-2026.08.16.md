# Stable release review: skillbox-2026.08.16

Review date: 2026-08-16

## Scope

- Bundle: `giant-salamander-skillbox` 1.0.0
- Skills: `readatable` 0.7.1, `reviewcitation` 0.3.4, `samplesize200` 1.0.0-rc.9, `draftcostsheet` 0.2.2
- Stable tag: `skillbox-2026.08.16`
- Acceptance basis: published rc.4 integrated ZIP, recorded in `CROSS_HOST_ACCEPTANCE_skillbox-2026.08.10-rc10.md`

## Acceptance and automated gates

| Gate | Status |
| --- | --- |
| Codex user acceptance | PASS |
| ChatGPT Work user acceptance | PASS |
| Claude Code user acceptance | PASS |
| Deterministic release build | PASS |
| Release-tree and checksum validation | PASS |
| Plugin manifest validation | PASS |
| Four skill quick validations | PASS |
| `samplesize200` engine smoke test | PASS |

## Promotion audit

- The accepted rc.4 tag and assets remain unchanged and available as historical prerelease evidence.
- Stable promotion uses a new semantic bundle version, new tag, and new bundle filename.
- `readatable`, `reviewcitation`, and `draftcostsheet` single-skill assets retain their published bytes and hashes.
- `samplesize200` advances to rc.9 because its product metadata and quick guide now identify the stable bundle. Engine 0.6.9, calculators, fixtures, and numerical methods are unchanged.
- The stable plugin tree contains exactly four skills and both `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json`.
- No credentials, private validation records, local absolute paths, caches, or compiled artifacts are included.

## Publication decision

The four-skill bundle is approved for a non-prerelease GitHub Release after the release commit is merged and the generated asset hashes are reconfirmed against the immutable tag.

Status: **approved for stable publication**.
