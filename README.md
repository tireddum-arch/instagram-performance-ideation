# Instagram Performance Ideation Skill

A reusable Hermes skill for turning a creator's own Instagram performance data into new content ideas.

It does **not** treat the most-liked post as the answer. It lets you choose the behavior you want—shares, saves, follows, or comments—then:

1. fetches media and insights through Instagram API;
2. joins metrics with labels describing what was actually inside the creative;
3. filters tiny samples, exclusions, and overly recent posts;
4. ranks source posts by outcome rate;
5. deduplicates repeated subjects and rotates used sources;
6. creates an ideation brief that preserves winning mechanisms without copying wording.

## Install as a Hermes skill

Clone this repository into your Hermes skills directory, or copy the repository directory there. Start a new Hermes session after installation so the skill index refreshes.

## Quick start

```bash
export IG_ACCESS_TOKEN='your-token'
export IG_GRAPH_VERSION='vXX.X'  # choose a currently supported Meta API version

python3 scripts/instagram_ideation.py fetch \
  --output data/posts.json --cache data/posts.json

cp examples/labels.example.json data/labels.json
# Replace the example with labels keyed by your real media IDs.

python3 scripts/instagram_ideation.py rank \
  --posts data/posts.json --labels data/labels.json \
  --primary shares --secondary follows \
  --min-reach 3000 --min-age-days 90 --count 8 \
  --output data/candidates.json

python3 scripts/instagram_ideation.py prompt \
  --candidates data/candidates.json \
  --brand templates/brand-context.md \
  --output data/ideation-brief.md
```

Then ask Hermes to use the brief to draft ideas. Full workflow and editorial rules are in [`SKILL.md`](SKILL.md).

## Privacy

`.gitignore` excludes `.env`, `data/`, downloaded media, tokens, and local output. The example data is synthetic and contains no account analytics.

## Requirements

- Python 3.10+
- Instagram professional account and valid access token
- A currently supported Instagram Graph API version
- No third-party Python packages

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT
