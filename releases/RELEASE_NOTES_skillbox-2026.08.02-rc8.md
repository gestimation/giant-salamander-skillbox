# Giant Salamander Skillbox — 2026.08.02 rc8

This prerelease updates the all-in-one plugin metadata and the OpenAI submission
package after cross-host plugin acceptance.

## Included skills

- `readatable` `0.7.1`
- `reviewcitation` `0.3.4`
- `samplesize200` `1.0.0-rc.7`

## Changes

- advances the all-in-one plugin to `1.0.0-rc.3`
- uses English install-surface descriptions and starter prompts, generated from
  the release configuration
- pins the Codex and Claude Code marketplace catalogs to
  `skillbox-2026.08.02-rc8`
- adds complete English OpenAI submission test cases and strengthens the
  missing-value and unverified-reference fixtures in both languages
- clarifies that no separate gestimation account is required and that
  `reviewcitation` external verification depends on host-provided web access
- expands the English and Japanese privacy and support documentation
- validates that the OpenAI submission copy remains synchronized with the
  release configuration

No calculation formulas, rounding rules, registered procedures, or numerical
results changed in this release candidate. The three single-skill ZIPs and four
cheat-sheet PDFs are unchanged from rc7.

## Assets

| Asset | Files | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `readatable-0.7.1.zip` | 4 | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 4 | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.7.zip` | 118 | 421,101 | `8b2ef987c1dfd1933bfb9b7be321ccbf0bc3bd1dd60405a2a9f5c52bcbead614` |
| `giant-salamander-skillbox-1.0.0-rc.3.zip` | 125 | 450,862 | `193b4ec3ab2c8c00d78746fb4e48a4d65eb3d9a3577d55e22d9ef099671559b7` |
| `skillbox-cheatsheet-ja.pdf` | 1 page | 863,971 | `193e8e6a00d3cbc939174ac5fd3d5eecefc32f0566c79f7455494f92ec05e895` |
| `skillbox-cheatsheet-en.pdf` | 1 page | 573,332 | `942192d6392f9cd037ad8841f5191681b540da6fc12e4c37b03fa7684b07030d` |
| `samplesize200-cheatsheet-ja.pdf` | 2 pages | 864,377 | `074781e525c88d58ec317c71127b5b9a40e0e63a77cc7c00a44796f21cb619e6` |
| `samplesize200-cheatsheet-en.pdf` | 2 pages | 870,631 | `ad7262a0eec34a36d39e248c7a769ad04c2f3d595b2eeceacefd4d2c17ce6193` |

`SHA256SUMS.txt` contains the hashes for the four installation ZIPs.

## Validation status

- deterministic two-build comparison: PASS
- repository release validator: PASS
- OpenAI/Codex plugin validator: PASS
- all-in-one rc.3 ZIP installation and three-skill execution: PASS (user acceptance)
- the published rc7 single-skill ZIP and cheat-sheet hashes remain unchanged: PASS

GitHub Releases is the canonical ZIP distribution source. Published assets are
never replaced without a version change.
