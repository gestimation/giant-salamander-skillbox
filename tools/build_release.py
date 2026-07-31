#!/usr/bin/env python3
"""Build deterministic, installable skill ZIP files and their checksums."""

from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from pathlib import Path

from release_config import PLUGINS, plugin_manifest


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DIST_DIR = ROOT / "dist"
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


def build_zip(skill: str, source: Path, destination: Path) -> dict[str, object]:
    if destination.exists():
        destination.unlink()

    source_files = skill_files(source)
    manifest = (
        json.dumps(plugin_manifest(skill), ensure_ascii=False, indent=2) + "\n"
    ).encode("utf-8")
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


def main() -> None:
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

    lines = [f"{result['sha256']}  {result['file']}" for result in results]
    checksum_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(json.dumps({"status": "PASS", "assets": results}, indent=2))


if __name__ == "__main__":
    main()
