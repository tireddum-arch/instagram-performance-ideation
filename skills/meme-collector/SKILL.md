---
name: meme-collector
description: Use when a user submits a meme image or text, including a !밈-style command, and wants it analyzed for reuse. Reads the exact visible text, extracts the transferable mechanism and sending situation, compares existing wiki formats, presents a classification draft, and saves it to the Meme LLM Wiki only after explicit approval.
version: 1.0.0
author: tireddum-arch
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memes, collection, vision, classification, approval]
    related_skills: [meme-llm-wiki, meme-writer]
---

# Meme Collector (`!밈` Workflow)

## Overview

Turn a submitted meme into reusable knowledge without contaminating the wiki with an unreviewed model judgment. The trigger may be `!밈`, “save this meme,” or an attached image with the same intent.

This skill analyzes and proposes. `meme-llm-wiki` performs approved storage.

## Workflow

### 1. Read the source

For an image, open it with the available vision tool. Zoom or crop small text before transcribing. Preserve:

- exact spelling and intentional mistakes;
- line breaks;
- side text and sound effects;
- punctuation that affects rhythm.

For text input, preserve the user's source text verbatim. Do not “improve” it.

Completion criterion: every visible phrase is accounted for, and uncertain characters are labeled as uncertain rather than guessed.

### 2. Compare existing formats

Run:

```bash
python3 <meme-llm-wiki-dir>/scripts/meme_wiki.py formats --wiki meme-wiki
python3 <meme-llm-wiki-dir>/scripts/meme_wiki.py context --wiki meme-wiki
```

Prefer an existing format when the mechanism matches. Create a new slug only when the underlying construction is actually new.

### 3. Extract the transferable mechanism

Fill these fields:

- `text`: exact source text;
- `side_text`: exact side text or empty;
- `structure`: replace subject-specific nouns with slots while preserving the comedic or recognition mechanism;
- `format_slug` and `format_title`;
- `why_it_works`: recognition, identity, contrast, escalation, reveal, specificity, rhythm, or sendability;
- `application`: a creator-fit direction, not finished copied content.

Ask: **Who sends this to whom?** If no sender/receiver is plausible, reconsider why it matters.

### 4. Present a draft—do not save

Show:

```text
Format:
Mechanism:
Why it spreads:
Possible creator application:
Exact source:
```

Then ask for approval or corrections. Do not run the add command yet.

### 5. Save only after explicit approval

Write the approved JSON to a temporary file, validate it, then add it:

```bash
python3 <meme-llm-wiki-dir>/scripts/meme_wiki.py validate --input proposed-meme.json
python3 <meme-llm-wiki-dir>/scripts/meme_wiki.py add \
  --wiki meme-wiki --input proposed-meme.json \
  --source user-submitted --image /absolute/path/to/image
```

If the user says no, discard the proposal. If they correct it, regenerate the proposal and ask again.

Completion criterion: the command's returned ID appears in the raw store and exactly one format file.

## Boundaries

- Do not claim the user experienced something merely because the meme mentions it.
- Do not merge collected external memes with owned Instagram analytics.
- Do not silently alter existing wiki text.
- Do not generate an image; this workflow handles text and knowledge.
- Do not treat a sentence-level paraphrase as a reusable mechanism.

## Verification Checklist

- [ ] Source text was visually verified
- [ ] Existing formats were checked
- [ ] Structure survives replacement of the original subject and wording
- [ ] Sender and receiver are plausible
- [ ] The user saw the proposal
- [ ] Explicit approval preceded storage
- [ ] External raw data stayed separate from owned performance data
