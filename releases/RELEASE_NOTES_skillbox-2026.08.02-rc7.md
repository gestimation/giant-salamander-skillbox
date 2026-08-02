# Giant Salamander Skillbox — 2026.08.02 rc7

This prerelease updates the `samplesize200` quick guides and publishes the
final skills-only plugin bundle prepared for OpenAI submission.

## Included skills

- `readatable` `0.7.1`
- `reviewcitation` `0.3.4`
- `samplesize200` `1.0.0-rc.7`

## Changes

- updates the Japanese and English `samplesize200` quick guides for the current
  GitHub Releases, all-in-one ZIP, Codex Marketplace, and Claude Code
  Marketplace installation paths
- restores the Japanese source wording to `田中司朗ほか、2022`
- cites *Sample Size Tables for Clinical Studies*, third edition, in Vancouver
  style in the English guide
- advances the all-in-one plugin to `1.0.0-rc.2`
- pins both marketplace catalogs to `skillbox-2026.08.02-rc7`
- adds the selected navy-and-jade production logo assets for OpenAI submission
- publishes separate Japanese and English cheat sheets for the complete
  Skillbox and for the 20 selected `samplesize200` prompt examples

No calculation formulas, rounding rules, registered procedures, or numerical
results changed in this release candidate.

## Assets

| Asset | Files | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `readatable-0.7.1.zip` | 4 | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 4 | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.7.zip` | 118 | 421,101 | `8b2ef987c1dfd1933bfb9b7be321ccbf0bc3bd1dd60405a2a9f5c52bcbead614` |
| `giant-salamander-skillbox-1.0.0-rc.2.zip` | 125 | 450,866 | `f82c6c5a1a03e9e1e8d2685ed92ebe20b84e4ddbd9eb732c575c6cbace1a8879` |
| `skillbox-cheatsheet-ja.pdf` | 1 page | 863,971 | `193e8e6a00d3cbc939174ac5fd3d5eecefc32f0566c79f7455494f92ec05e895` |
| `skillbox-cheatsheet-en.pdf` | 1 page | 573,332 | `942192d6392f9cd037ad8841f5191681b540da6fc12e4c37b03fa7684b07030d` |
| `samplesize200-cheatsheet-ja.pdf` | 2 pages | 864,377 | `074781e525c88d58ec317c71127b5b9a40e0e63a77cc7c00a44796f21cb619e6` |
| `samplesize200-cheatsheet-en.pdf` | 2 pages | 870,631 | `ad7262a0eec34a36d39e248c7a769ad04c2f3d595b2eeceacefd4d2c17ce6193` |

`SHA256SUMS.txt` contains the hashes for the four installation ZIPs.

## Validation status

- deterministic two-build comparison: PASS
- repository release validator: PASS
- OpenAI/Codex plugin validator: PASS
- `skills` CLI local and public-repository discovery of all three skills: PASS
- `samplesize200` quick-guide help-path smoke test: PASS
- ChatGPT installation and execution of the all-in-one rc.2 ZIP: PASS
- Claude Code installation and execution of the all-in-one rc.2 ZIP: PASS
- Codex Marketplace installation and execution from the rc7 tag: PASS
- all six cheat-sheet PDF pages open and render successfully: PASS

GitHub Releases is the canonical ZIP distribution source. Published assets are
never replaced without a version change.
