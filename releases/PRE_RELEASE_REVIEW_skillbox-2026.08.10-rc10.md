# Pre-release review: skillbox-2026.08.10-rc10

Review date: 2026-08-10

## Scope

- Bundle: `giant-salamander-skillbox` 1.0.0-rc.4
- Skills: `readatable` 0.7.1, `reviewcitation` 0.3.4, `samplesize200` 1.0.0-rc.8, `draftcostsheet` 0.2.2
- Candidate tag: `skillbox-2026.08.10-rc10`

## Automated review status

| Check | Status |
| --- | --- |
| Deterministic release build | PASS |
| Release-tree and checksum validation | PASS |
| Plugin manifest validation | PASS |
| Four skill quick validations | PASS |
| `samplesize200` engine smoke test | PASS |
| Draftcostsheet canonical-source hash preserved | PASS |

The canonical `skills/draftcostsheet/SKILL.md` matches the approved 0.2.2 source with SHA-256 `fdbd7c06601b952f6c3966eb534292c5e4438d5e71e6c7beacfcc04b74b323a7`.

## Release policy checks

- Existing published asset names are not reused for changed bytes.
- `samplesize200` was advanced from rc.7 to rc.8 because the current reproducible build normalizes line endings in generated catalogs; the engine and numerical methods did not change.
- The individual plugin and all-in-one bundle manifests use valid semantic versions.
- No credentials, private source documents, validation-corpus records, or local absolute paths are included in the release tree.
- No developer-operated external service or write permission is introduced.

## Remaining publication gates

- Review and merge the draft pull request.
- Build from the merged commit or immutable tag and confirm the recorded hashes.
- Create the GitHub prerelease, upload the five ZIP assets and `SHA256SUMS.txt`, and verify the uploaded assets.
- Perform cross-host installation checks in the intended public hosts where available.

Status: **ready for draft pull request; not yet a public GitHub release**.
