# Giant Salamander Skillbox — 2026.08.02 rc7

This prerelease updates the samplesize200 quick guides and prepares the final
skills-only plugin bundle for OpenAI submission.

## Included skills

- `readatable` `0.7.1`
- `reviewcitation` `0.3.4`
- `samplesize200` `1.0.0-rc.7`

## Changes

- updates the Japanese and English samplesize200 quick guides for the current
  GitHub Releases, all-in-one ZIP, Codex marketplace, and Claude Code
  marketplace installation paths
- restores the Japanese source wording to `田中司朗ほか、2022`
- cites *Sample Size Tables for Clinical Studies*, third edition, in Vancouver
  style in the English guide
- advances the all-in-one plugin to `1.0.0-rc.2`
- pins both marketplace catalogs to `skillbox-2026.08.02-rc7`
- adds the selected navy-and-jade production logo assets for OpenAI submission

No calculation formulas, rounding rules, registered procedures, or numerical
results changed in this release candidate.

## Assets

| Asset | Files | Bytes | SHA-256 |
| --- | ---: | ---: | --- |
| `readatable-0.7.1.zip` | 4 | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 4 | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.7.zip` | 118 | 421,101 | `8b2ef987c1dfd1933bfb9b7be321ccbf0bc3bd1dd60405a2a9f5c52bcbead614` |
| `giant-salamander-skillbox-1.0.0-rc.2.zip` | 125 | 450,866 | `f82c6c5a1a03e9e1e8d2685ed92ebe20b84e4ddbd9eb732c575c6cbace1a8879` |

`SHA256SUMS.txt` contains the same four hashes.

## Validation status

- deterministic two-build comparison: PASS
- repository release validator: PASS
- OpenAI/Codex plugin validator: PASS
- skills.sh `skills` CLI local discovery of all three skills: PASS
- samplesize200 quick-guide help-path smoke test: PASS
- ChatGPT installation and execution test of the new rc.2 ZIP: PASS
- Claude Code installation and execution test of the new rc.2 ZIP: PASS
- Codex installation retest and post-publication marketplace refresh: pending

GitHub Releases remains the canonical distribution source. Published assets are
never replaced without a version change.
