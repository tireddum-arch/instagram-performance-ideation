---
name: meme-writer
description: Use when a creator wants new meme copy from performance-ranked owned posts or approved external formats. Loads the Meme LLM Wiki, identifies each source's winning mechanism, preserves that mechanism while replacing wording and premise, creates materially different branches, checks a concrete sender/receiver, and rejects invented experience or cosmetic paraphrases.
version: 1.0.0
author: tireddum-arch
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [memes, copywriting, ideation, remix, creators]
    related_skills: [meme-llm-wiki, meme-collector, instagram-performance-ideation]
---

# Meme Writer

## Overview

Write new meme copy from evidence and learned formats. Performance data selects promising owned sources. The Meme LLM Wiki supplies audience, voice, boundaries, mechanisms, and user corrections. This skill performs the transformation.

The creator handles artwork unless explicitly stated otherwise. Default output is copy only.

## Inputs

- performance-ranked owned source posts, approved external formats, or both;
- the output of:

```bash
python3 <meme-llm-wiki-dir>/scripts/meme_wiki.py context --wiki meme-wiki
```

- an optional subject the user wants to explore.

Do not write until audience and off-limits context are available. If the wiki still contains placeholders, ask the user to fill the missing brand facts instead of inventing them.

## Workflow

### 1. Select sources

Use the metric that matches the intended action. For sendable content, shares/reach is usually more relevant than likes/reach. Exclude low-reach accidents, collaborations, and overly recent sources unless the user deliberately chooses otherwise.

Completion criterion: every selected source has a reason tied to the stated objective.

### 2. Find the axis

Before drafting, name where the source works:

- number or specificity;
- rhythm or repetition;
- title/address/identity cue;
- contrast or status drop;
- escalation;
- reveal position;
- audience situation;
- sender/receiver relationship.

This is the **axis**. Preserve it. If the source is funny because of a number, removing all specificity usually removes the joke.

### 3. Replace the expression

Replace:

- exact wording;
- exact premise and scene;
- examples and nouns;
- any experience, result, or number the creator cannot truthfully claim.

Keep only the axis or reusable format. A synonym swap fails.

### 4. Write distinct branches

Create three or four branches per source. Branches must differ in situation, axis, or format—not merely phrasing.

Use this output:

```text
=== Source N ===
[Axis] one-line mechanism

- [Approach] copy
- [Approach] copy
- [Approach] copy

[Send] sender → receiver, and why
[Why] why this source and how the mechanism survived
```

Do not add hashtags, image directions, or explanatory essays unless requested.

### 5. Self-reject weak drafts

Reject and rewrite when:

- the recipient needs an explanation;
- the draft reads like advice or a textbook;
- the source sentence is recognizable through paraphrase;
- all branches say the same thing;
- the idea relies on an invented fact;
- the topic belongs to the creator but not the audience;
- it repeats a rule in `brand/anti-patterns.md`.

Completion criterion: every surviving branch passes the wiki's applying and anti-pattern tests.

## Feedback Loop

When the user corrects a draft:

1. Rewrite in the same conversation.
2. Preserve their exact words in the wiki's correction log/anti-pattern file.
3. Add a future-facing test that would catch the same mistake.
4. Do not overturn something the user approved.

## Common Pitfalls

1. **Treating metrics as a writing formula.** Metrics select; mechanisms explain; writing transforms.
2. **Copying the winner.** Keep the axis, not the sentence.
3. **Using creator biography as audience material.** Only use experiences allowed by audience and off-limits files.
4. **Making quiet copy.** Recognition must land quickly; explanation is not a substitute.
5. **Forgetting the sending action.** A plausible sender/receiver is part of the quality test.

## Verification Checklist

- [ ] Objective and source choice agree
- [ ] Each source has a named axis
- [ ] Wording and premise are materially new
- [ ] Branches are genuinely different
- [ ] Sender and receiver are concrete
- [ ] No experience or number was invented
- [ ] Audience, boundaries, applying rules, and anti-patterns were loaded
- [ ] User corrections were preserved verbatim
