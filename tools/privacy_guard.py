#!/usr/bin/env python3
"""Fail closed on unexpected tracked files; review text before publication."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
ALLOWED = {
    ".gitignore", ".githooks/pre-commit", ".github/workflows/privacy-check.yml",
    "README.md", "使用说明.md", "CONTRIBUTING.md", "tools/privacy_guard.py",
    "image-creation-assistant/SKILL.md",
    "image-creation-assistant/references/acceptance-tests.md",
    "image-creation-assistant/references/huashu-visual-adapter.md",
    "image-creation-assistant/references/prompt-library.md",
    "image-creation-assistant/references/spatial-composition.md",
    "image-creation-assistant/references/备用工具与迁移.md",
    "image-creation-assistant/vendor/LICENSE-huashu-slide-doubao.txt",
    "image-creation-assistant/scripts/discover_skills.py",
    "image-creation-assistant/references/skill-discovery.md",
    "image-creation-assistant/references/skill-discovery-tests.md",
    "image-creation-assistant/references/feedback-memory.md",
    "image-creation-assistant/vendor/vercel-find-skills/SKILL.md",
    "image-creation-assistant/vendor/vercel-find-skills/LICENSE",
    "image-creation-assistant/vendor/vercel-find-skills/SOURCE.md",
}
CHECKS = [
    ("data URI / embedded image", re.compile(r"data:image/[a-z0-9.+-]+;base64,", re.I)),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("local Windows user path", re.compile(r"[A-Za-z]:[/\\]Users[/\\][^/\\\s]+[/\\]", re.I)),
    ("likely credential assignment", re.compile(r"(?i)\b(?:api[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"][^'\"\s]{12,}['\"]")),
]

def git(*args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(ROOT), *args], stderr=subprocess.PIPE)

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staged", action="store_true", required=True, help="Inspect the complete Git index")
    args = parser.parse_args()
    del args
    try:
        names = git("ls-files", "--cached", "--full-name", "-z").decode("utf-8").split("\0")
        names = [n for n in names if n]
    except (subprocess.CalledProcessError, UnicodeDecodeError, FileNotFoundError):
        print("Cannot read the Git index; run this from an initialized repository with git available.", file=sys.stderr)
        return 2
    block_path = os.environ.get("IMAGE_GUARD_BLOCKLIST")
    private_terms: list[str] = []
    if block_path:
        try:
            private_terms = [x.strip().casefold() for x in Path(block_path).read_text(encoding="utf-8").splitlines() if x.strip() and not x.lstrip().startswith("#")]
        except OSError:
            print("Configured private blocklist is unreadable; refusing publication.", file=sys.stderr)
            return 2
    errors: list[str] = []
    for name in names:
        if name not in ALLOWED:
            errors.append(f"unexpected tracked path: {name}")
            continue
        try:
            data = git("show", f":{name}")
        except subprocess.CalledProcessError:
            errors.append(f"cannot read staged file: {name}")
            continue
        if len(data) > 1_000_000 or b"\0" in data:
            errors.append(f"binary or oversized file: {name}")
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            errors.append(f"not UTF-8: {name}")
            continue
        for label, regex in CHECKS:
            if regex.search(text):
                errors.append(f"{label}: {name}")
        if any(term in text.casefold() for term in private_terms):
            errors.append(f"private blocklist match: {name}")
    if errors:
        print("Privacy guard rejected the index:", *errors, sep="\n- ", file=sys.stderr)
        return 1
    if not names:
        print("Empty index; refusing publication.", file=sys.stderr)
        return 1
    print(f"Privacy guard passed {len(names)} staged files. Manual review is still required; patterns cannot identify every real case.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
