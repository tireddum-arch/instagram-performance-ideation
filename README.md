# Creator Meme Toolkit

A downloadable Hermes skill package that connects four parts of a creator workflow without mixing their data:

```text
Instagram API performance ──┐
                            ├─> source selection ─> meme writing
Approved external memes ─> Meme LLM Wiki ────────┘
```

## Included skills

| Skill | Purpose |
|---|---|
| `instagram-performance-ideation` | Fetch Instagram media/insights, rank reliable source posts, separate recent references, deduplicate topics, and create an ideation brief |
| `meme-llm-wiki` | Initialize and maintain audience, voice, boundaries, reusable formats, approved originals, and corrections |
| `meme-collector` | Handle `!밈`-style image/text submissions, propose a mechanism, and save only after explicit approval |
| `meme-writer` | Turn ranked owned posts or approved external formats into materially new copy using the shared wiki |

The user's owned Instagram data stays in `posts.json`/`labels.json`. Collected external memes stay in `meme-wiki/raw/memes.json`. They meet only as writing context.

## One-package install

```bash
git clone https://github.com/tireddum-arch/instagram-performance-ideation.git creator-meme-toolkit
cd creator-meme-toolkit
python3 install.py
```

For an existing install:

```bash
python3 install.py --force
```

The default destination is `$HERMES_HOME/skills/creator-meme-toolkit`, or `~/.hermes/skills/creator-meme-toolkit` when `HERMES_HOME` is unset. Use `--dest` for a profile-specific skills directory.

Start a new Hermes session or run `/reload-skills` after installation.

## Hermes Skills Hub tap

Hermes can discover the individual skills from this repository:

```bash
hermes skills tap add tireddum-arch/instagram-performance-ideation
hermes skills install tireddum-arch/instagram-performance-ideation/skills/meme-llm-wiki
hermes skills install tireddum-arch/instagram-performance-ideation/skills/meme-collector
hermes skills install tireddum-arch/instagram-performance-ideation/skills/meme-writer
hermes skills install tireddum-arch/instagram-performance-ideation/skills/instagram-performance-ideation
```

The clone-and-install route above is the single-package option.

## First run

Initialize the shared wiki in the creator's working directory:

```bash
python3 ~/.hermes/skills/creator-meme-toolkit/meme-llm-wiki/scripts/meme_wiki.py \
  init --wiki meme-wiki
```

Fill in the generated `meme-wiki/brand/*.md` files with real audience, voice, and boundaries before writing.

Configure Instagram access:

```bash
export IG_ACCESS_TOKEN='your-token'
export IG_GRAPH_VERSION='vXX.X'  # use a currently supported Meta version
```

Fetch and rank:

```bash
IG_SKILL=~/.hermes/skills/creator-meme-toolkit/instagram-performance-ideation
printf '%s\n' "$IG_ACCESS_TOKEN" | python3 "$IG_SKILL/scripts/instagram_ideation.py" fetch \
  --token-stdin --output data/posts.json --cache data/posts.json

python3 "$IG_SKILL/scripts/instagram_ideation.py" rank \
  --posts data/posts.json --labels data/labels.json \
  --primary shares --secondary follows \
  --min-reach 3000 --min-age-days 90 --count 8 \
  --output data/candidates.json

python3 "$IG_SKILL/scripts/instagram_ideation.py" prompt \
  --candidates data/candidates.json \
  --wiki meme-wiki \
  --output data/ideation-brief.md
```

Then ask Hermes to use `meme-writer` with the generated brief.

## `!밈` flow

1. Submit an image or text with `!밈` or “save this meme.”
2. `meme-collector` transcribes it and proposes a reusable mechanism.
3. The user approves or corrects the proposal.
4. Only after approval, `meme-llm-wiki` stores the raw example and updates its format.
5. Future writing loads the updated wiki.

This repository provides the workflow, not a hard-coded Slack slash command. Any Hermes gateway can treat `!밈` as a natural-language trigger when the `meme-collector` skill is installed.

## Privacy

- Never commit `IG_ACCESS_TOKEN` or private analytics.
- Instagram CDN URLs can expire; download only media the account owner is allowed to retain.
- Do not publish the generated `data/` or `meme-wiki/raw/` directories by default.
- The repository contains templates and synthetic examples only.

## Tests

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover \
  -s skills/instagram-performance-ideation/tests -v
```

## License

MIT
