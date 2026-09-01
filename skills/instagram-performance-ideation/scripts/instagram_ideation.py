#!/usr/bin/env python3
"""Fetch Instagram insights and turn them into an evidence-based ideation brief."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

MEDIA_FIELDS = (
    "id,caption,media_type,media_product_type,media_url,thumbnail_url,"
    "permalink,timestamp,like_count,comments_count"
)
METRIC_SETS = [
    "reach,saved,shares,views,total_interactions,follows,profile_visits,likes,comments",
    "reach,saved,shares,views,total_interactions,likes,comments",
    "reach,saved,shares,views",
    "reach,saved,shares",
    "reach",
]
WORD_RE = re.compile(r"[^\W_]\w*", re.UNICODE)


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def load_json(path: str | Path | None, default: Any) -> Any:
    if not path:
        return default
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


def api_get(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        try:
            return json.load(error)
        except Exception:
            return {"error": {"message": f"HTTP {error.code}"}}
    except urllib.error.URLError as error:
        return {"error": {"message": str(error.reason)}}


def api_base(origin: str, version: str) -> str:
    clean_version = version.strip().strip("/")
    if not re.fullmatch(r"v\d+\.\d+", clean_version):
        raise ValueError("IG_GRAPH_VERSION must look like vXX.X and must be a currently supported version")
    return f"{origin.rstrip('/')}/{clean_version}"


def fetch_media(token: str, base: str, max_pages: int, page_size: int) -> list[dict[str, Any]] | None:
    output: list[dict[str, Any]] = []
    url = f"{base}/me/media"
    params: dict[str, Any] | None = {
        "fields": MEDIA_FIELDS,
        "limit": page_size,
        "access_token": token,
    }
    for _ in range(max_pages):
        result = api_get(url, params)
        if "error" in result:
            log("media fetch failed: " + result["error"].get("message", "unknown error"))
            return None
        output.extend(result.get("data", []))
        url = result.get("paging", {}).get("next", "")
        params = None
        if not url:
            break
        time.sleep(0.15)
    return output


def fetch_insights(token: str, base: str, media_id: str) -> tuple[dict[str, Any], str]:
    last_error = ""
    for metrics in METRIC_SETS:
        result = api_get(
            f"{base}/{media_id}/insights",
            {"metric": metrics, "access_token": token},
        )
        if "error" not in result and result.get("data"):
            values: dict[str, Any] = {}
            for item in result["data"]:
                raw = (item.get("values") or [{}])[0].get("value", 0)
                values[item["name"]] = raw if raw is not None else 0
            return values, ""
        if "error" in result:
            last_error = result["error"].get("message", "unknown error")[:300]
        else:
            last_error = "empty insights response"
    return {}, last_error


def parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def command_fetch(args: argparse.Namespace) -> int:
    token = os.getenv("IG_ACCESS_TOKEN", "").strip()
    version = args.api_version or os.getenv("IG_GRAPH_VERSION", "").strip()
    origin = args.api_origin or os.getenv("IG_API_ORIGIN", "https://graph.instagram.com")
    if not token:
        raise RuntimeError("IG_ACCESS_TOKEN is required")
    if not version:
        raise RuntimeError("IG_GRAPH_VERSION is required; choose a currently supported version from Meta docs")
    base = api_base(origin, version)

    media = fetch_media(token, base, args.max_pages, args.page_size)
    if media is None:
        log("existing cache/output was preserved")
        return 1
    if not media:
        log("API returned zero media")
        return 1

    cached_posts = load_json(args.cache, [])
    cached = {post.get("id"): post for post in cached_posts if post.get("id")}
    freeze_before = datetime.now(timezone.utc) - timedelta(days=args.metrics_fresh_days)
    output: list[dict[str, Any]] = []
    asked = reused = failed = 0

    for index, post in enumerate(media, 1):
        old = cached.get(post["id"], {})
        posted = parse_timestamp(post.get("timestamp"))
        frozen = posted is not None and posted < freeze_before
        if not args.force and frozen and old.get("metrics"):
            metrics = old["metrics"]
            metric_error = old.get("metrics_error", "")
            reused += 1
        else:
            metrics, metric_error = fetch_insights(token, base, post["id"])
            asked += 1
            failed += int(bool(metric_error))
            time.sleep(args.delay)

        output.append({
            "id": post["id"],
            "caption": post.get("caption") or "",
            "media_type": post.get("media_type") or "",
            "media_product_type": post.get("media_product_type") or "",
            "media_url": post.get("media_url") or "",
            "thumbnail_url": post.get("thumbnail_url") or "",
            "permalink": post.get("permalink") or "",
            "timestamp": post.get("timestamp") or "",
            "like_count": post.get("like_count") or 0,
            "comments_count": post.get("comments_count") or 0,
            "metrics": metrics,
            "metrics_error": metric_error,
        })
        if index % 50 == 0:
            log(f"fetched insights for {index}/{len(media)} posts")

    write_json(args.output, output)
    with_reach = sum(1 for post in output if numeric(post.get("metrics", {}).get("reach")) > 0)
    log(
        f"saved {len(output)} posts to {args.output}; insights asked={asked}, "
        f"cache reused={reused}, failures={failed}, with reach={with_reach}"
    )
    return 0 if with_reach else 2


def numeric(value: Any) -> float:
    if isinstance(value, bool):
        return float(value)
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def percentile_ranks(values: list[float]) -> list[float]:
    """Return stable 0..1 average ranks, including ties."""
    if not values:
        return []
    if len(values) == 1:
        return [1.0]
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    position = 0
    denominator = len(values) - 1
    while position < len(ordered):
        end = position + 1
        while end < len(ordered) and ordered[end][1] == ordered[position][1]:
            end += 1
        average_position = (position + end - 1) / 2
        for ordered_index in range(position, end):
            ranks[ordered[ordered_index][0]] = average_position / denominator
        position = end
    return ranks


def words(text: str) -> set[str]:
    return {word.casefold() for word in WORD_RE.findall(text) if len(word) > 1}


def source_text(post: dict[str, Any]) -> str:
    label = post.get("label", {})
    return (label.get("content_text") or post.get("caption") or "").strip()


def deduplicate(posts: list[dict[str, Any]], threshold: float) -> list[dict[str, Any]]:
    kept: list[dict[str, Any]] = []
    for post in posts:
        current = words(" ".join([
            source_text(post),
            str(post.get("label", {}).get("topic", "")),
            str(post.get("label", {}).get("situation", "")),
        ]))
        if not current:
            continue
        duplicate = False
        for existing in kept:
            other = words(" ".join([
                source_text(existing),
                str(existing.get("label", {}).get("topic", "")),
                str(existing.get("label", {}).get("situation", "")),
            ]))
            similarity = len(current & other) / max(len(current | other), 1)
            if similarity >= threshold:
                duplicate = True
                break
        if not duplicate:
            kept.append(post)
    return kept


def enrich_post(post: dict[str, Any], label: dict[str, Any], primary: str, secondary: str) -> dict[str, Any]:
    result = dict(post)
    result["label"] = label
    metrics = post.get("metrics", {})
    reach = numeric(metrics.get("reach"))
    result["reach"] = reach
    result["primary_count"] = numeric(metrics.get(primary))
    result["secondary_count"] = numeric(metrics.get(secondary)) if secondary else 0.0
    result["primary_rate"] = result["primary_count"] / max(reach, 1.0)
    result["secondary_rate"] = result["secondary_count"] / max(reach, 1.0)
    return result


def rank_posts(
    posts: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    used: set[str],
    primary: str,
    secondary: str,
    primary_weight: float,
    secondary_weight: float,
    min_reach: int,
    min_age_days: int,
    recent_count: int,
    count: int,
    pool_size: int,
    dedupe_threshold: float,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=min_age_days)
    enriched: list[dict[str, Any]] = []
    excluded = low_reach = unlabeled = 0

    for post in posts:
        label = labels.get(str(post.get("id")), {})
        if label.get("exclude"):
            excluded += 1
            continue
        item = enrich_post(post, label, primary, secondary)
        if not source_text(item):
            unlabeled += 1
            continue
        enriched.append(item)

    recent = [post for post in enriched if (parse_timestamp(post.get("timestamp")) or datetime.min.replace(tzinfo=timezone.utc)) >= cutoff]
    recent.sort(key=lambda post: post.get("timestamp", ""), reverse=True)
    recent = recent[:recent_count]

    mature: list[dict[str, Any]] = []
    for post in enriched:
        posted = parse_timestamp(post.get("timestamp"))
        if posted is None or posted >= cutoff:
            continue
        if post["reach"] < min_reach:
            low_reach += 1
            continue
        mature.append(post)

    primary_ranks = percentile_ranks([post["primary_rate"] for post in mature])
    secondary_ranks = percentile_ranks([post["secondary_rate"] for post in mature])
    for index, post in enumerate(mature):
        post["score"] = primary_ranks[index] * primary_weight
        if secondary:
            post["score"] += secondary_ranks[index] * secondary_weight
    mature.sort(key=lambda post: (-post["score"], -post["reach"]))
    pool = deduplicate(mature, dedupe_threshold)[:pool_size]

    fresh = [post for post in pool if str(post.get("id")) not in used]
    rotation_reset = len(fresh) < count and bool(used)
    chosen = (pool if rotation_reset else fresh)[:count]

    return {
        "objective": {
            "primary": primary,
            "secondary": secondary,
            "primary_weight": primary_weight,
            "secondary_weight": secondary_weight if secondary else 0,
            "denominator": "reach",
        },
        "candidates": chosen,
        "recent_reference": recent,
        "rotation_reset": rotation_reset,
        "stats": {
            "input_posts": len(posts),
            "excluded": excluded,
            "missing_content": unlabeled,
            "mature_below_min_reach": low_reach,
            "ranked_mature": len(mature),
            "deduplicated_pool": len(pool),
        },
    }


def command_rank(args: argparse.Namespace) -> int:
    posts = load_json(args.posts, [])
    labels = load_json(args.labels, {})
    used = set(load_json(args.used, []))
    if not posts:
        raise RuntimeError(f"no posts found in {args.posts}")
    result = rank_posts(
        posts=posts,
        labels=labels,
        used=used,
        primary=args.primary,
        secondary=args.secondary,
        primary_weight=args.primary_weight,
        secondary_weight=args.secondary_weight,
        min_reach=args.min_reach,
        min_age_days=args.min_age_days,
        recent_count=args.recent_count,
        count=args.count,
        pool_size=args.pool_size,
        dedupe_threshold=args.dedupe_threshold,
    )
    write_json(args.output, result)
    log(
        f"wrote {len(result['candidates'])} candidates and "
        f"{len(result['recent_reference'])} recent references to {args.output}"
    )
    return 0 if result["candidates"] else 2


def metric_line(post: dict[str, Any], objective: dict[str, Any]) -> str:
    primary = objective["primary"]
    secondary = objective.get("secondary")
    text = (
        f"reach {int(post.get('reach', 0)):,}; {primary} {int(post.get('primary_count', 0)):,} "
        f"({post.get('primary_rate', 0) * 100:.2f}%)"
    )
    if secondary:
        text += (
            f"; {secondary} {int(post.get('secondary_count', 0)):,} "
            f"({post.get('secondary_rate', 0) * 100:.2f}%)"
        )
    return text


def build_prompt(payload: dict[str, Any], brand: str, ideas_per_source: int) -> str:
    objective = payload.get("objective", {})
    lines = [
        "# Evidence-based Instagram ideation brief",
        "",
        "## Goal",
        f"Optimize for **{objective.get('primary', 'chosen action')} / reach**. "
        "Metrics select source posts; they do not prove causality.",
        "",
        "## Brand context",
        brand.strip() or "(Fill in the brand context before writing.)",
        "",
        "## Source posts",
    ]
    for index, post in enumerate(payload.get("candidates", []), 1):
        label = post.get("label", {})
        lines.extend([
            "",
            f"### Source {index} — media `{post.get('id', '')}`",
            f"- Performance: {metric_line(post, objective)}",
            f"- Date: {str(post.get('timestamp', ''))[:10]}",
            f"- Content: {source_text(post)}",
            f"- Topic: {label.get('topic', '')}",
            f"- Format: {label.get('format', '')}",
            f"- Situation: {label.get('situation', '')}",
            f"- Mechanism: {label.get('mechanism', '')}",
            f"- Sending situation: {label.get('send_to', '')}",
            f"- Link: {post.get('permalink', '')}",
        ])

    lines.extend(["", "## Recent references (tone/direction only; do not remake)"])
    for post in payload.get("recent_reference", []):
        lines.append(f"- {str(post.get('timestamp', ''))[:10]} — {source_text(post)}")

    lines.extend([
        "",
        "## Writing task",
        f"For each source, produce {ideas_per_source} materially different new ideas.",
        "",
        "For every idea include:",
        "1. **Kept mechanism** — the structural reason retained from the source.",
        "2. **New premise** — a different subject, examples, wording, and scene.",
        "3. **Draft** — a concise hook or copy draft appropriate to the format.",
        "4. **Send/save reason** — who acts on it and why.",
        "",
        "Reject copied wording, cosmetic paraphrases, invented experience, invented numbers, "
        "and ideas outside the stated audience or boundaries.",
    ])
    return "\n".join(lines) + "\n"


def load_wiki_text(path: str | None) -> str:
    """Load the shared Meme LLM Wiki without depending on another package."""
    if not path:
        return ""
    root = Path(path)
    ordered = [
        root / "brand" / "essence.md",
        root / "brand" / "audience.md",
        root / "brand" / "voice.md",
        root / "brand" / "off-limits.md",
        root / "brand" / "applying.md",
        root / "brand" / "anti-patterns.md",
    ]
    ordered += sorted((root / "formats").glob("*.md"))
    return "\n\n---\n\n".join(
        item.read_text(encoding="utf-8") for item in ordered if item.exists()
    )


def command_prompt(args: argparse.Namespace) -> int:
    payload = load_json(args.candidates, {})
    if not payload.get("candidates"):
        raise RuntimeError(f"no candidates found in {args.candidates}")
    brand_parts = []
    if args.brand:
        brand_parts.append(Path(args.brand).read_text(encoding="utf-8"))
    wiki = load_wiki_text(args.wiki)
    if wiki:
        brand_parts.append("# Meme LLM Wiki\n\n" + wiki)
    brand = "\n\n---\n\n".join(brand_parts)
    prompt = build_prompt(payload, brand, args.ideas_per_source)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(prompt, encoding="utf-8")
    log(f"wrote ideation brief to {target}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    fetch = commands.add_parser("fetch", help="fetch media and insights from Instagram API")
    fetch.add_argument("--output", required=True)
    fetch.add_argument("--cache", help="existing posts JSON whose old metrics may be reused")
    fetch.add_argument("--api-version", help="overrides IG_GRAPH_VERSION")
    fetch.add_argument("--api-origin", help="overrides IG_API_ORIGIN")
    fetch.add_argument("--metrics-fresh-days", type=int, default=120)
    fetch.add_argument("--page-size", type=int, default=100)
    fetch.add_argument("--max-pages", type=int, default=100)
    fetch.add_argument("--delay", type=float, default=0.12)
    fetch.add_argument("--force", action="store_true")
    fetch.set_defaults(func=command_fetch)

    rank = commands.add_parser("rank", help="rank and diversify source posts")
    rank.add_argument("--posts", required=True)
    rank.add_argument("--labels")
    rank.add_argument("--used")
    rank.add_argument("--primary", default="shares")
    rank.add_argument("--secondary", default="follows")
    rank.add_argument("--primary-weight", type=float, default=2.0)
    rank.add_argument("--secondary-weight", type=float, default=1.0)
    rank.add_argument("--min-reach", type=int, default=3000)
    rank.add_argument("--min-age-days", type=int, default=90)
    rank.add_argument("--recent-count", type=int, default=6)
    rank.add_argument("--count", type=int, default=8)
    rank.add_argument("--pool-size", type=int, default=40)
    rank.add_argument("--dedupe-threshold", type=float, default=0.45)
    rank.add_argument("--output", required=True)
    rank.set_defaults(func=command_rank)

    prompt = commands.add_parser("prompt", help="turn ranked candidates into an ideation brief")
    prompt.add_argument("--candidates", required=True)
    prompt.add_argument("--brand")
    prompt.add_argument("--wiki", help="Meme LLM Wiki directory to include in the brief")
    prompt.add_argument("--ideas-per-source", type=int, default=3)
    prompt.add_argument("--output", required=True)
    prompt.set_defaults(func=command_prompt)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        log(f"error: {error}")
        raise SystemExit(1)
