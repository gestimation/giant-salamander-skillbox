# Giant Salamander Skillbox 1.0.0-rc.4

Release tag: `skillbox-2026.08.10-rc10`

## Changes

- Adds `draftcostsheet` 0.2.2, an instruction-only skill for drafting traceable medical-cost sheets from authoritative clinical and unit-cost sources.
- Expands the all-in-one plugin from three to four independently triggered skills.
- Updates the OpenAI submission copy and test cases for medical-cost estimation and safe handling of unavailable monetary evidence.
- Publishes `samplesize200` 1.0.0-rc.8 as a packaging-normalization release. Its engine remains 0.6.9; calculation methods and numerical behavior are unchanged.
- Keeps `readatable` 0.7.1 and `reviewcitation` 0.3.4 unchanged, including their previously published asset bytes.

## Release assets

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `readatable-0.7.1.zip` | 10,159 | `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a` |
| `reviewcitation-0.3.4.zip` | 20,820 | `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad` |
| `samplesize200-1.0.0-rc.8.zip` | 420,986 | `88643f5c1635ae2371cbfd3db5a381fa6593a1540bf6360d1f53abc02091a1f5` |
| `draftcostsheet-0.2.2.zip` | 10,302 | `cfbcedb66cb6a398a8ebe5c3dafe9b9fedb22dfbac35ae0f57a9d51c9410fdbc` |
| `giant-salamander-skillbox-1.0.0-rc.4.zip` | 459,620 | `a6f2dfbd606c0646d2032e0006a29185866b1e6c28dc8d280ea7c5726921770d` |

`SHA256SUMS.txt` SHA-256: `c66451d9ce111e43c159a68117bd1b5c9b99ee658fdafe7d931cb27326fa7609`

## Verification performed

- Built the five ZIP assets twice and confirmed byte-for-byte deterministic SHA-256 output.
- Passed the repository release validator for 4 skills, 122 canonical source files, 127 bundle files, and 5 release ZIPs.
- Passed the Codex plugin manifest validator.
- Passed the skill quick validator for all four skills.
- Ran a `samplesize200` engine smoke test for `TWO-B-002`; the result was 392 participants (196 per group), with dependency and engine-compatibility checks passing.

The plugin contains no MCP server, custom UI, developer authentication, developer-operated telemetry, or external write action. `draftcostsheet` and `reviewcitation` may use host-provided web access to read public sources when the user requests current source verification.
