#!/usr/bin/env python3
"""Install every skill in this repository as one local package."""
from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


def default_destination() -> Path:
    home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    return home / "skills" / "creator-meme-toolkit"


def install(source: Path, destination: Path, force: bool) -> list[Path]:
    skills = source / "skills"
    if not skills.is_dir():
        raise RuntimeError(f"skills directory not found: {skills}")
    installed: list[Path] = []
    destination.mkdir(parents=True, exist_ok=True)
    for skill in sorted(skills.iterdir()):
        if not skill.is_dir() or not (skill / "SKILL.md").is_file():
            continue
        target = destination / skill.name
        if target.exists():
            if not force:
                raise RuntimeError(f"already installed: {target}; pass --force to replace")
            shutil.rmtree(target)
        shutil.copytree(skill, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        installed.append(target)
    if not installed:
        raise RuntimeError("no skills were found")
    return installed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=default_destination())
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    installed = install(root, args.dest.expanduser().resolve(), args.force)
    print(f"Installed {len(installed)} skills:")
    for path in installed:
        print(f"- {path}")
    print("Start a new Hermes session or run /reload-skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
