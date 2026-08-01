# Giant Salamander Skillbox — 2026.08.01 rc6

This prerelease adds one all-in-one plugin for ChatGPT Work, Codex, and Claude
Code while retaining the three previously published single-skill ZIPs.

## Included skills

- `readatable` `0.7.1`
- `reviewcitation` `0.3.4`
- `samplesize200` `1.0.0-rc.6`

## New all-in-one plugin

- plugin ID: `giant-salamander-skillbox`
- plugin version: `1.0.0-rc.1`
- asset: `giant-salamander-skillbox-1.0.0-rc.1.zip`
- OpenAI manifest: `.codex-plugin/plugin.json`
- Claude Code manifest: `.claude-plugin/plugin.json`
- bundled skills: exactly `readatable`, `reviewcitation`, and `samplesize200`

The user-facing cheat sheet remains a separate GitHub Release asset and is not
included in the plugin runtime package.

## Distribution

GitHub Releases remains the canonical source for release ZIPs, versions, and
checksums. The Codex and Claude Code marketplace catalogs are installation
indexes whose plugin source is pinned to the immutable
`skillbox-2026.08.01-rc6` Git tag.

The OpenAI Plugins Directory submission uses the same tested skills-only bundle
as the GitHub Release. OpenAI publication is a reviewed snapshot and requires a
new submission when the bundled skills change.

## Compatibility

- ChatGPT Work: install the all-in-one ZIP unchanged
- Codex: ZIP installation or marketplace installation
- Claude Code: marketplace installation

`samplesize200` requires Python 3.10 or later and SciPy 1.11 or later in the
execution environment. `readatable` and `reviewcitation` are instruction-only.

## Assets

- `readatable-0.7.1.zip`
- `reviewcitation-0.3.4.zip`
- `samplesize200-1.0.0-rc.6.zip`
- `giant-salamander-skillbox-1.0.0-rc.1.zip`
- `SHA256SUMS.txt`
- user-facing cheat sheet PDF or PNG

Final file sizes, hashes, and cross-host test results will be added after the
release candidate passes the publication checklist.
