# Created by Metrum AI for AMD

from __future__ import annotations

import html
import logging
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote_plus

import defusedxml.ElementTree as ET
import httpx
from app.config import settings
from app.db.models import Campaign, CircanaData
from app.providers.base import detect_product_vertical
from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

_MARKET_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "for",
    "with",
    "without",
    "from",
    "into",
    "onto",
    "over",
    "under",
    "this",
    "that",
    "these",
    "those",
    "deliver",
    "delivers",
    "delivering",
    "iconic",
    "original",
    "taste",
    "built",
    "designed",
    "made",
    "great",
    "best",
    "premium",
}

_VERTICAL_QUERY_MAP = {
    "beverage": {
        "news_terms": "soft drink beverage market trends",
        "reddit_terms": "soft drink soda cola consumer discussion",
        "fallback_terms": "cola beverage",
    },
    "gpu hardware": {
        "news_terms": "gpu hardware workstation ai market trends",
        "reddit_terms": "gpu workstation graphics card user discussion",
        "fallback_terms": "graphics card",
    },
    "ai software": {
        "news_terms": "ai software automation market trends",
        "reddit_terms": "ai software workflow user discussion",
        "fallback_terms": "ai automation",
    },
    "software platform": {
        "news_terms": "software platform saas market trends",
        "reddit_terms": "saas software workflow user discussion",
        "fallback_terms": "software platform",
    },
    "fashion beauty": {
        "news_terms": "beauty fashion consumer trends",
        "reddit_terms": "beauty product routine user discussion",
        "fallback_terms": "fashion beauty",
    },
    "automotive": {
        "news_terms": "automotive vehicle market trends",
        "reddit_terms": "vehicle ownership review user discussion",
        "fallback_terms": "automotive",
    },
    "financial services": {
        "news_terms": "fintech finance market trends",
        "reddit_terms": "banking fintech app user discussion",
        "fallback_terms": "financial services",
    },
    "health wellness": {
        "news_terms": "health wellness consumer trends",
        "reddit_terms": "health wellness routine user discussion",
        "fallback_terms": "health wellness",
    },
    "media entertainment": {
        "news_terms": "media entertainment audience trends",
        "reddit_terms": "media entertainment audience discussion",
        "fallback_terms": "media entertainment",
    },
    "sports fitness": {
        "news_terms": "fitness sports consumer trends",
        "reddit_terms": "fitness sports routine user discussion",
        "fallback_terms": "sports fitness",
    },
    "sustainability": {
        "news_terms": "sustainability green consumer trends",
        "reddit_terms": "sustainability eco consumer discussion",
        "fallback_terms": "green products",
    },
    "consumer product": {
        "news_terms": "consumer market trends",
        "reddit_terms": "consumer product user discussion",
        "fallback_terms": "consumer product",
    },
}

_TRACK_PRIORS = {
    "beverage": {
        "video": (
            0.85,
            "Highly visual consumer product with strong lifestyle/demo fit.",
        ),
        "audio_podcast": (
            0.35,
            "Usually weaker for audio-first discovery unless story-led.",
        ),
        "image_text": (
            0.65,
            "Static product and promo visuals still work well.",
        ),
    },
    "gpu hardware": {
        "video": (
            0.78,
            "Demos and visual performance storytelling fit the category.",
        ),
        "audio_podcast": (
            0.52,
            "Can work for explainers and technical conversations.",
        ),
        "image_text": (
            0.82,
            "Specs, comparisons, and static visuals are effective.",
        ),
    },
    "ai software": {
        "video": (
            0.62,
            "Demo-driven content can work when workflows are visual.",
        ),
        "audio_podcast": (
            0.58,
            "Explainer and thought-leadership formats can fit.",
        ),
        "image_text": (
            0.80,
            "Product-led screenshots and concise value props fit well.",
        ),
    },
    "software platform": {
        "video": (
            0.56,
            "Video can help but is not always the first-choice format.",
        ),
        "audio_podcast": (
            0.42,
            "Audio fit is usually secondary unless thought-leadership led.",
        ),
        "image_text": (
            0.84,
            "Image/text tends to fit platform and SaaS messaging best.",
        ),
    },
    "health wellness": {
        "video": (
            0.68,
            "Routine and benefit storytelling often works visually.",
        ),
        "audio_podcast": (
            0.70,
            "Educational and trust-based spoken content can work well.",
        ),
        "image_text": (
            0.60,
            "Static visuals help, but education often needs more context.",
        ),
    },
    "media entertainment": {
        "video": (
            0.88,
            "Entertainment categories strongly fit visual/high-motion formats.",
        ),
        "audio_podcast": (
            0.76,
            "Audio engagement is naturally aligned for this vertical.",
        ),
        "image_text": (0.50, "Static assets are useful but often secondary."),
    },
    "sports fitness": {
        "video": (
            0.84,
            "Motion, energy, and demonstration are strong visual drivers.",
        ),
        "audio_podcast": (0.55, "Audio can support coaching and motivation."),
        "image_text": (0.58, "Static assets are supportive, not primary."),
    },
    "consumer product": {
        "video": (
            0.65,
            "General products usually benefit from some visual storytelling.",
        ),
        "audio_podcast": (
            0.40,
            "Audio fit is less certain without stronger discussion signals.",
        ),
        "image_text": (
            0.62,
            "Image/text can support broad product promotion.",
        ),
    },
}

_VIDEO_TERMS = {
    "video",
    "youtube",
    "tiktok",
    "reel",
    "reels",
    "shorts",
    "viral",
    "watch",
    "demo",
    "commercial",
    "visual",
    "cinematic",
    "showcase",
}
_AUDIO_TERMS = {
    "podcast",
    "audio",
    "listen",
    "radio",
    "interview",
    "host",
    "spotify",
    "conversation",
    "spoken",
    "discussion",
    "storytelling",
}
_IMAGE_TEXT_TERMS = {
    "banner",
    "poster",
    "graphic",
    "display",
    "carousel",
    "headline",
    "copy",
    "image",
    "visuals",
    "packaging",
    "static",
    "infographic",
}

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_TECH_VERTICALS = frozenset(
    {"gpu hardware", "ai software", "software platform"}
)
_REDDIT_RSS_UA = (
    "AI-AdGenerator/1.0 (internal market snapshot; lightweight RSS)"
)


def _compact_words(text: str, limit: int = 8) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+._-]*", text or "")
    return " ".join(words[:limit])


def _strip_html_fragment(raw: str) -> str:
    s = html.unescape(raw or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return " ".join(s.split())[:800]


def _parse_reddit_atom(xml_text: str) -> list[dict]:
    posts: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return posts
    for entry in root.findall(f".//{_ATOM_NS}entry"):
        title_el = entry.find(f"{_ATOM_NS}title")
        title = (title_el.text or "").strip() if title_el is not None else ""
        content_el = entry.find(f"{_ATOM_NS}content")
        text = ""
        if content_el is not None:
            if content_el.text:
                text = _strip_html_fragment(content_el.text)
            if not text:
                text = _strip_html_fragment("".join(content_el.itertext()))
        cat = entry.find(f"{_ATOM_NS}category")
        sub = ""
        if cat is not None:
            sub = (cat.get("label") or cat.get("term") or "").strip()
            if sub.startswith("r/"):
                sub = sub[2:]
        if title:
            posts.append(
                {"title": title, "text": text, "subreddit": sub, "score": ""}
            )
    return posts


def _keyword_phrase(text: str, limit: int = 4) -> str:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9+._-]*", (text or "").lower())
    cleaned = []
    seen = set()
    for w in words:
        if w in _MARKET_STOPWORDS or len(w) < 3:
            continue
        if w in seen:
            continue
        seen.add(w)
        cleaned.append(w)
        if len(cleaned) >= limit:
            break
    return " ".join(cleaned)


def derive_market_queries(campaign) -> dict[str, str]:
    """Build search queries from campaign metadata."""
    brand_name = (
        campaign.brand.name if getattr(campaign, "brand", None) else ""
    ).strip()
    product_keywords = _keyword_phrase(
        campaign.product_description or "", limit=4
    )
    explicit_category = _compact_words(
        campaign.product_category or "", limit=4
    )
    combined_text = " ".join(
        p
        for p in [
            campaign.product_category or "",
            campaign.product_description or "",
        ]
        if p
    )
    vertical = detect_product_vertical(combined_text)
    broad_category = explicit_category or vertical
    vertical_cfg = _VERTICAL_QUERY_MAP.get(
        vertical, _VERTICAL_QUERY_MAP["consumer product"]
    )

    news_query = " ".join(
        p for p in [brand_name, vertical_cfg["news_terms"]] if p
    ).strip()
    reddit_query = " ".join(
        p for p in [brand_name, vertical_cfg["reddit_terms"]] if p
    ).strip()
    fallback_query = " ".join(
        p
        for p in [brand_name, product_keywords, vertical_cfg["fallback_terms"]]
        if p
    ).strip()

    return {
        "vertical": vertical,
        "broad_category": broad_category,
        "news_query": news_query[:180] or "consumer market trends",
        "reddit_query": reddit_query[:180]
        or "consumer product user discussion",
        "fallback_query": fallback_query or "consumer product",
    }


def _fetch_news(query: str, fallback_query: str = "") -> dict:
    if not settings.newsapi_key:
        return {"enabled": False, "headlines": [], "source": "newsapi"}

    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 5,
        "apiKey": settings.newsapi_key,
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        headlines = [
            {
                "title": a.get("title", ""),
                "source": (a.get("source") or {}).get("name", ""),
                "published_at": a.get("publishedAt", ""),
            }
            for a in data.get("articles", [])[:5]
            if a.get("title")
        ]
        if not headlines and fallback_query and fallback_query != query:
            return _fetch_news(fallback_query)
        return {
            "enabled": True,
            "headlines": headlines,
            "source": "newsapi",
            "query_used": query,
        }
    except Exception as exc:
        log.warning("NewsAPI fetch failed for '%s': %s", query, exc)
        return {
            "enabled": False,
            "headlines": [],
            "source": "newsapi",
            "error": str(exc),
        }


def _fetch_reddit_search_rss(query: str) -> dict:
    q = quote_plus(query.strip()[:300])
    url = f"https://www.reddit.com/search.rss?q={q}&limit=8&sort=relevance"
    try:
        with httpx.Client(timeout=12.0) as client:
            resp = client.get(url, headers={"User-Agent": _REDDIT_RSS_UA})
            resp.raise_for_status()
        posts = _parse_reddit_atom(resp.text)
        return {
            "enabled": bool(posts),
            "source": "reddit_rss",
            "query_used": query,
            "posts": posts,
        }
    except Exception as exc:
        log.warning("Reddit RSS fetch failed for '%s': %s", query, exc)
        return {
            "enabled": False,
            "source": "reddit_rss",
            "posts": [],
            "error": str(exc),
            "query_used": query,
        }


def _fetch_hacker_news(query: str) -> dict:
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": query, "tags": "story", "hitsPerPage": 6},
                headers={"User-Agent": _REDDIT_RSS_UA},
            )
            resp.raise_for_status()
            data = resp.json()
        posts = []
        for hit in data.get("hits") or []:
            title = (hit.get("title") or "").strip()
            if not title:
                continue
            link = (hit.get("url") or "").strip()
            posts.append(
                {
                    "title": title,
                    "text": link,
                    "subreddit": "Hacker News",
                    "score": str(hit.get("points") or ""),
                }
            )
        return {
            "enabled": bool(posts),
            "source": "hackernews",
            "query_used": query,
            "posts": posts,
        }
    except Exception as exc:
        log.warning("Hacker News fetch failed: %s", exc)
        return {
            "enabled": False,
            "source": "hackernews",
            "posts": [],
            "error": str(exc),
            "query_used": query,
        }


def _fetch_community_snapshot(query: str, vertical: str) -> dict:
    """
    Community-style text for track scoring: public Reddit search RSS, then
    Hacker News (Algolia) for tech-heavy verticals. No third-party proxies.
    """
    posts: list[dict] = []
    sources: list[str] = []

    rss_out = _fetch_reddit_search_rss(query)
    if rss_out.get("posts"):
        posts.extend(rss_out["posts"])
        sources.append("reddit_rss")

    if vertical in _TECH_VERTICALS:
        hn_out = _fetch_hacker_news(query)
        for p in hn_out.get("posts") or []:
            if len(posts) >= 10:
                break
            posts.append(p)
        if hn_out.get("posts"):
            sources.append("hackernews")

    src = "+".join(sources) if sources else "none"
    return {
        "enabled": bool(posts),
        "source": src,
        "query_used": query,
        "posts": posts[:10],
    }


def _score_track_signals(vertical: str, news: dict, community: dict) -> dict:
    priors = _TRACK_PRIORS.get(vertical, _TRACK_PRIORS["consumer product"])
    scores = {
        "video": priors["video"][0],
        "audio_podcast": priors["audio_podcast"][0],
        "image_text": priors["image_text"][0],
    }
    reasons = {
        "video": [priors["video"][1]],
        "audio_podcast": [priors["audio_podcast"][1]],
        "image_text": [priors["image_text"][1]],
    }

    text_blobs = []
    for item in news.get("headlines") or []:
        text_blobs.append(item.get("title", ""))
    for item in community.get("posts") or []:
        text_blobs.append(item.get("title", ""))
        text_blobs.append(item.get("text", ""))
    signal_text = " ".join(text_blobs).lower()

    def hits(terms: set[str]) -> int:
        return sum(1 for term in terms if term in signal_text)

    video_hits = hits(_VIDEO_TERMS)
    audio_hits = hits(_AUDIO_TERMS)
    image_hits = hits(_IMAGE_TEXT_TERMS)

    if video_hits:
        scores["video"] += min(0.18, video_hits * 0.03)
        reasons["video"].append(
            "Market signals contain visual/video-oriented discussion."
        )
    if audio_hits:
        scores["audio_podcast"] += min(0.18, audio_hits * 0.03)
        reasons["audio_podcast"].append(
            "Market signals contain spoken/audio-oriented discussion."
        )
    if image_hits:
        scores["image_text"] += min(0.15, image_hits * 0.025)
        reasons["image_text"].append(
            "Market signals mention static/graphic/packaging style content."
        )

    source_count = int(bool(news.get("headlines"))) + int(
        bool(community.get("posts"))
    )
    confidence = (
        "high"
        if source_count >= 2
        else "medium"
        if source_count == 1
        else "low"
    )

    result = {}
    for track, score in scores.items():
        score = max(0.0, min(1.0, round(score, 2)))
        result[track] = {
            "score": score,
            "recommended": score >= 0.55,
            "confidence": confidence,
            "reasons": reasons[track][:3],
        }
    return result


def fetch_market_data_payload(campaign) -> dict:
    """Fetch news, community, and track signals for the campaign."""
    queries = derive_market_queries(campaign)
    news = _fetch_news(
        queries["news_query"],
        fallback_query=queries["fallback_query"],
    )
    community = _fetch_community_snapshot(
        queries["reddit_query"], queries["vertical"]
    )
    track_signals = _score_track_signals(queries["vertical"], news, community)
    return {
        "query": queries["fallback_query"],
        "queries": queries,
        "news": news,
        "community": community,
        "reddit": community,
        "track_signals": track_signals,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }


def store_market_data(
    db: Session, campaign_id: str, campaign: Campaign, payload: dict
) -> CircanaData:
    """Persist a market data snapshot for a campaign."""
    queries = payload.get("queries") or {}
    row = CircanaData(
        campaign_id=uuid.UUID(campaign_id),
        product_category=campaign.product_category
        or queries.get("broad_category")
        or queries.get("vertical")
        or "consumer product",
        market_data=payload,
    )
    db.add(row)
    db.commit()
    return row


def latest_market_data(db, campaign_id: str) -> CircanaData | None:
    """Return the most recent market data row for a campaign."""
    return (
        db.execute(
            select(CircanaData)
            .where(CircanaData.campaign_id == uuid.UUID(campaign_id))
            .order_by(CircanaData.fetched_at.desc())
        )
        .scalars()
        .first()
    )


def build_market_context(payload: dict | None) -> str:
    """Format market data into a text block for LLM prompts."""
    if not payload:
        return ""

    lines = []
    queries = payload.get("queries") or {}
    if queries.get("vertical"):
        lines.append(f"Broad category: {queries['vertical']}")
    query = payload.get("query")
    if query:
        lines.append(f"Market query: {query}")

    news = (payload.get("news") or {}).get("headlines") or []
    if news:
        lines.append("Recent headlines:")
        for item in news[:3]:
            title = item.get("title", "").strip()
            source = item.get("source", "").strip()
            if title:
                lines.append(f"- {title}" + (f" ({source})" if source else ""))

    snap = payload.get("community") or payload.get("reddit") or {}
    posts = snap.get("posts") or []
    if posts:
        src = (snap.get("source") or "community").replace("_", " ")
        lines.append(f"Community snapshot ({src}):")
        for item in posts[:3]:
            title = item.get("title", "").strip()
            sub = item.get("subreddit", "").strip()
            if title:
                if sub == "Hacker News":
                    lines.append(f"- {title} (Hacker News)")
                elif sub:
                    lines.append(f"- {title} (r/{sub})")
                else:
                    lines.append(f"- {title}")

    track_signals = payload.get("track_signals") or {}
    if track_signals:
        lines.append("Track fit summary:")
        for track in ("video", "audio_podcast", "image_text"):
            info = track_signals.get(track) or {}
            lines.append(
                f"- {track}: score={info.get('score')}, "
                f"recommended={info.get('recommended')}, "
                f"confidence={info.get('confidence')}"
            )
            for reason in (info.get("reasons") or [])[:2]:
                lines.append(f"  reason: {reason}")

    return "\n".join(lines).strip()
