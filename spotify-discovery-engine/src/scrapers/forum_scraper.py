"""
Spotify Community Forum scraper using BeautifulSoup.
Targets community.spotify.com/Music-Discovery threads.
Falls back to mock data if blocked or unavailable.
"""
from __future__ import annotations

import json
import logging
import time
import random
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

FORUM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://community.spotify.com/",
}

FORUM_SEARCH_TERMS = [
    "discover weekly same songs",
    "echo chamber algorithm",
    "radio repeat loop",
    "recommendation stale",
    "discover weekly boring",
    "autoplay repeat",
]

BASE_URL = "https://community.spotify.com"
SEARCH_URL = f"{BASE_URL}/t5/forums/searchpage/tab/message?q={{query}}&search_type=thread"


def _throttle() -> None:
    time.sleep(random.uniform(2.0, 4.0))


def scrape_forum_search(query: str, session: requests.Session) -> list[dict]:
    """Scrape Spotify Community Forum search results."""
    results = []
    url = SEARCH_URL.format(query=query.replace(" ", "+"))

    try:
        _throttle()
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        threads = soup.select("div.lia-list-row, li.lia-component-search-result")
        for thread in threads[:20]:
            try:
                title_el = thread.select_one("a.lia-link-navigation, h3 a, .lia-message-subject a")
                author_el = thread.select_one("a.lia-user-name-link, .lia-user-name")
                body_el = thread.select_one("div.lia-truncated-body-text, .lia-message-body-content")
                time_el = thread.select_one("time, span.local-date")
                likes_el = thread.select_one("span.lia-kudos-count, .lia-kudos-display")

                title = title_el.get_text(strip=True) if title_el else ""
                author = author_el.get_text(strip=True) if author_el else "anonymous"
                body = body_el.get_text(strip=True) if body_el else title
                created = time_el.get("datetime", "") if time_el else ""
                likes = likes_el.get_text(strip=True) if likes_el else "0"
                post_url = title_el.get("href", "") if title_el else ""

                if not title:
                    continue

                results.append({
                    "id": f"forum_{len(results)}",
                    "source": "spotify_community",
                    "category": "Music & Discovery",
                    "author": author,
                    "title": title,
                    "body": body or title,
                    "likes": int(likes.replace(",", "")) if likes.replace(",", "").isdigit() else 0,
                    "replies": 0,
                    "created_at": created,
                    "url": f"{BASE_URL}{post_url}" if post_url.startswith("/") else post_url,
                    "scrape_strategy": "forum_html",
                })
            except Exception as e:
                logger.debug("Error parsing forum thread element: %s", e)

        logger.info("Forum scrape: %d threads for query '%s'", len(results), query)

    except requests.RequestException as e:
        logger.warning("Forum scrape failed for query '%s': %s", query, e)

    return results


def scrape_forum_category(category_path: str, session: requests.Session) -> list[dict]:
    """Scrape a specific Spotify Community category page."""
    results = []
    url = f"{BASE_URL}/t5/{category_path}/bd-p/en"

    try:
        _throttle()
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        threads = soup.select("li.lia-component-threadlist-widget-item, div.lia-message-view-wrapper")
        for thread in threads[:30]:
            try:
                title_el = thread.select_one("h2 a, h3 a, a.lia-link-navigation.lia-custom-event")
                author_el = thread.select_one("a.lia-user-name-link")
                body_el = thread.select_one("div.lia-truncated-body-text")
                likes_el = thread.select_one("span.lia-kudos-count")

                title = title_el.get_text(strip=True) if title_el else ""
                if not title:
                    continue

                results.append({
                    "id": f"forum_cat_{len(results)}",
                    "source": "spotify_community",
                    "category": "Music & Discovery",
                    "author": author_el.get_text(strip=True) if author_el else "anonymous",
                    "title": title,
                    "body": body_el.get_text(strip=True) if body_el else title,
                    "likes": int(likes_el.get_text(strip=True).replace(",", "")) if likes_el and likes_el.get_text(strip=True).replace(",", "").isdigit() else 0,
                    "replies": 0,
                    "created_at": "",
                    "url": f"{BASE_URL}{title_el.get('href', '')}" if title_el else "",
                    "scrape_strategy": "forum_category",
                })
            except Exception as e:
                logger.debug("Error parsing category thread: %s", e)

        logger.info("Forum category scrape: %d threads from %s", len(results), category_path)

    except requests.RequestException as e:
        logger.warning("Forum category scrape failed for %s: %s", category_path, e)

    return results


def load_mock_fallback() -> list[dict]:
    """Load pre-existing mock forum data."""
    mock_path = Path(__file__).parent.parent.parent / "data" / "raw" / "spotify_forums_raw.json"
    try:
        with open(mock_path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d records from mock forum fallback", len(data))
        return data
    except Exception as e:
        logger.error("Could not load mock forum data: %s", e)
        return []


def scrape_spotify_community(use_live: bool = False) -> list[dict]:
    """
    Main entry. Scrapes Spotify Community Forum for discovery-related discussions.
    Falls back to mock data if scraping fails.
    """
    if not use_live:
        logger.info("Using mock Spotify Community data (set use_live=True for live scraping)")
        return load_mock_fallback()

    session = requests.Session()
    session.headers.update(FORUM_HEADERS)
    all_results = []

    for query in FORUM_SEARCH_TERMS[:3]:
        results = scrape_forum_search(query, session)
        all_results.extend(results)

    for category in ["Music-Discovery-Tips", "Content-Questions", "Music-Discovery"]:
        results = scrape_forum_category(category, session)
        all_results.extend(results)

    if len(all_results) < 5:
        logger.warning("Forum live scraping insufficient, using mock data")
        return load_mock_fallback()

    seen = set()
    unique = []
    for r in all_results:
        key = r.get("title", "")[:80]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    logger.info("Forum scraping complete: %d unique threads collected", len(unique))
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = scrape_spotify_community(use_live=False)
    print(f"Collected {len(data)} forum posts")
