#!/usr/bin/env python3
"""Validate repository skill directories and generated release assets."""

from __future__ import annotations

import hashlib
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
DIST_DIR = ROOT / "dist"
EXPECTED = {
    "readatable": ("readatable", "readatable-0.4.1.zip"),
    "reviewcitation": ("reviewcitation", "reviewcitation-0.3.3.zip"),
    "samplesize200": ("samplesize200", "SAMPLESIZE200-1.0.0-rc.4.zip"),
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
    "references/SAMPLESIZE200_QUICK_GUIDE.md",
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
    if match.group(1).strip().lower() != expected_name:
        fail(f"{path.relative_to(ROOT)} has unexpected skill name")
    if not re.search(r"(?m)^description:\s*\S", frontmatter):
        fail(f"{path.relative_to(ROOT)} has no frontmatter description")


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
        fail(f"SAMPLESIZE200 is missing required paths: {missing}")
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
            if "SKILL.md" not in names or "LICENSE" not in names:
                fail(f"{filename} is not rooted at the skill directory")
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or ".." in path.parts:
                    fail(f"Unsafe archive path in {filename}")
                if any(part in FORBIDDEN_PARTS for part in path.parts):
                    fail(f"Forbidden directory in {filename}: {name}")
                if path.name in FORBIDDEN_NAMES or path.suffix.lower() in FORBIDDEN_SUFFIXES:
                    fail(f"Forbidden file in {filename}: {name}")
            if skill == "samplesize200":
                missing = [
                    path
                    for path in REQUIRED_SAMPLE_PATHS
                    if path not in names
                    and not any(name.startswith(f"{path}/") for name in names)
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
