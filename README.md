# Giant Salamander Skillbox

Downloadable, single-skill plugins for ChatGPT Work and Codex.

## Skills

| Skill | Version | Purpose |
| --- | --- | --- |
| [readatable](skills/readatable/) | 0.7.1 | Improves the readability and presentation of tables. |
| [reviewcitation](skills/reviewcitation/) | 0.3.4 | Reviews citation placement and reference consistency. |
| [samplesize200](skills/samplesize200/) | 1.0.0-rc.6 | Supports reproducible sample-size planning workflows. |

## Installation

1. Open the repository's [Releases](https://github.com/gestimation/giant-salamander-skillbox/releases) page.
2. Download the plugin ZIP for the skill you want.
3. Install the ZIP unchanged through the supported plugin installation flow in
   ChatGPT Work or Codex.

Do not extract or repackage the ZIP. Each asset is a skills-only plugin with a
`.codex-plugin/plugin.json` manifest and exactly one skill under
`skills/<skill-name>/`.

The directories under `skills/` are the canonical skill sources. The release
builder wraps each source in the plugin structure without changing the skill
contents.

## Runtime requirements

readatable and reviewcitation are instruction-only skills.

samplesize200 requires Python 3.10 or later and SciPy 1.11 or later in the execution environment. Its remaining runtime files, including its vendored YAML dependency, are included in the skill directory. Start with the [quick guide](skills/samplesize200/references/samplesize200_quick_guide.md); the [Python API](skills/samplesize200/references/PYTHON_API_1_0.md) and [solution catalog](skills/samplesize200/references/SOLUTION_CATALOG_1_0.md) provide further detail.

## Naming

Skill names are written in lowercase everywhere: `readatable`,
`reviewcitation`, and `samplesize200`. Release ZIP filenames use the same
lowercase names.

## Release integrity

Release assets are built from the directories under `skills/`. Plugin metadata
is defined once in `tools/release_config.py`. Every release includes
`SHA256SUMS.txt` so downloaded ZIP files can be verified. A published asset is
never replaced without a version change.

Maintainers can build and validate local release assets with:

```text
python tools/build_release.py
python tools/validate_release.py
```

## License

This repository and each distributed skill are licensed under the [MIT License](LICENSE).
