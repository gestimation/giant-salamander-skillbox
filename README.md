# Giant Salamander Skillbox

Installable research-support skills for ChatGPT Work, Codex, and Claude Code.

## Skills

| Skill | Version | Purpose |
| --- | --- | --- |
| [readatable](skills/readatable/) | 0.7.1 | Improves the readability and presentation of tables. |
| [reviewcitation](skills/reviewcitation/) | 0.3.4 | Reviews citation placement and reference consistency. |
| [samplesize200](skills/samplesize200/) | 1.0.0-rc.9 | Supports reproducible sample-size planning workflows. |
| [draftcostsheet](skills/draftcostsheet/) | 0.2.2 | Drafts traceable medical-cost sheets from authoritative sources. |

## Installation

### Recommended: install all four skills

Open the repository's
[Releases](https://github.com/gestimation/giant-salamander-skillbox/releases)
page and download `giant-salamander-skillbox-1.0.0.zip`. Install the ZIP
unchanged in ChatGPT Work, Codex, or Claude Code.

For Codex marketplace installation:

```text
codex plugin marketplace add gestimation/giant-salamander-skillbox
codex plugin add giant-salamander-skillbox@giant-salamander-skillbox
```

For Claude Code Desktop marketplace installation, run these slash commands in
the chat input:

```text
/plugin marketplace add gestimation/giant-salamander-skillbox
/plugin install giant-salamander-skillbox@giant-salamander-skillbox
/reload-plugins
```

Claude Code namespaces the skills as
`/giant-salamander-skillbox:readatable`,
`/giant-salamander-skillbox:reviewcitation`,
`/giant-salamander-skillbox:samplesize200`, and
`/giant-salamander-skillbox:draftcostsheet`.

### Install one skill only

Download the corresponding single-skill ZIP from the Releases page and install
it unchanged in ChatGPT Work or Codex.

Do not extract or repackage a ZIP. The all-in-one plugin contains both
`.codex-plugin/plugin.json` and `.claude-plugin/plugin.json`, plus all four
skills. The individual ZIPs remain one-skill plugins for ChatGPT Work and Codex.

The directories under `skills/` are the canonical skill sources. The release
builder copies them unchanged into individual ZIPs and the generated all-in-one
plugin under `plugins/giant-salamander-skillbox/`.

See [Installation](docs/INSTALLATION.md) for beginner-oriented steps. The
user-facing cheat sheet is distributed as a separate release asset and is not
included in the plugin runtime package.

## Runtime requirements

readatable, reviewcitation, and draftcostsheet are instruction-only skills.

samplesize200 requires Python 3.10 or later and SciPy 1.11 or later in the execution environment. Its remaining runtime files, including its vendored YAML dependency, are included in the skill directory. Start with the [quick guide](skills/samplesize200/references/samplesize200_quick_guide.md); the [Python API](skills/samplesize200/references/PYTHON_API_1_0.md) and [solution catalog](skills/samplesize200/references/SOLUTION_CATALOG_1_0.md) provide further detail.

## Naming

Skill names are written in lowercase everywhere: `readatable`,
`reviewcitation`, `samplesize200`, and `draftcostsheet`. Release ZIP filenames use the same
lowercase names.

## Release integrity

Release assets are built from the directories under `skills/`. Plugin and
marketplace metadata is defined once in `tools/release_config.py`. Marketplace
entries point to the immutable Git tag associated with the release rather than
to a mutable branch. Every release includes `SHA256SUMS.txt` so downloaded ZIP
files can be verified. A published asset is never replaced without a version
change.

Maintainers can build and validate local release assets with:

```text
python tools/build_release.py
python tools/validate_release.py
```

## License

This repository and each distributed skill are licensed under the [MIT License](LICENSE).
