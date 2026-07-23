# Giant Salamander Skillbox

Downloadable, self-contained skills for ChatGPT Work and Codex.

## Skills

| Skill | Version | Purpose |
| --- | --- | --- |
| [READATABLE](skills/readatable/) | 0.4.1 | Improves the readability and presentation of tables. |
| [REVIEWCITATION](skills/reviewcitation/) | 0.3.3 | Reviews citation placement and reference consistency. |
| [SAMPLESIZE200](skills/samplesize200/) | 1.0.0-rc.4 | Supports reproducible sample-size planning workflows. |

## Installation

1. Open the repository's [Releases](https://github.com/gestimation/giant-salamander-skillbox/releases) page.
2. Download the ZIP asset for the skill you want.
3. Upload the ZIP file unchanged in the ChatGPT Work or Codex web interface.

Each release ZIP is an installation unit. `SKILL.md` is located at the archive root; do not add an extra wrapper directory or repackage the archive.

## Runtime requirements

READATABLE and REVIEWCITATION are instruction-only skills.

SAMPLESIZE200 requires Python 3.10 or later and SciPy 1.11 or later in the execution environment. Its remaining runtime files, including its vendored YAML dependency, are included in the skill directory. Start with the [quick guide](skills/samplesize200/references/SAMPLESIZE200_QUICK_GUIDE.md); the [Python API](skills/samplesize200/references/PYTHON_API_1_0.md) and [solution catalog](skills/samplesize200/references/SOLUTION_CATALOG_1_0.md) provide further detail.

## Release integrity

Release assets are built from the directories under `skills/`. Every release includes `SHA256SUMS.txt` so downloaded ZIP files can be verified. A published asset is never replaced without a version change.

Maintainers can build and validate local release assets with:

```text
python tools/build_release.py
python tools/validate_release.py
```

## License

This repository and each distributed skill are licensed under the [MIT License](LICENSE).
