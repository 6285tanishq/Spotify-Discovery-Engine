"""
Reddit scraper with multi-strategy fallback:
1. Old Reddit HTML scraping (requests + BeautifulSoup)
2. Reddit search result scraping
3. Pushshift-style archive support
4. Graceful failure handling
"""
from __future__ import annotations

import json
import logging
import time
import random
from pathlib import Path
from datetime import datetime

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

DISCOVERY_KEYWORDS = [
    "recommendation loop", "stale music", "playing same songs",
    "autoplay repeat", "discover weekly echo chamber", "same songs",
    "echo chamber", "algorithmic loop", "recommendation stale",
    "discover weekly bad", "radio repeat", "stuck in loop",
    "feedback loop", "same playlist", "boring recommendations",
]

SUBREDDITS = [
    "spotify", "spotifymusic", "Music", "LetsTalkMusic",
    "audiophile", "indieheads", "hiphopheads",
]

TARGET_SEARCH_QUERIES = [
    "spotify discover weekly same songs",
    "spotify echo chamber algorithm",
    "spotify radio repeat loop",
    "spotify recommendation stale",
    "spotify algorithm broken discovery",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def _throttle(min_s: float = 1.5, max_s: float = 3.5) -> None:
    time.sleep(random.uniform(min_s, max_s))


def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def scrape_old_reddit_subreddit(subreddit: str, query: str, session: requests.Session, limit: int = 25) -> list[dict]:
    """Strategy 1: Old Reddit HTML scraping."""
    results = []
    url = f"https://old.reddit.com/r/{subreddit}/search?q={query}&restrict_sr=1&sort=relevance"

    try:
        _throttle()
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = soup.select("div.thing.link")[:limit]
        for post in posts:
            try:
                title_el = post.select_one("a.title")
                score_el = post.select_one("div.score.unvoted")
                author_el = post.select_one("a.author")
                time_el = post.select_one("time")

                title = title_el.get_text(strip=True) if title_el else ""
                score = score_el.get("title", "0") if score_el else "0"
                author = author_el.get_text(strip=True) if author_el else "unknown"
                created = time_el.get("datetime", "") if time_el else ""
                post_url = title_el.get("href", "") if title_el else ""

                if not title:
                    continue

                results.append({
                    "id": f"reddit_{subreddit}_{len(results)}",
                    "source": "reddit",
                    "subreddit": f"r/{subreddit}",
                    "author": author,
                    "title": title,
                    "body": title,
                    "score": int(score) if str(score).isdigit() else 0,
                    "num_comments": 0,
                    "created_utc": created,
                    "url": f"https://old.reddit.com{post_url}",
                    "scrape_strategy": "old_reddit_html",
                })
            except Exception as e:
                logger.debug("Error parsing Reddit post element: %s", e)

        logger.info("Strategy 1 (old Reddit): scraped %d posts from r/%s", len(results), subreddit)

    except requests.RequestException as e:
        logger.warning("Strategy 1 failed for r/%s: %s", subreddit, e)

    return results


def scrape_reddit_search(query: str, session: requests.Session, limit: int = 25) -> list[dict]:
    """Strategy 2: Reddit global search result scraping."""
    results = []
    url = f"https://old.reddit.com/search?q={query}&sort=relevance&t=year"

    try:
        _throttle()
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        posts = soup.select("div.thing.link")[:limit]
        for post in posts:
            try:
                title_el = post.select_one("a.title")
                author_el = post.select_one("a.author")
                subreddit_el = post.select_one("a.subreddit")
                time_el = post.select_one("time")

                title = title_el.get_text(strip=True) if title_el else ""
                author = author_el.get_text(strip=True) if author_el else "unknown"
                subreddit = subreddit_el.get_text(strip=True) if subreddit_el else "unknown"
                created = time_el.get("datetime", "") if time_el else ""

                if not title:
                    continue

                results.append({
                    "id": f"reddit_search_{len(results)}",
                    "source": "reddit",
                    "subreddit": subreddit,
                    "author": author,
                    "title": title,
                    "body": title,
                    "score": 0,
                    "num_comments": 0,
                    "created_utc": created,
                    "url": "",
                    "scrape_strategy": "reddit_search",
                })
            except Exception as e:
                logger.debug("Error parsing search result: %s", e)

        logger.info("Strategy 2 (Reddit search): scraped %d results for query '%s'", len(results), query)

    except requests.RequestException as e:
        logger.warning("Strategy 2 failed for query '%s': %s", query, e)

    return results


def scrape_pushshift_archive(subreddit: str, keyword: str) -> list[dict]:
    """Strategy 3: Pushshift-style archive fallback."""
    results = []
    pushshift_urls = [
        f"https://api.pushshift.io/reddit/search/submission/?subreddit={subreddit}&q={keyword}&size=25",
        f"https://arctic-shift.photon-reddit.com/api/posts/search?subreddit={subreddit}&q={keyword}&limit=25",
    ]

    for base_url in pushshift_urls:
        try:
            _throttle()
            resp = requests.get(base_url, timeout=10, headers=HEADERS)
            resp.raise_for_status()
            data = resp.json()

            posts = data.get("data", [])
            for post in posts:
                results.append({
                    "id": f"pushshift_{post.get('id', len(results))}",
                    "source": "reddit",
                    "subreddit": f"r/{subreddit}",
                    "author": post.get("author", "unknown"),
                    "title": post.get("title", ""),
                    "body": post.get("selftext", post.get("title", "")),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": datetime.fromtimestamp(post.get("created_utc", 0)).isoformat() if post.get("created_utc") else "",
                    "url": f"https://reddit.com{post.get('permalink', '')}",
                    "scrape_strategy": "pushshift_archive",
                })

            if results:
                logger.info("Strategy 3 (Pushshift): retrieved %d posts from r/%s", len(results), subreddit)
                return results

        except Exception as e:
            logger.debug("Pushshift URL %s failed: %s", base_url, e)

    logger.warning("Strategy 3 (Pushshift) failed for r/%s keyword '%s'", subreddit, keyword)
    return results


def load_mock_fallback() -> list[dict]:
    """Final fallback: load pre-existing mock Reddit data."""
    mock_path = Path(__file__).parent.parent.parent / "data" / "raw" / "reddit_raw.json"
    try:
        with open(mock_path, encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Loaded %d records from mock Reddit fallback", len(data))
        return data
    except Exception as e:
        logger.error("Could not load mock Reddit data: %s", e)
        return []


def scrape_reddit(use_live: bool = False) -> list[dict]:
    """
    Main entry point. Tries live scraping strategies in order,
    falls back to mock data if all fail or use_live=False.
    """
    if not use_live:
        logger.info("Using mock Reddit data (set use_live=True to attempt live scraping)")
        return load_mock_fallback()

    session = _get_session()
    all_results = []
    blocked = False

    for subreddit in SUBREDDITS[:3]:
        for query in TARGET_SEARCH_QUERIES[:2]:
            results = scrape_old_reddit_subreddit(subreddit, query, session)
            all_results.extend(results)
            if not results:
                blocked = True
                break
        if blocked:
            break

    if len(all_results) < 10:
        logger.warning("Strategy 1 insufficient, trying Strategy 2 (Reddit search)")
        for query in TARGET_SEARCH_QUERIES:
            results = scrape_reddit_search(query, session)
            all_results.extend(results)

    if len(all_results) < 10:
        logger.warning("Strategies 1+2 insufficient, trying Strategy 3 (Pushshift archive)")
        for subreddit in SUBREDDITS[:2]:
            results = scrape_pushshift_archive(subreddit, "discover weekly echo chamber")
            all_results.extend(results)

    if len(all_results) < 5:
        logger.warning("All live strategies failed or insufficient, falling back to mock data")
        return load_mock_fallback()

    seen = set()
    unique = []
    for r in all_results:
        key = r.get("title", "")[:80]
        if key not in seen:
            seen.add(key)
            unique.append(r)

    logger.info("Reddit scraping complete: %d unique posts collected", len(unique))
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data = scrape_reddit(use_live=False)
    print(f"Collected {len(data)} Reddit posts")
