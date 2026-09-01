---
name: instagram-performance-ideation
description: Use when a creator wants to connect Instagram API performance data to a repeatable idea-generation workflow. Fetches media and insights, ranks statistically useful source posts by the creator's chosen outcome, separates recent references from reusable older sources, adds image/content labels, removes duplicates, and turns winning mechanisms—not copied wording—into new ideas.
version: 1.0.0
author: tireddum-arch
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [instagram, analytics, content-strategy, ideation, creators]
    related_skills: [meme-llm-wiki, meme-writer, meme-collector]
---

# Instagram Performance Ideation

## Overview

Use Instagram performance as evidence for what to remake. The workflow is:

`API metrics → content labels → objective-specific ranking → diverse source pool → mechanism extraction → new ideas`

The key distinction is **source selection versus writing**. Metrics choose promising source posts. They do not explain why the post worked, and they must never be used as permission to copy the original wording.

The bundled script uses only Python's standard library. Read `references/data-schema.md` when adapting inputs.

## When to Use

Use this skill when:

- a creator has an Instagram professional account and wants ideas grounded in their own results;
- the goal can be named as an observable action such as shares, saves, follows, or interactions;
- image or video content needs labels because captions do not contain the actual hook;
- old winners should be rotated without repeating the same subject every run.

Do not use it when:

- there are too few posts to compare meaningfully;
- only public vanity metrics from someone else's account are available;
- the user wants to copy a competitor's post;
- the success objective has not been chosen.

## Inputs

Required:

1. `IG_ACCESS_TOKEN` for a professional account.
2. `IG_GRAPH_VERSION`, set to a currently supported Meta Graph API version such as `vXX.X`. Check Meta's current documentation instead of hard-coding an old version.
3. A primary metric that matches the content goal.

Recommended:

- `labels.json`, keyed by media ID, containing the text/hook inside the creative, topic, format, audience situation, and why it works;
- exclusions for paid partnerships, collaborations, giveaways, or posts that should not seed new ideas;
- `templates/brand-context.md`, completed with the creator's real audience, voice, boundaries, and lived experience.

Never commit access tokens, downloaded private analytics, or private media.

## Workflow

### 1. Define the outcome before fetching

Choose one primary action and, optionally, one secondary action:

| Goal | Primary rate | Useful secondary |
|---|---|---|
| Sendable/viral content | `shares / reach` | `follows / reach` |
| Reference/utility content | `saved / reach` | `shares / reach` |
| Audience growth | `follows / reach` | `shares / reach` |
| Conversation | `comments / reach` | `shares / reach` |

Do not rank by likes merely because likes are available. Completion criterion: one primary metric and its denominator are written down.

### 2. Fetch media and insights

From the skill directory:

```bash
export IG_ACCESS_TOKEN='...'
export IG_GRAPH_VERSION='vXX.X'
printf '%s\n' "$IG_ACCESS_TOKEN" | python3 scripts/instagram_ideation.py fetch \
  --token-stdin --output data/posts.json --cache data/posts.json
```

The token travels through stdin rather than process arguments or a script-level environment lookup.

The fetcher:

- paginates `/me/media`;
- asks for several insight metric sets, narrowing when a media type rejects a set;
- reuses cached metrics for old posts;
- preserves the previous output if media-list fetching fails;
- records metric errors instead of silently dropping posts.

Completion criterion: the command reports a non-zero media count and the output contains posts with `metrics.reach`.

### 3. Label what the audience actually saw

If the real hook is in the image/video, do not use the caption as a substitute. Create `data/labels.json` keyed by media ID:

```json
{
  "MEDIA_ID": {
    "content_text": "Exact visible hook or a faithful transcript",
    "topic": "short topic label",
    "format": "one-line / list / story / comparison",
    "situation": "audience situation",
    "mechanism": "why the reveal, contrast, number, rhythm, or identity cue works",
    "send_to": "who would send this to whom",
    "exclude": false
  }
}
```

Use vision/OCR if available, but visually verify small text. Preserve intentional spelling and line breaks when those are part of the creative. Set `exclude: true` for collaborations or non-repeatable campaign posts.

Completion criterion: every post eligible for the candidate pool has either a useful label or a caption that genuinely contains the content.

### 4. Rank reliable sources and separate recent references

```bash
python3 scripts/instagram_ideation.py rank \
  --posts data/posts.json \
  --labels data/labels.json \
  --primary shares \
  --secondary follows \
  --min-reach 3000 \
  --min-age-days 90 \
  --count 8 \
  --output data/candidates.json
```

Ranking uses percentile ranks so unlike rates can be combined. The default weighting is 2 parts primary to 1 part secondary. Low-reach posts are excluded because tiny denominators create unstable rates. Recent posts are separated as **tone/direction references**, not remake sources.

Tune `--min-reach` to the account rather than blindly keeping `3000`. A defensible first threshold is the lower quartile of reach among mature organic posts, with an absolute floor that prevents one or two actions from looking exceptional.

Completion criterion: `candidates` contains diverse older sources and `recent_reference` contains current-direction examples.

### 5. Build the ideation brief

```bash
python3 scripts/instagram_ideation.py prompt \
  --candidates data/candidates.json \
  --brand templates/brand-context.md \
  --wiki meme-wiki \
  --ideas-per-source 3 \
  --output data/ideation-brief.md
```

Read the brief, then generate ideas. For each selected source:

1. Name the **mechanism**: number, rhythm, identity cue, contrast, escalation, reveal position, useful specificity, or social sending situation.
2. Keep the mechanism.
3. Replace the subject, wording, examples, and scene.
4. Produce genuinely different branches, not synonyms.
5. State who would send each idea to whom.
6. Reject any idea that requires invented experience, invented results, or audience knowledge the creator does not have.

Completion criterion: every idea identifies its source mechanism, differs materially from the original, and has a plausible sender/receiver.

### 6. Rotate sources instead of exhausting one winner

Pass a used-ID file:

```bash
python3 scripts/instagram_ideation.py rank \
  --posts data/posts.json \
  --labels data/labels.json \
  --used data/used.json \
  --primary shares --secondary follows \
  --count 8 --output data/candidates.json
```

After choosing sources, store their IDs as a JSON array in `data/used.json`. When too few unused sources remain, the script reports `rotation_reset: true` and starts a new cycle. Do not mark candidates as used until ideas are actually accepted or published.

## Interpreting Results

- A high rate is a **selection signal**, not proof of causality.
- Compare like with like where possible: organic versus campaign, image versus reel, mature versus very recent.
- A post can be high-like and low-share. That is not a contradiction; it serves a different behavior.
- Recent winners show current taste but are often too fresh to remake.
- Repeated topic words can hide distinct mechanisms; deduplication is a guardrail, not final editorial judgment.

## Common Pitfalls

1. **Optimizing the wrong behavior.** Pick the metric from the goal, not from availability.
2. **Using raw counts only.** Large reach dominates. Rank rates and keep reach as a reliability floor.
3. **Trusting tiny samples.** A few shares on a few hundred reach can produce a misleading top rate.
4. **Reading captions instead of creatives.** Label image/video text and structure when that is where the idea lives.
5. **Mixing collaborations with organic posts.** Their audience and incentive structure differ; exclude or segment them.
6. **Copying the winner.** Preserve the mechanism, not the wording or exact premise.
7. **Making every branch the same.** Require different mechanisms or situations, not cosmetic rewrites.
8. **Hard-coding an API version forever.** Meta retires versions. Set `IG_GRAPH_VERSION` explicitly and update it from current docs.
9. **Committing secrets or private analytics.** Keep `.env`, `data/`, and downloaded media ignored.

## Verification Checklist

- [ ] The selected metric matches the stated content goal
- [ ] Fetch produced media and non-zero reach metrics
- [ ] API errors are visible and failed fetches do not erase the cache
- [ ] Low-reach and excluded posts are not candidates
- [ ] Recent posts are references, not remake sources
- [ ] Candidate topics are deduplicated
- [ ] Labels reflect the creative, not merely the caption
- [ ] Every proposed idea keeps a mechanism but replaces the expression
- [ ] No private data or token is tracked by git
