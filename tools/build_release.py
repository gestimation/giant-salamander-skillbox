#!/usr/bin/env python3
"""Build deterministic, installable skill ZIP files and their checksums."""

from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path

from release_config import (
    BUNDLE_FILENAME,
    BUNDLE_NAME,
    BUNDLE_VERSION,
    PLUGINS,
    RELEASE_REF,
    REPOSITORY_URL,
    claude_bundle_manifest,
    claude_marketplace,
    codex_bundle_manifest,
    codex_marketplace,
    plugin_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DIST_DIR = ROOT / "dist"
PLUGINS_DIR = ROOT / "plugins"
BUNDLE_DIR = PLUGINS_DIR / BUNDLE_NAME
CODEX_MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_MARKETPLACE_PATH = ROOT / ".claude-plugin" / "marketplace.json"
FIXED_TIMESTAMP = (2026, 1, 1, 0, 0, 0)
FORBIDDEN_PARTS = {".git", ".pytest_cache", "__pycache__", ".venv"}
FORBIDDEN_NAMES = {".DS_Store", ".Rhistory", "Thumbs.db"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def skill_files(source: Path) -> list[Path]:
    if not (source / "SKILL.md").is_file():
        raise SystemExit(f"Missing SKILL.md: {source}")
    if not (source / "LICENSE").is_file():
        raise SystemExit(f"Missing LICENSE: {source}")

    files: list[Path] = []
    for path in sorted(source.rglob("*"), key=lambda item: item.as_posix()):
        relative = path.relative_to(source)
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            raise SystemExit(f"Forbidden directory in skill: {relative}")
        if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            raise SystemExit(f"Forbidden file in skill: {relative}")
        if path.is_file():
            files.append(path)
    return files


def write_entry(archive: zipfile.ZipFile, name: str, contents: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    archive.writestr(info, contents, compresslevel=9)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(json_bytes(value))


def skill_tree_sha256(source: Path) -> str:
    digest = hashlib.sha256()
    for path in skill_files(source):
        relative = path.relative_to(source).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def bundle_readme() -> str:
    versions = ", ".join(
        f"`{name}` {config['version']}" for name, config in PLUGINS.items()
    )
    return f"""# Giant Salamander Skillbox

This skills-only plugin contains {versions}.

- `readatable` reconstructs and normalizes statistical tables.
- `reviewcitation` reviews scientific citations and reference lists.
- `samplesize200` supports validated study-size planning workflows.
- `draftcostsheet` drafts traceable medical-cost sheets from authoritative sources.

Official releases and the separate user-facing cheat sheet are available at
{REPOSITORY_URL}/releases. The cheat sheet is intentionally not bundled in the
plugin runtime package.

`samplesize200` requires Python 3.10 or later and SciPy 1.11 or later in the
execution environment. The other three skills are instruction-only.
"""


def bundle_component_manifest() -> dict[str, object]:
    return {
        "name": BUNDLE_NAME,
        "version": BUNDLE_VERSION,
        "releaseRef": RELEASE_REF,
        "canonicalSource": "skills/",
        "skills": [
            {
                "name": name,
                "version": config["version"],
                "treeSha256": skill_tree_sha256(SKILLS_DIR / name),
            }
            for name, config in PLUGINS.items()
        ],
    }


def sync_bundle_directory() -> None:
    resolved_parent = BUNDLE_DIR.parent.resolve()
    if resolved_parent != PLUGINS_DIR.resolve() or BUNDLE_DIR.name != BUNDLE_NAME:
        raise SystemExit(f"Unsafe bundle path: {BUNDLE_DIR}")

    expected_files: dict[Path, bytes] = {
        Path(".codex-plugin/plugin.json"): json_bytes(codex_bundle_manifest()),
        Path(".claude-plugin/plugin.json"): json_bytes(claude_bundle_manifest()),
        Path("BUNDLE_MANIFEST.json"): json_bytes(bundle_component_manifest()),
        Path("README.md"): bundle_readme().encode("utf-8"),
        Path("LICENSE"): (ROOT / "LICENSE").read_bytes(),
    }

    for skill in PLUGINS:
        source = SKILLS_DIR / skill
        for path in skill_files(source):
            relative = Path("skills") / skill / path.relative_to(source)
            expected_files[relative] = path.read_bytes()

    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    for relative, contents in expected_files.items():
        destination = BUNDLE_DIR / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file() or destination.read_bytes() != contents:
            destination.write_bytes(contents)

    for path in sorted(BUNDLE_DIR.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_file() and path.relative_to(BUNDLE_DIR) not in expected_files:
            path.unlink()


def write_marketplaces() -> None:
    write_json(CODEX_MARKETPLACE_PATH, codex_marketplace())
    write_json(CLAUDE_MARKETPLACE_PATH, claude_marketplace())


def build_zip(skill: str, source: Path, destination: Path) -> dict[str, object]:
    if destination.exists():
        destination.unlink()

    source_files = skill_files(source)
    manifest = json_bytes(plugin_manifest(skill))
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        write_entry(archive, ".codex-plugin/plugin.json", manifest)
        write_entry(archive, "LICENSE", (ROOT / "LICENSE").read_bytes())
        for path in source_files:
            relative = f"skills/{skill}/{path.relative_to(source).as_posix()}"
            with path.open("rb") as stream:
                write_entry(archive, relative, stream.read())

    return {
        "file": destination.name,
        "files": len(source_files) + 2,
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
    }


def build_bundle_zip(destination: Path) -> dict[str, object]:
    if destination.exists():
        destination.unlink()

    files = [
        path
        for path in sorted(BUNDLE_DIR.rglob("*"), key=lambda item: item.as_posix())
        if path.is_file()
    ]
    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            write_entry(
                archive,
                path.relative_to(BUNDLE_DIR).as_posix(),
                path.read_bytes(),
            )

    return {
        "file": destination.name,
        "files": len(files),
        "bytes": destination.stat().st_size,
        "sha256": sha256(destination),
        "plugin": BUNDLE_NAME,
        "version": BUNDLE_VERSION,
        "skills": list(PLUGINS),
    }


def main() -> None:
    sync_bundle_directory()
    write_marketplaces()
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    for old_archive in DIST_DIR.glob("*.zip"):
        old_archive.unlink()
    checksum_path = DIST_DIR / "SHA256SUMS.txt"
    if checksum_path.exists():
        checksum_path.unlink()

    results: list[dict[str, object]] = []
    for skill, config in PLUGINS.items():
        source = SKILLS_DIR / skill
        destination = DIST_DIR / config["filename"]
        result = build_zip(skill, source, destination)
        result["skill"] = skill
        result["version"] = config["version"]
        results.append(result)

    results.append(build_bundle_zip(DIST_DIR / BUNDLE_FILENAME))

    lines = [f"{result['sha256']}  {result['file']}" for result in results]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"status": "PASS", "assets": results}, indent=2))


if __name__ == "__main__":
    main()
