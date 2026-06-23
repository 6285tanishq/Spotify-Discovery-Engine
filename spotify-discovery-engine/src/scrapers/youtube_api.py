"""
YouTube Data API v3 comment scraper.
Searches for videos about Spotify discovery issues and pulls comment threads.
Falls back to mock data on quota exceeded or API errors.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)

YT_API_KEY = "AIzaSyChosYLkHJuFI7qaLq3KMCZY7CEXEmINtU"
YT_BASE = "https://www.googleapis.com/youtube/v3"

SEARCH_QUERIES = [
    "spotify discover weekly same songs problem",
    "spotify echo chamber algorithm fix",
    "spotify recommendation loop",
    "why spotify radio repeats songs",
    "spotify discovery broken 2024",
    "spotify algorithm echo chamber review",
]

SENTIMENT_KEYWORDS_NEG = [
    "same songs", "echo chamber", "loop", "boring", "stale", "repetitive",
    "broken", "useless", "stuck", "repeat", "never changes", "disappointed",
    "frustrating", "worst", "hate", "terrible", "failed", "doesn't work",
]

SENTIMENT_KEYWORDS_POS = [
    "great", "love", "amazing", "perfect", "excellent", "fantastic",
    "best", "awesome", "good", "works well", "happy", "satisfied",
]


def _estimate_sentiment(text: str) -> float:
    text_lower = text.lower()
    neg = sum(1 for kw in SENTIMENT_KEYWORDS_NEG if kw in text_lower)
    pos = sum(1 for kw in SENTIMENT_KEYWORDS_POS if kw in text_lower)
    if neg == 0 and pos == 0:
        return -0.1
    total = neg + pos
    return round((pos - neg) / total, 2)


def search_videos(query: str, max_results: int = 5) -> list[str]:
    """Search YouTube for relevant videos, return video IDs."""
    params = {
        "part": "id",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "relevanceLanguage": "en",
        "order": "relevance",
        "key": YT_API_KEY,
    }
    try:
        resp = requests.get(f"{YT_BASE}/search", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return [item["id"]["videoId"] for item in data.get("items", [])]
    except Exception as e:
        logger.warning("YouTube search failed for '%s': %s", query, e)
        return []


def get_video_details(video_ids: list[str]) -> dict[str, dict]:
    """Fetch video titles and channel names for a list of video IDs."""
    if not video_ids:
        return {}
    params = {
        "part": "snippet",
        "id": ",".join(video_ids),
        "key": YT_API_KEY,
    }
    try:
        resp = requests.get(f"{YT_BASE}/videos", params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {
            item["id"]: {
                "title": item["snippet"]["title"],
                "channel": item["snippet"]["channelTitle"],
            }
            for item in data.get("items", [])
        }
    except Exception as e:
        logger.warning("YouTube video details failed: %s", e)
        return {}


def get_comments(video_id: str, video_title: str, channel: str, max_results: int = 50) -> list[dict]:
    """Fetch top-level comments from a video."""
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(max_results, 100),
        "order": "relevance",
        "key": YT_API_KEY,
    }
    results = []
    try:
        resp = requests.get(f"{YT_BASE}/commentThreads", params=params, timeout=10)
        if resp.status_code == 403:
            logger.warning("YouTube API quota exceeded or comments disabled for video %s", video_id)
            return results
        resp.raise_for_status()
        data = resp.json()

        for i, item in enumerate(data.get("items", [])):
            snippet = item["snippet"]["topLevelComment"]["snippet"]
            text = snippet.get("textDisplay", "")
            if len(text) < 50:
                continue

            sentiment = _estimate_sentiment(text)
            results.append({
                "id": f"yt_{video_id}_{i}",
                "source": "youtube",
                "video_id": video_id,
                "video_title": video_title,
                "channel": channel,
                "author": snippet.get("authorDisplayName", "anonymous"),
                "comment": text,
                "likes": snippet.get("likeCount", 0),
                "created_at": snippet.get("publishedAt", ""),
                "subscription_tier": "unknown",
                "sentiment_raw": sentiment,
            })

        logger.info("Fetched %d comments from video %s ('%s')", len(results), video_id, video_title[:50])

    except Exception as e:
        logger.warning("Comment fetch failed for video %s: %s", video_id, e)

    return results


def load_mock_fallback() -> list[dict]:
    """Load pre-existing mock YouTube data."""
    mock_path = Path(__file__).parent.parent.parent / "data" / "raw" / "youtube_raw.json"
    try:
        with open(mock_path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d records from mock YouTube fallback", len(data))
        return data
    except Exception as e:
        logger.error("Could not load mock YouTube data: %s", e)
        return []


def scrape_youtube_comments(use_live: bool = True, max_videos_per_query: int = 3, max_comments_per_video: int = 30) -> list[dict]:
    """
    Main entry. Searches YouTube for Spotify discovery videos and pulls comments.
    Automatically falls back to mock data if API fails.
    """
    if not use_live:
        logger.info("Using mock YouTube data")
        return load_mock_fallback()

    all_comments = []
    collected_video_ids = set()

    for query in SEARCH_QUERIES:
        video_ids = search_videos(query, max_results=max_videos_per_query)
        new_ids = [vid for vid in video_ids if vid not in collected_video_ids]

        if not new_ids:
            continue

        video_details = get_video_details(new_ids)
        collected_video_ids.update(new_ids)

        for vid_id in new_ids:
            details = video_details.get(vid_id, {"title": "Unknown", "channel": "Unknown"})
            comments = get_comments(vid_id, details["title"], details["channel"], max_comments_per_video)
            all_comments.extend(comments)

    if len(all_comments) < 10:
        logger.warning("YouTube live scraping insufficient (%d comments), falling back to mock", len(all_comments))
        return load_mock_fallback()

    logger.info("YouTube scraping complete: %d comments from %d videos", len(all_comments), len(collected_video_ids))
    return all_comments


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = scrape_youtube_comments(use_live=False)
    print(f"Collected {len(data)} YouTube comments")
