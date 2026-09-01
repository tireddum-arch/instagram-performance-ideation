#!/usr/bin/env python3
"""Initialize and maintain a local, approval-gated meme LLM wiki."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BRAND_FILES = {
    "brand/essence.md": """# Brand essence

## Why this content should spread

Describe the emotional job the content performs and the action that matters most.

## Non-negotiable promise

Write one sentence the creator should preserve across formats.
""",
    "brand/audience.md": """# Audience

## Primary reader

Describe a recognizable person, situation, and tension. Avoid broad demographics alone.

## Sending situation

Who sends this content to whom, and what are they trying to say without explaining it?
""",
    "brand/voice.md": """# Voice

## Traits

List three voice traits with concrete examples.

## Writing habits

Record sentence length, rhythm, punctuation, and devices used sparingly.
""",
    "brand/off-limits.md": """# Off limits

## Subjects

List subjects that belong to the creator but not the audience.

## Claims

List experiences, numbers, and outcomes that must never be invented.
""",
    "brand/applying.md": """# Applying a source meme

## Keep

Preserve the mechanism that creates recognition: number, rhythm, identity cue, escalation, contrast, reveal position, or sending situation.

## Replace

Replace wording, exact premise, scene, examples, and any experience the creator cannot truthfully claim.

## Failure test

Reject copied wording, cosmetic paraphrases, explanation-heavy drafts, and branches that are the same idea in different words.
""",
    "brand/anti-patterns.md": """# Rejected patterns

Record user feedback verbatim. Add the rejected draft, the user's exact words, and the corrected rule. Do not silently rewrite old feedback.
""",
}

INDEX = """# Meme LLM Wiki

This wiki separates three kinds of knowledge:

- `brand/`: audience, voice, boundaries, application rules, and corrections
- `formats/`: reusable meme mechanisms plus collected originals
- `raw/memes.json`: structured external examples; never merge this with the creator's own performance dataset

Only add an external meme after the user approves the proposed classification.
"""

LOG = """# Wiki log

Append-only record of approved additions and explicit corrections.
"""

REQUIRED = [
    "text", "side_text", "structure", "format_slug", "format_title",
    "why_it_works", "application",
]


def load_json(path: str | Path, default: Any) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(target)


def safe_slug(value: str) -> str:
    slug = value.strip()
    if not re.fullmatch(r"[a-z0-9-]{1,64}", slug):
        raise ValueError("format_slug must be 1-64 lowercase ASCII letters, digits, or hyphens")
    return slug


def initialize(root: Path) -> list[Path]:
    created: list[Path] = []
    files = {"index.md": INDEX, "log.md": LOG, **BRAND_FILES}
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(path)
    (root / "formats").mkdir(parents=True, exist_ok=True)
    (root / "raw" / "images").mkdir(parents=True, exist_ok=True)
    raw = root / "raw" / "memes.json"
    if not raw.exists():
        write_json(raw, [])
        created.append(raw)
    return created


def format_list(root: Path) -> list[dict[str, str]]:
    output = []
    for path in sorted((root / "formats").glob("*.md")):
        title = path.stem
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                title = line[2:].replace("Format:", "").strip()
                break
        output.append({"slug": path.stem, "title": title})
    return output


def context(root: Path) -> str:
    paths = [root / name for name in BRAND_FILES]
    paths += sorted((root / "formats").glob("*.md"))
    return "\n\n---\n\n".join(
        path.read_text(encoding="utf-8") for path in paths if path.exists()
    )


def validate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED if field not in entry]
    if missing:
        raise ValueError("missing required fields: " + ", ".join(missing))
    normalized = {field: str(entry.get(field, "")).strip() for field in REQUIRED}
    normalized["format_slug"] = safe_slug(normalized["format_slug"])
    if not normalized["text"] or not normalized["structure"] or not normalized["format_title"]:
        raise ValueError("text, structure, and format_title cannot be empty")
    return normalized


def new_id(existing: list[dict[str, Any]]) -> str:
    base = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    used = {str(item.get("id")) for item in existing}
    candidate = base
    suffix = 1
    while candidate in used:
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def append_format(root: Path, entry: dict[str, Any], meme_id: str) -> Path:
    path = root / "formats" / f"{entry['format_slug']}.md"
    today = datetime.now(timezone.utc).date().isoformat()
    quote = "\n".join("> " + line for line in entry["text"].splitlines())
    side = f"\n> *(side: {entry['side_text']})*\n" if entry["side_text"] else ""
    block = (
        f"\n### {meme_id} · collected {today}\n\n{quote}\n{side}\n"
        f"- Mechanism: {entry['structure']}\n"
        f"- Why it works: {entry['why_it_works']}\n"
        f"- Possible application: {entry['application']}\n"
    )
    if not path.exists():
        path.write_text(
            f"# Format: {entry['format_title']}\n\n"
            f"## Reusable mechanism\n\n{entry['structure']}\n\n"
            f"## Collected originals\n{block}\n"
            f"## Creator versions\n\nAdd published or approved adaptations here.\n",
            encoding="utf-8",
        )
    else:
        text = path.read_text(encoding="utf-8")
        marker = "## Collected originals"
        if marker in text:
            position = text.index(marker) + len(marker)
            text = text[:position] + "\n" + block + text[position:]
        else:
            text = text.rstrip() + f"\n\n{marker}\n{block}"
        path.write_text(text, encoding="utf-8")
    return path


def add_entry(root: Path, entry_path: Path, source: str, note: str, image: Path | None) -> dict[str, str]:
    initialize(root)
    entry = validate_entry(load_json(entry_path, {}))
    raw_path = root / "raw" / "memes.json"
    raw = load_json(raw_path, [])
    meme_id = new_id(raw)
    image_relative = ""
    if image:
        if not image.is_file():
            raise ValueError(f"image does not exist: {image}")
        suffix = image.suffix.lower() if image.suffix else ".bin"
        destination = root / "raw" / "images" / f"{meme_id}{suffix}"
        shutil.copy2(image, destination)
        image_relative = str(destination.relative_to(root))
    record = {
        "id": meme_id,
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": source,
        "note": note,
        "image": image_relative,
        **entry,
    }
    raw.append(record)
    write_json(raw_path, raw)
    format_path = append_format(root, entry, meme_id)
    with (root / "log.md").open("a", encoding="utf-8") as handle:
        handle.write(
            f"\n- {record['collected_at']} `{meme_id}` added to "
            f"`formats/{format_path.name}` from {source}\n"
        )
    return {"id": meme_id, "format": str(format_path), "raw": str(raw_path)}


def command_init(args: argparse.Namespace) -> int:
    created = initialize(Path(args.wiki))
    print(json.dumps({"wiki": args.wiki, "created": [str(p) for p in created]}, ensure_ascii=False))
    return 0


def command_context(args: argparse.Namespace) -> int:
    print(context(Path(args.wiki)))
    return 0


def command_formats(args: argparse.Namespace) -> int:
    print(json.dumps(format_list(Path(args.wiki)), ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    print(json.dumps(validate_entry(load_json(args.input, {})), ensure_ascii=False, indent=2))
    return 0


def command_add(args: argparse.Namespace) -> int:
    result = add_entry(
        Path(args.wiki), Path(args.input), args.source, args.note,
        Path(args.image) if args.image else None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="initialize a wiki without overwriting existing files")
    init.add_argument("--wiki", default="meme-wiki")
    init.set_defaults(func=command_init)
    show = commands.add_parser("context", help="print brand and format knowledge for an LLM prompt")
    show.add_argument("--wiki", default="meme-wiki")
    show.set_defaults(func=command_context)
    formats = commands.add_parser("formats", help="list existing format slugs and titles")
    formats.add_argument("--wiki", default="meme-wiki")
    formats.set_defaults(func=command_formats)
    validate = commands.add_parser("validate", help="validate a proposed meme JSON file")
    validate.add_argument("--input", required=True)
    validate.set_defaults(func=command_validate)
    add = commands.add_parser("add", help="store an explicitly approved meme")
    add.add_argument("--wiki", default="meme-wiki")
    add.add_argument("--input", required=True)
    add.add_argument("--source", default="user-submitted")
    add.add_argument("--note", default="")
    add.add_argument("--image")
    add.set_defaults(func=command_add)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(1)
