#!/usr/bin/env python3
"""Validate repository skill directories and generated release assets."""

from __future__ import annotations

import hashlib
import json
import re
import stat
import sys
import unicodedata
import zipfile
from pathlib import Path, PurePosixPath

from release_config import PLUGINS, plugin_manifest


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DIST_DIR = ROOT / "dist"
EXPECTED = {
    name: (name, config["filename"])
    for name, config in PLUGINS.items()
}
FORBIDDEN_PARTS = {".git", ".pytest_cache", "__pycache__", ".venv"}
FORBIDDEN_NAMES = {".DS_Store", ".Rhistory", "Thumbs.db"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo"}
REQUIRED_SAMPLE_PATHS = {
    "agents",
    "engine",
    "references",
    "scripts",
    "vendor",
    "PRODUCT_MANIFEST.yaml",
    "references/samplesize200_quick_guide.md",
    "references/PYTHON_API_1_0.md",
    "references/SOLUTION_CATALOG_1_0.md",
}
PERSONAL_PATH_PATTERNS = (
    re.compile(r"[A-Za-z]:\\Users\\", re.IGNORECASE),
    re.compile(r"\\Dropbox\\", re.IGNORECASE),
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\b(?:ghp|github_pat|sk)-[A-Za-z0-9_-]{20,}\b"),
)
TEXT_SUFFIXES = {
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".r",
    ".rst",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[A-Za-z-][0-9A-Za-z-]*))*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_skill_markdown(path: Path, expected_name: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        fail(f"{path.relative_to(ROOT)} has no YAML frontmatter")
    try:
        end = next(index for index, line in enumerate(lines[1:], 1) if line.strip() == "---")
    except StopIteration:
        fail(f"{path.relative_to(ROOT)} has unterminated YAML frontmatter")
    frontmatter = "\n".join(lines[1:end])
    match = re.search(r"(?m)^name:\s*[\"']?([^\"'\n]+?)[\"']?\s*$", frontmatter)
    if not match:
        fail(f"{path.relative_to(ROOT)} has no frontmatter name")
    actual_name = match.group(1).strip()
    if actual_name != expected_name:
        fail(f"{path.relative_to(ROOT)} has unexpected skill name")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", actual_name):
        fail(f"{path.relative_to(ROOT)} has a non-lowercase skill name")
    if not re.search(r"(?m)^description:\s*\S", frontmatter):
        fail(f"{path.relative_to(ROOT)} has no frontmatter description")


def validate_plugin_manifest_values(
    filename: str,
    skill: str,
    manifest: dict[str, object],
) -> None:
    if manifest.get("name") != skill or not re.fullmatch(
        r"[a-z0-9]+(?:-[a-z0-9]+)*", skill
    ):
        fail(f"{filename} has an invalid lowercase plugin name")
    version = manifest.get("version")
    if not isinstance(version, str) or SEMVER_RE.fullmatch(version) is None:
        fail(f"{filename} has an invalid semantic version")
    if manifest.get("skills") != "./skills/":
        fail(f"{filename} has an invalid skills path")
    if "apps" in manifest or "mcpServers" in manifest:
        fail(f"{filename} is not a skills-only plugin")
    author = manifest.get("author")
    interface = manifest.get("interface")
    if not isinstance(author, dict) or not isinstance(interface, dict):
        fail(f"{filename} is missing author or interface metadata")
    if author.get("name") != interface.get("developerName"):
        fail(f"{filename} author and developer names do not match")
    display_name = interface.get("displayName")
    short_description = interface.get("shortDescription")
    long_description = interface.get("longDescription")
    default_prompt = interface.get("defaultPrompt")
    if not isinstance(display_name, str) or not 1 <= len(display_name) <= 30:
        fail(f"{filename} display name exceeds directory-submission limits")
    if not isinstance(short_description, str) or not 1 <= len(short_description) <= 30:
        fail(f"{filename} short description exceeds directory-submission limits")
    if not isinstance(long_description, str) or not 1 <= len(long_description) <= 4000:
        fail(f"{filename} has an invalid long description")
    prompts = default_prompt if isinstance(default_prompt, list) else [default_prompt]
    if not 1 <= len(prompts) <= 3 or not all(
        isinstance(prompt, str) and 1 <= len(prompt) <= 128 and "\n" not in prompt
        for prompt in prompts
    ):
        fail(f"{filename} has invalid default prompts")


def validate_tree() -> int:
    actual = {path.name for path in SKILLS_DIR.iterdir() if path.is_dir()}
    if actual != set(EXPECTED):
        fail(f"Unexpected skill directories: {sorted(actual)}")

    file_count = 0
    for skill, (expected_name, _) in EXPECTED.items():
        source = SKILLS_DIR / skill
        for required in ("SKILL.md", "LICENSE"):
            if not (source / required).is_file():
                fail(f"Missing skills/{skill}/{required}")
        validate_skill_markdown(source / "SKILL.md", expected_name)

        for path in source.rglob("*"):
            relative = path.relative_to(source)
            if any(part in FORBIDDEN_PARTS for part in relative.parts):
                fail(f"Forbidden directory: skills/{skill}/{relative.as_posix()}")
            if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                fail(f"Forbidden file: skills/{skill}/{relative.as_posix()}")
            if not path.is_file():
                continue
            file_count += 1
            if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {"SKILL.md", "LICENSE"}:
                continue
            try:
                text = path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                continue
            if any(pattern.search(text) for pattern in PERSONAL_PATH_PATTERNS):
                fail(f"Personal filesystem path found in skills/{skill}/{relative.as_posix()}")
            if any(pattern.search(text) for pattern in SECRET_PATTERNS):
                fail(f"Possible secret found in skills/{skill}/{relative.as_posix()}")

    sample = SKILLS_DIR / "samplesize200"
    missing = [path for path in REQUIRED_SAMPLE_PATHS if not (sample / path).exists()]
    if missing:
        fail(f"samplesize200 is missing required paths: {missing}")
    show_help = (sample / "scripts" / "show_help.py").read_text(encoding="utf-8")
    expected_guide = 'ROOT / "references" / "samplesize200_quick_guide_ja.md"'
    if expected_guide not in show_help:
        fail("samplesize200 show_help.py does not use the lowercase quick-guide path")
    return file_count


def validate_archives() -> int:
    if not DIST_DIR.exists():
        fail("dist does not exist; run tools/build_release.py first")

    checksum_path = DIST_DIR / "SHA256SUMS.txt"
    if not checksum_path.is_file():
        fail("Missing dist/SHA256SUMS.txt")
    checksums: dict[str, str] = {}
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, separator, filename = line.partition("  ")
        if not separator or not re.fullmatch(r"[0-9a-f]{64}", digest):
            fail("Malformed SHA256SUMS.txt")
        checksums[filename] = digest

    expected_assets = {data[1] for data in EXPECTED.values()}
    actual_assets = {path.name for path in DIST_DIR.glob("*.zip")}
    if actual_assets != expected_assets:
        fail(f"Unexpected ZIP assets: {sorted(actual_assets)}")
    if set(checksums) != expected_assets:
        fail("Checksum asset list does not match expected ZIP assets")

    for skill, (_, filename) in EXPECTED.items():
        archive_path = DIST_DIR / filename
        if sha256(archive_path) != checksums[filename]:
            fail(f"Checksum mismatch: {filename}")
        with zipfile.ZipFile(archive_path) as archive:
            names = archive.namelist()
            required = {
                ".codex-plugin/plugin.json",
                "LICENSE",
                f"skills/{skill}/SKILL.md",
                f"skills/{skill}/LICENSE",
            }
            missing_root = sorted(required - set(names))
            if missing_root:
                fail(f"{filename} is missing plugin paths: {missing_root}")
            if "SKILL.md" in names:
                fail(f"{filename} still uses the standalone-skill ZIP layout")

            try:
                manifest = json.loads(
                    archive.read(".codex-plugin/plugin.json").decode("utf-8")
                )
            except (KeyError, UnicodeDecodeError, json.JSONDecodeError):
                fail(f"{filename} has an invalid plugin manifest")
            if manifest != plugin_manifest(skill):
                fail(f"{filename} plugin manifest does not match release metadata")
            validate_plugin_manifest_values(filename, skill, manifest)

            archived_skills = {
                PurePosixPath(name).parts[1]
                for name in names
                if len(PurePosixPath(name).parts) >= 3
                and PurePosixPath(name).parts[0] == "skills"
            }
            if archived_skills != {skill}:
                fail(f"{filename} must contain exactly the {skill} skill")

            normalized_names: set[str] = set()
            total_uncompressed = 0
            for info in archive.infolist():
                name = info.filename
                path = PurePosixPath(name)
                if not name or name != name.strip() or "\\" in name:
                    fail(f"Malformed archive path in {filename}: {name!r}")
                if path.is_absolute() or ".." in path.parts or "" in path.parts:
                    fail(f"Unsafe archive path in {filename}")
                if len(path.parts) > 20 or len(name) > 240:
                    fail(f"Archive path limit exceeded in {filename}: {name}")
                normalized = unicodedata.normalize("NFC", name).casefold()
                if normalized in normalized_names:
                    fail(f"Normalized archive path collision in {filename}: {name}")
                normalized_names.add(normalized)
                if any(part in FORBIDDEN_PARTS for part in path.parts):
                    fail(f"Forbidden directory in {filename}: {name}")
                if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                    fail(f"Forbidden file in {filename}: {name}")
                if info.flag_bits & 0x1:
                    fail(f"Encrypted archive member in {filename}: {name}")
                member_type = stat.S_IFMT((info.external_attr >> 16) & 0xFFFF)
                if member_type not in (0, stat.S_IFREG):
                    fail(f"Unsupported archive member type in {filename}: {name}")
                if info.file_size > 100 * 1024 * 1024:
                    fail(f"Oversized archive member in {filename}: {name}")
                total_uncompressed += info.file_size
            if len(names) > 5000 or total_uncompressed > 512 * 1024 * 1024:
                fail(f"Archive limits exceeded in {filename}")
            if archive_path.stat().st_size > 100 * 1024 * 1024:
                fail(f"Compressed archive exceeds 100 MB: {filename}")

            source = SKILLS_DIR / skill
            archived_source = {
                name[len(f"skills/{skill}/"):]: archive.read(name)
                for name in names
                if name.startswith(f"skills/{skill}/")
            }
            expected_source = {
                path.relative_to(source).as_posix(): path.read_bytes()
                for path in source.rglob("*")
                if path.is_file()
            }
            if archived_source != expected_source:
                fail(f"{filename} does not contain an exact source snapshot")
            if skill == "samplesize200":
                missing = [
                    path
                    for path in REQUIRED_SAMPLE_PATHS
                    if f"skills/{skill}/{path}" not in names
                    and not any(
                        name.startswith(f"skills/{skill}/{path}/") for name in names
                    )
                ]
                if missing:
                    fail(f"{filename} is missing required paths: {missing}")
    return len(expected_assets)


def main() -> None:
    files = validate_tree()
    archives = validate_archives()
    print(f"PASS: {len(EXPECTED)} skills, {files} source files, {archives} release ZIPs, checksums verified")


if __name__ == "__main__":
    main()
