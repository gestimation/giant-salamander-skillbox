# Giant Salamander Skillbox — 2026.07.31 rc5

This release standardizes the public skill names and release assets in
lowercase, makes GitHub Releases the single official distribution source, and
updates all three skills.

## Included skills

- `readatable` `0.7.1`
- `reviewcitation` `0.3.4`
- `samplesize200` `1.0.0-rc.6`

## Changes

### readatable 0.7.1

- replaces the previously published `0.4.1` skill with the compact
  single-file `0.7.1` contract
- clarifies source-faithful reconstruction, readable cleanup, and atomic
  semantic export boundaries
- adds structured provenance and the `readatable.parsed_items` interoperability
  contract
- adds a guarded, once-per-request handoff to READP after the requested table
  work is complete
- does not certify a reconstructed table as fully analysis-ready

### reviewcitation 0.3.4

- establishes `0.3.4` as the official release derived from `0.3.3`
- standardizes the skill name and public references as `reviewcitation`
- does not include the separately evaluated experimental `0.4.0` line

### samplesize200 1.0.0-rc.6

- standardizes the skill name, runtime labels, documentation, schemas,
  quick-guide filenames, and release asset as `samplesize200`
- updates the bundled engine metadata to samplesize200 Alpha `0.6.9`
- corrects the ONE-S-001 citation from *Pharmaceutical Statistics* `20(2)` to
  `20(3)` and adds `references/source_corrections.yaml`
- fixes the lowercase Japanese quick-guide path used by `scripts/show_help.py`
- excludes caches, `.Rhistory`, and compiled Python artifacts from the release
  package
- preserves the formulas, rounding rules, and numerical results from rc.5;
  the rc.5 engine update itself contained citation and version metadata changes
  only relative to rc.4

## Distribution

- GitHub Releases is the only official distribution source.
- Dropbox is no longer maintained as a distribution source.
- Skill names and release ZIP filenames are lowercase.
- Each ZIP is a skills-only plugin containing exactly one skill.
- Each plugin includes `.codex-plugin/plugin.json` and stores the unchanged
  canonical skill source under `skills/<skill-name>/`.
- Published assets are versioned and are not replaced in place.

Download the required ZIP and install it unchanged through the supported
plugin installation flow in ChatGPT Work or Codex.

## Validation

- repository release build and validation: PASS
- OpenAI plugin-creator validation for all three extracted plugins: PASS
- ChatGPT installation, lowercase display names, invocation, and representative
  operations for all three plugins: PASS
- readatable `0.7.1` contract validation: PASS
- samplesize200 complete rc.6 suite: `669 passed`
- documented samplesize200 Alpha `0.6.9` engine regression: `11,945 passed`
- extracted ZIP and samplesize200 help-path smoke test: PASS
- forbidden generated files, personal paths, and secrets: none found

## Assets

- `readatable-0.7.1.zip`
  - 4 files
  - SHA-256:
    `cc6621ccf896bef7814ee5f9fc8ea7b60d58997ede17e8f427d150b3bffd5a0a`
- `reviewcitation-0.3.4.zip`
  - 4 files
  - SHA-256:
    `8475b87ac2730e099043073d1d055e1c16fd2909020c96a7c1299e1aa585aaad`
- `samplesize200-1.0.0-rc.6.zip`
  - 118 files
  - SHA-256:
    `126f02f17c51dc041aaad58c3d040958722b1066bbdefd25be28fbb037a6348c`
- `SHA256SUMS.txt`

## Runtime requirement

`samplesize200` requires Python `3.10` or later and SciPy `1.11` or later in
the execution environment. The remaining runtime files, including the vendored
YAML dependency, are included in the skill.
