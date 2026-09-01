---
name: meme-llm-wiki
description: Use when a creator needs a local LLM-readable knowledge base for meme formats, audience recognition, voice, boundaries, collected originals, and corrections. Initializes and reads the wiki, validates structured entries, keeps external examples separate from the creator's performance data, and writes only explicitly approved additions.
version: 1.0.0
author: tireddum-arch
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memes, llm-wiki, knowledge-base, creator-workflow]
    related_skills: [meme-collector, meme-writer, instagram-performance-ideation]
---

# Meme LLM Wiki

## Overview

This skill creates the memory layer shared by meme collection, performance-based source selection, and writing. The wiki stores reusable mechanisms and user corrections, not model-generated guesses.

The manager is `scripts/meme_wiki.py`. It uses only Python's standard library.

## When to Use

Use when:

- starting a creator-specific meme knowledge base;
- loading audience, voice, boundaries, formats, and corrections into a writing prompt;
- saving an external meme after the user approves its classification;
- recording feedback so the same rejected pattern does not return.

Do not use the wiki as a dump for raw Instagram analytics. The creator's own performance posts and collected external memes remain separate datasets.

## Initialize

From the project directory:

```bash
python3 <skill-dir>/scripts/meme_wiki.py init --wiki meme-wiki
```

This creates, without overwriting existing files:

- `brand/essence.md`
- `brand/audience.md`
- `brand/voice.md`
- `brand/off-limits.md`
- `brand/applying.md`
- `brand/anti-patterns.md`
- `formats/`
- `raw/memes.json`
- `log.md`

Completion criterion: `meme-wiki/index.md` exists and every brand file reflects the creator rather than placeholder prose.

## Read Context

```bash
python3 <skill-dir>/scripts/meme_wiki.py context --wiki meme-wiki
```

Use this output as the knowledge section of a writing prompt. The command reads brand files first and formats second.

Completion criterion: the prompt includes current audience, boundaries, application rules, corrections, and every format file.

## Add an Approved Entry

Prepare JSON:

```json
{
  "text": "Exact visible text with line breaks preserved",
  "side_text": "Small side text or empty string",
  "structure": "Reusable mechanism, not a sentence-level paraphrase",
  "format_slug": "lowercase-hyphen-slug",
  "format_title": "Human-readable title",
  "why_it_works": "Why an audience recognizes or sends it",
  "application": "How the mechanism could fit this creator without copying"
}
```

Validate first:

```bash
python3 <skill-dir>/scripts/meme_wiki.py validate --input proposed-meme.json
```

Only after explicit approval:

```bash
python3 <skill-dir>/scripts/meme_wiki.py add \
  --wiki meme-wiki \
  --input proposed-meme.json \
  --source user-submitted \
  --image /absolute/path/to/image
```

The command appends to `raw/memes.json`, stores an optional image, updates the matching format, and appends `log.md`.

Completion criterion: the returned ID exists in both `raw/memes.json` and the target format file.

## Corrections

When the user rejects or corrects a draft:

1. Preserve the user's exact words in `brand/anti-patterns.md`.
2. Add the rejected draft and a concrete future test.
3. Show edits before changing an existing rule; append-only feedback is the safe default.
4. Re-run the next writing task against the updated context.

## Common Pitfalls

1. **Writing before approval.** Classification proposals are drafts until the user says yes.
2. **Mixing datasets.** External examples go to `raw/memes.json`; owned Instagram performance stays in its own posts/labels files.
3. **Saving prose instead of a mechanism.** A format must be reusable after names, wording, and subject are replaced.
4. **Summarizing user feedback.** Preserve exact wording so nuance is not lost.
5. **Silently rewriting existing wiki rules.** Show and ask before replacement; append new evidence when possible.

## Verification Checklist

- [ ] Brand files are creator-specific
- [ ] External and owned data are separate
- [ ] Every saved entry was explicitly approved
- [ ] Exact source text is preserved
- [ ] Format structure is reusable rather than copied wording
- [ ] Corrections include the user's verbatim feedback
- [ ] `context` includes all brand and format files
