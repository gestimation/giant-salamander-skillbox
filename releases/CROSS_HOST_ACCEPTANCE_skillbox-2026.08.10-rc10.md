# Cross-host acceptance: skillbox-2026.08.10-rc10

Acceptance recorded: 2026-08-16

## Artifact under test

- Release: `skillbox-2026.08.10-rc10`
- Bundle: `giant-salamander-skillbox-1.0.0-rc.4.zip`
- Bundle SHA-256: `a6f2dfbd606c0646d2032e0006a29185866b1e6c28dc8d280ea7c5726921770d`
- Included skills: `readatable` 0.7.1, `reviewcitation` 0.3.4, `samplesize200` 1.0.0-rc.8, and `draftcostsheet` 0.2.2

## User acceptance results

| Host | Result |
| --- | --- |
| Codex | PASS — the integrated ZIP installed and operated successfully |
| ChatGPT Work | PASS — the integrated ZIP installed and operated successfully |
| Claude Code | PASS — the integrated ZIP installed and operated successfully |

The results were reported by the release owner after testing the published integrated ZIP. Host version numbers and detailed execution transcripts were not retained in this repository, so this record is user acceptance evidence rather than an automated conformance test.

## Promotion decision

The accepted four-skill configuration is approved for promotion to the stable `giant-salamander-skillbox` 1.0.0 bundle. Stable promotion changes bundle release metadata and packaging identity. `samplesize200` advances to rc.9 only to update product and distribution documentation; its engine remains 0.6.9 and its numerical methods are unchanged.
